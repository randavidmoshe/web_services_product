# form_mapper_tasks_new_bad.py
# Celery tasks for Form Mapper AI operations
# SCALABLE: Integrated with AI Budget Service for token tracking and limits
# 
# IMPORTANT: Each task calls orchestrator.process_celery_result() after completion
# to continue the state machine chain.

import redis
import os
import json
from services.encryption_service import get_decrypted_api_key
import logging
from celery_app import celery
from celery import shared_task
from typing import Dict, Optional, List
from services.ai_form_mapper_main_prompter import AIParseError
from services.session_logger import SessionLogger, get_session_logger, ActivityType
from services.ai_budget_service import BudgetExceededError, AccessDeniedError
logger = logging.getLogger(__name__)


#def _get_redis_client():
#    """Get Redis client with connection pooling"""
#    import redis
#    pool = redis.ConnectionPool(
#        host=os.getenv("REDIS_HOST", "redis"),
#        port=int(os.getenv("REDIS_PORT", 6379)),
#        db=0,
#        max_connections=50
#    )
#    return redis.Redis(connection_pool=pool)

# Module-level shared connection pool — created ONCE per worker process, reused by all tasks
_redis_pool = redis.ConnectionPool(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=0,
    max_connections=50
)

def _get_redis_client():
    """Get Redis client from shared connection pool"""
    return redis.Redis(connection_pool=_redis_pool)


def _get_db_session():
    """Get database session"""
    from models.database import SessionLocal
    return SessionLocal()


def _check_budget_and_get_api_key(db, company_id: int, product_id: int) -> str:
    """Check budget and get API key."""
    from services.ai_budget_service import get_budget_service, BudgetExceededError, AccessDeniedError
    from models.database import CompanyProductSubscription
    
    redis_client = _get_redis_client()
    budget_service = get_budget_service(redis_client)
    
    has_budget, remaining, total = budget_service.check_budget(db, company_id, product_id)
    
    if not has_budget:
        raise BudgetExceededError(company_id, total, total - remaining)

    # Note: AccessDeniedError is raised automatically by check_budget()
    # for pending access, expired trial, missing API key, etc.

    subscription = db.query(CompanyProductSubscription).filter(
        CompanyProductSubscription.company_id == company_id,
        CompanyProductSubscription.product_id == product_id
    ).first()

    if subscription and subscription.customer_claude_api_key:
        # Decrypt the API key (uses Redis cache for performance)
        return get_decrypted_api_key(company_id, subscription.customer_claude_api_key)

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

    # Get company_name from Redis (stored at session creation by orchestrator)
    company_name = decoded.get("company_name")
    company_id = int(decoded.get("company_id", 0))

    return {
        "company_id": company_id,
        "user_id": int(decoded.get("user_id", 0)),
        "product_id": int(decoded.get("product_id", 1)),
        "network_id": int(decoded.get("network_id", 0)),
        "form_route_id": int(decoded.get("form_route_id", 0)),
        "company_name": company_name,
        "mapping_type": decoded.get("mapping_type", "form"),
        "test_case_description": decoded.get("test_case_description", ""),
        "test_page_route_id": int(decoded.get("test_page_route_id", 0)),
        "test_scenario_id": int(decoded.get("test_scenario_id", 0)) or None
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

        # Version check — discard stale task results
        try:
            dispatched_version_raw = redis_client.get(f"mapper_task_version:{session_id}")
            current_version_raw = redis_client.hget(f"mapper_session:{session_id}", "session_version")
            dispatched_version = int(dispatched_version_raw) if dispatched_version_raw else 0
            current_version = int(current_version_raw) if current_version_raw else 0
            if dispatched_version < current_version:
                logger.warning(
                    f"[FormMapperTask] Discarding stale {task_name} result for session {session_id} "
                    f"(task version {dispatched_version} < current {current_version})")
                return {"success": False, "stale": True}
        except Exception as e:
            logger.debug(f"[FormMapperTask] Version check skipped: {e}")

        orchestrator = FormMapperOrchestrator(redis_client, db)
        response = orchestrator.process_celery_result(session_id, task_name, result)
        
        if response.get("trigger_celery") and response.get("celery_task"):
            next_task_name = response.get("celery_task")
            celery_args = response.get("celery_args", {})
            countdown = response.get("celery_countdown")
            logger.info(f"[FormMapperTask] Chaining to next task: {next_task_name}")
            _trigger_celery_task(next_task_name, celery_args, countdown)
        
        if response.get("push_agent_task"):
            logger.info(f"[FormMapperTask] Agent task queued: {response.get('agent_task_type')}")
        
        return response

    except Exception as e:
        msg = f"!!!! ❌ Orchestrator crashed in {task_name}: {e}"
        print(msg)
        logger.error(f"[FormMapperTask] Orchestrator crashed in {task_name}: {e}", exc_info=True)
        if 'log' in locals():
            log.error(msg, category="error")
        sync_mapper_session_status.delay(session_id, "failed", f"Orchestrator error: {e}")
        return {"success": False, "error": str(e)}
        
    finally:
        db.close()


def _trigger_celery_task(task_name: str, celery_args: dict, countdown: int = None):
    """Trigger another Celery task by name"""
    task_map = {
        "analyze_form_page": analyze_form_page,
        "analyze_failure_and_recover": analyze_failure_and_recover,
        "handle_alert_recovery": handle_alert_recovery,
        "verify_ui_visual": verify_ui_visual,
        "regenerate_steps": regenerate_steps,
        "evaluate_paths_with_ai": evaluate_paths_with_ai,
        "evaluate_existing_paths": evaluate_existing_paths,
        "save_mapping_result": save_mapping_result,
        "verify_junction_visual": verify_junction_visual,
        "verify_page_visual": verify_page_visual,
        "verify_dynamic_step_visual": verify_dynamic_step_visual,
        "trigger_visual_page_screenshot": trigger_visual_page_screenshot,
    }

    task = task_map.get(task_name)
    if task:
        # Snapshot session version before dispatch (stale result detection)
        session_id = celery_args.get("session_id")
        if session_id:
            try:
                redis_client = _get_redis_client()
                version_raw = redis_client.hget(f"mapper_session:{session_id}", "session_version")
                version = int(version_raw) if version_raw else 0
                redis_client.set(f"mapper_task_version:{session_id}", version, ex=3600)
            except Exception:
                pass  # Non-critical — version check is defense-in-depth
        if countdown:
            task.apply_async(kwargs=celery_args, countdown=countdown)
        else:
            task.delay(**celery_args)
    else:
        msg = f"!!!! ❌ Unknown task: {task_name}"
        print(msg)
        logger.error(f"[FormMapperTask] Unknown task: {task_name}")
        # CloudWatch logging
        session_id = celery_args.get("session_id")
        if session_id:
            try:
                from services.session_logger import get_session_logger, ActivityType
                cw_log = get_session_logger(
                    db_session=None,
                    activity_type=ActivityType.MAPPING.value,
                    session_id=str(session_id),
                    company_id=None,
                    user_id=None
                )
                cw_log.error(msg, category="error")
            except:
                pass


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

    # Fetch screenshot from Redis (removed from Celery kwargs — P0 scalability fix)
    ss_raw = redis_client.get(f"mapper_screenshot:{session_id}")
    screenshot_base64 = ss_raw.decode() if isinstance(ss_raw, bytes) else (ss_raw or "")

    # Fetch DOM from Redis (removed from Celery kwargs — P0 scalability fix)
    dom_raw = redis_client.get(f"mapper_dom:{session_id}")
    dom_html = dom_raw.decode() if isinstance(dom_raw, bytes) else (dom_raw or "")
    
    try:
        ctx = _get_session_context(redis_client, session_id)
        if ctx.get("company_id") is None or ctx.get("company_id") == 0:
            result = {"success": False, "error": "Session not found"}
            _continue_orchestrator_chain(session_id, "analyze_form_page", result)
            return result
        
        api_key = _check_budget_and_get_api_key(db, ctx["company_id"], ctx["product_id"])

        # Structured logging
        log = get_session_logger(db_session=None, activity_type=ActivityType.MAPPING.value, session_id=session_id,
                                 company_id=ctx.get("company_id"), company_name=ctx.get("company_name"))
        log.info("Celery task: analyze_form_page started", category="celery_task")

        if not api_key:
            result = {"success": False, "error": "No API key available"}
            _continue_orchestrator_chain(session_id, "analyze_form_page", result)
            return result
        
        #from services.form_mapper_ai_helpers import create_ai_helpers
        from services.ai_helper_factory import generate_steps_for_mapping
        #helpers = create_ai_helpers(api_key, session_logger=log)
        
        #ai_helper = helpers["form_mapper"]
        logger.info(f"[FormMapperTask] Screenshot size: {len(screenshot_base64) if screenshot_base64 else 0}")
        msg = f"!!!! 🤖 Entering AI for Generating steps ..."
        print(msg)
        log.debug(msg, category="debug_trace")
        # Structured logging
        log.ai_call("generate_steps", prompt_size=len(str(dom_html or "")))
        msg = f"!!!! Generating steps: screenshot size: {len(screenshot_base64) if screenshot_base64 else 0}"
        print(msg)
        log.debug(msg, category="debug_trace")
        msg = f"!!!! Generating steps: critical_fields_checklist: {critical_fields_checklist} steps"
        print(msg)
        log.debug(msg, category="debug_trace")
        msg = f"!!!! Generating steps: field_requirements: {field_requirements}"
        print(msg)
        log.debug(msg, category="debug_trace")
        msg = f"!!!! Generating steps: junction instructions: {junction_instructions}"
        print(msg)
        log.debug(msg, category="debug_trace")
        msg = f"!!!! Generating steps: test_cases: {test_cases}"
        print(msg)
        log.debug(msg, category="debug_trace")

        # Login mapping: load credentials from DB (SECURITY: never in Redis/Celery kwargs)
        login_credentials = None
        mapping_type = ctx.get("mapping_type", "form")
        if mapping_type == "login_mapping" and ctx.get("network_id"):
            try:
                from models.database import Network
                from services.encryption_service import decrypt_credential
                network = db.query(Network).filter(Network.id == ctx["network_id"]).first()
                if network:
                    login_credentials = {
                        "username": decrypt_credential(network.login_username, network.company_id,
                               network.id, "login_username") if network.login_username else "", "password": decrypt_credential(network.login_password, network.company_id,
                               network.id, "login_password") if network.login_password else "", "site_url": network.url or "", "login_hints": network.login_hints or ""

                    }
                    log.debug(
                        f"!!!! Credentials loaded: username_len={len(login_credentials.get('username', ''))}, password_len={len(login_credentials.get('password', ''))}",
                        category="debug_trace")
            except Exception as e:
                logger.error(f"[FormMapperTask] Failed to load credentials: {e}")

        ai_result = generate_steps_for_mapping(
            mapping_type=mapping_type,
            api_key=api_key,
            session_logger=log,
            dom_html=dom_html,
            test_cases=test_cases,
            screenshot_base64=screenshot_base64,
            critical_fields_checklist=critical_fields_checklist or {},
            field_requirements=field_requirements or "",
            junction_instructions=_build_junction_instructions_text(
                junction_instructions) if junction_instructions else None,
            user_provided_inputs=user_provided_inputs or {},
            is_first_iteration=True,
            test_case_description=ctx.get("test_case_description", ""),
            login_credentials=login_credentials
        )

        #print(f"!!!!!!! ✅ AI Generated steps: {len(ai_result.get('steps', []))} new steps:")
        msg = f"!!!!!!! ✅ AI Generated steps: {len(ai_result.get('steps', []))} new steps:"
        print(msg)
        log.debug(msg, category="debug_trace")

        # Structured logging
        log.ai_response("generate_steps", success=True, tokens=ai_result.get('total_tokens', 0))
        log.debug(f"!!! AI Generated {len(ai_result.get('steps', []))} steps", category="ai_response",
                  steps_count=len(ai_result.get('steps', [])))
        for s in ai_result.get('steps', []):
            msg = f"    !!!! Step {s.get('step_number', '?')}: {s.get('action', '?')} | {(s.get('selector') or '')[:50]} | {s.get('description', '')[:40]} | field_name: {s.get('field_name', '')}"
            print(msg)
            log.debug(msg, category="debug_trace")
            if s.get('is_junction') or s.get('junction_info'):
                msg = f"      !!!! -> is_junction: {s.get('is_junction')}, junction_info: {s.get('junction_info')}"
                print(msg)
                log.debug(msg, category="debug_trace")
        
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
            "form_fields": ai_result.get("form_fields", []),
            "page_error_detected": ai_result.get("page_error_detected", False),
            "error_type": ai_result.get("error_type", ""),
            "already_logged_in": ai_result.get("already_logged_in", False),
            "login_failed": ai_result.get("login_failed", False),
            "error_message": ai_result.get("error_message", "")
        }
        


        _continue_orchestrator_chain(session_id, "analyze_form_page", result)
        return result
        
    except BudgetExceededError as e:
        logger.warning(f"[FormMapperTask] Budget exceeded for company {e.company_id}")
        result = {"success": False, "error": "AI budget exceeded", "budget_exceeded": True}
        _continue_orchestrator_chain(session_id, "analyze_form_page", result)
        return result

    except AccessDeniedError as e:
        result = {"success": False, "error": str(e), "access_denied": True}
        _continue_orchestrator_chain(session_id, "analyze_form_page", result)
        return result

    except AIParseError as e:
        msg = f"!!!! ❌ AI parse failed: {e}"
        print(msg)
        logger.error(f"[FormMapperTask] AI parse failed: {e}")
        if 'log' in locals():
            log.error(msg, category="error")
        result = {"success": False, "error": f"AI parse failed: {e}", "ai_parse_failed": True}
        _continue_orchestrator_chain(session_id, "analyze_form_page", result)
        return result

    except Exception as e:
        msg = f"!!!! ❌ Analysis failed: {e}"
        print(msg)
        logger.error(f"[FormMapperTask] Analysis failed: {e}", exc_info=True)
        if 'log' in locals():
            log.error(msg, category="error")
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

    # Fetch screenshot from Redis (removed from Celery kwargs — P0 scalability fix)
    ss_raw = redis_client.get(f"mapper_screenshot:{session_id}")
    screenshot_base64 = ss_raw.decode() if isinstance(ss_raw, bytes) else (ss_raw or "")

    # Fetch DOM from Redis (removed from Celery kwargs — P0 scalability fix)
    dom_raw = redis_client.get(f"mapper_dom:{session_id}")
    fresh_dom = dom_raw.decode() if isinstance(dom_raw, bytes) else (dom_raw or "")
    
    try:
        ctx = _get_session_context(redis_client, session_id)
        print(f"DEBUG: ctx company_name='{ctx.get('company_name')}' company_id={ctx.get('company_id')}")
        if ctx.get("company_id") is None or ctx.get("company_id") == 0:
            result = {"success": False, "error": "Session not found"}
            _continue_orchestrator_chain(session_id, "analyze_failure_and_recover", result)
            return result
        
        api_key = _check_budget_and_get_api_key(db, ctx["company_id"], ctx["product_id"])
        # Structured logging
        log = get_session_logger(db_session=None, activity_type=ActivityType.MAPPING.value, session_id=session_id,
                                 company_id=ctx.get("company_id"), company_name=ctx.get("company_name"))
        log.info(f"Celery task: analyze_failure_and_recover started (attempt {attempt_number})", category="celery_task")
        
        if not api_key:
            result = {"success": False, "error": "No API key available"}
            _continue_orchestrator_chain(session_id, "analyze_failure_and_recover", result)
            return result

        from services.ai_helper_factory import recover_from_failure_for_mapping
        #from services.form_mapper_ai_helpers import create_ai_helpers
        #helpers = create_ai_helpers(api_key, session_logger=log)

        #ai_helper = helpers["form_mapper"]
        
        recovery_context = {
            "failed_step": failed_step,
            "attempt_number": attempt_number,
            "recovery_failure_history": recovery_failure_history or [],
            **(test_context or {})
        }

        #print(f"!!!! 🤖 Regen remain steps errors and recover ...")
        msg = f"!!!! 🤖 Regen remain steps errors and recover ..."
        print(msg)
        log.debug(msg, category="debug_trace")

        # Structured logging
        log.ai_call("recovery_steps", prompt_size=len(str(fresh_dom or "")))
        log.debug(f"!!! Recovery: failed step {failed_step.get('step_number', '?')}: {failed_step.get('action', '?')}",
                  category="ai_call", failed_step=failed_step.get('step_number'),
                  executed_steps_count=len(executed_steps))


        msg = f"!!!! ❌ FAILED STEP: {failed_step.get('step_number', '?')}: {failed_step.get('action', '?')} | {failed_step.get('selector', '')[:50]} | {failed_step.get('description', '')[:40]}"
        print(msg)
        log.debug(msg, category="debug_trace")
        msg = f"!!!! ❌ FAILED STEP ERROR: {recovery_failure_history[-1].get('error') if recovery_failure_history else 'Unknown'}"
        print(msg)
        log.debug(msg, category="debug_trace")
        msg = f"!!!! Regen remain steps errors and recover: screenshot size: {len(screenshot_base64) if screenshot_base64 else 0}"
        print(msg)
        log.debug(msg, category="debug_trace")
        msg = f"!!!! Regen remain steps errors and recover, Already executed: {len(executed_steps)} steps:"
        print(msg)
        log.debug(msg, category="debug_trace")

        for s in executed_steps:
            msg = f"    !!!! Executed Step {s.get('step_number', '?')}: {s.get('action', '?')} | {(s.get('selector') or '')[:50]} | {s.get('description', '')[:40]} | field_name: {s.get('field_name', '')}"
            print(msg)
            log.debug(msg, category="debug_trace")
        #print(f"!!!! Regen remain steps errors and recover, recovery_context: {recovery_context} steps")
        msg = f"!!!! Regen remain steps errors and recover, recovery_context: {recovery_context} steps"
        print(msg)
        log.debug(msg, category="debug_trace")

        error_message = ""
        if recovery_failure_history:
            error_message = recovery_failure_history[-1].get('error', '')

        recovery_result = recover_from_failure_for_mapping(
            mapping_type=ctx.get("mapping_type", "form"),
            api_key=api_key,
            session_logger=log,
            failed_step=failed_step,
            executed_steps=executed_steps,
            fresh_dom=fresh_dom,
            screenshot_base64=screenshot_base64,
            test_cases=test_cases,
            test_context=test_context,
            attempt_number=attempt_number,
            recovery_failure_history=recovery_failure_history,
            error_message=error_message,
            test_case_description=ctx.get("test_case_description", "")
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

        # Check if page error was detected - fail session
        if isinstance(recovery_result, dict) and recovery_result.get("page_error_detected"):
            print(f"[FormMapperTask] ❌ Page error detected: {recovery_result.get('error_type')} - failing session")
            result = {
                "success": False,
                "page_error_detected": True,
                "error_type": recovery_result.get("error_type", "unknown")
            }
            _continue_orchestrator_chain(session_id, "analyze_failure_and_recover", result)
            return result


        recovery_steps = recovery_result if isinstance(recovery_result, list) else []
        ai_result = {"steps": recovery_steps, "no_more_paths": False}

        msg = f"!!!! ✅ Regenerated steps (errors and recover) : {len(ai_result.get('steps', []))} new steps:"
        print(msg)
        log.debug(msg, category="debug_trace")
        log.ai_response("recovery_steps", success=True)
        log.debug(f"!!! Recovery generated {len(ai_result.get('steps', []))} steps", category="ai_response",
                  steps_count=len(ai_result.get('steps', [])))
        for s in ai_result.get('steps', []):
            msg = f"    !!!! New Step {s.get('step_number', '?')}: {s.get('action', '?')} | {(s.get('selector') or '')[:50]} | {s.get('description', '')} | field_name: {s.get('field_name', '')}"
            print(msg)
            log.debug(msg, category="debug_trace")
            if s.get('is_junction') or s.get('junction_info'):
                msg = f"      !!!! -> is_junction: {s.get('is_junction')}, junction_info: {s.get('junction_info')}"
                print(msg)
                log.debug(msg, category="debug_trace")
        
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
            msg = f"    !!!! Recovery Step: {step.get('action')} | {step.get('selector', '')[:50]} | {step.get('description', '')[:40]} | field_name: {step.get('field_name', '')}"
            print(msg)
            log.debug(msg, category="debug_trace")

        _continue_orchestrator_chain(session_id, "analyze_failure_and_recover", result)
        return result
        
    except BudgetExceededError as e:
        result = {"success": False, "error": "AI budget exceeded", "budget_exceeded": True}
        _continue_orchestrator_chain(session_id, "analyze_failure_and_recover", result)
        return result

    except AccessDeniedError as e:
        result = {"success": False, "error": str(e), "access_denied": True}
        _continue_orchestrator_chain(session_id, "analyze_failure_and_recover", result)
        return result
        
    except Exception as e:
        msg = f"!!!! ❌ Failure analysis failed: {e}"
        print(msg)
        logger.error(f"[FormMapperTask] Failure analysis failed: {e}", exc_info=True)
        if 'log' in locals():
            log.error(msg, category="error")
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

    # Fetch screenshot from Redis (removed from Celery kwargs — P0 scalability fix)
    ss_raw = redis_client.get(f"mapper_screenshot:{session_id}")
    screenshot_base64 = ss_raw.decode() if isinstance(ss_raw, bytes) else (ss_raw or "")

    # Fetch DOM from Redis (removed from Celery kwargs — P0 scalability fix)
    dom_raw = redis_client.get(f"mapper_dom:{session_id}")
    dom_html = dom_raw.decode() if isinstance(dom_raw, bytes) else (dom_raw or "")
    
    try:
        ctx = _get_session_context(redis_client, session_id)
        if ctx.get("company_id") is None or ctx.get("company_id") == 0:
            result = {"success": False, "error": "Session not found"}
            _continue_orchestrator_chain(session_id, "handle_alert_recovery", result)
            return result
        
        api_key = _check_budget_and_get_api_key(db, ctx["company_id"], ctx["product_id"])
        # Structured logging
        log = get_session_logger(db_session=None, activity_type=ActivityType.MAPPING.value, session_id=session_id,
                                 company_id=ctx.get("company_id"), company_name=ctx.get("company_name"))
        log.info("Celery task: handle_alert_recovery started", category="celery_task")
        
        if not api_key:
            result = {"success": False, "error": "No API key available"}
            _continue_orchestrator_chain(session_id, "handle_alert_recovery", result)
            return result
        
        from services.form_mapper_ai_helpers import create_ai_helpers
        helpers = create_ai_helpers(api_key, session_logger=log)
        
        ai_recovery = helpers["alert_recovery"]
        #print(f"!!!! 🤖 Regen remain steps for alert ...")
        msg = f"!!!! 🤖 Regen remain steps for alert ..."
        print(msg)
        log.debug(msg, category="debug_trace")

        # Structured logging
        log.ai_call("alert_recovery", prompt_size=len(str(dom_html or "")))
        log.debug(f"!!! Alert recovery: {alert_info.get('alert_type', 'unknown')}",
                  category="ai_call", alert_type=alert_info.get('alert_type'))
        last_step = executed_steps[-1] if executed_steps else {}
        #print(f"!!!! ⚠️ Regen remain steps for alert, TRIGGERED AFTER STEP: {last_step.get('step_number', '?')}: {last_step.get('action', '?')} | {last_step.get('selector', '')[:50]} | {last_step.get('description', '')[:40]}")
        #print(f"!!!! Regen remain steps for alert, Already executed: {executed_steps} steps")
        #print(f"!!!! Regen remain steps for alert, gathered_error_info: {gathered_error_info} steps")
        msg = f"!!!! ⚠️ Regen remain steps for alert, TRIGGERED AFTER STEP: {last_step.get('step_number', '?')}: {last_step.get('action', '?')} | {last_step.get('selector', '')[:50]} | {last_step.get('description', '')[:40]}"
        print(msg)
        log.debug(msg, category="debug_trace")
        msg = f"!!!! Regen remain steps for alert, Already executed: {executed_steps} steps"
        print(msg)
        log.debug(msg, category="debug_trace")
        msg = f"!!!! Regen remain steps for alert, gathered_error_info: {gathered_error_info} steps"
        print(msg)
        log.debug(msg, category="debug_trace")

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
        msg = f"!!!! ✅ AI regenerate_steps (alert) returned {ai_result} new steps"
        print(msg)
        log.debug(msg, category="debug_trace")
        log.ai_response("alert_recovery", success=True)
        log.debug(
            f"!!! Alert recovery completed: scenario={ai_result.get('scenario') if isinstance(ai_result, dict) else 'list'}",
            category="ai_response")

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

    except AccessDeniedError as e:
        result = {"success": False, "error": str(e), "access_denied": True}
        _continue_orchestrator_chain(session_id, "handle_alert_recovery", result)
        return result
        
    except Exception as e:
        msg = f"!!!! ❌ Alert recovery failed: {e}"
        print(msg)
        logger.error(f"[FormMapperTask] Alert recovery failed: {e}", exc_info=True)
        if 'log' in locals():
            log.error(msg, category="error")
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
        test_cases: List[Dict],
        test_context: Dict
):
    """Analyze validation errors (red borders, error messages) and determine if real_issue or ai_issue"""
    from services.ai_budget_service import AIOperationType, BudgetExceededError

    logger.info(f"[FormMapperTask] Validation error recovery for session {session_id}")

    db = _get_db_session()
    redis_client = _get_redis_client()

    # Fetch screenshot from Redis (removed from Celery kwargs — P0 scalability fix)
    ss_raw = redis_client.get(f"mapper_screenshot:{session_id}")
    screenshot_base64 = ss_raw.decode() if isinstance(ss_raw, bytes) else (ss_raw or "")

    # Fetch DOM from Redis (removed from Celery kwargs — P0 scalability fix)
    dom_raw = redis_client.get(f"mapper_dom:{session_id}")
    dom_html = dom_raw.decode() if isinstance(dom_raw, bytes) else (dom_raw or "")

    try:
        ctx = _get_session_context(redis_client, session_id)
        if ctx.get("company_id") is None or ctx.get("company_id") == 0:
            result = {"success": False, "error": "Session not found"}
            _continue_orchestrator_chain(session_id, "handle_validation_error_recovery", result)
            return result

        api_key = _check_budget_and_get_api_key(db, ctx["company_id"], ctx["product_id"])
        # Structured logging
        log = get_session_logger(db_session=None, activity_type=ActivityType.MAPPING.value, session_id=session_id,
                                 company_id=ctx.get("company_id"), company_name=ctx.get("company_name"))
        log.info("Celery task: handle_validation_error_recovery started", category="celery_task")
        if not api_key:
            result = {"success": False, "error": "No API key available"}
            _continue_orchestrator_chain(session_id, "handle_validation_error_recovery", result)
            return result

        from services.form_mapper_ai_helpers import create_ai_helpers
        helpers = create_ai_helpers(api_key, session_logger=log)
        ai_recovery = helpers["alert_recovery"]

        #print(f"!!!! 🔴 Analyzing validation errors...")
        msg = f"!!!! 🔴 Analyzing validation errors prompter ..."
        print(msg)
        log.debug(msg, category="debug_trace")

        # Structured logging
        log.ai_call("validation_error_analysis", prompt_size=len(str(dom_html or "")))

        ai_result = ai_recovery.analyze_validation_errors(
            executed_steps=executed_steps,
            dom_html=dom_html,
            screenshot_base64=screenshot_base64
        )

        #print(f"!!!! ✅ AI validation error analysis returned: {ai_result}")
        msg = f"!*!*!*!!!*!  ✅ AI validation error analysis returned: {ai_result}"
        print(msg)
        log.debug(msg, category="debug_trace")

        # Structured logging
        log.ai_response("validation_error_analysis", success=True)
        log.debug(f"!!! Validation error analysis: issue_type={ai_result.get('issue_type', 'unknown')}",
                  category="ai_response")

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

    except AccessDeniedError as e:
        result = {"success": False, "error": str(e), "access_denied": True}
        _continue_orchestrator_chain(session_id, "handle_validation_error_recovery", result)
        return result

    except Exception as e:
        msg = f"!!!! ❌ Validation error recovery failed: {e}"
        print(msg)
        logger.error(f"[FormMapperTask] Validation error recovery failed: {e}", exc_info=True)
        if 'log' in locals():
            log.error(msg, category="error")
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
    previously_reported_issues: Optional[List[str]] = None
) -> Dict:
    """Celery task: Visual UI verification with AI."""
    from services.ai_budget_service import AIOperationType, BudgetExceededError
    
    logger.info(f"[FormMapperTask] UI verification for session {session_id}")

    
    db = _get_db_session()
    redis_client = _get_redis_client()

    # Fetch screenshot from Redis (removed from Celery kwargs — P0 scalability fix)
    ss_raw = redis_client.get(f"mapper_screenshot:{session_id}")
    screenshot_base64 = ss_raw.decode() if isinstance(ss_raw, bytes) else (ss_raw or "")
    
    try:
        ctx = _get_session_context(redis_client, session_id)
        if ctx.get("company_id") is None or ctx.get("company_id") == 0:
            result = {"success": False, "error": "Session not found"}
            _continue_orchestrator_chain(session_id, "verify_ui_visual", result)
            return result
        
        api_key = _check_budget_and_get_api_key(db, ctx["company_id"], ctx["product_id"])
        # Structured logging
        log = get_session_logger(db_session=None, activity_type=ActivityType.MAPPING.value, session_id=session_id,
                                 company_id=ctx.get("company_id"), company_name=ctx.get("company_name"))
        log.info("Celery task: verify_ui_visual started", category="celery_task")
        
        if not api_key:
            result = {"success": False, "error": "No API key available"}
            _continue_orchestrator_chain(session_id, "verify_ui_visual", result)
            return result
        
        #from services.form_mapper_ai_helpers import create_ai_helpers
        from services.ai_helper_factory import verify_visual_for_mapping
        #helpers = create_ai_helpers(api_key, session_logger=log)
        
        #ai_verifier = helpers["ui_verifier"]
        ui_issue = verify_visual_for_mapping(
            mapping_type=ctx.get("mapping_type", "form"),
            api_key=api_key,
            session_logger=log,
            screenshot_base64=screenshot_base64,
            previously_reported_issues=previously_reported_issues,
            test_case_description=ctx.get("test_case_description", "")
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

    except AccessDeniedError as e:
        result = {"success": False, "error": str(e), "access_denied": True}
        _continue_orchestrator_chain(session_id, "verify_ui_visual", result)
        return result
        
    except Exception as e:
        msg = f"!!!! ❌ UI verification failed: {e}"
        print(msg)
        logger.error(f"[FormMapperTask] UI verification failed: {e}", exc_info=True)
        if 'log' in locals():
            log.error(msg, category="error")
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
    executed_steps: List[Dict],
    test_cases: List[Dict],
    test_context: Dict,
    critical_fields_checklist: Optional[Dict] = None,
    field_requirements: Optional[str] = None,
    enable_junction_discovery: bool = True,
    junction_instructions: str = None,
    user_provided_inputs: dict = None,
    regenerate_retry_message: str = ""
) -> Dict:
    """Celery task: Regenerate remaining steps after DOM change."""
    from services.ai_budget_service import AIOperationType, BudgetExceededError
    
    logger.info(f"[FormMapperTask] Regenerating steps for session {session_id}")
    
    db = _get_db_session()
    redis_client = _get_redis_client()

    # Fetch screenshot from Redis (removed from Celery kwargs — P0 scalability fix)
    ss_raw = redis_client.get(f"mapper_screenshot:{session_id}")
    screenshot_base64 = ss_raw.decode() if isinstance(ss_raw, bytes) else (ss_raw or "")

    # Fetch DOM from Redis (removed from Celery kwargs — P0 scalability fix)
    dom_raw = redis_client.get(f"mapper_dom:{session_id}")
    dom_html = dom_raw.decode() if isinstance(dom_raw, bytes) else (dom_raw or "")
    
    try:
        ctx = _get_session_context(redis_client, session_id)
        if ctx.get("company_id") is None or ctx.get("company_id") == 0:
            result = {"success": False, "error": "Session not found"}
            _continue_orchestrator_chain(session_id, "regenerate_steps", result)
            return result
        
        api_key = _check_budget_and_get_api_key(db, ctx["company_id"], ctx["product_id"])

        # Structured logging
        log = get_session_logger(db_session=None, activity_type=ActivityType.MAPPING.value, session_id=session_id,
                                 company_id=ctx.get("company_id"), company_name=ctx.get("company_name"))
        log.info("Celery task: regenerate_steps started", category="celery_task")
        
        if not api_key:
            result = {"success": False, "error": "No API key available"}
            _continue_orchestrator_chain(session_id, "regenerate_steps", result)
            return result
        from services.ai_helper_factory import regenerate_steps_for_mapping
        #from services.form_mapper_ai_helpers import create_ai_helpers
        #helpers = create_ai_helpers(api_key, session_logger=log)
        
        #ai_helper = helpers["form_mapper"]
        #print(f"!!!! 🤖 Regen remain steps(regular)...")
        msg = f"!!!! 🤖 Regen remain steps(regular)..."
        print(msg)
        log.debug(msg, category="debug_trace")

        # Structured logging
        log.ai_call("regenerate_steps", prompt_size=len(str(dom_html or "")))
        log.debug(f"!!! Regenerate steps: {len(executed_steps)} already executed",
                  category="ai_call", executed_steps_count=len(executed_steps))


        last_step = executed_steps[-1] if executed_steps else {}

        msg = f"!!!!!!!!!!!!!!! 🔄 Regen remain steps(regular), TRIGGERED BY STEP: {last_step.get('step_number', '?')}: {last_step.get('action', '?')} | {last_step.get('selector', '')[:50]} | {last_step.get('description', '')[:40]}"
        print(msg)
        log.debug(msg, category="debug_trace")
        msg = f"!!!! Regen remain steps(regular): screenshot size: {len(screenshot_base64) if screenshot_base64 else 0}"
        print(msg)
        log.debug(msg, category="debug_trace")
        msg = f"!!!! Regen remain steps(regular), Already executed: {len(executed_steps)} steps"
        print(msg)
        log.debug(msg, category="debug_trace")

        for step in executed_steps:
            msg = f"    !!!! Executed Step {step.get('step_number', '?')}: {step.get('action', '?')} | {(step.get('selector') or '')[:50]} | {(step.get('description') or '')[:40]}"
            print(msg)
            log.debug(msg, category="debug_trace")

        #raise Exception("TEST CRASH - Simulating celery failure")  # <-- ADD THIS

        msg = f"!!!! Regen remain steps(regular), critical_fields_checklist: {critical_fields_checklist} steps"
        print(msg)
        log.debug(msg, category="debug_trace")
        msg = f"!!!! Regen: junction instructions: {junction_instructions}"
        print(msg)
        log.debug(msg, category="debug_trace")
        msg = f"!!!! Regen remain steps(regular), field_requirements: {field_requirements} steps"
        print(msg)
        log.debug(msg, category="debug_trace")

        # Login mapping: load credentials for regeneration (e.g., 2FA page appeared)
        login_credentials = None
        mapping_type = ctx.get("mapping_type", "form")
        if mapping_type == "login_mapping" and ctx.get("network_id"):
            try:
                from models.database import Network
                from services.encryption_service import decrypt_credential
                network = db.query(Network).filter(Network.id == ctx["network_id"]).first()
                if network:
                    login_credentials = {
                        "username": decrypt_credential(network.login_username, network.company_id,
                               network.id, "login_username") if network.login_username else "", "password": decrypt_credential(network.login_password, network.company_id,
                               network.id, "login_password") if network.login_password else "", "site_url": network.url or "", "login_hints": network.login_hints or ""
                    }
            except Exception as e:
                logger.error(f"[FormMapperTask] Failed to load credentials for regen: {e}")


        ai_result = regenerate_steps_for_mapping(
            mapping_type=mapping_type,
            api_key=api_key,
            session_logger=log,
            dom_html=dom_html,
            executed_steps=executed_steps,
            screenshot_base64=screenshot_base64,
            test_cases=test_cases,
            test_context=test_context,
            critical_fields_checklist=critical_fields_checklist,
            field_requirements=field_requirements,
            junction_instructions=_build_junction_instructions_text(junction_instructions),
            user_provided_inputs=user_provided_inputs or {},
            retry_message=regenerate_retry_message,
            test_case_description=ctx.get("test_case_description", ""),
            login_credentials=login_credentials
        )
        # print(f"!!!! ✅ AI regenerated_steps (regular): {len(ai_result.get('steps', []))} new steps:")
        msg = f"!!!! ✅ AI regenerated_steps (regular): {len(ai_result.get('steps', []))} new steps:"
        print(msg)
        log.debug(msg, category="debug_trace")
        log.ai_response("regenerate_steps", success=True)

        for s in ai_result.get('steps', []):
            msg = f"    !!!! New Step {s.get('step_number', '?')}: {s.get('action', '?')} | {(s.get('selector') or '')[:50]} | {s.get('description', '')} | field_name: {s.get('field_name', '')}"
            print(msg)
            log.debug(msg, category="debug_trace")
            if s.get('is_junction') or s.get('junction_info'):
                msg = f"      !!!! -> is_junction: {s.get('is_junction')}, junction_info: {s.get('junction_info')}"
                print(msg)
                log.debug(msg, category="debug_trace")

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
            "validation_errors_detected": ai_result.get("validation_errors_detected", False),
            "page_error_detected": ai_result.get("page_error_detected", False),
            "error_type": ai_result.get("error_type", ""),
            "login_failed": ai_result.get("login_failed", False),
            "error_message": ai_result.get("error_message", "")
        }
        

        _continue_orchestrator_chain(session_id, "regenerate_steps", result)
        return result
        
    except BudgetExceededError as e:
        result = {"success": False, "error": "AI budget exceeded", "budget_exceeded": True}
        _continue_orchestrator_chain(session_id, "regenerate_steps", result)
        return result

    except AccessDeniedError as e:
        result = {"success": False, "error": str(e), "access_denied": True}
        _continue_orchestrator_chain(session_id, "regenerate_steps", result)
        return result

    except AIParseError as e:
        msg = f"!!!! ❌ AI parse failed (regenerate): {e}"
        print(msg)
        logger.error(f"[FormMapperTask] AI parse failed: {e}")
        if 'log' in locals():
            log.error(msg, category="error")
        result = {"success": False, "error": f"AI parse failed: {e}", "ai_parse_failed": True}
        _continue_orchestrator_chain(session_id, "regenerate_steps", result)
        return result

    except Exception as e:
        msg = f"!!!! ❌ Step regeneration failed: {e}"
        print(msg)
        logger.error(f"[FormMapperTask] Step regeneration failed: {e}", exc_info=True)
        if 'log' in locals():
            log.error(msg, category="error")
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
        executed_steps: List[Dict],
        test_cases: List[Dict],
        test_context: Dict,
) -> Dict:
    """Celery task: Regenerate verification steps after Save/Submit."""
    from services.ai_budget_service import AIOperationType, BudgetExceededError

    logger.info(f"[FormMapperTask] Regenerating VERIFY steps for session {session_id}")

    db = _get_db_session()
    redis_client = _get_redis_client()

    # Fetch screenshot from Redis (removed from Celery kwargs — P0 scalability fix)
    ss_raw = redis_client.get(f"mapper_screenshot:{session_id}")
    screenshot_base64 = ss_raw.decode() if isinstance(ss_raw, bytes) else (ss_raw or "")

    # Fetch DOM from Redis (removed from Celery kwargs — P0 scalability fix)
    dom_raw = redis_client.get(f"mapper_dom:{session_id}")
    dom_html = dom_raw.decode() if isinstance(dom_raw, bytes) else (dom_raw or "")

    try:
        ctx = _get_session_context(redis_client, session_id)
        if ctx.get("company_id") is None or ctx.get("company_id") == 0:
            result = {"success": False, "error": "Session not found"}
            _continue_orchestrator_chain(session_id, "regenerate_verify_steps", result)
            return result

        api_key = _check_budget_and_get_api_key(db, ctx["company_id"], ctx["product_id"])
        # Structured logging
        log = get_session_logger(db_session=None, activity_type=ActivityType.MAPPING.value, session_id=session_id,
                                 company_id=ctx.get("company_id"), company_name=ctx.get("company_name"))
        log.info("Celery task: regenerate_verify_steps started", category="celery_task")

        if not api_key:
            result = {"success": False, "error": "No API key available"}
            _continue_orchestrator_chain(session_id, "regenerate_verify_steps", result)
            return result

        from services.form_mapper_ai_helpers import create_ai_helpers
        helpers = create_ai_helpers(api_key, session_logger=log)

        ai_helper = helpers["form_mapper"]
        #print(f"!!!! 🔍 Regen VERIFY steps...")
        msg = f"!!!! 🔍 Regen VERIFY steps..."
        print(msg)
        log.debug(msg, category="debug_trace")

        last_step = executed_steps[-1] if executed_steps else {}
        #print(
        #    f"!!!! 🔍 Regen VERIFY steps, TRIGGERED BY STEP: {last_step.get('step_number', '?')}: {last_step.get('action', '?')} | {last_step.get('selector', '')[:50]} | {last_step.get('description', '')[:40]}")
        msg = f"!!!! 🔍 Regen VERIFY steps, TRIGGERED BY STEP: {last_step.get('step_number', '?')}: {last_step.get('action', '?')} | {last_step.get('selector', '')[:50]} | {last_step.get('description', '')[:40]}"
        print(msg)
        log.debug(msg, category="debug_trace")


        msg = f"!!!!!!!!!!!!! Regen VERIFY steps: screenshot size: {len(screenshot_base64) if screenshot_base64 else 0}"
        print(msg)
        log.debug(msg, category="debug_trace")
        msg = f"!!!! Regen VERIFY steps, Already executed: {len(executed_steps)} steps"
        print(msg)
        log.debug(msg, category="debug_trace")
        log.ai_call("regenerate_verify_steps", prompt_size=len(str(dom_html or "")))

        for step in executed_steps:
            msg = f"    !!!! Executed Step {step.get('step_number', '?')}: {step.get('action', '?')} | {step.get('selector', '')[:50]} | {step.get('description', '')[:40]}"
            print(msg)
            log.debug(msg, category="debug_trace")

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
        msg = f"!!!! ✅ AI regenerated_verify_steps: {len(new_steps)} new steps:"
        print(msg)
        log.debug(msg, category="debug_trace")
        for step in new_steps:
            desc = step.get('description', '')[:40]
            sel = step.get('selector', '')[:50]
            msg = f"    !!!! New Step {step.get('step_number')}: {step.get('action')} | {sel} | {desc}"
            print(msg)
            log.debug(msg, category="debug_trace")

        logger.info(f"[FormMapperTask] Verify regeneration complete: {len(new_steps)} new steps")
        log.ai_response("regenerate_verify_steps", success=True)

        result = {
            "success": True,
            "new_steps": new_steps,
            "no_more_paths": no_more_paths,
            "validation_errors_detected": ai_result.get("validation_errors_detected", False),
            "page_error_detected": ai_result.get("page_error_detected", False),
            "error_type": ai_result.get("error_type", ""),
        }
        _continue_orchestrator_chain(session_id, "regenerate_verify_steps", result)
        return result

    except BudgetExceededError as e:
        logger.warning(f"[FormMapperTask] Budget exceeded for verify regeneration: {e}")
        result = {"success": False, "error": "AI budget exceeded", "budget_exceeded": True}
        _continue_orchestrator_chain(session_id, "regenerate_verify_steps", result)
        return result

    except AccessDeniedError as e:
        result = {"success": False, "error": str(e), "access_denied": True}
        _continue_orchestrator_chain(session_id, "regenerate_verify_steps", result)
        return result

    except AIParseError as e:
        msg = f"!!!! ❌ AI parse failed (verify regenerate): {e}"
        print(msg)
        logger.error(f"[FormMapperTask] AI parse failed: {e}")
        if 'log' in locals():
            log.error(msg, category="error")
        result = {"success": False, "error": f"AI parse failed: {e}", "ai_parse_failed": True}
        _continue_orchestrator_chain(session_id, "regenerate_verify_steps", result)
        return result

    except Exception as e:
        msg = f"!!!! ❌ Verify regeneration error: {e}"
        print(msg)
        logger.error(f"[FormMapperTask] Verify regeneration error: {e}", exc_info=True)
        if 'log' in locals():
            log.error(msg, category="error")
        sync_mapper_session_status.delay(session_id, "failed", str(e))
        result = {"success": False, "error": str(e)}
        _continue_orchestrator_chain(session_id, "regenerate_verify_steps", result)
        return result

    finally:
        db.close()


@shared_task(bind=True, max_retries=2)
def verify_junction_visual(
        self,
        session_id: str,
        step_info: Dict
) -> Dict:
    """Celery task: Use AI vision to verify if junction revealed new fields."""
    logger.info(f"[FormMapperTask] Junction visual verification for session {session_id}")

    db = _get_db_session()
    redis_client = _get_redis_client()

    # Fetch junction screenshots from Redis (removed from Celery kwargs — P0 scalability fix)
    before_raw = redis_client.get(f"mapper_screenshot_before:{session_id}")
    before_screenshot = before_raw.decode() if isinstance(before_raw, bytes) else (before_raw or "")
    after_raw = redis_client.get(f"mapper_screenshot:{session_id}")
    after_screenshot = after_raw.decode() if isinstance(after_raw, bytes) else (after_raw or "")

    try:
        ctx = _get_session_context(redis_client, session_id)
        if ctx.get("company_id") is None or ctx.get("company_id") == 0:
            result = {"success": False, "error": "Session not found"}
            _continue_orchestrator_chain(session_id, "verify_junction_visual", result)
            return result

        api_key = _check_budget_and_get_api_key(db, ctx["company_id"], ctx["product_id"])

        # Structured logging
        log = get_session_logger(db_session=None, activity_type=ActivityType.MAPPING.value, session_id=session_id,
                                 company_id=ctx.get("company_id"), company_name=ctx.get("company_name"))
        log.info("Celery task: verify_junction_visual started", category="celery_task")

        msg = f"!!!! 🔀 Junction Visual Verification for session {session_id}"
        print(msg)
        log.debug(msg, category="debug_trace")
        msg = f"!!!! Step info: {step_info}"
        print(msg)
        log.debug(msg, category="debug_trace")

        log.ai_call("verify_junction_visual", prompt_size=len(before_screenshot) + len(after_screenshot))

        if not api_key:
            result = {"success": False, "error": "No API key available"}
            _continue_orchestrator_chain(session_id, "verify_junction_visual", result)
            return result

        from services.ai_form_mapper_junction_visual_prompter import create_junction_visual_verifier
        verifier = create_junction_visual_verifier(api_key, session_logger=log)

        # Call AI to verify junction
        ai_result = verifier.verify_junction(
            before_screenshot=before_screenshot,
            after_screenshot=after_screenshot,
            step_info=step_info
        )

        msg = f"!!!! ✅ Junction Visual Verification result: is_junction={ai_result.get('is_junction')}, reason={ai_result.get('reason')}"
        print(msg)
        log.debug(msg, category="debug_trace")
        log.ai_response("verify_junction_visual", success=True)

        logger.info(f"[FormMapperTask] Junction visual verification result: {ai_result}")

        # Record AI usage
        from services.ai_budget_service import AIOperationType
        _record_usage(
            db, ctx["company_id"], ctx["product_id"], ctx.get("user_id", 0),
            AIOperationType.FORM_MAPPER_REGENERATE,
            500,  # Approximate input tokens (images are ~1000 tokens each but we use a rough estimate)
            100,  # Approximate output tokens
            session_id
        )

        result = {
            "success": True,
            "is_junction": ai_result.get("is_junction", True),
            "reason": ai_result.get("reason", ""),
            "new_fields_detected": ai_result.get("new_fields_detected", [])
        }
        _continue_orchestrator_chain(session_id, "verify_junction_visual", result)
        return result

    except Exception as e:
        msg = f"!!!! ❌ Junction visual verification error: {e}"
        print(msg)
        logger.error(f"[FormMapperTask] Junction visual verification error: {e}")
        if 'log' in locals():
            log.error(msg, category="error")


        # On error, default to keeping junction (safer)
        result = {
            "success": True,
            "is_junction": True,
            "reason": f"Verification error: {str(e)} - keeping junction flag as precaution"
        }
        _continue_orchestrator_chain(session_id, "verify_junction_visual", result)
        return result
    finally:
        db.close()


@shared_task(bind=True, max_retries=2)
def verify_page_visual(
        self,
        session_id: str,
        executed_steps: List[Dict],
        already_verified_fields: List[Dict],
        retry_count: int = 0,
        total_wait_seconds: int = 0
) -> Dict:
    """Celery task: Use AI vision to verify form field values on result page (view/list page)."""
    logger.info(f"[FormMapperTask] Visual page verification for session {session_id}, retry={retry_count}")

    db = _get_db_session()
    redis_client = _get_redis_client()

    # Fetch screenshot from Redis (removed from Celery kwargs — P0 scalability fix)
    ss_raw = redis_client.get(f"mapper_screenshot:{session_id}")
    screenshot_base64 = ss_raw.decode() if isinstance(ss_raw, bytes) else (ss_raw or "")

    try:
        ctx = _get_session_context(redis_client, session_id)
        if ctx.get("company_id") is None or ctx.get("company_id") == 0:
            result = {"success": False, "error": "Session not found"}
            _continue_orchestrator_chain(session_id, "verify_page_visual", result)
            return result

        api_key = _check_budget_and_get_api_key(db, ctx["company_id"], ctx["product_id"])

        # Structured logging
        log = get_session_logger(db_session=None, activity_type=ActivityType.MAPPING.value, session_id=session_id,
                                 company_id=ctx.get("company_id"), company_name=ctx.get("company_name"))
        log.info(f"Celery task: verify_page_visual started (retry={retry_count}, waited={total_wait_seconds}s)", category="celery_task")

        msg = f"!!!! 👁️ Visual Page Verification for session {session_id}, retry={retry_count}, total_wait={total_wait_seconds}s"
        print(msg)
        log.debug(msg, category="debug_trace")

        log.ai_call("verify_page_visual", prompt_size=len(screenshot_base64))

        if not api_key:
            result = {"success": False, "error": "No API key available"}
            _continue_orchestrator_chain(session_id, "verify_page_visual", result)
            return result

        from services.ai_form_mapper_page_visual_verifier import create_page_visual_verifier
        verifier = create_page_visual_verifier(api_key, session_logger=log)

        # Load verification instructions from FormPageRoute
        verification_instructions = None
        form_page_route_id = ctx.get("form_route_id")
        if form_page_route_id:
            from models.database import FormPageRoute
            form_page = db.query(FormPageRoute).filter(FormPageRoute.id == form_page_route_id).first()
            if form_page and form_page.verification_file_content:
                verification_instructions = form_page.verification_file_content
                log.info(f"Loaded verification instructions ({len(verification_instructions)} chars)",
                         category="ai_routing")

        # Call AI to verify page
        ai_result = verifier.verify_page(
            screenshot_base64=screenshot_base64,
            executed_steps=executed_steps,
            already_verified_fields=already_verified_fields,
            verification_instructions=verification_instructions
        )

        msg = f"!!!! 👁️ Visual Page Verification result: page_ready={ai_result.get('page_ready')}, results_count={len(ai_result.get('results', []))}"
        print(msg)
        log.debug(msg, category="debug_trace")
        log.ai_response("verify_page_visual", success=True)

        logger.info(f"[FormMapperTask] Visual page verification result: page_ready={ai_result.get('page_ready')}")

        # Record AI usage
        from services.ai_budget_service import AIOperationType
        _record_usage(
            db, ctx["company_id"], ctx["product_id"], ctx.get("user_id", 0),
            AIOperationType.FORM_MAPPER_REGENERATE,
            800,  # Approximate input tokens
            200,  # Approximate output tokens
            session_id
        )

        result = {
            "success": True,
            "page_ready": ai_result.get("page_ready", True),
            "page_type": ai_result.get("page_type", "unknown"),
            "results": ai_result.get("results", []),
            "reason": ai_result.get("reason", ""),
            "retry_count": retry_count,
            "total_wait_seconds": total_wait_seconds
        }
        _continue_orchestrator_chain(session_id, "verify_page_visual", result)
        return result

    except Exception as e:
        msg = f"!!!! ❌ Visual page verification error: {e}"
        print(msg)
        logger.error(f"[FormMapperTask] Visual page verification error: {e}")
        if 'log' in locals():
            log.error(msg, category="error")

        # On error, continue without verification (don't block mapping)
        result = {
            "success": True,
            "page_ready": True,
            "page_type": "unknown",
            "results": [],
            "reason": f"Verification error: {str(e)} - continuing without visual verification",
            "retry_count": retry_count,
            "total_wait_seconds": total_wait_seconds
        }
        _continue_orchestrator_chain(session_id, "verify_page_visual", result)
        return result
    finally:
        db.close()


@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def verify_dynamic_step_visual(
        self,
        session_id: str,
        step_description: str,
        test_case_description: str = "",
        test_page_route_id: int = 0
) -> Dict:
    """Celery task: Visual verification of a verify step for dynamic content."""
    logger.info(f"[FormMapperTask] Dynamic content verify step for session {session_id}")

    db = _get_db_session()
    redis_client = _get_redis_client()

    # Fetch screenshot from Redis (removed from Celery kwargs — P0 scalability fix)
    ss_raw = redis_client.get(f"mapper_screenshot:{session_id}")
    screenshot_base64 = ss_raw.decode() if isinstance(ss_raw, bytes) else (ss_raw or "")

    try:
        ctx = _get_session_context(redis_client, session_id)
        if ctx.get("company_id") is None or ctx.get("company_id") == 0:
            result = {"success": False, "error": "Session not found"}
            _continue_orchestrator_chain(session_id, "verify_dynamic_step_visual", result)
            return result

        api_key = _check_budget_and_get_api_key(db, ctx["company_id"], ctx["product_id"])

        # Structured logging
        log = get_session_logger(db_session=None, activity_type=ActivityType.MAPPING.value, session_id=session_id,
                                 company_id=ctx.get("company_id"), company_name=ctx.get("company_name"))
        log.info("Celery task: verify_dynamic_step_visual started", category="celery_task")

        msg = f"!!!! 👁️ Dynamic Verify Step for session {session_id}"
        print(msg)
        log.debug(msg, category="debug_trace")

        if not api_key:
            result = {"success": False, "error": "No API key available"}
            _continue_orchestrator_chain(session_id, "verify_dynamic_step_visual", result)
            return result

        from services.ai_dynamic_content_verify_prompter import DynamicContentVerifyHelper

        # Fetch reference images and verification instructions
        reference_images = None
        verification_instructions = None

        if test_page_route_id:
            from models.test_page_models import TestPageRoute, TestPageReferenceImage
            from services.s3_storage import get_s3_files_as_base64_parallel

            # Get test page for verification instructions
            test_page = db.query(TestPageRoute).filter(TestPageRoute.id == test_page_route_id).first()
            if test_page:
                verification_instructions = test_page.verification_file_content

                # Get reference images
                ref_images_db = db.query(TestPageReferenceImage).filter(
                    TestPageReferenceImage.test_page_route_id == test_page_route_id,
                    TestPageReferenceImage.status == "ready"
                ).all()

                if ref_images_db:
                    # Fetch all images from S3 in parallel
                    s3_keys = [img.s3_key for img in ref_images_db]
                    base64_images = get_s3_files_as_base64_parallel(s3_keys)

                    reference_images = []
                    for i, img in enumerate(ref_images_db):
                        if base64_images[i]:
                            reference_images.append({
                                "name": img.name,
                                "base64": base64_images[i]
                            })

                    log.info(f"Loaded {len(reference_images)} reference images for verification", category="ai_routing")

                if verification_instructions:
                    log.info(f"Loaded verification instructions ({len(verification_instructions)} chars)",
                             category="ai_routing")

        verifier = DynamicContentVerifyHelper(api_key, session_logger=log)

        # Call AI to verify step
        ai_result = verifier.verify_step_visual(
            screenshot_base64=screenshot_base64,
            step_description=step_description,
            test_case_description=test_case_description,
            reference_images=reference_images,
            verification_instructions=verification_instructions
        )

        msg = f"!!!! 👁️ Dynamic Verify Step result: success={ai_result.get('success')}, page_issue={ai_result.get('page_issue', False)}"
        print(msg)
        log.debug(msg, category="debug_trace")

        logger.info(f"[FormMapperTask] Dynamic verify step result: success={ai_result.get('success')}")

        # Record AI usage
        from services.ai_budget_service import AIOperationType
        _record_usage(
            db, ctx["company_id"], ctx["product_id"], ctx.get("user_id", 0),
            AIOperationType.FORM_MAPPER_REGENERATE,
            800,  # Approximate input tokens
            200,  # Approximate output tokens
            session_id
        )

        result = {
            "success": ai_result.get("success", True),
            "page_issue": ai_result.get("page_issue", False),
            "reason": ai_result.get("reason", "")
        }
        _continue_orchestrator_chain(session_id, "verify_dynamic_step_visual", result)
        return result

    except Exception as e:
        msg = f"!!!! ❌ Dynamic verify step error: {e}"
        print(msg)
        logger.error(f"[FormMapperTask] Dynamic verify step error: {e}")
        if 'log' in locals():
            log.error(msg, category="error")

        # On error, continue without verification (don't block mapping)
        result = {
            "success": True,
            "page_issue": False,
            "reason": f"Verification error: {str(e)} - continuing without verification"
        }
        _continue_orchestrator_chain(session_id, "verify_dynamic_step_visual", result)
        return result
    finally:
        db.close()

@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def trigger_visual_page_screenshot(self, session_id: str) -> Dict:
    """
    Celery task: Delayed trigger for visual page screenshot capture.
    This task does NO work - just signals orchestrator to request fresh screenshot from agent.
    Keeps architecture fully scalable (Celery handles delay, agent handles browser).
    """
    logger.info(f"[FormMapperTask] trigger_visual_page_screenshot fired for session {session_id}")

    result = {"success": True, "session_id": session_id}
    _continue_orchestrator_chain(session_id, "trigger_visual_page_screenshot", result)
    return result

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

    db = _get_db_session()
    redis_client = _get_redis_client()

    try:
        ctx = _get_session_context(redis_client, session_id)
        if ctx.get("company_id") is None or ctx.get("company_id") == 0:
            result = {"success": False, "error": "Session not found"}
            _continue_orchestrator_chain(session_id, "evaluate_paths_with_ai", result)
            return result

        api_key = _check_budget_and_get_api_key(db, ctx["company_id"], ctx["product_id"])

        # Structured logging
        log = get_session_logger(db_session=None, activity_type=ActivityType.MAPPING.value, session_id=session_id,
                                 company_id=ctx.get("company_id"), company_name=ctx.get("company_name"))
        log.info("Celery task: evaluate_paths_with_ai started", category="celery_task")
        msg = f"!!!! 🤖 AI Path Evaluation for session {session_id}"
        print(msg)
        log.debug(msg, category="debug_trace")
        msg = f"!!!! Completed paths: {completed_paths}"
        print(msg)
        log.debug(msg, category="debug_trace")
        msg = f"!!!! Discover all combinations: {discover_all_combinations}"
        print(msg)
        log.debug(msg, category="debug_trace")
        log.ai_call("evaluate_paths", prompt_size=len(str(completed_paths)))


        if not api_key:
            result = {"success": False, "error": "No API key available"}
            _continue_orchestrator_chain(session_id, "evaluate_paths_with_ai", result)
            return result

        from services.form_mapper_ai_helpers import create_ai_helpers
        helpers = create_ai_helpers(api_key, session_logger=log)
        ai_helper = helpers["form_mapper"]

        # Call AI to evaluate paths
        ai_result = ai_helper.evaluate_paths(
            completed_paths=completed_paths,
            discover_all_combinations=discover_all_combinations,
            max_paths=max_paths
        )

        # print(f"!!!! ✅ AI Path Evaluation result: {ai_result}")
        msg = f"!!!! ✅ AI Path Evaluation result: {ai_result}"
        print(msg)
        log.debug(msg, category="debug_trace")
        log.ai_response("evaluate_paths", success=True)

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

        msg = f"!!!! ❌ AI Path Evaluation error: {e}"
        print(msg)
        logger.error(f"[FormMapperTask] AI path evaluation error: {e}")
        if 'log' in locals():
            log.error(msg, category="error")

        sync_mapper_session_status.delay(session_id, "failed", str(e))
        result = {"success": False, "error": str(e)}
        _continue_orchestrator_chain(session_id, "evaluate_paths_with_ai", result)
        return result
    finally:
        db.close()

@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def evaluate_existing_paths(
        self,
        session_id: str,
        completed_paths: List[Dict],
        discover_all_combinations: bool = False,
        max_paths: int = 7
) -> Dict:
    """Celery task: Evaluate existing paths from DB to determine if more paths needed (continue mapping)."""
    logger.info(f"[FormMapperTask] Evaluate existing paths for session {session_id}")

    db = _get_db_session()
    redis_client = _get_redis_client()

    try:
        ctx = _get_session_context(redis_client, session_id)
        if ctx.get("company_id") is None or ctx.get("company_id") == 0:
            result = {"success": False, "error": "Session not found"}
            _continue_orchestrator_chain(session_id, "evaluate_existing_paths", result)
            return result

        api_key = _check_budget_and_get_api_key(db, ctx["company_id"], ctx["product_id"])

        log = get_session_logger(db_session=None, activity_type=ActivityType.MAPPING.value, session_id=session_id,
                                 company_id=ctx.get("company_id"), company_name=ctx.get("company_name"))
        log.info("Celery task: evaluate_existing_paths started", category="celery_task")
        msg = f"!!!! 🔄 Evaluate Existing Paths for session {session_id}"
        print(msg)
        log.debug(msg, category="debug_trace")
        msg = f"!!!! Existing paths from DB: {completed_paths}"
        print(msg)
        log.debug(msg, category="debug_trace")
        log.ai_call("evaluate_existing_paths", prompt_size=len(str(completed_paths)))

        if not api_key:
            result = {"success": False, "error": "No API key available"}
            _continue_orchestrator_chain(session_id, "evaluate_existing_paths", result)
            return result

        from services.form_mapper_ai_helpers import create_ai_helpers
        helpers = create_ai_helpers(api_key, session_logger=log)
        ai_helper = helpers["form_mapper"]

        ai_result = ai_helper.evaluate_paths(
            completed_paths=completed_paths,
            discover_all_combinations=discover_all_combinations,
            max_paths=max_paths
        )

        msg = f"!!!! ✅ Evaluate Existing Paths result: {ai_result}"
        print(msg)
        log.debug(msg, category="debug_trace")
        log.ai_response("evaluate_existing_paths", success=True)

        logger.info(f"[FormMapperTask] Evaluate existing paths result: {ai_result}")

        from services.ai_budget_service import AIOperationType
        _record_usage(
            db, ctx["company_id"], ctx["product_id"], ctx.get("user_id", 0),
            AIOperationType.FORM_MAPPER_REGENERATE,
            ai_result.get("tokens_used", 500) // 2,
            ai_result.get("tokens_used", 500) // 2,
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
        _continue_orchestrator_chain(session_id, "evaluate_existing_paths", result)
        return result

    except Exception as e:
        msg = f"!!!! ❌ Evaluate Existing Paths error: {e}"
        print(msg)
        logger.error(f"[FormMapperTask] Evaluate existing paths error: {e}")
        if 'log' in locals():
            log.error(msg, category="error")

        result = {"success": False, "error": str(e)}
        _continue_orchestrator_chain(session_id, "evaluate_existing_paths", result)
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

        # Structured logging
        log = get_session_logger(db_session=None, activity_type=ActivityType.MAPPING.value, session_id=session_id,
                                 company_id=ctx.get("company_id"), company_name=ctx.get("company_name"))
        log.info("Celery task: save_mapping_result started", category="celery_task")

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
        helpers = create_ai_helpers(api_key, session_logger=log)

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
        mapping_type = ctx.get("mapping_type", "form")

        # Login/logout mapping: no FormMapResult to save — steps go to Network.login_stages/logout_stages
        # via handle_mapping_complete → _save_login_logout_to_network
        if mapping_type in ("login_mapping", "logout_mapping"):
            result = {"stages": stages, "success": True, "continue_to_next_path": continue_to_next_path}
            _continue_orchestrator_chain(session_id, "save_mapping_result", result)
            return result

        test_page_route_id = ctx.get("test_page_route_id")

        #existing_paths = db.query(FormMapResult).filter(
        #    FormMapResult.form_page_route_id == form_page_route_id
        #).count()

        if mapping_type == "dynamic_content" and test_page_route_id:
            existing_paths = db.query(FormMapResult).filter(
                FormMapResult.test_page_route_id == test_page_route_id
            ).count()
        else:
            existing_paths = db.query(FormMapResult).filter(
                FormMapResult.form_page_route_id == form_page_route_id
            ).count()

        # Get test_scenario_id if in scenario mode
        test_scenario_id = ctx.get("test_scenario_id")
        if test_scenario_id and isinstance(test_scenario_id, str):
            test_scenario_id = int(test_scenario_id) if test_scenario_id != "0" else None
        elif test_scenario_id == 0:
            test_scenario_id = None

        form_map_result = FormMapResult(
            form_mapper_session_id=int(session_id),
            form_page_route_id=form_page_route_id if mapping_type != "dynamic_content" else None,
            test_page_route_id=test_page_route_id if mapping_type == "dynamic_content" else None,
            test_scenario_id=test_scenario_id,
            network_id=ctx.get("network_id"),
            company_id=ctx.get("company_id"),
            path_number=existing_paths + 1,
            path_junctions=path_junctions if path_junctions else [],
            steps=updated_stages if updated_stages else stages,
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

    except AccessDeniedError as e:
        result = {"success": False, "error": str(e), "access_denied": True}
        _continue_orchestrator_chain(session_id, "save_mapping_result", result)
        return result

    except Exception as e:
        msg = f"!!!! ❌ Save mapping result failed: {e}"
        print(msg)
        logger.error(f"[FormMapperTask] Save mapping result failed: {e}", exc_info=True)
        if 'log' in locals():
            log.error(msg, category="error")
        sync_mapper_session_status.delay(session_id, "failed", str(e))
        result = {"success": False, "error": str(e)}
        _continue_orchestrator_chain(session_id, "save_mapping_result", result)
        return result

    finally:
        db.close()


@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def field_assist_query(
        self,
        session_id: str,
        screenshot_base64: str,
        step: Dict,
        query_type: str,
        rail_bounds: Dict = None,
        action_type: str = None
) -> Dict:
    """Celery task: Field assist query (lightweight AI check)."""
    from services.ai_budget_service import AIOperationType, BudgetExceededError

    logger.info(f"[FormMapperTask] Field assist query '{query_type}' for session {session_id}")

    db = _get_db_session()
    redis_client = _get_redis_client()

    try:
        ctx = _get_session_context(redis_client, session_id)
        if ctx.get("company_id") is None or ctx.get("company_id") == 0:
            return {"success": False, "error": "Session not found"}

        api_key = _check_budget_and_get_api_key(db, ctx["company_id"], ctx["product_id"])

        if not api_key:
            return {"success": False, "error": "No API key available"}

        # Route slider queries to dedicated prompter
        if query_type in ("slider_click_points", "slider_read_value"):
            from services.ai_form_mapper_field_assist_slider_prompter import AIFieldAssistSliderPrompter
            slider_prompter = AIFieldAssistSliderPrompter(api_key)

            log = get_session_logger(db_session=None, activity_type=ActivityType.MAPPING.value, session_id=session_id,
                                     company_id=ctx.get("company_id"), company_name=ctx.get("company_name"))

            if query_type == "slider_click_points":
                result = slider_prompter.generate_click_points(rail_bounds, action_type, step)
            else:

                screenshot_size_bytes = len(screenshot_base64) if screenshot_base64 else 0
                screenshot_size_kb = screenshot_size_bytes / 1024
                log.info(
                    f"!!!!! ENTERING slider read_value - action_type: {action_type}, screenshot_size: {screenshot_size_kb:.2f} KB ({screenshot_size_bytes} bytes)",
                    category="ai_request")

                result = slider_prompter.read_value(screenshot_base64, action_type, step)

                log.info(f"!!!!! RAW AI OUTPUT for slider read_value: {result}", category="ai_response")
        else:
            from services.form_mapper_ai_helpers import create_ai_helpers
            helpers = create_ai_helpers(api_key)
            field_assist = helpers["field_assist"]
            result = field_assist.query(
                query_type=query_type,
                screenshot_base64=screenshot_base64,
                step=step
            )

        # Record usage (lightweight - small tokens)
        input_tokens = len(screenshot_base64) // 100 + 200
        output_tokens = 50

        _record_usage(
            db, ctx["company_id"], ctx["product_id"], ctx["user_id"],
            AIOperationType.FORM_MAPPER_FIELD_ASSIST,
            input_tokens, output_tokens, session_id
        )

        logger.info(f"[FormMapperTask] Field assist query result: {result}")

        return {"success": True, **result}

    except BudgetExceededError as e:
        return {"success": False, "error": "AI budget exceeded", "budget_exceeded": True}

    except AccessDeniedError as e:
        return {"success": False, "error": str(e), "access_denied": True}

    except Exception as e:
        msg = f"!!!! ❌ Field assist query failed: {e}"
        print(msg)
        logger.error(f"[FormMapperTask] Field assist query failed: {e}", exc_info=True)
        if 'log' in locals():
            log.error(msg, category="error")
        if self.request.retries >= self.max_retries:
            return {"success": False, "error": str(e)}
        raise

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

            # Also update TestPageRoute status for dynamic content
            if db_session.test_page_route_id:
                from models.test_page_models import TestPageRoute
                test_page = db.query(TestPageRoute).filter(
                    TestPageRoute.id == db_session.test_page_route_id
                ).first()
                if test_page:
                    if status == "completed":
                        test_page.status = "mapped"
                    elif status == "failed":
                        test_page.status = "failed"
                    db.commit()
                    logger.info(
                        f"[MapperTasks] TestPageRoute {db_session.test_page_route_id} status -> {test_page.status}")

            # Push close task to agent when session fails
            if status == "failed":
                try:
                    import time
                    user_id = db_session.user_id  # From DB - authoritative
                    task = {
                        "task_id": f"mapper_{session_id}_form_mapper_close_{int(time.time() * 1000)}",
                        "task_type": "form_mapper_close",
                        "session_id": session_id,
                        "payload": {
                            "complete_logging": True,
                            "log_message": f"❌ Mapping failed: {error}",
                            "log_level": "error"
                        }
                    }
                    _get_redis_client().lpush(f"agent:{user_id}", json.dumps(task))
                    logger.info(f"[MapperTasks] Pushed form_mapper_close to agent:{user_id}")
                except Exception as close_err:
                    msg = f"!!!! ❌ Failed to push close task: {close_err}"
                    print(msg)
                    logger.error(f"[MapperTasks] Failed to push close task: {close_err}")
                    # CloudWatch logging
                    try:
                        from services.session_logger import get_session_logger, ActivityType
                        cw_log = get_session_logger(
                            db_session=None,
                            activity_type=ActivityType.MAPPING.value,
                            session_id=str(session_id),
                            company_id=None,
                            user_id=None
                        )
                        cw_log.error(msg, category="error")
                    except:
                        pass


    except Exception as e:
        msg = f"!!!! ❌ Failed to sync DB session {session_id}: {e}"
        print(msg)
        logger.error(f"[MapperTasks] Failed to sync DB session {session_id}: {e}")
        # CloudWatch logging
        try:
            from services.session_logger import get_session_logger, ActivityType
            cw_log = get_session_logger(
                db_session=None,
                activity_type=ActivityType.MAPPING.value,
                session_id=str(session_id),
                company_id=None,
                user_id=None
            )
            cw_log.error(msg, category="error")
        except:
            pass
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
        redis_client = _get_redis_client()
        for session in stale_sessions:
            session.status = "failed"
            session.last_error = f"Session timed out after {timeout_hours} hours"
            session.completed_at = datetime.utcnow()

            # Clean up Redis keys for this session
            sid = str(session.id)
            redis_client.delete(
                f"mapper_session:{sid}",
                f"mapper_dom:{sid}",
                f"mapper_screenshot:{sid}",
                f"mapper_screenshot_before:{sid}",
                f"mapper_lock:{sid}",
            )
            # Clean up agent queue if user_id available
            if session.user_id:
                redis_client.delete(f"agent:{session.user_id}")
            logger.info(f"[MapperTasks] Cleaned Redis keys for stale session {sid}")

        db.commit()
        logger.info(f"[MapperTasks] Cleaned up {count} stale sessions")
        return {"cleaned": count}
    except Exception as e:
        logger.error(f"[MapperTasks] Cleanup failed: {e}")
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()

@shared_task(name="tasks.detect_stuck_mapper_sessions")
def detect_stuck_mapper_sessions():
    """
    Periodic task: detect sessions stuck waiting for agent response.
    If mapper_agent_active:{session_id} expired (agent hasn't responded in 3 min),
    fail the session. Runs every 60 seconds via Celery beat.
    """
    db = _get_db_session()
    redis_client = _get_redis_client()
    try:
        from models.form_mapper_models import FormMapperSession
        from datetime import datetime

        # Agent-waiting states — session expects an agent response
        agent_waiting_states = {
            "extracting_initial_dom", "getting_initial_screenshot",
            "executing_step", "step_failed_extracting_dom",
            "alert_extracting_dom", "alert_navigating_back",
            "dom_change_navigating_back", "dom_change_getting_screenshot",
            "dom_change_getting_dom", "validation_error_getting_dom",
            "next_path_navigating",
            "junction_getting_before_screenshot", "junction_getting_after_screenshot",
            "visual_page_getting_screenshot", "dynamic_verify_getting_screenshot",
        }

        # Get all running sessions from DB
        running_sessions = db.query(FormMapperSession).filter(
            FormMapperSession.status.in_(["running", "initializing", "pending"])
        ).all()

        failed_count = 0
        for session in running_sessions:
            sid = str(session.id)
            # Check Redis session state
            state_raw = redis_client.hget(f"mapper_session:{sid}", "state")
            if not state_raw:
                continue
            state = state_raw.decode() if isinstance(state_raw, bytes) else state_raw

            if state not in agent_waiting_states:
                continue  # Session is waiting for Celery (AI), not agent

            # Check if agent heartbeat key exists
            if not redis_client.exists(f"mapper_agent_active:{sid}"):
                # Agent hasn't responded in 3+ minutes — fail session via orchestrator
                from services.form_mapper_orchestrator import FormMapperOrchestrator
                orchestrator = FormMapperOrchestrator(redis_client, db)
                orchestrator._fail_session(sid, "Agent unresponsive — no response for 3+ minutes")
                failed_count += 1

                # Clean up Redis keys immediately
                redis_client.delete(
                    f"mapper_session:{sid}",
                    f"mapper_dom:{sid}",
                    f"mapper_screenshot:{sid}",
                    f"mapper_screenshot_before:{sid}",
                    f"mapper_lock:{sid}",
                    f"mapper_agent_active:{sid}",
                )


        if failed_count:
            db.commit()
            logger.info(f"[MapperTasks] Failed {failed_count} stuck sessions (agent unresponsive)")
        return {"failed": failed_count, "checked": len(running_sessions)}

    except Exception as e:
        logger.error(f"[MapperTasks] Stuck session detection failed: {e}", exc_info=True)
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


@shared_task(name="tasks.cancel_previous_sessions_for_test_page")
def cancel_previous_sessions_for_test_page(test_page_route_id: int, new_session_id: int):
    """Cancel previous sessions and cleanup results for test page (dynamic content)"""
    db = _get_db_session()
    try:
        from models.form_mapper_models import FormMapperSession, FormMapResult
        from datetime import datetime

        # Cancel active sessions for this test page
        active_sessions = db.query(FormMapperSession).filter(
            FormMapperSession.test_page_route_id == test_page_route_id,
            FormMapperSession.id != new_session_id,
            FormMapperSession.status.in_(["initializing", "pending", "running"])
        ).all()

        count = len(active_sessions)
        for session in active_sessions:
            session.status = "cancelled_ack"
            session.last_error = f"Cancelled - new session {new_session_id} started"
            session.completed_at = datetime.utcnow()

        # Delete previous mapping results for fresh start
        deleted_paths = db.query(FormMapResult).filter(
            FormMapResult.test_page_route_id == test_page_route_id
        ).delete()

        db.commit()

        logger.info(
            f"[FormMapperTask] Test page {test_page_route_id}: cancelled {count} sessions, deleted {deleted_paths} paths")

        return {"cancelled": count, "deleted_paths": deleted_paths}
    except Exception as e:
        db.rollback()
        logger.error(f"[FormMapperTask] Failed to cleanup test page {test_page_route_id}: {e}")
        return {"error": str(e)}
    finally:
        db.close()