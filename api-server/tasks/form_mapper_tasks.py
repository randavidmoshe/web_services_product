# form_mapper_tasks.py
# Celery tasks for Form Mapper AI operations
# SCALABLE: Integrated with AI Budget Service for token tracking and limits
# 
# IMPORTANT: Each task calls orchestrator.process_celery_result() after completion
# to continue the state machine chain.

import os
import json
import logging
from celery_app import celery
from celery import shared_task
from typing import Dict, Optional, List
from services.ai_form_mapper_main_prompter import AIParseError

logger = logging.getLogger(__name__)


def _get_redis_client():
    """Get Redis client with connection pooling"""
    import redis
    pool = redis.ConnectionPool(
        host=os.getenv("REDIS_HOST", "redis"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=0,
        max_connections=50
    )
    return redis.Redis(connection_pool=pool)


def _get_db_session():
    """Get database session"""
    from models.database import SessionLocal
    return SessionLocal()


def _check_budget_and_get_api_key(db, company_id: int, product_id: int) -> str:
    """Check budget and get API key."""
    from services.ai_budget_service import get_budget_service, BudgetExceededError
    from models.database import CompanyProductSubscription
    
    redis_client = _get_redis_client()
    budget_service = get_budget_service(redis_client)
    
    has_budget, remaining, total = budget_service.check_budget(db, company_id, product_id)
    
    if not has_budget:
        raise BudgetExceededError(company_id, total, total - remaining)
    
    subscription = db.query(CompanyProductSubscription).filter(
        CompanyProductSubscription.company_id == company_id,
        CompanyProductSubscription.product_id == product_id
    ).first()
    
    if subscription and subscription.customer_claude_api_key:
        return subscription.customer_claude_api_key
    
    return os.getenv("ANTHROPIC_API_KEY")


def _record_usage(db, company_id: int, product_id: int, user_id: int, 
                  operation_type, input_tokens: int, output_tokens: int,
                  session_id: str = None):
    """Record AI usage after successful call"""
    from services.ai_budget_service import get_budget_service
    
    redis_client = _get_redis_client()
    budget_service = get_budget_service(redis_client)
    
    return budget_service.record_usage(
        db=db,
        company_id=company_id,
        product_id=product_id,
        user_id=user_id,
        operation_type=operation_type,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        session_id=session_id
    )


def _get_session_context(redis_client, session_id: str) -> Dict:
    """Get session context from Redis"""
    session_key = f"mapper_session:{session_id}"
    session_data = redis_client.hgetall(session_key)
    
    if not session_data:
        return {}
    
    decoded = {}
    for k, v in session_data.items():
        key_str = k.decode() if isinstance(k, bytes) else k
        val_str = v.decode() if isinstance(v, bytes) else v
        decoded[key_str] = val_str
    
    return {
        "company_id": int(decoded.get("company_id", 0)),
        "user_id": int(decoded.get("user_id", 0)),
        "product_id": int(decoded.get("product_id", 1)),
        "network_id": int(decoded.get("network_id", 0)),
        "form_route_id": int(decoded.get("form_route_id", 0))
    }


def _continue_orchestrator_chain(session_id: str, task_name: str, result: Dict):
    """
    Continue the orchestrator state machine after a Celery task completes.
    This chains Celery tasks together via the orchestrator.
    """
    from services.form_mapper_orchestrator import FormMapperOrchestrator
    from models.form_mapper_models import FormMapperSession

    db = _get_db_session()
    redis_client = _get_redis_client()

    try:
        # Check if session was cancelled while task was running
        session = db.query(FormMapperSession).filter(FormMapperSession.id == int(session_id)).first()
        if session and session.status in ['cancelled', 'cancelled_ack']:
            logger.info(f"[FormMapperTask] Session {session_id} was cancelled, skipping {task_name} result")
            return {"success": False, "cancelled": True}

        orchestrator = FormMapperOrchestrator(redis_client, db)
        response = orchestrator.process_celery_result(session_id, task_name, result)
        
        if response.get("trigger_celery") and response.get("celery_task"):
            next_task_name = response.get("celery_task")
            celery_args = response.get("celery_args", {})
            logger.info(f"[FormMapperTask] Chaining to next task: {next_task_name}")
            _trigger_celery_task(next_task_name, celery_args)
        
        if response.get("push_agent_task"):
            logger.info(f"[FormMapperTask] Agent task queued: {response.get('agent_task_type')}")
        
        return response

    except Exception as e:
        logger.error(f"[FormMapperTask] Orchestrator crashed in {task_name}: {e}", exc_info=True)
        sync_mapper_session_status.delay(session_id, "failed", f"Orchestrator error: {e}")
        return {"success": False, "error": str(e)}
        
    finally:
        db.close()


def _trigger_celery_task(task_name: str, celery_args: dict):
    """Trigger another Celery task by name"""
    task_map = {
        "analyze_form_page": analyze_form_page,
        "analyze_failure_and_recover": analyze_failure_and_recover,
        "handle_alert_recovery": handle_alert_recovery,
        "verify_ui_visual": verify_ui_visual,
        "regenerate_steps": regenerate_steps,
        "evaluate_paths_with_ai": evaluate_paths_with_ai,
        "save_mapping_result": save_mapping_result,
    }
    
    task = task_map.get(task_name)
    if task:
        task.delay(**celery_args)
    else:
        logger.error(f"[FormMapperTask] Unknown task: {task_name}")


# ============================================================================
# CELERY TASKS
# ============================================================================

def _build_junction_instructions_text(junction_instructions) -> str:
    """Build junction instructions text for AI prompt"""
    if not junction_instructions:
        return ""

    # Handle string (JSON) input
    if isinstance(junction_instructions, str):
        try:
            junction_instructions = json.loads(junction_instructions)
        except:
            return ""

    if not junction_instructions or not isinstance(junction_instructions, dict):
        return ""

    lines = ["For this path, you MUST select these specific options:"]
    for selector, value in junction_instructions.items():
        lines.append(f"- For field '{selector}': select '{value}'")
    lines.append("\nThese are required junction choices for this path.")
    return "\n".join(lines)

@shared_task(bind=True, max_retries=3, default_retry_delay=10, 
             autoretry_for=(Exception,), retry_backoff=True)
def analyze_form_page(
    self,
    session_id: str,
    dom_html: str,
    screenshot_base64: str,
    test_cases: list,
    current_path: int = 1,
    enable_junction_discovery: bool = True,
    max_junction_paths: int = 5,
    use_detect_fields_change: bool = True,
    enable_ui_verification: bool = True,
    critical_fields_checklist: dict = None,
    field_requirements: str = "",
    junction_instructions: dict = None,
    user_provided_inputs: dict = None
) -> Dict:
    """Celery task: Analyze form page with AI (initial step generation)."""
    from services.ai_budget_service import AIOperationType, BudgetExceededError
    
    logger.info(f"[FormMapperTask] Analyzing form page for session {session_id}")
    
    db = _get_db_session()
    redis_client = _get_redis_client()
    
    try:
        ctx = _get_session_context(redis_client, session_id)
        if ctx.get("company_id") is None or ctx.get("company_id") == 0:
            result = {"success": False, "error": "Session not found"}
            _continue_orchestrator_chain(session_id, "analyze_form_page", result)
            return result
        
        api_key = _check_budget_and_get_api_key(db, ctx["company_id"], ctx["product_id"])
        
        if not api_key:
            result = {"success": False, "error": "No API key available"}
            _continue_orchestrator_chain(session_id, "analyze_form_page", result)
            return result
        
        from services.form_mapper_ai_helpers import create_ai_helpers
        helpers = create_ai_helpers(api_key)
        
        ai_helper = helpers["form_mapper"]
        logger.info(f"[FormMapperTask] Screenshot size: {len(screenshot_base64) if screenshot_base64 else 0}")
        print(f"!!!! 🤖 Entering AI for Generating steps ...")
        print(f"!!!! Generating steps: screenshot size: {len(screenshot_base64) if screenshot_base64 else 0}")
        print(f"!!!! Generating steps: critical_fields_checklist: {critical_fields_checklist} steps")
        print(f"!!!! Generating steps: field_requirements: {field_requirements}")
        print(f"!!!! Generating steps: junction instructions: {junction_instructions}")
        print(f"!!!! Generating steps: test_cases: {test_cases}")
        ai_result = ai_helper.generate_test_steps(
            dom_html=dom_html,
            test_cases=test_cases,
            screenshot_base64=screenshot_base64,
            critical_fields_checklist=critical_fields_checklist or {},
            field_requirements=field_requirements or "",
            junction_instructions=_build_junction_instructions_text(
                junction_instructions) if junction_instructions else None,
            user_provided_inputs=user_provided_inputs or {},
            is_first_iteration=True
        )

        print(f"!!!!!!! ✅ AI Generated steps: {len(ai_result.get('steps', []))} new steps:")
        for s in ai_result.get('steps', []):
            print(f"    Step {s.get('step_number', '?')}: {s.get('action', '?')} | {(s.get('selector') or '')[:50]} | {s.get('description', '')[:40]}")
            if s.get('is_junction') or s.get('junction_info'):
                print(f"      -> is_junction: {s.get('is_junction')}, junction_info: {s.get('junction_info')}")
        
        input_tokens = len(dom_html) // 4 + (len(screenshot_base64) // 100 if screenshot_base64 else 0)
        output_tokens = len(json.dumps(ai_result)) // 4 if ai_result else 0
        
        _record_usage(
            db, ctx["company_id"], ctx["product_id"], ctx["user_id"],
            AIOperationType.FORM_MAPPER_ANALYZE,
            input_tokens, output_tokens, session_id
        )
        
        result = {
            "success": True,
            "steps": ai_result.get("steps", []),
            "no_more_paths": ai_result.get("no_more_paths", False),
            "form_fields": ai_result.get("form_fields", [])
        }
        


        _continue_orchestrator_chain(session_id, "analyze_form_page", result)
        return result
        
    except BudgetExceededError as e:
        logger.warning(f"[FormMapperTask] Budget exceeded for company {e.company_id}")
        result = {"success": False, "error": "AI budget exceeded", "budget_exceeded": True}
        _continue_orchestrator_chain(session_id, "analyze_form_page", result)
        return result

    except AIParseError as e:
        logger.error(f"[FormMapperTask] AI parse failed: {e}")
        result = {"success": False, "error": f"AI parse failed: {e}", "ai_parse_failed": True}
        _continue_orchestrator_chain(session_id, "analyze_form_page", result)
        return result

    except Exception as e:
        logger.error(f"[FormMapperTask] Analysis failed: {e}", exc_info=True)
        if self.request.retries >= self.max_retries:
            sync_mapper_session_status.delay(session_id, "failed", str(e))
        raise
        
    finally:
        db.close()


@shared_task(bind=True, max_retries=3, default_retry_delay=10,
             autoretry_for=(Exception,), retry_backoff=True)
def analyze_failure_and_recover(
    self,
    session_id: str,
    failed_step: Dict,
    executed_steps: List[Dict],
    fresh_dom: str,
    screenshot_base64: str,
    test_cases: List[Dict],
    test_context: Dict,
    attempt_number: int = 1,
    recovery_failure_history: List[Dict] = None
) -> Dict:
    """Celery task: AI analyzes step failure and generates recovery steps."""
    from services.ai_budget_service import AIOperationType, BudgetExceededError
    
    logger.info(f"[FormMapperTask] Analyzing failure for session {session_id}, attempt {attempt_number}")
    
    db = _get_db_session()
    redis_client = _get_redis_client()
    
    try:
        ctx = _get_session_context(redis_client, session_id)
        if ctx.get("company_id") is None or ctx.get("company_id") == 0:
            result = {"success": False, "error": "Session not found"}
            _continue_orchestrator_chain(session_id, "analyze_failure_and_recover", result)
            return result
        
        api_key = _check_budget_and_get_api_key(db, ctx["company_id"], ctx["product_id"])
        
        if not api_key:
            result = {"success": False, "error": "No API key available"}
            _continue_orchestrator_chain(session_id, "analyze_failure_and_recover", result)
            return result
        
        from services.form_mapper_ai_helpers import create_ai_helpers
        helpers = create_ai_helpers(api_key)
        
        ai_helper = helpers["form_mapper"]
        
        recovery_context = {
            "failed_step": failed_step,
            "attempt_number": attempt_number,
            "recovery_failure_history": recovery_failure_history or [],
            **(test_context or {})
        }

        print(f"!!!! 🤖 Regen remain steps errors and recover ...")
        print(f"!!!! ❌ FAILED STEP: {failed_step.get('step_number', '?')}: {failed_step.get('action', '?')} | {failed_step.get('selector', '')[:50]} | {failed_step.get('description', '')[:40]}")
        print(f"!!!! ❌ FAILED STEP ERROR: {recovery_failure_history[-1].get('error') if recovery_failure_history else 'Unknown'}")
        print(f"!!!! Regen remain steps errors and recover: screenshot size: {len(screenshot_base64) if screenshot_base64 else 0}")
        print(f"!!!! Regen remain steps errors and recover, Already executed: {len(executed_steps)} steps:")
        for s in executed_steps:
            print(f"    Step {s.get('step_number', '?')}: {s.get('action', '?')} | {(s.get('selector') or '')[:50]} | {s.get('description', '')[:40]}")
        print(f"!!!! Regen remain steps errors and recover, recovery_context: {recovery_context} steps")
        error_message = ""
        if recovery_failure_history:
            error_message = recovery_failure_history[-1].get('error', '')

        recovery_result = ai_helper.analyze_failure_and_recover(
            failed_step=failed_step,
            executed_steps=executed_steps,
            fresh_dom=fresh_dom,
            screenshot_base64=screenshot_base64,
            test_cases=test_cases,
            test_context=test_context,
            attempt_number=attempt_number,
            recovery_failure_history=recovery_failure_history,
            error_message=error_message
        )

        # Check if validation errors were detected
        if isinstance(recovery_result, dict) and recovery_result.get("validation_errors_detected"):
            print(f"[FormMapperTask] ⚠️ Validation errors detected - routing to validation error recovery")
            result = {
                "success": True,
                "validation_errors_detected": True,
                "recovery_steps": []
            }
            _continue_orchestrator_chain(session_id, "analyze_failure_and_recover", result)
            return result

        recovery_steps = recovery_result if isinstance(recovery_result, list) else []
        ai_result = {"steps": recovery_steps, "no_more_paths": False}

        print(
            f"!!!! ✅ Regenerated steps (errors and recover) : {len(ai_result.get('steps', []))} new steps:")
        for s in ai_result.get('steps', []):
            print(f"    Step {s.get('step_number', '?')}: {s.get('action', '?')} | {(s.get('selector') or '')[:50]} | {s.get('description', '')[:40]}")
        
        input_tokens = len(fresh_dom) // 4 + 500
        output_tokens = len(json.dumps(ai_result)) // 4 if ai_result else 0
        
        _record_usage(
            db, ctx["company_id"], ctx["product_id"], ctx["user_id"],
            AIOperationType.FORM_MAPPER_REGENERATE,
            input_tokens, output_tokens, session_id
        )
        
        result = {
            "success": True,
            "recovery_steps": ai_result.get("steps", []),
            "no_more_paths": ai_result.get("no_more_paths", False)
        }
        
        logger.info(f"[FormMapperTask] Recovery generated: {len(result.get('recovery_steps', []))} steps")
        for step in result.get('recovery_steps', []):
            logger.info(f"  Step: {step.get('action')} | {step.get('description')}")
            logger.info(f"    selector: {step.get('selector')}")

        _continue_orchestrator_chain(session_id, "analyze_failure_and_recover", result)
        return result
        
    except BudgetExceededError as e:
        result = {"success": False, "error": "AI budget exceeded", "budget_exceeded": True}
        _continue_orchestrator_chain(session_id, "analyze_failure_and_recover", result)
        return result
        
    except Exception as e:
        logger.error(f"[FormMapperTask] Failure analysis failed: {e}", exc_info=True)
        if self.request.retries >= self.max_retries:
            sync_mapper_session_status.delay(session_id, "failed", str(e))
        raise
        
    finally:
        db.close()


@shared_task(bind=True, max_retries=3, default_retry_delay=10,
             autoretry_for=(Exception,), retry_backoff=True)
def handle_alert_recovery(
    self,
    session_id: str,
    alert_info: Dict,
    executed_steps: List[Dict],
    dom_html: str,
    screenshot_base64: Optional[str],
    test_cases: List[Dict],
    test_context: Dict,
    step_where_alert_appeared: int,
    include_accept_step: bool = True,
    gathered_error_info: Optional[Dict] = None
) -> Dict:
    """Celery task: Handle alert/error recovery with AI."""
    from services.ai_budget_service import AIOperationType, BudgetExceededError
    
    logger.info(f"[FormMapperTask] Alert recovery for session {session_id}")
    
    db = _get_db_session()
    redis_client = _get_redis_client()
    
    try:
        ctx = _get_session_context(redis_client, session_id)
        if ctx.get("company_id") is None or ctx.get("company_id") == 0:
            result = {"success": False, "error": "Session not found"}
            _continue_orchestrator_chain(session_id, "handle_alert_recovery", result)
            return result
        
        api_key = _check_budget_and_get_api_key(db, ctx["company_id"], ctx["product_id"])
        
        if not api_key:
            result = {"success": False, "error": "No API key available"}
            _continue_orchestrator_chain(session_id, "handle_alert_recovery", result)
            return result
        
        from services.form_mapper_ai_helpers import create_ai_helpers
        helpers = create_ai_helpers(api_key)
        
        ai_recovery = helpers["alert_recovery"]
        print(f"!!!! 🤖 Regen remain steps for alert ...")
        last_step = executed_steps[-1] if executed_steps else {}
        print(f"!!!! ⚠️ Regen remain steps for alert, TRIGGERED AFTER STEP: {last_step.get('step_number', '?')}: {last_step.get('action', '?')} | {last_step.get('selector', '')[:50]} | {last_step.get('description', '')[:40]}")
        print(f"!!!! Regen remain steps for alert, Already executed: {executed_steps} steps")
        print(f"!!!! Regen remain steps for alert, gathered_error_info: {gathered_error_info} steps")

        ai_result = ai_recovery.regenerate_steps_after_alert(
            alert_info=alert_info,
            executed_steps=executed_steps,
            dom_html=dom_html,
            screenshot_base64=screenshot_base64,
            test_cases=test_cases,
            test_context=test_context,
            step_where_alert_appeared=step_where_alert_appeared,
            include_accept_step=include_accept_step,
            gathered_error_info=gathered_error_info
        )
        print(
            f"!!!! ✅ AI regenerate_steps (alert) returned {ai_result} new steps")


        input_tokens = len(dom_html) // 4 + 500
        output_tokens = len(json.dumps(ai_result)) // 4 if ai_result else 0
        
        _record_usage(
            db, ctx["company_id"], ctx["product_id"], ctx["user_id"],
            AIOperationType.FORM_MAPPER_ALERT_RECOVERY,
            input_tokens, output_tokens, session_id
        )

        if isinstance(ai_result, dict):
            result = {"success": True, **ai_result}
        else:
            # ai_result is a list or None - wrap it
            result = {"success": True, "steps": ai_result if ai_result else [], "scenario": "alert_recovery"}
        
        logger.info(f"[FormMapperTask] Alert recovery complete: scenario={ai_result.get('scenario', 'unknown')}")
        _continue_orchestrator_chain(session_id, "handle_alert_recovery", result)
        return result
        
    except BudgetExceededError as e:
        result = {"success": False, "error": "AI budget exceeded", "budget_exceeded": True}
        _continue_orchestrator_chain(session_id, "handle_alert_recovery", result)
        return result
        
    except Exception as e:
        logger.error(f"[FormMapperTask] Alert recovery failed: {e}", exc_info=True)
        if self.request.retries >= self.max_retries:
            sync_mapper_session_status.delay(session_id, "failed", str(e))
        raise
        
    finally:
        db.close()


@shared_task(bind=True, max_retries=3, default_retry_delay=10,
             autoretry_for=(Exception,), retry_backoff=True)
def handle_validation_error_recovery(
        self,
        session_id: str,
        executed_steps: List[Dict],
        dom_html: str,
        screenshot_base64: Optional[str],
        test_cases: List[Dict],
        test_context: Dict
):
    """Analyze validation errors (red borders, error messages) and determine if real_issue or ai_issue"""
    from services.ai_budget_service import AIOperationType, BudgetExceededError

    logger.info(f"[FormMapperTask] Validation error recovery for session {session_id}")

    db = _get_db_session()
    redis_client = _get_redis_client()

    try:
        ctx = _get_session_context(redis_client, session_id)
        if ctx.get("company_id") is None or ctx.get("company_id") == 0:
            result = {"success": False, "error": "Session not found"}
            _continue_orchestrator_chain(session_id, "handle_validation_error_recovery", result)
            return result

        api_key = _check_budget_and_get_api_key(db, ctx["company_id"], ctx["product_id"])
        if not api_key:
            result = {"success": False, "error": "No API key available"}
            _continue_orchestrator_chain(session_id, "handle_validation_error_recovery", result)
            return result

        from services.form_mapper_ai_helpers import create_ai_helpers
        helpers = create_ai_helpers(api_key)
        ai_recovery = helpers["alert_recovery"]

        print(f"!!!! 🔴 Analyzing validation errors...")

        ai_result = ai_recovery.analyze_validation_errors(
            executed_steps=executed_steps,
            dom_html=dom_html,
            screenshot_base64=screenshot_base64
        )

        print(f"!!!! ✅ AI validation error analysis returned: {ai_result}")

        input_tokens = len(dom_html) // 4 + 500
        output_tokens = len(json.dumps(ai_result)) // 4 if ai_result else 0

        _record_usage(
            db, ctx["company_id"], ctx["product_id"], ctx["user_id"],
            AIOperationType.FORM_MAPPER_ALERT_RECOVERY,
            input_tokens, output_tokens, session_id
        )

        result = {"success": True, **ai_result}

        logger.info(
            f"[FormMapperTask] Validation error recovery complete: issue_type={ai_result.get('issue_type', 'unknown')}")
        _continue_orchestrator_chain(session_id, "handle_validation_error_recovery", result)
        return result

    except BudgetExceededError as e:
        logger.warning(f"[FormMapperTask] Budget exceeded for validation error recovery: {e}")
        result = {"success": False, "error": "AI budget exceeded", "budget_exceeded": True}
        _continue_orchestrator_chain(session_id, "handle_validation_error_recovery", result)
        return result

    except Exception as e:
        logger.error(f"[FormMapperTask] Validation error recovery failed: {e}", exc_info=True)
        sync_mapper_session_status.delay(session_id, "failed", str(e))
        result = {"success": False, "error": str(e)}
        _continue_orchestrator_chain(session_id, "handle_validation_error_recovery", result)
        return result

    finally:
        db.close()



@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def verify_ui_visual(
    self,
    session_id: str,
    screenshot_base64: str,
    previously_reported_issues: Optional[List[str]] = None
) -> Dict:
    """Celery task: Visual UI verification with AI."""
    from services.ai_budget_service import AIOperationType, BudgetExceededError
    
    logger.info(f"[FormMapperTask] UI verification for session {session_id}")

    
    db = _get_db_session()
    redis_client = _get_redis_client()
    
    try:
        ctx = _get_session_context(redis_client, session_id)
        if ctx.get("company_id") is None or ctx.get("company_id") == 0:
            result = {"success": False, "error": "Session not found"}
            _continue_orchestrator_chain(session_id, "verify_ui_visual", result)
            return result
        
        api_key = _check_budget_and_get_api_key(db, ctx["company_id"], ctx["product_id"])
        
        if not api_key:
            result = {"success": False, "error": "No API key available"}
            _continue_orchestrator_chain(session_id, "verify_ui_visual", result)
            return result
        
        from services.form_mapper_ai_helpers import create_ai_helpers
        helpers = create_ai_helpers(api_key)
        
        ai_verifier = helpers["ui_verifier"]
        ui_issue = ai_verifier.verify_visual_ui(
            screenshot_base64=screenshot_base64,
            previously_reported_issues=previously_reported_issues
        )
        
        input_tokens = len(screenshot_base64) // 100 + 500
        output_tokens = len(ui_issue) // 4 if ui_issue else 0
        
        _record_usage(
            db, ctx["company_id"], ctx["product_id"], ctx["user_id"],
            AIOperationType.FORM_MAPPER_UI_VERIFY,
            input_tokens, output_tokens, session_id
        )
        
        result = {"success": True, "ui_issue": ui_issue}
        
        logger.info(f"[FormMapperTask] UI verification complete: {'issue found' if ui_issue else 'no issues'}")
        if ui_issue:
            logger.info(f"  UI Issue: {ui_issue[:150]}")
        _continue_orchestrator_chain(session_id, "verify_ui_visual", result)
        return result
        
    except BudgetExceededError as e:
        result = {"success": False, "error": "AI budget exceeded", "budget_exceeded": True}
        _continue_orchestrator_chain(session_id, "verify_ui_visual", result)
        return result
        
    except Exception as e:
        logger.error(f"[FormMapperTask] UI verification failed: {e}", exc_info=True)
        if self.request.retries >= self.max_retries:
            sync_mapper_session_status.delay(session_id, "failed", str(e))
        raise
        
    finally:
        db.close()


@shared_task(bind=True, max_retries=3, default_retry_delay=10,
             autoretry_for=(Exception,), retry_backoff=True)
def regenerate_steps(
    self,
    session_id: str,
    dom_html: str,
    executed_steps: List[Dict],
    test_cases: List[Dict],
    test_context: Dict,
    screenshot_base64: Optional[str] = None,
    critical_fields_checklist: Optional[Dict] = None,
    field_requirements: Optional[str] = None,
    enable_junction_discovery: bool = True,
    junction_instructions: str = None,
    user_provided_inputs: dict = None
) -> Dict:
    """Celery task: Regenerate remaining steps after DOM change."""
    from services.ai_budget_service import AIOperationType, BudgetExceededError
    
    logger.info(f"[FormMapperTask] Regenerating steps for session {session_id}")
    
    db = _get_db_session()
    redis_client = _get_redis_client()
    
    try:
        ctx = _get_session_context(redis_client, session_id)
        if ctx.get("company_id") is None or ctx.get("company_id") == 0:
            result = {"success": False, "error": "Session not found"}
            _continue_orchestrator_chain(session_id, "regenerate_steps", result)
            return result
        
        api_key = _check_budget_and_get_api_key(db, ctx["company_id"], ctx["product_id"])
        
        if not api_key:
            result = {"success": False, "error": "No API key available"}
            _continue_orchestrator_chain(session_id, "regenerate_steps", result)
            return result
        
        from services.form_mapper_ai_helpers import create_ai_helpers
        helpers = create_ai_helpers(api_key)
        
        ai_helper = helpers["form_mapper"]
        print(f"!!!! 🤖 Regen remain steps(regular)...")
        last_step = executed_steps[-1] if executed_steps else {}
        print(f"!!!! 🔄 Regen remain steps(regular), TRIGGERED BY STEP: {last_step.get('step_number', '?')}: {last_step.get('action', '?')} | {last_step.get('selector', '')[:50]} | {last_step.get('description', '')[:40]}")
        print(f"!!!! Regen remain steps(regular): screenshot size: {len(screenshot_base64) if screenshot_base64 else 0}")
        print(f"!!!! Regen remain steps(regular), Already executed: {len(executed_steps)} steps")
        for step in executed_steps:
            print(
                f"    Step {step.get('step_number', '?')}: {step.get('action', '?')} | {step.get('selector', '')[:50]} | {step.get('description', '')[:40]}")
        print(f"!!!! Regen remain steps(regular), critical_fields_checklist: {critical_fields_checklist} steps")
        print(f"!!!! Regen: junction instructions: {junction_instructions}")
        print(f"!!!! Regen remain steps(regular), field_requirements: {field_requirements} steps")
        ai_result = ai_helper.regenerate_steps(
            dom_html=dom_html,
            executed_steps=executed_steps,
            test_cases=test_cases,
            test_context=test_context,
            screenshot_base64=screenshot_base64,
            critical_fields_checklist=critical_fields_checklist,
            field_requirements=field_requirements,
            junction_instructions=_build_junction_instructions_text(junction_instructions),
            user_provided_inputs=user_provided_inputs or {}
        )
        print(f"!!!! ✅ AI regenerated_steps (regular): {len(ai_result.get('steps', []))} new steps:")
        for s in ai_result.get('steps', []):
            print(
                f"    Step {s.get('step_number', '?')}: {s.get('action', '?')} | {(s.get('selector') or '')[:50]} | {s.get('description', '')[:40]}")
            if s.get('is_junction') or s.get('junction_info'):
                print(f"      -> is_junction: {s.get('is_junction')}, junction_info: {s.get('junction_info')}")

        input_tokens = len(dom_html) // 4 + (len(screenshot_base64) // 100 if screenshot_base64 else 0)
        output_tokens = len(json.dumps(ai_result)) // 4 if ai_result else 0
        
        _record_usage(
            db, ctx["company_id"], ctx["product_id"], ctx["user_id"],
            AIOperationType.FORM_MAPPER_REGENERATE,
            input_tokens, output_tokens, session_id
        )

        result = {
            "success": True,
            "new_steps": ai_result.get("steps", []),
            "no_more_paths": ai_result.get("no_more_paths", False),
            "validation_errors_detected": ai_result.get("validation_errors_detected", False)
        }
        

        _continue_orchestrator_chain(session_id, "regenerate_steps", result)
        return result
        
    except BudgetExceededError as e:
        result = {"success": False, "error": "AI budget exceeded", "budget_exceeded": True}
        _continue_orchestrator_chain(session_id, "regenerate_steps", result)
        return result

    except AIParseError as e:
        logger.error(f"[FormMapperTask] AI parse failed: {e}")
        result = {"success": False, "error": f"AI parse failed: {e}", "ai_parse_failed": True}
        _continue_orchestrator_chain(session_id, "regenerate_steps", result)
        return result

    except Exception as e:
        logger.error(f"[FormMapperTask] Step regeneration failed: {e}", exc_info=True)
        if self.request.retries >= self.max_retries:
            sync_mapper_session_status.delay(session_id, "failed", str(e))
        raise
        
    finally:
        db.close()


@shared_task(bind=True, max_retries=3, default_retry_delay=10,
             autoretry_for=(Exception,), retry_backoff=True)
def regenerate_verify_steps(
        self,
        session_id: str,
        dom_html: str,
        executed_steps: List[Dict],
        test_cases: List[Dict],
        test_context: Dict,
        screenshot_base64: Optional[str] = None
) -> Dict:
    """Celery task: Regenerate verification steps after Save/Submit."""
    from services.ai_budget_service import AIOperationType, BudgetExceededError

    logger.info(f"[FormMapperTask] Regenerating VERIFY steps for session {session_id}")

    db = _get_db_session()
    redis_client = _get_redis_client()

    try:
        ctx = _get_session_context(redis_client, session_id)
        if ctx.get("company_id") is None or ctx.get("company_id") == 0:
            result = {"success": False, "error": "Session not found"}
            _continue_orchestrator_chain(session_id, "regenerate_verify_steps", result)
            return result

        api_key = _check_budget_and_get_api_key(db, ctx["company_id"], ctx["product_id"])

        if not api_key:
            result = {"success": False, "error": "No API key available"}
            _continue_orchestrator_chain(session_id, "regenerate_verify_steps", result)
            return result

        from services.form_mapper_ai_helpers import create_ai_helpers
        helpers = create_ai_helpers(api_key)

        ai_helper = helpers["form_mapper"]
        print(f"!!!! 🔍 Regen VERIFY steps...")
        last_step = executed_steps[-1] if executed_steps else {}
        print(
            f"!!!! 🔍 Regen VERIFY steps, TRIGGERED BY STEP: {last_step.get('step_number', '?')}: {last_step.get('action', '?')} | {last_step.get('selector', '')[:50]} | {last_step.get('description', '')[:40]}")
        print(f"!!!! Regen VERIFY steps: screenshot size: {len(screenshot_base64) if screenshot_base64 else 0}")
        print(f"!!!! Regen VERIFY steps, Already executed: {len(executed_steps)} steps")
        for step in executed_steps:
            print(
                f"    Step {step.get('step_number', '?')}: {step.get('action', '?')} | {step.get('selector', '')[:50]} | {step.get('description', '')[:40]}")

        ai_result = ai_helper.regenerate_verify_steps(
            dom_html=dom_html,
            executed_steps=executed_steps,
            test_cases=test_cases,
            test_context=test_context,
            screenshot_base64=screenshot_base64
        )

        new_steps = ai_result.get("steps", [])
        no_more_paths = ai_result.get("no_more_paths", False)

        # Log steps
        logger.warning(f"!!!! ✅ AI regenerated_verify_steps: {len(new_steps)} new steps:")
        for step in new_steps[:15]:
            desc = step.get('description', '')[:40]
            sel = step.get('selector', '')[:50]
            logger.warning(f"    Step {step.get('step_number')}: {step.get('action')} | {sel} | {desc}")

        logger.info(f"[FormMapperTask] Verify regeneration complete: {len(new_steps)} new steps")

        result = {
            "success": True,
            "new_steps": new_steps,
            "no_more_paths": no_more_paths,
            "validation_errors_detected": ai_result.get("validation_errors_detected", False)
        }
        _continue_orchestrator_chain(session_id, "regenerate_verify_steps", result)
        return result

    except BudgetExceededError as e:
        logger.warning(f"[FormMapperTask] Budget exceeded for verify regeneration: {e}")
        result = {"success": False, "error": "AI budget exceeded", "budget_exceeded": True}
        _continue_orchestrator_chain(session_id, "regenerate_verify_steps", result)
        return result

    except AIParseError as e:
        logger.error(f"[FormMapperTask] AI parse failed: {e}")
        result = {"success": False, "error": f"AI parse failed: {e}", "ai_parse_failed": True}
        _continue_orchestrator_chain(session_id, "regenerate_verify_steps", result)
        return result

    except Exception as e:
        logger.error(f"[FormMapperTask] Verify regeneration error: {e}", exc_info=True)
        sync_mapper_session_status.delay(session_id, "failed", str(e))
        result = {"success": False, "error": str(e)}
        _continue_orchestrator_chain(session_id, "regenerate_verify_steps", result)
        return result

    finally:
        db.close()


@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def evaluate_paths_with_ai(
        self,
        session_id: str,
        completed_paths: List[Dict],
        discover_all_combinations: bool = False,
        max_paths: int = 7
) -> Dict:
    """Celery task: Use AI to evaluate paths and determine next junction combination."""
    logger.info(f"[FormMapperTask] AI path evaluation for session {session_id}")
    print(f"!!!! 🤖 AI Path Evaluation for session {session_id}")
    print(f"!!!! Completed paths: {completed_paths}")
    print(f"!!!! Discover all combinations: {discover_all_combinations}")

    db = _get_db_session()
    redis_client = _get_redis_client()

    try:
        ctx = _get_session_context(redis_client, session_id)
        if ctx.get("company_id") is None or ctx.get("company_id") == 0:
            result = {"success": False, "error": "Session not found"}
            _continue_orchestrator_chain(session_id, "evaluate_paths_with_ai", result)
            return result

        api_key = _check_budget_and_get_api_key(db, ctx["company_id"], ctx["product_id"])

        if not api_key:
            result = {"success": False, "error": "No API key available"}
            _continue_orchestrator_chain(session_id, "evaluate_paths_with_ai", result)
            return result

        from services.form_mapper_ai_helpers import create_ai_helpers
        helpers = create_ai_helpers(api_key)
        ai_helper = helpers["form_mapper"]

        # Call AI to evaluate paths
        ai_result = ai_helper.evaluate_paths(
            completed_paths=completed_paths,
            discover_all_combinations=discover_all_combinations,
            max_paths=max_paths
        )

        print(f"!!!! ✅ AI Path Evaluation result: {ai_result}")
        logger.info(f"[FormMapperTask] AI path evaluation result: {ai_result}")

        # Record AI usage
        from services.ai_budget_service import AIOperationType
        _record_usage(
            db, ctx["company_id"], ctx["product_id"], ctx.get("user_id", 0),
            AIOperationType.FORM_MAPPER_REGENERATE,
            ai_result.get("tokens_used", 500) // 2,  # Approximate input tokens
            ai_result.get("tokens_used", 500) // 2,  # Approximate output tokens
            session_id
        )

        result = {
            "success": True,
            "all_paths_complete": ai_result.get("all_paths_complete", True),
            "next_path": ai_result.get("next_path", {}),
            "total_paths_estimated": ai_result.get("total_paths_estimated", 0),
            "reason": ai_result.get("reason", ""),
            "next_path_number": len(completed_paths) + 1
        }
        _continue_orchestrator_chain(session_id, "evaluate_paths_with_ai", result)
        return result

    except Exception as e:
        logger.error(f"[FormMapperTask] AI path evaluation error: {e}")
        print(f"!!!! ❌ AI Path Evaluation error: {e}")
        sync_mapper_session_status.delay(session_id, "failed", str(e))
        result = {"success": False, "error": str(e)}
        _continue_orchestrator_chain(session_id, "evaluate_paths_with_ai", result)
        return result
    finally:
        db.close()


@shared_task(bind=True, max_retries=2)
def save_mapping_result(self, session_id: str, stages: List[Dict], path_junctions: List[Dict], continue_to_next_path: bool = False):
    """Celery task: Organize stages and save FormMapResult to database."""
    from services.ai_budget_service import AIOperationType, BudgetExceededError

    logger.info(f"[FormMapperTask] Saving mapping result for session {session_id}")

    db = _get_db_session()
    redis_client = _get_redis_client()

    try:
        ctx = _get_session_context(redis_client, session_id)
        if ctx.get("company_id") is None or ctx.get("company_id") == 0:
            result = {"success": False, "error": "Session not found"}
            _continue_orchestrator_chain(session_id, "save_mapping_result", result)
            return result

        # Get test_cases from session context
        test_cases = ctx.get("test_cases", [])
        if isinstance(test_cases, str):
            test_cases = json.loads(test_cases) if test_cases else []

        api_key = _check_budget_and_get_api_key(db, ctx["company_id"], ctx["product_id"])

        if not api_key:
            result = {"success": False, "error": "No API key available"}
            _continue_orchestrator_chain(session_id, "save_mapping_result", result)
            return result

        from services.form_mapper_ai_helpers import create_ai_helpers
        helpers = create_ai_helpers(api_key)

        ai_end = helpers["end_prompter"]
        updated_stages = ai_end.organize_stages(
            stages=stages,
            test_cases=test_cases
        )

        input_tokens = len(json.dumps(stages)) // 4 + len(json.dumps(test_cases)) // 4
        output_tokens = len(json.dumps(updated_stages)) // 4 if updated_stages else 0

        _record_usage(
            db, ctx["company_id"], ctx["product_id"], ctx["user_id"],
            AIOperationType.FORM_MAPPER_END_ASSIGN,
            input_tokens, output_tokens, session_id
        )

        # Save FormMapResult to database
        from models.form_mapper_models import FormMapResult

        # Check how many paths already exist for this form_page_route
        form_page_route_id = ctx.get("form_route_id")
        existing_paths = db.query(FormMapResult).filter(
            FormMapResult.form_page_route_id == form_page_route_id
        ).count()

        form_map_result = FormMapResult(
            form_mapper_session_id=int(session_id),
            form_page_route_id=form_page_route_id,
            network_id=ctx.get("network_id"),
            company_id=ctx.get("company_id"),
            path_number=existing_paths + 1,
            path_junctions=path_junctions if path_junctions else [],
            steps=updated_stages if updated_stages else stages
        )

        db.add(form_map_result)
        db.commit()

        logger.info(
            f"[FormMapperTask] Saved FormMapResult id={form_map_result.id} for session {session_id}, path #{form_map_result.path_number}, {len(updated_stages or stages)} stages")

        result = {"stages": updated_stages, "success": True, "form_map_result_id": form_map_result.id, "continue_to_next_path": continue_to_next_path}
        _continue_orchestrator_chain(session_id, "save_mapping_result", result)
        return result

    except BudgetExceededError as e:
        result = {"success": False, "error": "AI budget exceeded", "budget_exceeded": True}
        _continue_orchestrator_chain(session_id, "save_mapping_result", result)
        return result

    except Exception as e:
        logger.error(f"[FormMapperTask] Save mapping result failed: {e}", exc_info=True)
        sync_mapper_session_status.delay(session_id, "failed", str(e))
        result = {"success": False, "error": str(e)}
        _continue_orchestrator_chain(session_id, "save_mapping_result", result)
        return result

    finally:
        db.close()


@shared_task(name="tasks.sync_mapper_session_status")
def sync_mapper_session_status(session_id: str, status: str, error: str = None):
    """Async task to sync mapper session status to DB"""
    db = _get_db_session()
    try:
        from models.form_mapper_models import FormMapperSession
        from datetime import datetime

        db_session = db.query(FormMapperSession).filter(
            FormMapperSession.id == int(session_id)
        ).first()

        if db_session:
            db_session.status = status
            if error:
                db_session.last_error = error
            if status in ("completed", "failed"):
                db_session.completed_at = datetime.utcnow()
            db.commit()
            logger.info(f"[MapperTasks] DB session {session_id} status -> {status}")
    except Exception as e:
        logger.error(f"[MapperTasks] Failed to sync DB session {session_id}: {e}")
        db.rollback()
    finally:
        db.close()

@shared_task(name="tasks.log_mapping_activity")
def log_mapping_activity(
    company_id: int,
    project_id: int,
    user_id: int,
    mapper_session_id: int,
    message: str,
    level: str = 'info',
    extra_data: dict = None
):
    """
    Async task to log mapping activity to activity_log_entries table.
    Fire-and-forget - does not block orchestrator.
    """
    db = _get_db_session()
    try:
        from models.database import ActivityLogEntry
        from datetime import datetime

        entry = ActivityLogEntry(
            company_id=company_id,
            project_id=project_id,
            user_id=user_id,
            activity_type="mapping",
            mapper_session_id=mapper_session_id,
            timestamp=datetime.utcnow(),
            level=level,
            category="milestone",
            message=message,
            extra_data=extra_data
        )
        db.add(entry)
        db.commit()
        logger.info(f"[MapperTasks] Logged activity: {message[:50]}...")
    except Exception as e:
        logger.error(f"[MapperTasks] Failed to log activity: {e}")
        db.rollback()
    finally:
        db.close()


@shared_task(name="tasks.cleanup_stale_mapper_sessions")
def cleanup_stale_mapper_sessions(timeout_hours: int = 2):
    """
    Periodic task to cleanup stale sessions.
    Marks sessions stuck in 'initializing' for too long as 'failed'.
    """
    db = _get_db_session()
    try:
        from models.form_mapper_models import FormMapperSession
        from datetime import datetime, timedelta

        cutoff = datetime.utcnow() - timedelta(hours=timeout_hours)

        stale_sessions = db.query(FormMapperSession).filter(
            FormMapperSession.status.in_(["initializing", "pending", "running"]),
            FormMapperSession.created_at < cutoff
        ).all()

        count = len(stale_sessions)
        for session in stale_sessions:
            session.status = "failed"
            session.last_error = f"Session timed out after {timeout_hours} hours"
            session.completed_at = datetime.utcnow()

        db.commit()
        logger.info(f"[MapperTasks] Cleaned up {count} stale sessions")
        return {"cleaned": count}
    except Exception as e:
        logger.error(f"[MapperTasks] Cleanup failed: {e}")
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()


def _cleanup_previous_mapping_results(db, form_page_route_id: int) -> int:
    """
    Delete all previous FormMapResult records for a form page route.
    This ensures a fresh start for junction discovery.

    Returns:
        Number of deleted records
    """
    from models.form_mapper_models import FormMapResult

    deleted_count = db.query(FormMapResult).filter(
        FormMapResult.form_page_route_id == form_page_route_id
    ).delete()

    logger.info(
        f"[FormMapperTask] Deleted {deleted_count} previous FormMapResult records for route {form_page_route_id}")
    return deleted_count


@shared_task(name="tasks.cancel_previous_sessions_for_route")
def cancel_previous_sessions_for_route(form_page_route_id: int, new_session_id: int):
    db = _get_db_session()
    try:
        from models.form_mapper_models import FormMapperSession
        from datetime import datetime
        import redis

        active_sessions = db.query(FormMapperSession).filter(
            FormMapperSession.form_page_route_id == form_page_route_id,
            FormMapperSession.id != new_session_id,
            FormMapperSession.status.in_(["initializing", "pending", "running"])
        ).all()
        count = len(active_sessions)
        user_id = None
        for session in active_sessions:
            session.status = "cancelled_ack"
            session.last_error = f"Cancelled - new session {new_session_id} started"
            session.completed_at = datetime.utcnow()
            user_id = session.user_id

        # Delete previous mapping results for fresh junction discovery
        deleted_paths = _cleanup_previous_mapping_results(db, form_page_route_id)

        db.commit()



        return {"cancelled": count, "deleted_paths": deleted_paths}
    except Exception as e:
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()