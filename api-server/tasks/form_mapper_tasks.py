# ============================================================================
# Form Mapper - Celery Tasks
# ============================================================================
# All AI-heavy operations are handled by Celery workers.
# Results are stored in Redis for FastAPI orchestrator to pick up.
# ============================================================================

import json
import logging
import os
import redis
from typing import Dict, List, Optional, Any
from datetime import datetime
from celery import shared_task

logger = logging.getLogger(__name__)

# Redis client for storing results
redis_client = redis.Redis(
    host=os.environ.get('REDIS_HOST', 'redis'),
    port=int(os.environ.get('REDIS_PORT', 6379)),
    db=int(os.environ.get('REDIS_DB', 0)),
    decode_responses=True
)

# Constants
RESULT_TTL = 3600  # 1 hour
CLAUDE_MODEL = "claude-sonnet-4-5-20250929"


# ============================================================================
# Helper Functions
# ============================================================================

def get_session_data(session_id: str) -> Optional[Dict]:
    """Get session data from Redis"""
    key = f"mapper_session:{session_id}"
    data = redis_client.hgetall(key)
    if not data:
        return None
    
    # Parse JSON fields
    json_fields = [
        'config', 'test_cases', 'steps', 'executed_steps', 'test_context',
        'recovery_failure_history', 'critical_fields_checklist',
        'current_path_junctions', 'previous_paths', 'reported_ui_issues'
    ]
    
    for field in json_fields:
        if field in data and data[field]:
            try:
                data[field] = json.loads(data[field])
            except json.JSONDecodeError:
                data[field] = {} if 'checklist' in field else []
    
    return data


def store_celery_result(session_id: str, task_type: str, result: Dict):
    """Store Celery task result in Redis for orchestrator to pick up"""
    key = f"mapper_celery_result:{session_id}:{task_type}"
    result['completed_at'] = datetime.utcnow().isoformat()
    redis_client.setex(key, RESULT_TTL, json.dumps(result))
    logger.info(f"[Celery] Stored result: {key}")


def increment_ai_usage(session_id: str, tokens_used: int, cost_estimate: float):
    """Increment AI usage counters in Redis"""
    key = f"mapper_session:{session_id}"
    redis_client.hincrby(key, 'ai_calls_count', 1)
    redis_client.hincrby(key, 'ai_tokens_used', tokens_used)
    redis_client.hincrbyfloat(key, 'ai_cost_estimate', cost_estimate)


def get_anthropic_api_key() -> str:
    """Get Anthropic API key from environment"""
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in environment")
    return api_key


# ============================================================================
# TASK: generate_steps_task
# ============================================================================

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def generate_steps_task(
    self,
    session_id: str,
    dom_html: str,
    screenshot_base64: Optional[str] = None
) -> Dict:
    """
    Generate initial test steps using Claude AI.
    
    Args:
        session_id: Mapping session ID
        dom_html: Current DOM HTML
        screenshot_base64: Optional screenshot for visual context
    
    Returns:
        Dict with 'success', 'steps', 'no_more_paths', etc.
    """
    try:
        logger.info(f"[generate_steps_task] Starting for session {session_id}")
        
        # Get session data from Redis
        session = get_session_data(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found in Redis")
        
        test_cases = session.get('test_cases', [])
        test_context = session.get('test_context', {})
        critical_fields = session.get('critical_fields_checklist')
        field_requirements = session.get('field_requirements_for_recovery')
        previous_paths = session.get('previous_paths')
        current_path_junctions = session.get('current_path_junctions')
        
        # Import AI helper (lazy import to avoid circular deps)
        from services.form_mapper_ai_helpers import AIFormMapperHelper
        
        api_key = get_anthropic_api_key()
        ai_helper = AIFormMapperHelper(api_key=api_key)
        
        # Call AI to generate steps
        result = ai_helper.generate_test_steps(
            dom_html=dom_html,
            test_cases=test_cases,
            test_context=test_context,
            screenshot_base64=screenshot_base64,
            critical_fields_checklist=critical_fields,
            field_requirements=field_requirements,
            previous_paths=previous_paths,
            current_path_junctions=current_path_junctions
        )
        
        steps = result.get('steps', [])
        no_more_paths = result.get('no_more_paths', False)
        
        # Track AI usage (rough estimate based on content size)
        tokens_used = len(dom_html) // 4 + len(json.dumps(steps)) // 4
        cost_estimate = tokens_used * 0.000003  # Rough estimate
        increment_ai_usage(session_id, tokens_used, cost_estimate)
        
        # Store result for orchestrator
        celery_result = {
            'success': True,
            'steps': steps,
            'no_more_paths': no_more_paths,
            'steps_count': len(steps),
            'ai_tokens_used': tokens_used
        }
        store_celery_result(session_id, 'generate_steps', celery_result)
        
        logger.info(f"[generate_steps_task] Generated {len(steps)} steps for session {session_id}")
        return celery_result
        
    except Exception as e:
        logger.error(f"[generate_steps_task] Error: {e}", exc_info=True)
        
        celery_result = {
            'success': False,
            'error': str(e),
            'steps': []
        }
        store_celery_result(session_id, 'generate_steps', celery_result)
        
        # Retry on transient errors
        if "overloaded" in str(e).lower() or "rate" in str(e).lower():
            raise self.retry(exc=e)
        
        return celery_result


# ============================================================================
# TASK: regenerate_steps_task
# ============================================================================

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def regenerate_steps_task(
    self,
    session_id: str,
    dom_html: str,
    executed_steps: List[Dict],
    screenshot_base64: Optional[str] = None
) -> Dict:
    """
    Regenerate remaining test steps after DOM change.
    
    Args:
        session_id: Mapping session ID
        dom_html: Current DOM HTML
        executed_steps: Steps already executed
        screenshot_base64: Optional screenshot
    
    Returns:
        Dict with 'success', 'steps', 'no_more_paths', etc.
    """
    try:
        logger.info(f"[regenerate_steps_task] Starting for session {session_id}")
        
        session = get_session_data(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        test_cases = session.get('test_cases', [])
        test_context = session.get('test_context', {})
        critical_fields = session.get('critical_fields_checklist')
        field_requirements = session.get('field_requirements_for_recovery')
        previous_paths = session.get('previous_paths')
        current_path_junctions = session.get('current_path_junctions')
        
        from services.form_mapper_ai_helpers import AIFormMapperHelper
        
        api_key = get_anthropic_api_key()
        ai_helper = AIFormMapperHelper(api_key=api_key)
        
        result = ai_helper.regenerate_steps(
            dom_html=dom_html,
            executed_steps=executed_steps,
            test_cases=test_cases,
            test_context=test_context,
            screenshot_base64=screenshot_base64,
            critical_fields_checklist=critical_fields,
            field_requirements=field_requirements,
            previous_paths=previous_paths,
            current_path_junctions=current_path_junctions
        )
        
        steps = result.get('steps', [])
        no_more_paths = result.get('no_more_paths', False)
        
        tokens_used = len(dom_html) // 4 + len(json.dumps(steps)) // 4
        increment_ai_usage(session_id, tokens_used, tokens_used * 0.000003)
        
        celery_result = {
            'success': True,
            'steps': steps,
            'no_more_paths': no_more_paths,
            'steps_count': len(steps)
        }
        store_celery_result(session_id, 'regenerate_steps', celery_result)
        
        logger.info(f"[regenerate_steps_task] Regenerated {len(steps)} steps for session {session_id}")
        return celery_result
        
    except Exception as e:
        logger.error(f"[regenerate_steps_task] Error: {e}", exc_info=True)
        
        celery_result = {
            'success': False,
            'error': str(e),
            'steps': []
        }
        store_celery_result(session_id, 'regenerate_steps', celery_result)
        
        if "overloaded" in str(e).lower():
            raise self.retry(exc=e)
        
        return celery_result


# ============================================================================
# TASK: alert_recovery_task
# ============================================================================

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def alert_recovery_task(
    self,
    session_id: str,
    alert_info: Dict,
    dom_html: str,
    executed_steps: List[Dict],
    step_where_alert_appeared: int,
    screenshot_base64: Optional[str] = None,
    gathered_error_info: Optional[Dict] = None
) -> Dict:
    """
    Generate recovery steps after alert/validation error.
    
    Args:
        session_id: Mapping session ID
        alert_info: Alert details (type, text)
        dom_html: Current DOM HTML
        executed_steps: Steps executed before alert
        step_where_alert_appeared: Step number that triggered alert
        screenshot_base64: Optional screenshot
        gathered_error_info: Optional validation errors from DOM
    
    Returns:
        Dict with 'success', 'scenario', 'steps', 'problematic_fields', etc.
    """
    try:
        logger.info(f"[alert_recovery_task] Starting for session {session_id}")
        
        session = get_session_data(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        test_cases = session.get('test_cases', [])
        test_context = session.get('test_context', {})
        
        from services.form_mapper_ai_helpers import AIAlertRecoveryHelper
        
        api_key = get_anthropic_api_key()
        ai_recovery = AIAlertRecoveryHelper(api_key=api_key)
        
        result = ai_recovery.regenerate_steps_after_alert(
            alert_info=alert_info,
            executed_steps=executed_steps,
            dom_html=dom_html,
            screenshot_base64=screenshot_base64,
            test_cases=test_cases,
            test_context=test_context,
            step_where_alert_appeared=step_where_alert_appeared,
            include_accept_step=False,
            gathered_error_info=gathered_error_info
        )
        
        if not result:
            raise ValueError("AI returned empty result")
        
        scenario = result.get('scenario', 'B')
        steps = result.get('steps', [])
        issue_type = result.get('issue_type', 'ai_issue')
        problematic_fields = result.get('problematic_fields', [])
        field_requirements = result.get('field_requirements', '')
        
        tokens_used = len(dom_html) // 4 + len(json.dumps(steps)) // 4
        increment_ai_usage(session_id, tokens_used, tokens_used * 0.000003)
        
        celery_result = {
            'success': True,
            'scenario': scenario,
            'issue_type': issue_type,
            'steps': steps,
            'problematic_fields': problematic_fields,
            'field_requirements': field_requirements,
            'explanation': result.get('explanation', ''),
            'problematic_field_claimed': result.get('problematic_field_claimed', ''),
            'our_action': result.get('our_action', '')
        }
        store_celery_result(session_id, 'alert_recovery', celery_result)
        
        logger.info(f"[alert_recovery_task] Scenario {scenario} for session {session_id}")
        return celery_result
        
    except Exception as e:
        logger.error(f"[alert_recovery_task] Error: {e}", exc_info=True)
        
        celery_result = {
            'success': False,
            'error': str(e)
        }
        store_celery_result(session_id, 'alert_recovery', celery_result)
        
        if "overloaded" in str(e).lower():
            raise self.retry(exc=e)
        
        return celery_result


# ============================================================================
# TASK: failure_recovery_task
# ============================================================================

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def failure_recovery_task(
    self,
    session_id: str,
    failed_step: Dict,
    dom_html: str,
    executed_steps: List[Dict],
    screenshot_base64: str,
    attempt_number: int,
    recovery_failure_history: List[Dict]
) -> Dict:
    """
    Generate recovery steps after step execution failure.
    
    Args:
        session_id: Mapping session ID
        failed_step: The step that failed
        dom_html: Current DOM HTML
        executed_steps: Steps executed before failure
        screenshot_base64: Screenshot showing current state
        attempt_number: Which recovery attempt this is
        recovery_failure_history: History of failed recovery attempts
    
    Returns:
        Dict with 'success', 'steps', etc.
    """
    try:
        logger.info(f"[failure_recovery_task] Starting for session {session_id}, attempt {attempt_number}")
        
        session = get_session_data(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        test_cases = session.get('test_cases', [])
        test_context = session.get('test_context', {})
        
        from services.form_mapper_ai_helpers import AIFormMapperHelper
        
        api_key = get_anthropic_api_key()
        ai_helper = AIFormMapperHelper(api_key=api_key)
        
        recovery_steps = ai_helper.analyze_failure_and_recover(
            failed_step=failed_step,
            executed_steps=executed_steps,
            fresh_dom=dom_html,
            screenshot_base64=screenshot_base64,
            test_cases=test_cases,
            test_context=test_context,
            attempt_number=attempt_number,
            recovery_failure_history=recovery_failure_history
        )
        
        tokens_used = len(dom_html) // 4 + len(json.dumps(recovery_steps or [])) // 4
        increment_ai_usage(session_id, tokens_used, tokens_used * 0.000003)
        
        celery_result = {
            'success': True,
            'steps': recovery_steps or [],
            'steps_count': len(recovery_steps) if recovery_steps else 0
        }
        store_celery_result(session_id, 'failure_recovery', celery_result)
        
        logger.info(f"[failure_recovery_task] Generated {len(recovery_steps or [])} recovery steps")
        return celery_result
        
    except Exception as e:
        logger.error(f"[failure_recovery_task] Error: {e}", exc_info=True)
        
        celery_result = {
            'success': False,
            'error': str(e),
            'steps': []
        }
        store_celery_result(session_id, 'failure_recovery', celery_result)
        
        if "overloaded" in str(e).lower():
            raise self.retry(exc=e)
        
        return celery_result


# ============================================================================
# TASK: ui_verify_task
# ============================================================================

@shared_task(bind=True, max_retries=2, default_retry_delay=15)
def ui_verify_task(
    self,
    session_id: str,
    screenshot_base64: str
) -> Dict:
    """
    Verify UI for visual defects.
    
    Args:
        session_id: Mapping session ID
        screenshot_base64: Screenshot to analyze
    
    Returns:
        Dict with 'success', 'ui_issue', etc.
    """
    try:
        logger.info(f"[ui_verify_task] Starting for session {session_id}")
        
        session = get_session_data(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        reported_issues = session.get('reported_ui_issues', [])
        
        from services.form_mapper_ai_helpers import AIUIVisualVerifier
        
        api_key = get_anthropic_api_key()
        ui_verifier = AIUIVisualVerifier(api_key=api_key)
        
        ui_issue = ui_verifier.verify_visual_ui(
            screenshot_base64=screenshot_base64,
            previously_reported_issues=reported_issues
        )
        
        # Estimate tokens for vision call
        tokens_used = 2000  # Rough estimate for image analysis
        increment_ai_usage(session_id, tokens_used, tokens_used * 0.000003)
        
        celery_result = {
            'success': True,
            'ui_issue': ui_issue or '',
            'has_issue': bool(ui_issue)
        }
        store_celery_result(session_id, 'ui_verify', celery_result)
        
        if ui_issue:
            logger.info(f"[ui_verify_task] UI issue found: {ui_issue[:100]}...")
        else:
            logger.info(f"[ui_verify_task] No UI issues found")
        
        return celery_result
        
    except Exception as e:
        logger.error(f"[ui_verify_task] Error: {e}", exc_info=True)
        
        celery_result = {
            'success': False,
            'error': str(e),
            'ui_issue': ''
        }
        store_celery_result(session_id, 'ui_verify', celery_result)
        
        if "overloaded" in str(e).lower():
            raise self.retry(exc=e)
        
        return celery_result


# ============================================================================
# TASK: assign_test_cases_task
# ============================================================================

@shared_task(bind=True, max_retries=2, default_retry_delay=15)
def assign_test_cases_task(
    self,
    session_id: str,
    steps: List[Dict]
) -> Dict:
    """
    Assign test_case field to completed stages (final step).
    
    Args:
        session_id: Mapping session ID
        steps: All executed steps
    
    Returns:
        Dict with 'success', 'steps' (with test_case assigned), etc.
    """
    try:
        logger.info(f"[assign_test_cases_task] Starting for session {session_id}")
        
        session = get_session_data(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        test_cases = session.get('test_cases', [])
        
        from services.form_mapper_ai_helpers import AIFormPageEndPrompter
        
        api_key = get_anthropic_api_key()
        end_prompter = AIFormPageEndPrompter(api_key=api_key)
        
        updated_steps = end_prompter.assign_test_cases(steps, test_cases)
        
        tokens_used = len(json.dumps(steps)) // 4 + len(json.dumps(updated_steps)) // 4
        increment_ai_usage(session_id, tokens_used, tokens_used * 0.000003)
        
        celery_result = {
            'success': True,
            'steps': updated_steps,
            'steps_count': len(updated_steps)
        }
        store_celery_result(session_id, 'assign_test_cases', celery_result)
        
        logger.info(f"[assign_test_cases_task] Assigned test cases to {len(updated_steps)} steps")
        return celery_result
        
    except Exception as e:
        logger.error(f"[assign_test_cases_task] Error: {e}", exc_info=True)
        
        celery_result = {
            'success': False,
            'error': str(e),
            'steps': steps  # Return original steps on failure
        }
        store_celery_result(session_id, 'assign_test_cases', celery_result)
        
        return celery_result
