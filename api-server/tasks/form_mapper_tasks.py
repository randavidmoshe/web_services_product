# form_mapper_tasks.py
# Celery tasks for Form Mapper AI operations
# SCALABLE: Integrated with AI Budget Service for token tracking and limits

import os
import json
import logging
from celery_app import celery
from celery import shared_task
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def _get_redis_client():
    """Get Redis client with connection pooling"""
    import redis
    # Use connection pool for efficiency at scale
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
    """
    Check budget and get API key.
    Uses customer's API key if provided, otherwise falls back to system key.
    Raises BudgetExceededError if budget exceeded.
    """
    from services.ai_budget_service import get_budget_service, BudgetExceededError
    from models.database import CompanyProductSubscription
    
    redis_client = _get_redis_client()
    budget_service = get_budget_service(redis_client)
    
    # Check budget (raises BudgetExceededError if exceeded)
    has_budget, remaining, total = budget_service.check_budget(db, company_id, product_id)
    
    if not has_budget:
        raise BudgetExceededError(company_id, total, total - remaining)
    
    # Get API key (customer's or system)
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
    
    # Decode bytes if needed
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


@shared_task(bind=True, max_retries=3, default_retry_delay=10, 
             autoretry_for=(Exception,), retry_backoff=True)
def analyze_form_page(
    self,
    session_id: str,
    dom_html: str,
    screenshot_base64: str,
    test_cases: list,
    previous_paths: list,
    current_path: int,
    enable_junction_discovery: bool = True,
    max_junction_paths: int = 5,
    use_detect_fields_change: bool = True,
    enable_ui_verification: bool = True
) -> Dict:
    """
    Celery task: Analyze form page with AI.
    
    - Checks budget before AI call
    - Records token usage after call
    - Stores result in Redis for orchestrator
    """
    from services.ai_budget_service import AIOperationType, BudgetExceededError
    
    logger.info(f"[FormMapperTask] Analyzing form page for session {session_id}")
    
    db = _get_db_session()
    redis_client = _get_redis_client()
    
    try:
        # Get session context
        ctx = _get_session_context(redis_client, session_id)
        if not ctx.get("company_id"):
            return {"success": False, "error": "Session not found"}
        
        # Check budget and get API key
        api_key = _check_budget_and_get_api_key(db, ctx["company_id"], ctx["product_id"])
        
        if not api_key:
            return {"success": False, "error": "No API key available"}
        
        # Import and use AI helper
        from services.form_mapper_ai_helpers import create_ai_helpers
        helpers = create_ai_helpers(api_key)
        
        ai_helper = helpers["main"]
        result = ai_helper.generate_next_steps(
            dom_html=dom_html,
            screenshot_base64=screenshot_base64,
            test_context={"test_cases": test_cases},
            previous_paths=previous_paths,
            current_path_junctions=[],
            current_step_number=1
        )
        
        # Record usage (estimate tokens)
        input_tokens = len(dom_html) // 4 + len(screenshot_base64) // 100
        output_tokens = len(json.dumps(result)) // 4 if result else 0
        
        _record_usage(
            db, ctx["company_id"], ctx["product_id"], ctx["user_id"],
            AIOperationType.FORM_MAPPER_ANALYZE,
            input_tokens, output_tokens, session_id
        )
        
        # Store result in Redis for orchestrator
        result_key = f"mapper_ai_result:{session_id}"
        redis_client.setex(result_key, 3600, json.dumps(result))
        
        logger.info(f"[FormMapperTask] Analysis complete: {len(result.get('steps', []))} steps")
        return result
        
    except BudgetExceededError as e:
        logger.warning(f"[FormMapperTask] Budget exceeded for company {e.company_id}")
        return {
            "success": False, 
            "error": "AI budget exceeded",
            "budget_exceeded": True,
            "budget": e.budget,
            "used": e.used
        }
        
    except Exception as e:
        logger.error(f"[FormMapperTask] Analysis failed: {e}")
        raise  # Let Celery retry handle it
        
    finally:
        db.close()


@shared_task(bind=True, max_retries=3, default_retry_delay=10,
             autoretry_for=(Exception,), retry_backoff=True)
def handle_alert_recovery(
    self,
    session_id: str,
    alert_text: str,
    dom_html: str,
    screenshot_base64: str,
    all_steps: list,
    current_step_index: int
) -> Dict:
    """
    Celery task: Handle alert/error recovery with AI.
    """
    from services.ai_budget_service import AIOperationType, BudgetExceededError
    
    logger.info(f"[FormMapperTask] Alert recovery for session {session_id}")
    
    db = _get_db_session()
    redis_client = _get_redis_client()
    
    try:
        ctx = _get_session_context(redis_client, session_id)
        if not ctx.get("company_id"):
            return {"success": False, "error": "Session not found"}
        
        api_key = _check_budget_and_get_api_key(db, ctx["company_id"], ctx["product_id"])
        
        if not api_key:
            return {"success": False, "error": "No API key available"}
        
        from services.form_mapper_ai_helpers import create_ai_helpers
        helpers = create_ai_helpers(api_key)
        
        ai_recovery = helpers["alert_recovery"]
        failed_step = all_steps[current_step_index] if current_step_index < len(all_steps) else {}
        
        result = ai_recovery.analyze_and_recover(
            dom_html=dom_html,
            screenshot_base64=screenshot_base64,
            alert_text=alert_text,
            failed_step=failed_step,
            all_steps=all_steps
        )
        
        # Record usage
        input_tokens = len(dom_html) // 4 + len(screenshot_base64) // 100
        output_tokens = len(json.dumps(result)) // 4 if result else 0
        
        _record_usage(
            db, ctx["company_id"], ctx["product_id"], ctx["user_id"],
            AIOperationType.FORM_MAPPER_ALERT_RECOVERY,
            input_tokens, output_tokens, session_id
        )
        
        # Store result
        result_key = f"mapper_recovery_result:{session_id}"
        redis_client.setex(result_key, 3600, json.dumps(result))
        
        return result
        
    except BudgetExceededError as e:
        return {"success": False, "error": "AI budget exceeded", "budget_exceeded": True}
        
    except Exception as e:
        logger.error(f"[FormMapperTask] Alert recovery failed: {e}")
        raise
        
    finally:
        db.close()


@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def verify_ui_visual(
    self,
    session_id: str,
    screenshot_base64: str,
    expected_state: dict
) -> Dict:
    """
    Celery task: Visual UI verification with AI.
    """
    from services.ai_budget_service import AIOperationType, BudgetExceededError
    
    logger.info(f"[FormMapperTask] UI verification for session {session_id}")
    
    db = _get_db_session()
    redis_client = _get_redis_client()
    
    try:
        ctx = _get_session_context(redis_client, session_id)
        if not ctx.get("company_id"):
            return {"success": False, "error": "Session not found"}
        
        api_key = _check_budget_and_get_api_key(db, ctx["company_id"], ctx["product_id"])
        
        if not api_key:
            return {"success": False, "error": "No API key available"}
        
        from services.form_mapper_ai_helpers import create_ai_helpers
        helpers = create_ai_helpers(api_key)
        
        ai_verifier = helpers["ui_verifier"]
        result = ai_verifier.verify_ui(
            screenshot_base64=screenshot_base64,
            expected_state=expected_state
        )
        
        # Record usage (mostly image tokens)
        input_tokens = len(screenshot_base64) // 100 + 500
        output_tokens = len(json.dumps(result)) // 4 if result else 0
        
        _record_usage(
            db, ctx["company_id"], ctx["product_id"], ctx["user_id"],
            AIOperationType.FORM_MAPPER_UI_VERIFY,
            input_tokens, output_tokens, session_id
        )
        
        return result
        
    except BudgetExceededError as e:
        return {"success": False, "error": "AI budget exceeded", "budget_exceeded": True}
        
    except Exception as e:
        logger.error(f"[FormMapperTask] UI verification failed: {e}")
        raise
        
    finally:
        db.close()


@shared_task(bind=True, max_retries=2)
def assign_test_cases(
    self,
    session_id: str,
    all_steps: list,
    test_cases: list
) -> Dict:
    """
    Celery task: Assign test cases to steps at end of mapping.
    """
    from services.ai_budget_service import AIOperationType, BudgetExceededError
    
    logger.info(f"[FormMapperTask] Assigning test cases for session {session_id}")
    
    db = _get_db_session()
    redis_client = _get_redis_client()
    
    try:
        ctx = _get_session_context(redis_client, session_id)
        if not ctx.get("company_id"):
            return {"success": False, "error": "Session not found"}
        
        api_key = _check_budget_and_get_api_key(db, ctx["company_id"], ctx["product_id"])
        
        if not api_key:
            return {"success": False, "error": "No API key available"}
        
        from services.form_mapper_ai_helpers import create_ai_helpers
        helpers = create_ai_helpers(api_key)
        
        ai_end = helpers["end_prompter"]
        result = ai_end.assign_test_cases(
            steps=all_steps,
            test_cases=test_cases
        )
        
        # Record usage
        input_tokens = len(json.dumps(all_steps)) // 4 + len(json.dumps(test_cases)) // 4
        output_tokens = len(json.dumps(result)) // 4 if result else 0
        
        _record_usage(
            db, ctx["company_id"], ctx["product_id"], ctx["user_id"],
            AIOperationType.FORM_MAPPER_END_ASSIGN,
            input_tokens, output_tokens, session_id
        )
        
        # Store final result
        result_key = f"mapper_final_result:{session_id}"
        redis_client.setex(result_key, 86400, json.dumps(result))  # 24h TTL
        
        return result
        
    except BudgetExceededError as e:
        return {"success": False, "error": "AI budget exceeded", "budget_exceeded": True}
        
    except Exception as e:
        logger.error(f"[FormMapperTask] Test case assignment failed: {e}")
        return {"success": False, "error": str(e)}
        
    finally:
        db.close()
