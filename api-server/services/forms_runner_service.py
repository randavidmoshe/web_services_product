# forms_runner_service.py
# Distributed Forms Runner Service - executes stages via agent with AI error recovery
# Used for: Login, Navigation to form pages, and future Test Case execution

import json
import logging
from typing import Dict, List, Optional, Tuple
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class RunnerPhase(str, Enum):
    """Phases of the forms runner"""
    LOGIN = "login"
    NAVIGATE = "navigate"
    EXECUTE_TEST = "execute_test"


class RunnerStepStatus(str, Enum):
    """Status of a runner step"""
    PENDING = "pending"
    EXECUTING = "executing"
    SUCCESS = "success"
    FAILED = "failed"
    RECOVERING = "recovering"
    SKIPPED = "skipped"


class FormsRunnerService:
    """
    Distributed Forms Runner - executes stages through agent with AI error recovery.
    
    This service manages the execution of:
    1. Login stages (from Network.login_stages)
    2. Navigation stages (from FormPageRoute.navigation_steps)
    3. Test case stages (from FormMapResult - future)
    
    Works with Redis for state and agent communication.
    """
    
    def __init__(self, redis_client, db_session=None):
        self.redis = redis_client
        self.db = db_session
        
        # Retry configuration
        self.max_retries_locator_changed = 2
        self.max_retries_general_error = 2
        self.max_retries_correction_steps = 2
        self.general_error_wait_time = 60
    
    # ============================================================
    # STATE MANAGEMENT (Redis)
    # ============================================================
    
    def _get_runner_key(self, session_id: str) -> str:
        """Get Redis key for runner state"""
        return f"forms_runner:{session_id}"
    
    def init_runner_state(
        self,
        session_id: str,
        phase: RunnerPhase,
        stages: List[Dict],
        network_id: int,
        form_route_id: Optional[int] = None
    ) -> Dict:
        """Initialize runner state in Redis"""
        state = {
            "session_id": session_id,
            "phase": phase.value,
            "network_id": network_id,
            "form_route_id": form_route_id,
            "stages": json.dumps(stages),
            "total_stages": len(stages),
            "current_stage_index": 0,
            "status": "running",
            "retry_count": 0,
            "recovery_attempts": 0,
            "last_error": "",
            "last_ai_decision": "",
            "stages_updated": "false",  # Flag if any stage was modified
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": ""
        }
        
        key = self._get_runner_key(session_id)
        self.redis.hset(key, mapping=state)
        self.redis.expire(key, 7200)  # 2 hour TTL
        
        logger.info(f"[FormsRunner] Initialized {phase.value} with {len(stages)} stages for session {session_id}")
        return state
    
    def get_runner_state(self, session_id: str) -> Optional[Dict]:
        """Get runner state from Redis"""
        key = self._get_runner_key(session_id)
        state = self.redis.hgetall(key)
        
        if not state:
            return None
        
        # Decode bytes if needed
        decoded = {}
        for k, v in state.items():
            key_str = k.decode() if isinstance(k, bytes) else k
            val_str = v.decode() if isinstance(v, bytes) else v
            decoded[key_str] = val_str
        
        # Parse JSON fields
        if "stages" in decoded:
            decoded["stages"] = json.loads(decoded["stages"])
        decoded["total_stages"] = int(decoded.get("total_stages", 0))
        decoded["current_stage_index"] = int(decoded.get("current_stage_index", 0))
        decoded["retry_count"] = int(decoded.get("retry_count", 0))
        decoded["recovery_attempts"] = int(decoded.get("recovery_attempts", 0))
        
        return decoded
    
    def update_runner_state(self, session_id: str, updates: Dict) -> None:
        """Update runner state in Redis"""
        key = self._get_runner_key(session_id)
        
        # Serialize stages if present
        if "stages" in updates:
            updates["stages"] = json.dumps(updates["stages"])
        
        self.redis.hset(key, mapping=updates)
    
    def get_current_stage(self, session_id: str) -> Optional[Dict]:
        """Get the current stage to execute"""
        state = self.get_runner_state(session_id)
        if not state:
            return None
        
        stages = state.get("stages", [])
        index = state.get("current_stage_index", 0)
        
        if index >= len(stages):
            return None
        
        return stages[index]
    
    def advance_to_next_stage(self, session_id: str) -> bool:
        """Advance to next stage. Returns False if no more stages."""
        state = self.get_runner_state(session_id)
        if not state:
            return False
        
        next_index = state["current_stage_index"] + 1
        total = state["total_stages"]
        
        if next_index >= total:
            # All stages complete
            self.update_runner_state(session_id, {
                "status": "completed",
                "completed_at": datetime.utcnow().isoformat()
            })
            logger.info(f"[FormsRunner] All {total} stages completed for session {session_id}")
            return False
        
        self.update_runner_state(session_id, {
            "current_stage_index": next_index,
            "retry_count": 0,
            "recovery_attempts": 0,
            "last_error": ""
        })
        
        logger.info(f"[FormsRunner] Advanced to stage {next_index + 1}/{total} for session {session_id}")
        return True
    
    # ============================================================
    # STAGE EXECUTION
    # ============================================================
    
    def create_agent_task_for_stage(
        self,
        session_id: str,
        stage: Dict,
        user_id: int
    ) -> Dict:
        """Create agent task for executing a stage"""
        return {
            "task_id": f"runner_{session_id}_{stage.get('step_number', 0)}_{datetime.utcnow().timestamp()}",
            "task_type": "forms_runner_exec_step",
            "session_id": session_id,
            "payload": {
                "step": stage
            },
            "created_at": datetime.utcnow().isoformat()
        }
    
    def handle_step_success(self, session_id: str) -> Dict:
        """Handle successful step execution"""
        state = self.get_runner_state(session_id)
        if not state:
            return {"success": False, "error": "Session not found"}
        
        current_index = state["current_stage_index"]
        total = state["total_stages"]
        
        logger.info(f"[FormsRunner] Step {current_index + 1}/{total} succeeded for session {session_id}")
        
        # Advance to next stage
        has_more = self.advance_to_next_stage(session_id)
        
        return {
            "success": True,
            "has_more_stages": has_more,
            "current_index": current_index + 1 if has_more else current_index,
            "total_stages": total
        }
    
    def handle_step_failure(
        self,
        session_id: str,
        error_message: str,
        dom_html: str,
        screenshot_base64: str
    ) -> Dict:
        """
        Handle step failure - determine recovery action.
        
        Returns dict with:
        - decision: "retry", "ai_recovery", "fail"
        - Additional fields based on decision
        """
        state = self.get_runner_state(session_id)
        if not state:
            return {"decision": "fail", "error": "Session not found"}
        
        current_stage = state["stages"][state["current_stage_index"]]
        action = current_stage.get("action", "")
        
        # Special handling for alert actions - just skip
        if action in ["accept_alert", "dismiss_alert"]:
            logger.info(f"[FormsRunner] Alert action failed (no alert) - skipping")
            self.advance_to_next_stage(session_id)
            return {"decision": "skip", "reason": "Alert already handled"}
        
        # Verify action failure = test assertion failure, not recoverable
        if action == "verify":
            self.update_runner_state(session_id, {
                "status": "failed",
                "last_error": "Verification failed - test assertion failure",
                "completed_at": datetime.utcnow().isoformat()
            })
            return {"decision": "fail", "reason": "Verification failed - test assertion"}
        
        # Check for general error (page load issues)
        if self._is_general_error(dom_html):
            return self._handle_general_error_decision(session_id, state)
        
        # Need AI analysis for other errors
        self.update_runner_state(session_id, {
            "status": "recovering",
            "last_error": error_message,
            "recovery_attempts": state["recovery_attempts"] + 1
        })
        
        return {
            "decision": "ai_recovery",
            "failed_stage": current_stage,
            "all_stages": state["stages"],
            "error_message": error_message,
            "dom_html": dom_html,
            "screenshot_base64": screenshot_base64
        }
    
    def _is_general_error(self, dom_html: str) -> bool:
        """Check if DOM indicates a general error (404, blank page, etc.)"""
        if not dom_html or len(dom_html.strip()) < 200:
            return True
        
        dom_lower = dom_html.lower()
        
        error_patterns = [
            "this site can't be reached",
            "err_connection_refused",
            "err_connection",
            "err_name_not_resolved",
            "unable to connect",
            "connection refused",
            "404 not found",
            "404 error",
            "page not found",
            "500 internal server error",
            "502 bad gateway",
            "503 service unavailable",
            "504 gateway timeout",
            "the page isn't working",
            "can't reach this page"
        ]
        
        for pattern in error_patterns:
            if pattern in dom_lower:
                return True
        
        # If page has form elements, not a general error
        if any(ind in dom_lower for ind in ['<input', '<select', '<textarea', '<form']):
            return False
        
        return False
    
    def _handle_general_error_decision(self, session_id: str, state: Dict) -> Dict:
        """Decide how to handle general error"""
        retry_count = state["retry_count"]
        
        if retry_count < self.max_retries_general_error:
            self.update_runner_state(session_id, {
                "retry_count": retry_count + 1,
                "last_error": "General error - page load issue"
            })
            return {
                "decision": "wait_and_retry",
                "wait_seconds": self.general_error_wait_time,
                "retry_number": retry_count + 1,
                "max_retries": self.max_retries_general_error
            }
        else:
            self.update_runner_state(session_id, {
                "status": "failed",
                "last_error": f"General error after {self.max_retries_general_error} retries",
                "completed_at": datetime.utcnow().isoformat()
            })
            return {"decision": "fail", "reason": "General error - max retries exceeded"}
    
    # ============================================================
    # AI RECOVERY HANDLING
    # ============================================================
    
    def apply_ai_recovery(self, session_id: str, ai_result: Dict) -> Dict:
        """
        Apply AI recovery decision to runner state.
        
        AI decisions:
        - locator_changed: Update stage with new selector
        - general_error: Wait and retry
        - need_healing: Fail - major UI changes
        - correction_steps: Apply corrected step (with optional presteps)
        """
        state = self.get_runner_state(session_id)
        if not state:
            return {"success": False, "error": "Session not found"}
        
        decision = ai_result.get("decision")
        description = ai_result.get("description", "")
        
        logger.info(f"[FormsRunner] AI decision: {decision} - {description}")
        
        self.update_runner_state(session_id, {
            "last_ai_decision": decision
        })
        
        if decision == "locator_changed":
            return self._apply_locator_changed(session_id, state, ai_result)
        
        elif decision == "general_error":
            return self._handle_general_error_decision(session_id, state)
        
        elif decision == "need_healing":
            self.update_runner_state(session_id, {
                "status": "failed",
                "last_error": f"Need healing: {description}",
                "completed_at": datetime.utcnow().isoformat()
            })
            return {
                "success": False,
                "decision": "need_healing",
                "description": description,
                "action": "Form needs re-analysis"
            }
        
        elif decision == "correction_steps":
            return self._apply_correction_steps(session_id, state, ai_result)
        
        else:
            return {"success": False, "error": f"Unknown AI decision: {decision}"}
    
    def _apply_locator_changed(self, session_id: str, state: Dict, ai_result: Dict) -> Dict:
        """Apply locator_changed fix"""
        corrected_step = ai_result.get("corrected_step")
        if not corrected_step:
            return {"success": False, "error": "No corrected step from AI"}
        
        # Update stage in state
        stages = state["stages"]
        index = state["current_stage_index"]
        stages[index] = corrected_step
        
        self.update_runner_state(session_id, {
            "stages": stages,
            "stages_updated": "true",
            "status": "running"
        })
        
        return {
            "success": True,
            "decision": "retry_with_fix",
            "corrected_step": corrected_step,
            "action": "Retry with updated selector"
        }
    
    def _apply_correction_steps(self, session_id: str, state: Dict, ai_result: Dict) -> Dict:
        """Apply correction_steps fix"""
        correction_type = ai_result.get("type")
        corrected_step = ai_result.get("corrected_step")
        
        if not corrected_step:
            return {"success": False, "error": "No corrected step from AI"}
        
        # Update stage in state
        stages = state["stages"]
        index = state["current_stage_index"]
        stages[index] = corrected_step
        
        self.update_runner_state(session_id, {
            "stages": stages,
            "stages_updated": "true",
            "status": "running"
        })
        
        if correction_type == "present_only":
            return {
                "success": True,
                "decision": "retry_with_fix",
                "corrected_step": corrected_step,
                "action": "Retry with corrected step"
            }
        
        elif correction_type == "with_presteps":
            presteps = ai_result.get("presteps", [])
            return {
                "success": True,
                "decision": "execute_presteps",
                "presteps": presteps,
                "corrected_step": corrected_step,
                "action": f"Execute {len(presteps)} presteps then corrected step"
            }
        
        return {"success": False, "error": f"Unknown correction type: {correction_type}"}
    
    # ============================================================
    # DATABASE PERSISTENCE
    # ============================================================
    
    def persist_updated_stages_to_db(
        self,
        session_id: str,
        network_id: Optional[int] = None,
        form_route_id: Optional[int] = None
    ) -> bool:
        """
        Persist updated stages back to database if they were modified.
        
        - Login stages → networks.login_stages
        - Navigation stages → form_page_routes.navigation_steps
        """
        if not self.db:
            logger.warning("[FormsRunner] No DB session - cannot persist stages")
            return False
        
        state = self.get_runner_state(session_id)
        if not state:
            return False
        
        if state.get("stages_updated") != "true":
            logger.info("[FormsRunner] No stages were modified - skip DB update")
            return True
        
        phase = state.get("phase")
        stages = state.get("stages", [])
        
        try:
            if phase == RunnerPhase.LOGIN.value and network_id:
                # Update Network.login_stages
                from models.database import Network
                network = self.db.query(Network).filter(Network.id == network_id).first()
                if network:
                    network.login_stages = stages
                    self.db.commit()
                    logger.info(f"[FormsRunner] Updated login_stages for network {network_id}")
                    return True
            
            elif phase == RunnerPhase.NAVIGATE.value and form_route_id:
                # Update FormPageRoute.navigation_steps
                from models.database import FormPageRoute
                route = self.db.query(FormPageRoute).filter(FormPageRoute.id == form_route_id).first()
                if route:
                    route.navigation_steps = stages
                    self.db.commit()
                    logger.info(f"[FormsRunner] Updated navigation_steps for form_route {form_route_id}")
                    return True
            
            logger.warning(f"[FormsRunner] Could not persist - phase={phase}, network_id={network_id}, form_route_id={form_route_id}")
            return False
            
        except Exception as e:
            logger.error(f"[FormsRunner] Failed to persist stages: {e}")
            self.db.rollback()
            return False
    
    # ============================================================
    # CONVENIENCE METHODS
    # ============================================================
    
    def load_login_stages(self, network_id: int) -> List[Dict]:
        """Load login stages from database"""
        if not self.db:
            return []
        
        from models.database import Network
        network = self.db.query(Network).filter(Network.id == network_id).first()
        
        if not network or not network.login_stages:
            return []
        
        return network.login_stages if isinstance(network.login_stages, list) else []
    
    def load_navigation_stages(self, form_route_id: int) -> List[Dict]:
        """Load navigation stages from database"""
        if not self.db:
            return []
        
        from models.database import FormPageRoute
        route = self.db.query(FormPageRoute).filter(FormPageRoute.id == form_route_id).first()
        
        if not route or not route.navigation_steps:
            return []
        
        return route.navigation_steps if isinstance(route.navigation_steps, list) else []
    
    def get_runner_summary(self, session_id: str) -> Dict:
        """Get summary of runner execution"""
        state = self.get_runner_state(session_id)
        if not state:
            return {"error": "Session not found"}
        
        return {
            "session_id": session_id,
            "phase": state.get("phase"),
            "status": state.get("status"),
            "progress": f"{state.get('current_stage_index', 0) + 1}/{state.get('total_stages', 0)}",
            "stages_updated": state.get("stages_updated") == "true",
            "last_error": state.get("last_error", ""),
            "last_ai_decision": state.get("last_ai_decision", ""),
            "started_at": state.get("started_at"),
            "completed_at": state.get("completed_at")
        }
