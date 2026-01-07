# forms_runner_tasks.py
# Celery tasks for Forms Runner operations
# FULLY SCALABLE: All orchestration via Celery, no blocking API workers

import os
import json
import logging
import time
from celery_app import celery
from celery import shared_task
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)


# ============================================================
# CONNECTION HELPERS (with pooling)
# ============================================================

_redis_pool = None

def _get_redis_client():
    """Get Redis client with connection pooling"""
    global _redis_pool
    import redis
    
    if _redis_pool is None:
        _redis_pool = redis.ConnectionPool(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=0,
            max_connections=100,
            decode_responses=False
        )
    
    return redis.Redis(connection_pool=_redis_pool)


_db_engine = None

def _get_db_session():
    """Get database session with connection pooling"""
    global _db_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import create_engine
    
    if _db_engine is None:
        database_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@db:5432/formfinder")
        _db_engine = create_engine(
            database_url,
            pool_size=20,
            max_overflow=30,
            pool_pre_ping=True,
            pool_recycle=3600
        )
    
    Session = sessionmaker(bind=_db_engine)
    return Session()


# ============================================================
# REDIS STATE HELPERS
# ============================================================

def _get_runner_key(session_id: str) -> str:
    return f"forms_runner:{session_id}"


def _get_runner_state(redis_client, session_id: str) -> Optional[Dict]:
    """Get runner state from Redis"""
    key = _get_runner_key(session_id)
    state = redis_client.hgetall(key)
    
    if not state:
        return None
    
    decoded = {}
    for k, v in state.items():
        key_str = k.decode() if isinstance(k, bytes) else k
        val_str = v.decode() if isinstance(v, bytes) else v
        decoded[key_str] = val_str
    
    # Parse JSON fields
    if "stages" in decoded:
        try:
            decoded["stages"] = json.loads(decoded["stages"])
        except:
            decoded["stages"] = []
    
    # Parse integers
    for field in ["total_stages", "current_stage_index", "retry_count", 
                  "recovery_attempts", "company_id", "user_id", "product_id",
                  "network_id", "form_route_id"]:
        if field in decoded:
            decoded[field] = int(decoded.get(field, 0))
    
    return decoded


def _update_runner_state(redis_client, session_id: str, updates: Dict) -> None:
    """Update runner state in Redis"""
    key = _get_runner_key(session_id)
    
    # Serialize JSON fields
    if "stages" in updates:
        updates["stages"] = json.dumps(updates["stages"])
    
    redis_client.hset(key, mapping=updates)


def _init_runner_state(
    redis_client,
    session_id: str,
    phase: str,
    stages: List[Dict],
    company_id: int,
    user_id: int,
    product_id: int,
    network_id: int,
    form_route_id: int,
    network_url: str = "",
    log_message: str = None,
    session_context: dict = None
) -> Dict:
    """Initialize runner state in Redis"""
    from datetime import datetime
    
    state = {
        "session_id": session_id,
        "phase": phase,
        "company_id": str(company_id),
        "user_id": str(user_id),
        "product_id": str(product_id),
        "network_id": str(network_id),
        "form_route_id": str(form_route_id),
        "network_url": network_url,
        "stages": json.dumps(stages),
        "total_stages": str(len(stages)),
        "current_stage_index": "0",
        "status": "running",
        "retry_count": "0",
        "recovery_attempts": "0",
        "stages_updated": "false",
        "last_error": "",
        "started_at": datetime.utcnow().isoformat(),
        "log_message": log_message or "",
        "session_context": json.dumps(session_context) if session_context else ""
    }
    
    key = _get_runner_key(session_id)
    redis_client.hset(key, mapping=state)
    redis_client.expire(key, 7200)  # 2 hour TTL
    
    return state


# ============================================================
# BUDGET HELPERS
# ============================================================

def _check_budget_and_get_api_key(db, company_id: int, product_id: int) -> str:
    """Check budget and get API key"""
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
                  operation_type, input_tokens: int, output_tokens: int):
    """Record AI usage"""
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
        output_tokens=output_tokens
    )


# ============================================================
# MAIN ORCHESTRATION TASKS
# ============================================================

@shared_task(bind=True, max_retries=2)
def start_runner_phase(
    self,
    session_id: str,
    phase: str,  # "login" or "navigate"
    stages: List[Dict],
    company_id: int,
    user_id: int,
    product_id: int,
    network_id: int,
    form_route_id: int,
    network_url: str = "",
    log_message: str = None,
    session_context: dict = None
) -> Dict:
    """
    Start a runner phase (login or navigation).
    Initializes state and triggers first step execution.
    """
    logger.info(f"[FormsRunner] Starting {phase} phase for session {session_id}")
    
    redis_client = _get_redis_client()
    
    if not stages:
        logger.info(f"[FormsRunner] No {phase} stages - phase complete")
        
        # Signal phase complete immediately
        result_key = f"runner_phase_complete:{session_id}"
        redis_client.setex(result_key, 300, json.dumps({
            "phase": phase,
            "success": True,
            "skipped": True
        }))
        
        # Trigger mapping phase if navigation completed
        if phase == "navigate":
            trigger_mapping_phase.delay(session_id)
            logger.info(f"[FormsRunner] Queued mapping phase trigger for session {session_id}")
        
        return {
            "success": True,
            "phase_complete": True,
            "phase": phase,
            "session_id": session_id,
            "skipped": True
        }
    
    # Initialize state
    _init_runner_state(
        redis_client, session_id, phase, stages,
        company_id, user_id, product_id, network_id, form_route_id, network_url, log_message, session_context
    )
    
    # Queue first step execution
    execute_runner_step.delay(session_id)
    
    return {
        "success": True,
        "phase": phase,
        "total_stages": len(stages),
        "session_id": session_id
    }


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def execute_runner_step(self, session_id: str) -> Dict:
    """
    Execute current runner step via agent.
    On success: advance to next step or complete phase.
    On failure: trigger AI recovery.
    """
    redis_client = _get_redis_client()
    
    state = _get_runner_state(redis_client, session_id)
    if not state:
        return {"success": False, "error": "Session not found"}
    
    if state["status"] in ["completed", "failed", "cancelled"]:
        return {"success": False, "error": f"Session already {state['status']}"}
    
    stages = state["stages"]
    current_index = state["current_stage_index"]
    
    if current_index >= len(stages):
        # All steps complete
        return _complete_runner_phase(redis_client, session_id, state)
    
    current_stage = stages[current_index]
    phase = state["phase"]
    
    logger.info(f"[FormsRunner] Executing {phase} step {current_index + 1}/{len(stages)} for session {session_id}")
    
    # Queue agent task and wait for result
    log_msg = state.get("log_message") if current_index == 0 else None
    session_ctx = json.loads(state.get("session_context")) if current_index == 0 and state.get(
        "session_context") else None
    agent_result = _execute_step_via_agent(
        session_id=session_id,
        stage=current_stage,
        user_id=state["user_id"],
        log_message=log_msg,
        session_context=session_ctx
    )

    if agent_result.get("success"):
        # Step succeeded - advance
        return _handle_step_success(redis_client, session_id, state)
    elif agent_result.get("skipped") or agent_result.get("aborted"):
        # Task was skipped (session cancelled) - don't trigger recovery
        logger.info(
            f"[FormsRunner] Task skipped/aborted for session {session_id}: {agent_result.get('reason', agent_result.get('error'))}")
        return {"success": False, "skipped": True, "reason": agent_result.get("reason", agent_result.get("error"))}
    else:
        # Step failed - handle error
        return _handle_step_failure(redis_client, session_id, state, agent_result)


def _execute_step_via_agent(session_id: str, stage: Dict, user_id: int, log_message: str = None, session_context: dict = None) -> Dict:
    """
    Queue step execution to agent and wait for result.
    Uses Redis for async communication with agent.
    """
    redis_client = _get_redis_client()
    
    # Create agent task
    payload = {"step": stage}
    if log_message:
        payload["log_message"] = log_message
    if session_context:
        payload["session_context"] = session_context

    task = {
        "task_id": f"runner_{session_id}_{stage.get('step_number', 0)}_{int(time.time())}",
        "task_type": "forms_runner_exec_step",
        "session_id": session_id,
        "payload": payload
    }

    # Check session status before pushing (prevent stale tasks after cancel)
    state = _get_runner_state(redis_client, session_id)
    if state and state.get("status") == "cancelled":
        logger.info(f"[FormsRunner] Session {session_id} is {state.get('status')}, skipping task push")
        return {"success": False, "error": f"Session {state.get('status')}", "skipped": True}

    # Push to agent queue
    agent_queue_key = f"agent:{user_id}"
    logger.info(f"[FormsRunner] DEBUG: Pushing to queue {agent_queue_key}")
    result = redis_client.lpush(agent_queue_key, json.dumps(task))
    logger.info(f"[FormsRunner] DEBUG: lpush result: {result}")
    
    # Wait for result (with timeout)
    result_key = f"runner_step_result:{session_id}"
    
    # Poll for result (agent will set this key)
    timeout_seconds = 300  # 5 min timeout
    poll_interval = 1  # 1 second
    
    for _ in range(timeout_seconds // poll_interval):
        # Check if session was cancelled while waiting
        state = _get_runner_state(redis_client, session_id)
        if state and state.get("status") == "cancelled":
            logger.info(f"[FormsRunner] Session {session_id} {state.get('status')} during wait, aborting")
            return {"success": False, "error": f"Session {state.get('status')}", "aborted": True}

        result = redis_client.get(result_key)
        if result:
            redis_client.delete(result_key)
            return json.loads(result)
        time.sleep(poll_interval)
    
    return {"success": False, "error": "Agent timeout"}


def _handle_step_success(redis_client, session_id: str, state: Dict) -> Dict:
    """Handle successful step - advance to next or complete"""
    current_index = state["current_stage_index"]
    total = state["total_stages"]
    
    next_index = current_index + 1
    
    if next_index >= total:
        return _complete_runner_phase(redis_client, session_id, state)
    
    # Advance to next step
    _update_runner_state(redis_client, session_id, {
        "current_stage_index": str(next_index),
        "retry_count": "0",
        "last_error": ""
    })
    
    logger.info(f"[FormsRunner] Step {current_index + 1} complete, advancing to {next_index + 1}")
    
    # Queue next step
    execute_runner_step.delay(session_id)
    
    return {"success": True, "advanced_to": next_index + 1}


def _handle_step_failure(redis_client, session_id: str, state: Dict, result: Dict) -> Dict:
    """Handle step failure - skip alerts or trigger AI recovery"""
    stages = state["stages"]
    current_index = state["current_stage_index"]
    current_stage = stages[current_index]
    action = current_stage.get("action", "")
    error = result.get("error", "Unknown error")
    
    # Alert actions that fail = no alert present, just skip
    if action in ["accept_alert", "dismiss_alert"]:
        logger.info(f"[FormsRunner] Alert action skipped (no alert)")
        return _handle_step_success(redis_client, session_id, state)
    
    # Verify action failure = test assertion, not recoverable
    if action == "verify":
        _update_runner_state(redis_client, session_id, {
            "status": "failed",
            "last_error": "Verification failed - test assertion"
        })
        return {"success": False, "error": "Verification failed"}
    
    logger.info(f"[FormsRunner] Step failed: {error}, triggering AI recovery")
    
    _update_runner_state(redis_client, session_id, {
        "status": "recovering",
        "last_error": error
    })
    
    # Trigger AI recovery
    analyze_runner_error.delay(
        session_id=session_id,
        failed_stage=current_stage,
        dom_html=result.get("dom_html", ""),
        screenshot_base64=result.get("screenshot_base64", ""),
        all_stages=stages,
        error_message=error
    )
    
    return {"success": True, "recovering": True}


def _complete_runner_phase(redis_client, session_id: str, state: Dict) -> Dict:
    """Complete runner phase and persist updated stages if needed"""
    phase = state["phase"]

    logger.info(f"[FormsRunner] {phase} phase complete for session {session_id}")

    _update_runner_state(redis_client, session_id, {
        "status": "completed"
    })

    # Persist updated stages to DB if modified
    if state.get("stages_updated") == "true":
        persist_runner_stages.delay(
            session_id=session_id,
            phase=phase,
            stages=state["stages"],
            network_id=state["network_id"],
            form_route_id=state["form_route_id"]
        )

    # Signal phase complete (orchestrator will pick this up)
    result_key = f"runner_phase_complete:{session_id}"
    redis_client.setex(result_key, 300, json.dumps({
        "phase": phase,
        "success": True,
        "stages_updated": state.get("stages_updated") == "true"
    }))

    # Trigger mapping phase if navigation completed
    if phase == "navigate":
        trigger_mapping_phase.delay(session_id)
        logger.info(f"[FormsRunner] Queued mapping phase trigger for session {session_id}")

    return {
        "success": True,
        "phase_complete": True,
        "phase": phase,
        "stages_executed": state["total_stages"]
    }


# ============================================================
# AI ERROR RECOVERY TASK
# ============================================================

@shared_task(bind=True, max_retries=3, default_retry_delay=5,
             autoretry_for=(Exception,), retry_backoff=True)
def analyze_runner_error(
    self,
    session_id: str,
    failed_stage: Dict,
    dom_html: str,
    screenshot_base64: str,
    all_stages: List[Dict],
    error_message: str
) -> Dict:
    """
    Analyze step failure with AI and apply recovery.
    """
    from services.ai_budget_service import AIOperationType, BudgetExceededError
    
    logger.info(f"[FormsRunner] AI analyzing error for session {session_id}")
    
    redis_client = _get_redis_client()
    db = _get_db_session()
    
    try:
        state = _get_runner_state(redis_client, session_id)
        if not state:
            return {"decision": "general_error", "description": "Session not found"}
        
        company_id = state["company_id"]
        user_id = state["user_id"]
        product_id = state["product_id"]
        
        # Check budget and get API key
        api_key = _check_budget_and_get_api_key(db, company_id, product_id)
        
        if not api_key:
            return {"decision": "general_error", "description": "No API key"}
        
        # Analyze with AI
        from services.ai_forms_runner_error_prompter import AIFormPageRunError
        analyzer = AIFormPageRunError(api_key=api_key)
        
        result = analyzer.analyze_error(
            failed_stage=failed_stage,
            dom_html=dom_html,
            screenshot_base64=screenshot_base64,
            all_stages=all_stages,
            error_message=error_message
        )
        
        # Record usage
        input_tokens = len(dom_html) // 4 + len(screenshot_base64) // 100
        output_tokens = len(json.dumps(result)) // 4 if result else 0
        
        _record_usage(
            db, company_id, product_id, user_id,
            AIOperationType.FORMS_RUNNER_ERROR_ANALYZE,
            input_tokens, output_tokens
        )
        
        logger.info(f"[FormsRunner] AI decision: {result.get('decision')}")
        
        # Apply recovery
        apply_runner_recovery.delay(session_id, result)
        
        return result
        
    except BudgetExceededError as e:
        logger.warning(f"[FormsRunner] Budget exceeded")
        _update_runner_state(redis_client, session_id, {
            "status": "failed",
            "last_error": "AI budget exceeded"
        })
        return {"decision": "general_error", "description": "Budget exceeded", "budget_exceeded": True}
        
    except Exception as e:
        logger.error(f"[FormsRunner] AI analysis failed: {e}")
        raise
        
    finally:
        db.close()


@shared_task(bind=True, max_retries=2)
def apply_runner_recovery(self, session_id: str, ai_result: Dict) -> Dict:
    """
    Apply AI recovery decision and continue execution.
    """
    redis_client = _get_redis_client()
    
    state = _get_runner_state(redis_client, session_id)
    if not state:
        return {"success": False, "error": "Session not found"}
    
    decision = ai_result.get("decision")
    
    logger.info(f"[FormsRunner] Applying recovery: {decision}")
    
    if decision == "locator_changed":
        corrected_step = ai_result.get("corrected_step")
        if corrected_step:
            # Update stage
            stages = state["stages"]
            stages[state["current_stage_index"]] = corrected_step
            
            _update_runner_state(redis_client, session_id, {
                "stages": stages,
                "stages_updated": "true",
                "status": "running"
            })
            
            # Retry step
            execute_runner_step.delay(session_id)
            return {"success": True, "action": "retry_with_fix"}
    
    elif decision == "correction_steps":
        corrected_step = ai_result.get("corrected_step")
        presteps = ai_result.get("presteps", [])
        
        if corrected_step:
            stages = state["stages"]
            stages[state["current_stage_index"]] = corrected_step
            
            _update_runner_state(redis_client, session_id, {
                "stages": stages,
                "stages_updated": "true",
                "status": "running"
            })
            
            if presteps:
                # Execute presteps then retry
                execute_presteps_and_retry.delay(session_id, presteps)
            else:
                # Just retry
                execute_runner_step.delay(session_id)
            
            return {"success": True, "action": "correction_applied"}
    
    elif decision == "general_error":
        # Wait and retry
        retry_count = state.get("retry_count", 0)
        if retry_count < 3:
            _update_runner_state(redis_client, session_id, {
                "retry_count": str(retry_count + 1),
                "status": "running"
            })
            
            # Wait then retry
            runner_wait_and_retry.apply_async(
                args=[session_id],
                countdown=60  # Wait 60 seconds
            )
            return {"success": True, "action": "wait_and_retry"}
        else:
            _update_runner_state(redis_client, session_id, {
                "status": "failed",
                "last_error": "General error - max retries exceeded"
            })
            return {"success": False, "error": "Max retries exceeded"}
    
    elif decision == "need_healing":
        _update_runner_state(redis_client, session_id, {
            "status": "failed",
            "last_error": f"Need healing: {ai_result.get('description', '')}"
        })
        return {"success": False, "error": "Need healing - form re-analysis required"}
    
    # Unknown decision
    _update_runner_state(redis_client, session_id, {
        "status": "failed",
        "last_error": f"Unknown AI decision: {decision}"
    })
    return {"success": False, "error": f"Unknown decision: {decision}"}


@shared_task(bind=True)
def execute_presteps_and_retry(self, session_id: str, presteps: List[Dict]) -> Dict:
    """
    Execute presteps then retry the main step.
    """
    redis_client = _get_redis_client()
    
    state = _get_runner_state(redis_client, session_id)
    if not state:
        return {"success": False, "error": "Session not found"}
    
    logger.info(f"[FormsRunner] Executing {len(presteps)} presteps for session {session_id}")
    
    # Execute each prestep
    for i, prestep in enumerate(presteps):
        result = _execute_step_via_agent(session_id, prestep, state["user_id"])
        
        if not result.get("success"):
            logger.warning(f"[FormsRunner] Prestep {i+1} failed: {result.get('error')}")
            # Continue anyway - presteps are best effort
        
        time.sleep(0.3)  # Small delay between steps
    
    # Now retry the main step
    execute_runner_step.delay(session_id)
    
    return {"success": True, "presteps_executed": len(presteps)}


@shared_task(bind=True)
def runner_wait_and_retry(self, session_id: str) -> Dict:
    """
    Wait task - used for general_error recovery.
    (Countdown already applied when called)
    """
    redis_client = _get_redis_client()
    
    state = _get_runner_state(redis_client, session_id)
    if not state:
        return {"success": False, "error": "Session not found"}
    
    if state["status"] != "running":
        return {"success": False, "error": f"Session status: {state['status']}"}
    
    logger.info(f"[FormsRunner] Retrying after wait for session {session_id}")
    
    # Retry step
    execute_runner_step.delay(session_id)
    
    return {"success": True, "action": "retry_triggered"}


# ============================================================
# PERSISTENCE TASK
# ============================================================

@shared_task(bind=True, max_retries=3, default_retry_delay=10,
             autoretry_for=(Exception,), retry_backoff=True)
def persist_runner_stages(
    self,
    session_id: str,
    phase: str,
    stages: List[Dict],
    network_id: int,
    form_route_id: int,
    network_url: str = ""
) -> Dict:
    """
    Persist updated stages to database.
    
    - Login stages → networks.login_stages
    - Navigation stages → form_page_routes.navigation_steps
    """
    logger.info(f"[FormsRunner] Persisting {phase} stages for session {session_id}")
    
    db = _get_db_session()
    
    try:
        if phase == "login" and network_id:
            # Login stages are managed by form pages discovery, not runner
            logger.info(f"[FormsRunner] Login phase complete for network {network_id} (stages managed by discovery)")
            return {"success": True, "phase": "login"}

        elif phase == "navigate" and form_route_id:
            # Navigation stages are managed by form pages discovery, not runner
            logger.info(
                f"[FormsRunner] Navigate phase complete for form_route {form_route_id} (stages managed by discovery)")
            return {"success": True, "phase": "navigate"}

        return {"success": False, "error": "Unknown phase"}
        
    except Exception as e:
        db.rollback()
        logger.error(f"[FormsRunner] Failed to persist stages: {e}")
        raise
        
    finally:
        db.close()


# ============================================================
# STATUS / HELPER TASKS
# ============================================================

@shared_task
def get_runner_status(session_id: str) -> Dict:
    """Get current runner status"""
    redis_client = _get_redis_client()
    state = _get_runner_state(redis_client, session_id)
    
    if not state:
        return {"error": "Session not found"}
    
    return {
        "session_id": session_id,
        "phase": state.get("phase"),
        "status": state.get("status"),
        "progress": f"{state.get('current_stage_index', 0) + 1}/{state.get('total_stages', 0)}",
        "last_error": state.get("last_error", ""),
        "stages_updated": state.get("stages_updated") == "true"
    }


@shared_task
def cancel_runner(session_id: str) -> Dict:
    """Cancel a running runner session"""
    redis_client = _get_redis_client()
    
    state = _get_runner_state(redis_client, session_id)
    if not state:
        return {"success": False, "error": "Session not found"}
    
    _update_runner_state(redis_client, session_id, {
        "status": "cancelled"
    })
    
    logger.info(f"[FormsRunner] Cancelled session {session_id}")
    
    return {"success": True, "status": "cancelled"}


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def trigger_mapping_phase(self, session_id: str) -> Dict:
    """
    Trigger mapping phase after navigation completes.
    Called automatically by runner when navigate phase finishes.
    """
    logger.info(f"[FormsRunner] Triggering mapping phase for session {session_id}")
    print(f"[TRACE] trigger_mapping_phase CELERY TASK CALLED for session={session_id}")
    from models.database import SessionLocal
    from services.form_mapper_orchestrator import FormMapperOrchestrator
    
    db = SessionLocal()
    try:
        orchestrator = FormMapperOrchestrator(db)
        result = orchestrator.start_mapping_phase(session_id)
        
        if result.get("success"):
            logger.info(f"[FormsRunner] Mapping phase started for session {session_id}")
        else:
            logger.error(f"[FormsRunner] Failed to start mapping: {result.get('error')}")
        
        return result
        
    except Exception as e:
        logger.error(f"[FormsRunner] Error triggering mapping phase: {e}", exc_info=True)
        raise self.retry(exc=e)
    finally:
        db.close()
