# ============================================================================
# Form Mapper - Orchestrator Service
# ============================================================================
# The "brain" of the Form Mapper system. Implements the state machine that:
# - Manages session lifecycle
# - Processes agent results and decides next actions
# - Queues Celery tasks for AI operations
# - Queues agent tasks for browser operations
# - Handles alerts, DOM changes, failures, and recovery
# ============================================================================

import json
import logging
import os
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import redis
from sqlalchemy.orm import Session

from models.form_mapper_models import (
    FormMapperSession, FormMapResult, FormMapperSessionLog
)
from tasks.form_mapper_tasks import (
    generate_steps_task, regenerate_steps_task, alert_recovery_task,
    failure_recovery_task, ui_verify_task, assign_test_cases_task
)

logger = logging.getLogger(__name__)

# Redis client
redis_client = redis.Redis(
    host=os.environ.get('REDIS_HOST', 'redis'),
    port=int(os.environ.get('REDIS_PORT', 6379)),
    db=int(os.environ.get('REDIS_DB', 0)),
    decode_responses=True
)

# Constants
SESSION_TTL = 86400  # 24 hours
MAX_CONSECUTIVE_FAILURES = 3
MAX_RECOVERY_ATTEMPTS = 3


# ============================================================================
# Agent Task Types
# ============================================================================
class AgentTaskType:
    FORM_MAPPER_INIT = "form_mapper_init"
    FORM_MAPPER_EXTRACT_DOM = "form_mapper_extract_dom"
    FORM_MAPPER_EXEC_STEP = "form_mapper_exec_step"
    FORM_MAPPER_SCREENSHOT = "form_mapper_screenshot"
    FORM_MAPPER_NAVIGATE = "form_mapper_navigate"
    FORM_MAPPER_CLOSE = "form_mapper_close"


# ============================================================================
# Session Status
# ============================================================================
class SessionStatus:
    PENDING = "pending"
    INITIALIZING = "initializing"
    EXTRACTING_DOM = "extracting_dom"
    GENERATING_STEPS = "generating_steps"
    EXECUTING = "executing"
    RECOVERING = "recovering"
    REGENERATING = "regenerating"
    VERIFYING_UI = "verifying_ui"
    COMPLETING = "completing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ============================================================================
# FormMapperOrchestrator Class
# ============================================================================
class FormMapperOrchestrator:
    """
    Orchestrates the Form Mapper workflow using a state machine approach.
    
    Flow:
    1. create_session() - Create DB record + Redis state
    2. start_mapping() - Queue INIT task to agent
    3. process_agent_result() - Main loop: process result → decide next action
    4. check_and_process_celery_results() - Poll for AI results → queue next agent task
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    # ========================================================================
    # Session Management
    # ========================================================================
    
    def create_session(
        self,
        form_page_route_id: int,
        user_id: int,
        network_id: Optional[int] = None,
        company_id: Optional[int] = None,
        config: Optional[Dict] = None
    ) -> FormMapperSession:
        """
        Create a new mapping session.
        
        Args:
            form_page_route_id: ID of the form page route to map
            user_id: User starting the mapping
            network_id: Network ownership
            company_id: Company ownership
            config: Session configuration
        
        Returns:
            Created FormMapperSession
        """
        # Default config
        default_config = {
            "browser": "chrome",
            "headless": False,
            "enable_ui_verification": True,
            "use_full_dom": True,
            "include_js_in_dom": True,
            "max_retries": 3,
            "enable_junction_discovery": True,
            "max_junction_paths": 5
        }
        
        if config:
            default_config.update(config)
        
        # Create DB record
        session = FormMapperSession(
            form_page_route_id=form_page_route_id,
            user_id=user_id,
            network_id=network_id,
            company_id=company_id,
            config=default_config,
            status=SessionStatus.PENDING
        )
        
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        
        logger.info(f"[Orchestrator] Created session {session.id} for route {form_page_route_id}")
        
        return session
    
    def start_mapping(
        self,
        session_id: int,
        agent_id: str,
        form_page_route: Any,  # FormPageRoute model
        test_cases: List[Dict]
    ) -> bool:
        """
        Start the mapping process for a session.
        
        Args:
            session_id: Session ID
            agent_id: Agent to assign
            form_page_route: The form page route with URL, navigation steps, etc.
            test_cases: Test cases to generate steps for
        
        Returns:
            True if started successfully
        """
        # Get session from DB
        session = self.db.query(FormMapperSession).filter(
            FormMapperSession.id == session_id
        ).first()
        
        if not session:
            logger.error(f"[Orchestrator] Session {session_id} not found")
            return False
        
        # Initialize Redis state
        self._init_redis_state(
            session_id=session_id,
            form_page_route=form_page_route,
            test_cases=test_cases,
            config=session.config
        )
        
        # Update DB
        session.agent_id = agent_id
        session.status = SessionStatus.INITIALIZING
        session.started_at = datetime.utcnow()
        self.db.commit()
        
        # Log event
        self._log_event(session_id, "state_change", {
            "from": SessionStatus.PENDING,
            "to": SessionStatus.INITIALIZING
        })
        
        # Queue INIT task to agent
        self._queue_agent_task(
            user_id=session.user_id,
            task_type=AgentTaskType.FORM_MAPPER_INIT,
            session_id=session_id,
            payload={
                "url": form_page_route.url,
                "login_url": form_page_route.login_url,
                "username": form_page_route.username,
                "password": form_page_route.password,
                "navigation_steps": form_page_route.navigation_steps or [],
                "browser": session.config.get("browser", "chrome"),
                "headless": session.config.get("headless", False)
            }
        )
        
        logger.info(f"[Orchestrator] Started mapping for session {session_id}")
        return True
    
    def _init_redis_state(
        self,
        session_id: int,
        form_page_route: Any,
        test_cases: List[Dict],
        config: Dict
    ):
        """Initialize session state in Redis"""
        key = f"mapper_session:{session_id}"
        
        state = {
            "session_id": str(session_id),
            "form_page_route_id": str(form_page_route.id),
            "status": SessionStatus.INITIALIZING,
            "config": json.dumps(config),
            "test_cases": json.dumps(test_cases),
            "base_url": form_page_route.url,
            "current_dom_hash": "",
            "steps": "[]",
            "executed_steps": "[]",
            "current_step_index": "0",
            "test_context": "{}",
            "consecutive_failures": "0",
            "recovery_attempts": "0",
            "pending_celery_task": "",
            "pending_celery_task_id": "",
            # Alert recovery
            "critical_fields_checklist": "{}",
            "field_requirements_for_recovery": "",
            # Junction discovery
            "current_path_number": "1",
            "current_path_junctions": "[]",
            "previous_paths": "[]",
            # UI verification
            "reported_ui_issues": "[]",
            "enable_ui_verification": str(config.get("enable_ui_verification", True)),
            # AI tracking
            "ai_calls_count": "0",
            "ai_tokens_used": "0",
            "ai_cost_estimate": "0"
        }
        
        redis_client.hset(key, mapping=state)
        redis_client.expire(key, SESSION_TTL)
        
        logger.info(f"[Orchestrator] Initialized Redis state for session {session_id}")
    
    # ========================================================================
    # Agent Result Processing (Main State Machine)
    # ========================================================================
    
    def process_agent_result(
        self,
        session_id: int,
        result: Dict
    ) -> Dict[str, Any]:
        """
        Process result from agent and decide next action.
        This is the main state machine entry point.
        
        Args:
            session_id: Session ID
            result: Agent task result
        
        Returns:
            Dict with status and next action info
        """
        task_type = result.get("task_type")
        success = result.get("success", False)
        
        logger.info(f"[Orchestrator] Processing {task_type} result for session {session_id}")
        
        # Log the result
        self._log_event(session_id, "task_completed", {
            "task_type": task_type,
            "success": success
        })
        
        if not success:
            return self._handle_agent_failure(session_id, result)
        
        # Route to appropriate handler
        handlers = {
            AgentTaskType.FORM_MAPPER_INIT: self._handle_init_complete,
            AgentTaskType.FORM_MAPPER_EXTRACT_DOM: self._handle_dom_extracted,
            AgentTaskType.FORM_MAPPER_EXEC_STEP: self._handle_step_executed,
            AgentTaskType.FORM_MAPPER_SCREENSHOT: self._handle_screenshot_captured,
            AgentTaskType.FORM_MAPPER_NAVIGATE: self._handle_navigation_complete,
            AgentTaskType.FORM_MAPPER_CLOSE: self._handle_close_complete,
        }
        
        handler = handlers.get(task_type)
        if handler:
            return handler(session_id, result)
        else:
            logger.warning(f"[Orchestrator] Unknown task type: {task_type}")
            return {"status": "error", "message": f"Unknown task type: {task_type}"}
    
    def _handle_init_complete(self, session_id: int, result: Dict) -> Dict:
        """Handle browser initialization complete - queue DOM extraction"""
        self._update_status(session_id, SessionStatus.EXTRACTING_DOM)
        
        config = self._get_redis_json(session_id, "config")
        
        self._queue_agent_task(
            user_id=self._get_user_id(session_id),
            task_type=AgentTaskType.FORM_MAPPER_EXTRACT_DOM,
            session_id=session_id,
            payload={
                "use_full_dom": config.get("use_full_dom", True),
                "include_js_in_dom": config.get("include_js_in_dom", True)
            }
        )
        
        return {"status": "ok", "next_action": "extract_dom"}
    
    def _handle_dom_extracted(self, session_id: int, result: Dict) -> Dict:
        """Handle DOM extraction complete - queue step generation"""
        dom_html = result.get("dom_html", "")
        dom_hash = hashlib.md5(dom_html.encode()).hexdigest()
        
        # Store DOM hash
        redis_client.hset(f"mapper_session:{session_id}", "current_dom_hash", dom_hash)
        
        # Store DOM temporarily for Celery task
        redis_client.setex(
            f"mapper_dom:{session_id}",
            3600,  # 1 hour TTL
            dom_html
        )
        
        # Check if UI verification is enabled
        enable_ui_verify = self._get_redis_value(session_id, "enable_ui_verification") == "True"
        
        if enable_ui_verify:
            # First capture screenshot for UI verification
            self._update_status(session_id, SessionStatus.VERIFYING_UI)
            self._queue_agent_task(
                user_id=self._get_user_id(session_id),
                task_type=AgentTaskType.FORM_MAPPER_SCREENSHOT,
                session_id=session_id,
                payload={
                    "scenario": "initial_ui_verify",
                    "encode_base64": True
                }
            )
            return {"status": "ok", "next_action": "capture_screenshot_for_ui_verify"}
        else:
            # Skip UI verification, go directly to step generation
            return self._queue_step_generation(session_id)
    
    def _handle_screenshot_captured(self, session_id: int, result: Dict) -> Dict:
        """Handle screenshot captured - could be for UI verify or other purposes"""
        scenario = result.get("scenario", "")
        screenshot_base64 = result.get("screenshot_base64", "")
        
        if scenario == "initial_ui_verify":
            # Queue UI verification task
            self._set_pending_celery_task(session_id, "ui_verify")
            
            ui_verify_task.delay(
                session_id=str(session_id),
                screenshot_base64=screenshot_base64
            )
            
            return {"status": "ok", "next_action": "waiting_for_ui_verify"}
        
        elif scenario == "for_step_generation":
            # Store screenshot and queue step generation
            redis_client.setex(
                f"mapper_screenshot:{session_id}",
                3600,
                screenshot_base64
            )
            return self._queue_step_generation(session_id, with_screenshot=True)
        
        elif scenario == "for_regeneration":
            # Store and queue regeneration
            redis_client.setex(
                f"mapper_screenshot:{session_id}",
                3600,
                screenshot_base64
            )
            return self._queue_step_regeneration(session_id, with_screenshot=True)
        
        return {"status": "ok", "next_action": "screenshot_captured"}
    
    def _handle_step_executed(self, session_id: int, result: Dict) -> Dict:
        """Handle step execution complete - check for alerts/DOM changes"""
        step_index = result.get("step_index", 0)
        
        # Check for alert
        if result.get("alert_present"):
            return self._handle_alert_detected(session_id, result, step_index)
        
        # Check for DOM change
        if result.get("dom_changed"):
            return self._handle_dom_changed(session_id, result, step_index)
        
        # Update executed steps
        executed_step = result.get("executed_step", {})
        self._append_executed_step(session_id, executed_step)
        
        # Reset failure counter on success
        redis_client.hset(f"mapper_session:{session_id}", "consecutive_failures", "0")
        
        # Check if all steps complete
        steps = self._get_redis_json(session_id, "steps")
        current_index = int(self._get_redis_value(session_id, "current_step_index") or "0")
        next_index = current_index + 1
        
        if next_index >= len(steps):
            return self._handle_all_steps_complete(session_id)
        
        # Execute next step
        redis_client.hset(f"mapper_session:{session_id}", "current_step_index", str(next_index))
        return self._execute_step(session_id, next_index)
    
    def _handle_alert_detected(self, session_id: int, result: Dict, step_index: int) -> Dict:
        """Handle alert detection - queue alert recovery"""
        self._update_status(session_id, SessionStatus.RECOVERING)
        
        alert_info = {
            "alert_type": result.get("alert_type", "alert"),
            "alert_text": result.get("alert_text", "")
        }
        
        self._log_event(session_id, "alert_detected", alert_info)
        
        # Add accept_alert step to executed steps (alert was already accepted by agent)
        accept_step = {
            "step_number": step_index + 1,
            "action": "accept_alert",
            "description": f"Accept alert: {alert_info['alert_text'][:50]}...",
            "alert_text": alert_info["alert_text"]
        }
        self._append_executed_step(session_id, accept_step)
        
        # Get current state for recovery
        dom_html = redis_client.get(f"mapper_dom:{session_id}") or ""
        executed_steps = self._get_redis_json(session_id, "executed_steps")
        test_cases = self._get_redis_json(session_id, "test_cases")
        
        # Queue Celery task for alert recovery
        self._set_pending_celery_task(session_id, "alert_recovery")
        
        alert_recovery_task.delay(
            session_id=str(session_id),
            alert_info=alert_info,
            dom_html=dom_html,
            executed_steps=executed_steps,
            step_where_alert_appeared=step_index,
            screenshot_base64=None,
            gathered_error_info=result.get("gathered_error_info")
        )
        
        return {"status": "ok", "next_action": "waiting_for_alert_recovery"}
    
    def _handle_dom_changed(self, session_id: int, result: Dict, step_index: int) -> Dict:
        """Handle DOM change - queue step regeneration"""
        self._update_status(session_id, SessionStatus.REGENERATING)
        
        new_dom_html = result.get("new_dom_html", "")
        new_dom_hash = hashlib.md5(new_dom_html.encode()).hexdigest()
        
        self._log_event(session_id, "dom_changed", {
            "step_index": step_index,
            "old_hash": result.get("old_dom_hash"),
            "new_hash": new_dom_hash,
            "fields_changed": result.get("fields_changed", False)
        })
        
        # Update stored DOM
        redis_client.hset(f"mapper_session:{session_id}", "current_dom_hash", new_dom_hash)
        redis_client.setex(f"mapper_dom:{session_id}", 3600, new_dom_html)
        
        # Add the executed step
        executed_step = result.get("executed_step", {})
        self._append_executed_step(session_id, executed_step)
        
        # Check if fields changed (might be a junction)
        if result.get("fields_changed"):
            # Capture screenshot for regeneration
            self._queue_agent_task(
                user_id=self._get_user_id(session_id),
                task_type=AgentTaskType.FORM_MAPPER_SCREENSHOT,
                session_id=session_id,
                payload={
                    "scenario": "for_regeneration",
                    "encode_base64": True
                }
            )
            return {"status": "ok", "next_action": "capture_screenshot_for_regeneration"}
        
        # Queue regeneration without screenshot
        return self._queue_step_regeneration(session_id, with_screenshot=False)
    
    def _handle_all_steps_complete(self, session_id: int) -> Dict:
        """Handle all steps complete - queue test case assignment"""
        self._update_status(session_id, SessionStatus.COMPLETING)
        
        executed_steps = self._get_redis_json(session_id, "executed_steps")
        
        # Queue Celery task to assign test cases
        self._set_pending_celery_task(session_id, "assign_test_cases")
        
        assign_test_cases_task.delay(
            session_id=str(session_id),
            steps=executed_steps
        )
        
        return {"status": "ok", "next_action": "waiting_for_test_case_assignment"}
    
    def _handle_navigation_complete(self, session_id: int, result: Dict) -> Dict:
        """Handle navigation complete - queue DOM extraction"""
        self._update_status(session_id, SessionStatus.EXTRACTING_DOM)
        
        config = self._get_redis_json(session_id, "config")
        
        self._queue_agent_task(
            user_id=self._get_user_id(session_id),
            task_type=AgentTaskType.FORM_MAPPER_EXTRACT_DOM,
            session_id=session_id,
            payload={
                "use_full_dom": config.get("use_full_dom", True),
                "include_js_in_dom": config.get("include_js_in_dom", True)
            }
        )
        
        return {"status": "ok", "next_action": "extract_dom"}
    
    def _handle_close_complete(self, session_id: int, result: Dict) -> Dict:
        """Handle browser close complete - finalize session"""
        # Clean up Redis temporary keys
        redis_client.delete(f"mapper_dom:{session_id}")
        redis_client.delete(f"mapper_screenshot:{session_id}")
        
        logger.info(f"[Orchestrator] Session {session_id} browser closed")
        
        return {"status": "ok", "next_action": "session_complete"}
    
    def _handle_agent_failure(self, session_id: int, result: Dict) -> Dict:
        """Handle agent task failure"""
        error = result.get("error", "Unknown error")
        task_type = result.get("task_type", "unknown")
        
        self._log_event(session_id, "error", {
            "task_type": task_type,
            "error": error
        })
        
        # Increment failure counter
        key = f"mapper_session:{session_id}"
        failures = int(redis_client.hget(key, "consecutive_failures") or "0") + 1
        redis_client.hset(key, "consecutive_failures", str(failures))
        
        if failures >= MAX_CONSECUTIVE_FAILURES:
            # Too many failures - mark session as failed
            self._update_status(session_id, SessionStatus.FAILED)
            self._update_db_session(session_id, {
                "status": SessionStatus.FAILED,
                "last_error": error,
                "completed_at": datetime.utcnow()
            })
            
            # Close browser
            self._queue_agent_task(
                user_id=self._get_user_id(session_id),
                task_type=AgentTaskType.FORM_MAPPER_CLOSE,
                session_id=session_id,
                payload={}
            )
            
            return {"status": "failed", "error": error}
        
        # Attempt recovery based on task type
        if task_type == AgentTaskType.FORM_MAPPER_EXEC_STEP:
            return self._attempt_step_recovery(session_id, result)
        
        # For other failures, retry the task
        logger.warning(f"[Orchestrator] Retrying {task_type} for session {session_id}")
        return {"status": "retrying", "task_type": task_type}
    
    def _attempt_step_recovery(self, session_id: int, result: Dict) -> Dict:
        """Attempt to recover from step execution failure"""
        self._update_status(session_id, SessionStatus.RECOVERING)
        
        failed_step = result.get("failed_step", {})
        dom_html = redis_client.get(f"mapper_dom:{session_id}") or ""
        executed_steps = self._get_redis_json(session_id, "executed_steps")
        recovery_attempts = int(self._get_redis_value(session_id, "recovery_attempts") or "0") + 1
        recovery_history = self._get_redis_json(session_id, "recovery_failure_history")
        
        if recovery_attempts > MAX_RECOVERY_ATTEMPTS:
            self._update_status(session_id, SessionStatus.FAILED)
            return {"status": "failed", "error": "Max recovery attempts exceeded"}
        
        redis_client.hset(f"mapper_session:{session_id}", "recovery_attempts", str(recovery_attempts))
        
        # Queue screenshot then recovery
        self._queue_agent_task(
            user_id=self._get_user_id(session_id),
            task_type=AgentTaskType.FORM_MAPPER_SCREENSHOT,
            session_id=session_id,
            payload={
                "scenario": "for_failure_recovery",
                "encode_base64": True,
                "failed_step": failed_step,
                "recovery_attempt": recovery_attempts
            }
        )
        
        return {"status": "ok", "next_action": "recovering"}
    
    # ========================================================================
    # Celery Result Processing
    # ========================================================================
    
    def check_and_process_celery_results(self, session_id: int) -> Optional[Dict]:
        """
        Check for pending Celery results and process them.
        Called periodically or on status check.
        
        Returns:
            Result dict if processed, None if no pending results
        """
        pending_task = self._get_redis_value(session_id, "pending_celery_task")
        
        if not pending_task:
            return None
        
        # Check for result
        result_key = f"mapper_celery_result:{session_id}:{pending_task}"
        result_json = redis_client.get(result_key)
        
        if not result_json:
            return None
        
        # Parse and process result
        result = json.loads(result_json)
        redis_client.delete(result_key)
        redis_client.hset(f"mapper_session:{session_id}", "pending_celery_task", "")
        
        logger.info(f"[Orchestrator] Processing Celery result: {pending_task}")
        
        # Route to handler
        handlers = {
            "generate_steps": self._process_generate_steps_result,
            "regenerate_steps": self._process_regenerate_steps_result,
            "alert_recovery": self._process_alert_recovery_result,
            "failure_recovery": self._process_failure_recovery_result,
            "ui_verify": self._process_ui_verify_result,
            "assign_test_cases": self._process_assign_test_cases_result,
        }
        
        handler = handlers.get(pending_task)
        if handler:
            return handler(session_id, result)
        
        return None
    
    def _process_generate_steps_result(self, session_id: int, result: Dict) -> Dict:
        """Process generate_steps Celery result"""
        if not result.get("success"):
            self._update_status(session_id, SessionStatus.FAILED)
            return {"status": "failed", "error": result.get("error")}
        
        steps = result.get("steps", [])
        
        if not steps:
            self._update_status(session_id, SessionStatus.FAILED)
            return {"status": "failed", "error": "No steps generated"}
        
        # Store steps
        redis_client.hset(f"mapper_session:{session_id}", mapping={
            "steps": json.dumps(steps),
            "current_step_index": "0"
        })
        
        # Update DB
        self._update_db_session(session_id, {"total_steps": len(steps)})
        
        self._update_status(session_id, SessionStatus.EXECUTING)
        
        # Execute first step
        return self._execute_step(session_id, 0)
    
    def _process_regenerate_steps_result(self, session_id: int, result: Dict) -> Dict:
        """Process regenerate_steps Celery result"""
        if not result.get("success"):
            self._update_status(session_id, SessionStatus.FAILED)
            return {"status": "failed", "error": result.get("error")}
        
        new_steps = result.get("steps", [])
        executed_steps = self._get_redis_json(session_id, "executed_steps")
        
        # Combine executed + new steps
        all_steps = executed_steps + new_steps
        
        redis_client.hset(f"mapper_session:{session_id}", mapping={
            "steps": json.dumps(all_steps),
            "current_step_index": str(len(executed_steps))
        })
        
        self._update_db_session(session_id, {"total_steps": len(all_steps)})
        self._update_status(session_id, SessionStatus.EXECUTING)
        
        if new_steps:
            return self._execute_step(session_id, len(executed_steps))
        else:
            return self._handle_all_steps_complete(session_id)
    
    def _process_alert_recovery_result(self, session_id: int, result: Dict) -> Dict:
        """Process alert_recovery Celery result"""
        if not result.get("success"):
            self._update_status(session_id, SessionStatus.FAILED)
            return {"status": "failed", "error": result.get("error")}
        
        scenario = result.get("scenario", "B")
        issue_type = result.get("issue_type", "ai_issue")
        new_steps = result.get("steps", [])
        
        self._log_event(session_id, "alert_recovery", {
            "scenario": scenario,
            "issue_type": issue_type,
            "steps_count": len(new_steps)
        })
        
        if scenario == "A":
            # Simple alert - append new steps and continue
            executed_steps = self._get_redis_json(session_id, "executed_steps")
            all_steps = executed_steps + new_steps
            
            redis_client.hset(f"mapper_session:{session_id}", mapping={
                "steps": json.dumps(all_steps),
                "current_step_index": str(len(executed_steps))
            })
            
            self._update_status(session_id, SessionStatus.EXECUTING)
            
            if new_steps:
                return self._execute_step(session_id, len(executed_steps))
            else:
                return self._handle_all_steps_complete(session_id)
        
        elif scenario == "B":
            if issue_type == "real_issue":
                # Real validation issue - mark as failed with info
                self._update_status(session_id, SessionStatus.FAILED)
                self._update_db_session(session_id, {
                    "status": SessionStatus.FAILED,
                    "last_error": f"Real validation issue: {result.get('explanation', '')}",
                    "completed_at": datetime.utcnow()
                })
                
                self._queue_agent_task(
                    user_id=self._get_user_id(session_id),
                    task_type=AgentTaskType.FORM_MAPPER_CLOSE,
                    session_id=session_id,
                    payload={}
                )
                
                return {"status": "failed", "reason": "real_issue"}
            
            else:
                # AI issue - navigate back and retry with critical fields
                problematic_fields = result.get("problematic_fields", [])
                field_requirements = result.get("field_requirements", "")
                
                # Store critical fields for next attempt
                critical_checklist = {}
                for field in problematic_fields:
                    critical_checklist[field] = field_requirements
                
                redis_client.hset(f"mapper_session:{session_id}", mapping={
                    "critical_fields_checklist": json.dumps(critical_checklist),
                    "field_requirements_for_recovery": field_requirements,
                    "executed_steps": "[]",
                    "current_step_index": "0"
                })
                
                # Navigate back to base URL
                base_url = self._get_redis_value(session_id, "base_url")
                
                self._queue_agent_task(
                    user_id=self._get_user_id(session_id),
                    task_type=AgentTaskType.FORM_MAPPER_NAVIGATE,
                    session_id=session_id,
                    payload={"url": base_url}
                )
                
                return {"status": "ok", "next_action": "navigate_to_retry"}
        
        return {"status": "ok"}
    
    def _process_failure_recovery_result(self, session_id: int, result: Dict) -> Dict:
        """Process failure_recovery Celery result"""
        if not result.get("success"):
            self._update_status(session_id, SessionStatus.FAILED)
            return {"status": "failed", "error": result.get("error")}
        
        recovery_steps = result.get("steps", [])
        
        if not recovery_steps:
            self._update_status(session_id, SessionStatus.FAILED)
            return {"status": "failed", "error": "No recovery steps generated"}
        
        executed_steps = self._get_redis_json(session_id, "executed_steps")
        all_steps = executed_steps + recovery_steps
        
        redis_client.hset(f"mapper_session:{session_id}", mapping={
            "steps": json.dumps(all_steps),
            "current_step_index": str(len(executed_steps))
        })
        
        self._update_status(session_id, SessionStatus.EXECUTING)
        
        return self._execute_step(session_id, len(executed_steps))
    
    def _process_ui_verify_result(self, session_id: int, result: Dict) -> Dict:
        """Process ui_verify Celery result"""
        ui_issue = result.get("ui_issue", "")
        
        if ui_issue:
            # Store reported issue
            reported_issues = self._get_redis_json(session_id, "reported_ui_issues")
            reported_issues.append(ui_issue)
            redis_client.hset(
                f"mapper_session:{session_id}",
                "reported_ui_issues",
                json.dumps(reported_issues)
            )
            
            self._log_event(session_id, "ui_issue", {"issue": ui_issue})
        
        # Continue with step generation
        return self._queue_step_generation(session_id)
    
    def _process_assign_test_cases_result(self, session_id: int, result: Dict) -> Dict:
        """Process assign_test_cases Celery result - save final result"""
        steps = result.get("steps", [])
        
        # Get session data
        session = self.db.query(FormMapperSession).filter(
            FormMapperSession.id == session_id
        ).first()
        
        if not session:
            return {"status": "error", "message": "Session not found"}
        
        # Get additional data from Redis
        path_junctions = self._get_redis_json(session_id, "current_path_junctions")
        path_number = int(self._get_redis_value(session_id, "current_path_number") or "1")
        ui_issues = self._get_redis_json(session_id, "reported_ui_issues")
        
        # Extract form fields from steps
        form_fields = self._extract_form_fields(steps)
        field_relationships = self._extract_field_relationships(steps)
        
        # Create result record
        map_result = FormMapResult(
            form_mapper_session_id=session_id,
            form_page_route_id=session.form_page_route_id,
            network_id=session.network_id,
            company_id=session.company_id,
            path_number=path_number,
            path_junctions=path_junctions,
            steps=steps,
            form_fields=form_fields,
            field_relationships=field_relationships,
            ui_issues=ui_issues
        )
        
        self.db.add(map_result)
        
        # Update session
        session.status = SessionStatus.COMPLETED
        session.completed_at = datetime.utcnow()
        session.steps_executed = len(steps)
        session.total_paths_discovered = path_number
        
        # Update AI usage from Redis
        session.ai_calls_count = int(self._get_redis_value(session_id, "ai_calls_count") or "0")
        session.ai_tokens_used = int(self._get_redis_value(session_id, "ai_tokens_used") or "0")
        session.ai_cost_estimate = float(self._get_redis_value(session_id, "ai_cost_estimate") or "0")
        
        self.db.commit()
        
        self._update_status(session_id, SessionStatus.COMPLETED)
        
        # Close browser
        self._queue_agent_task(
            user_id=session.user_id,
            task_type=AgentTaskType.FORM_MAPPER_CLOSE,
            session_id=session_id,
            payload={}
        )
        
        logger.info(f"[Orchestrator] Session {session_id} completed with {len(steps)} steps")
        
        return {
            "status": "completed",
            "result_id": map_result.id,
            "steps_count": len(steps)
        }
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def _queue_step_generation(self, session_id: int, with_screenshot: bool = False) -> Dict:
        """Queue Celery task to generate steps"""
        self._update_status(session_id, SessionStatus.GENERATING_STEPS)
        
        dom_html = redis_client.get(f"mapper_dom:{session_id}") or ""
        screenshot = None
        
        if with_screenshot:
            screenshot = redis_client.get(f"mapper_screenshot:{session_id}")
        
        self._set_pending_celery_task(session_id, "generate_steps")
        
        generate_steps_task.delay(
            session_id=str(session_id),
            dom_html=dom_html,
            screenshot_base64=screenshot
        )
        
        return {"status": "ok", "next_action": "waiting_for_step_generation"}
    
    def _queue_step_regeneration(self, session_id: int, with_screenshot: bool = False) -> Dict:
        """Queue Celery task to regenerate steps"""
        dom_html = redis_client.get(f"mapper_dom:{session_id}") or ""
        executed_steps = self._get_redis_json(session_id, "executed_steps")
        screenshot = None
        
        if with_screenshot:
            screenshot = redis_client.get(f"mapper_screenshot:{session_id}")
        
        self._set_pending_celery_task(session_id, "regenerate_steps")
        
        regenerate_steps_task.delay(
            session_id=str(session_id),
            dom_html=dom_html,
            executed_steps=executed_steps,
            screenshot_base64=screenshot
        )
        
        return {"status": "ok", "next_action": "waiting_for_regeneration"}
    
    def _execute_step(self, session_id: int, step_index: int) -> Dict:
        """Queue agent task to execute a step"""
        steps = self._get_redis_json(session_id, "steps")
        
        if step_index >= len(steps):
            return self._handle_all_steps_complete(session_id)
        
        step = steps[step_index]
        
        self._queue_agent_task(
            user_id=self._get_user_id(session_id),
            task_type=AgentTaskType.FORM_MAPPER_EXEC_STEP,
            session_id=session_id,
            payload={
                "step": step,
                "step_index": step_index
            }
        )
        
        # Update DB progress
        self._update_db_session(session_id, {
            "current_step_index": step_index,
            "steps_executed": step_index
        })
        
        return {"status": "ok", "next_action": f"executing_step_{step_index}"}
    
    def _queue_agent_task(
        self,
        user_id: int,
        task_type: str,
        session_id: int,
        payload: Dict
    ):
        """Queue a task for the agent via Redis"""
        task = {
            "task_type": task_type,
            "session_id": session_id,
            "payload": payload,
            "queued_at": datetime.utcnow().isoformat()
        }
        
        queue_key = f"agent:{user_id}"
        redis_client.rpush(queue_key, json.dumps(task))
        
        self._log_event(session_id, "task_queued", {
            "task_type": task_type,
            "queue": queue_key
        })
        
        logger.info(f"[Orchestrator] Queued {task_type} to {queue_key}")
    
    def _update_status(self, session_id: int, status: str):
        """Update session status in Redis and DB"""
        old_status = self._get_redis_value(session_id, "status")
        redis_client.hset(f"mapper_session:{session_id}", "status", status)
        
        self._log_event(session_id, "state_change", {
            "from": old_status,
            "to": status
        })
        
        self._update_db_session(session_id, {"status": status})
    
    def _update_db_session(self, session_id: int, updates: Dict):
        """Update session in database"""
        self.db.query(FormMapperSession).filter(
            FormMapperSession.id == session_id
        ).update(updates)
        self.db.commit()
    
    def _log_event(self, session_id: int, event_type: str, event_data: Dict):
        """Log event to database"""
        log = FormMapperSessionLog(
            session_id=session_id,
            event_type=event_type,
            event_data=event_data
        )
        self.db.add(log)
        self.db.commit()
    
    def _get_redis_value(self, session_id: int, field: str) -> Optional[str]:
        """Get a single value from Redis session"""
        return redis_client.hget(f"mapper_session:{session_id}", field)
    
    def _get_redis_json(self, session_id: int, field: str) -> Any:
        """Get a JSON field from Redis session"""
        value = redis_client.hget(f"mapper_session:{session_id}", field)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return {} if "checklist" in field else []
        return {} if "checklist" in field else []
    
    def _get_user_id(self, session_id: int) -> int:
        """Get user_id for session from DB"""
        session = self.db.query(FormMapperSession).filter(
            FormMapperSession.id == session_id
        ).first()
        return session.user_id if session else 0
    
    def _set_pending_celery_task(self, session_id: int, task_type: str):
        """Mark a Celery task as pending"""
        redis_client.hset(f"mapper_session:{session_id}", "pending_celery_task", task_type)
    
    def _append_executed_step(self, session_id: int, step: Dict):
        """Append a step to executed_steps in Redis"""
        executed_steps = self._get_redis_json(session_id, "executed_steps")
        executed_steps.append(step)
        redis_client.hset(
            f"mapper_session:{session_id}",
            "executed_steps",
            json.dumps(executed_steps)
        )
    
    def _extract_form_fields(self, steps: List[Dict]) -> List[Dict]:
        """Extract form field definitions from steps"""
        fields = []
        seen_selectors = set()
        
        for step in steps:
            action = step.get("action", "")
            selector = step.get("selector", "")
            
            if action in ["fill", "select", "check", "upload_file"] and selector:
                if selector not in seen_selectors:
                    seen_selectors.add(selector)
                    fields.append({
                        "selector": selector,
                        "action": action,
                        "description": step.get("description", ""),
                        "is_junction": step.get("junction", False)
                    })
        
        return fields
    
    def _extract_field_relationships(self, steps: List[Dict]) -> List[Dict]:
        """Extract field relationships from steps (e.g., parent dropdown → child fields)"""
        relationships = []
        
        # Find junction steps and their following steps
        for i, step in enumerate(steps):
            if step.get("junction"):
                parent_selector = step.get("selector", "")
                parent_value = step.get("value", "")
                
                # Look at following steps until next junction or different test_case
                for j in range(i + 1, min(i + 10, len(steps))):
                    next_step = steps[j]
                    if next_step.get("junction"):
                        break
                    if next_step.get("test_case") != step.get("test_case"):
                        break
                    
                    if next_step.get("action") in ["fill", "select", "check"]:
                        relationships.append({
                            "parent_selector": parent_selector,
                            "parent_value": parent_value,
                            "child_selector": next_step.get("selector", ""),
                            "type": "conditional"
                        })
        
        return relationships
    
    # ========================================================================
    # Public Query Methods
    # ========================================================================
    
    def get_session_status(self, session_id: int) -> Dict:
        """Get current session status"""
        # Check Redis first
        status = self._get_redis_value(session_id, "status")
        
        if not status:
            # Fall back to DB
            session = self.db.query(FormMapperSession).filter(
                FormMapperSession.id == session_id
            ).first()
            
            if not session:
                return {"error": "Session not found"}
            
            return session.to_dict()
        
        return {
            "session_id": session_id,
            "status": status,
            "current_step_index": int(self._get_redis_value(session_id, "current_step_index") or "0"),
            "total_steps": len(self._get_redis_json(session_id, "steps")),
            "steps_executed": len(self._get_redis_json(session_id, "executed_steps")),
            "pending_celery_task": self._get_redis_value(session_id, "pending_celery_task"),
            "ai_calls_count": int(self._get_redis_value(session_id, "ai_calls_count") or "0")
        }
    
    def cancel_session(self, session_id: int) -> bool:
        """Cancel a mapping session"""
        self._update_status(session_id, SessionStatus.CANCELLED)
        self._update_db_session(session_id, {
            "status": SessionStatus.CANCELLED,
            "completed_at": datetime.utcnow()
        })
        
        # Queue browser close
        self._queue_agent_task(
            user_id=self._get_user_id(session_id),
            task_type=AgentTaskType.FORM_MAPPER_CLOSE,
            session_id=session_id,
            payload={}
        )
        
        return True
