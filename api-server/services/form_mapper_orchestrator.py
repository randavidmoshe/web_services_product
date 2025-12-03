# form_mapper_orchestrator.py
# UPDATED: Added LOGIN and NAVIGATE phases using Forms Runner
# Distributed Form Mapper Orchestrator - manages state machine for form analysis

import json
import logging
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class MapperState(str, Enum):
    """States in the form mapper state machine"""
    # Pre-mapping phases (Forms Runner)
    INITIALIZING = "initializing"
    LOGGING_IN = "logging_in"           # NEW: Execute login stages
    LOGIN_RECOVERING = "login_recovering" # NEW: AI recovery for login
    NAVIGATING = "navigating"           # NEW: Execute navigation stages
    NAV_RECOVERING = "nav_recovering"   # NEW: AI recovery for navigation
    
    # Form mapping phases
    EXTRACTING_DOM = "extracting_dom"
    ANALYZING = "analyzing"
    EXECUTING_STEP = "executing_step"
    HANDLING_ALERT = "handling_alert"
    VERIFYING_UI = "verifying_ui"
    
    # Completion states
    PATH_COMPLETE = "path_complete"
    ALL_PATHS_COMPLETE = "all_paths_complete"
    ASSIGNING_TEST_CASES = "assigning_test_cases"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Backwards compatibility alias for routes that use SessionStatus
class SessionStatus:
    INITIALIZING = "initializing"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FormMapperOrchestrator:
    """
    Distributed Form Mapper Orchestrator.
    
    Manages the complete flow:
    1. LOGIN - Execute login stages via Forms Runner
    2. NAVIGATE - Navigate to form page via Forms Runner  
    3. MAP - Analyze form and discover all paths
    
    Uses Redis for state management and communicates with agent via task queue.
    Company-level configuration is loaded from the database.
    """
    
    def __init__(self, redis_client_or_db, db_session=None):
        """
        Initialize orchestrator.
        
        Supports two patterns:
        - FormMapperOrchestrator(db) - route compatibility, auto-connect to Redis
        - FormMapperOrchestrator(redis, db) - explicit Redis client
        """
        import redis
        import os
        
        # Check if first arg is a db session (SQLAlchemy) or Redis client
        if hasattr(redis_client_or_db, 'query'):
            # First arg is db session (route pattern)
            self.db = redis_client_or_db
            self.redis = redis.Redis(
                host=os.getenv("REDIS_HOST", "redis"),
                port=int(os.getenv("REDIS_PORT", 6379)),
                db=0,
                decode_responses=False
            )
        else:
            # First arg is redis client
            self.redis = redis_client_or_db
            self.db = db_session
        
        # Default configuration (overridden by company config)
        self.max_retries = 3
        self.max_paths = 50  # Safety limit on junction paths
    
    def _load_company_config(self, company_id: int) -> dict:
        """Load Form Mapper config for a company"""
        if not self.db:
            return self._get_default_config()
        
        try:
            from models.form_mapper_config_models import get_company_config
            config = get_company_config(self.db, company_id)
            return config.dict()
        except Exception as e:
            logger.warning(f"[Orchestrator] Failed to load company config: {e}, using defaults")
            return self._get_default_config()
    
    def _get_default_config(self) -> dict:
        """Get default Form Mapper configuration"""
        return {
            "test_cases_file": "test_cases1.json",
            "enable_ui_verification": True,
            "max_retries": 3,
            "use_detect_fields_change": True,
            "use_full_dom": True,
            "use_optimized_dom": False,
            "use_forms_dom": False,
            "include_js_in_dom": True,
            "enable_junction_discovery": True,
            "max_junction_paths": 5
        }
    
    # ============================================================
    # SESSION STATE MANAGEMENT
    # ============================================================
    
    def _get_session_key(self, session_id: str) -> str:
        return f"mapper_session:{session_id}"
    
    def create_session(
        self,
        session_id: str = None,
        user_id: int = None,
        company_id: int = None,
        network_id: int = None,
        form_route_id: int = None,
        form_page_route_id: int = None,  # Alias for route compatibility
        test_cases: List[Dict] = None,
        product_id: int = 1,  # Default to form_mapper product
        config: Optional[Dict] = None
    ):
        """
        Create a new mapping session with company configuration.
        
        Supports route-style call:
            create_session(form_page_route_id=..., user_id=..., network_id=..., company_id=..., config=...)
        """
        import uuid
        
        # Handle form_page_route_id alias
        if form_route_id is None and form_page_route_id is not None:
            form_route_id = form_page_route_id
        
        # Auto-generate session_id if not provided
        if session_id is None:
            session_id = str(uuid.uuid4())[:8]
        
        # Default empty test cases
        if test_cases is None:
            test_cases = []
        
        # Load company config from database
        company_config = self._load_company_config(company_id) if company_id else self._get_default_config()
        
        # Override with any explicitly provided config
        if config:
            company_config.update(config)
        
        # Apply config to orchestrator
        self.max_retries = company_config.get("max_retries", 3)
        self.max_paths = company_config.get("max_junction_paths", 5)
        
        session_state = {
            "session_id": session_id,
            "user_id": user_id or 0,
            "company_id": company_id or 0,
            "product_id": product_id or "",  # For AI budget tracking
            "network_id": network_id or 0,
            "form_route_id": form_route_id or 0,
            
            # State machine
            "state": MapperState.INITIALIZING.value,
            "previous_state": "",
            
            # Form mapping state
            "current_path": 0,
            "total_paths_discovered": 0,
            "current_step_index": 0,
            "all_steps": "[]",
            "current_dom_hash": "",
            "previous_paths": "[]",
            "current_path_junctions": "[]",
            
            # Test cases
            "test_cases": json.dumps(test_cases),
            
            # Company configuration (loaded from DB)
            "config": json.dumps(company_config),
            
            # Error handling
            "retry_count": 0,
            "last_error": "",
            "recovery_attempts": 0,
            
            # Results
            "final_steps": "[]",
            
            # Timestamps
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "completed_at": ""
        }
        
        key = self._get_session_key(session_id)
        self.redis.hset(key, mapping=session_state)
        self.redis.expire(key, 86400)  # 24h TTL
        
        logger.info(f"[Orchestrator] Created session {session_id} for form_route {form_route_id} with company config")
        
        # Return object with .id attribute for route compatibility
        class SessionResult:
            def __init__(self, sid, state):
                self.id = sid
                self.state = state
        
        return SessionResult(session_id, session_state)
    
    def start_mapping(self, session_id, agent_id: str, form_page_route, test_cases: List[Dict]) -> bool:
        """
        Start the mapping process for a session.
        Called by the route after create_session.
        """
        session = self.get_session(session_id)
        if not session:
            logger.error(f"[Orchestrator] Session {session_id} not found")
            return False
        
        # Update test_cases if provided
        if test_cases:
            self.update_session(session_id, {"test_cases": json.dumps(test_cases)})
        
        # Start LOGIN phase (or skip to NAVIGATE if no login)
        result = self.start_login_phase(session_id)
        
        return result.get("success", True)  # Default to True for now
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session state from Redis"""
        key = self._get_session_key(session_id)
        state = self.redis.hgetall(key)
        
        if not state:
            return None
        
        # Decode and parse
        decoded = {}
        for k, v in state.items():
            key_str = k.decode() if isinstance(k, bytes) else k
            val_str = v.decode() if isinstance(v, bytes) else v
            decoded[key_str] = val_str
        
        # Parse JSON fields
        json_fields = ["test_cases", "config", "all_steps", "final_steps", 
                       "previous_paths", "current_path_junctions", "runner_stages"]
        for field in json_fields:
            if field in decoded:
                try:
                    decoded[field] = json.loads(decoded[field])
                except:
                    decoded[field] = []
        
        # Parse integers
        int_fields = ["user_id", "company_id", "network_id", "form_route_id",
                      "current_path", "total_paths_discovered", "current_step_index",
                      "retry_count", "recovery_attempts", "runner_stage_index", "runner_total_stages"]
        for field in int_fields:
            if field in decoded:
                decoded[field] = int(decoded.get(field, 0))
        
        return decoded
    
    def update_session(self, session_id: str, updates: Dict) -> None:
        """Update session state"""
        key = self._get_session_key(session_id)
        
        # Serialize JSON fields
        json_fields = ["test_cases", "config", "all_steps", "final_steps",
                       "previous_paths", "current_path_junctions", "runner_stages"]
        for field in json_fields:
            if field in updates:
                updates[field] = json.dumps(updates[field])
        
        updates["updated_at"] = datetime.utcnow().isoformat()
        self.redis.hset(key, mapping=updates)
    
    def transition_to(self, session_id: str, new_state: MapperState, **kwargs) -> None:
        """Transition to a new state"""
        session = self.get_session(session_id)
        if session:
            updates = {
                "previous_state": session["state"],
                "state": new_state.value,
                **kwargs
            }
            self.update_session(session_id, updates)
            logger.info(f"[Orchestrator] Session {session_id}: {session['state']} → {new_state.value}")
    
    # ============================================================
    # PHASE 1: LOGIN (via Celery - non-blocking)
    # ============================================================
    
    def start_login_phase(self, session_id: str) -> Dict:
        """Start the login phase using Forms Runner (Celery-based)"""
        session = self.get_session(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}
        
        # Load login stages from database
        login_stages = self._load_login_stages(session["network_id"])
        
        if not login_stages:
            # No login required - skip to navigation
            logger.info(f"[Orchestrator] No login stages for network {session['network_id']} - skipping to navigation")
            return self.start_navigation_phase(session_id)
        
        self.transition_to(session_id, MapperState.LOGGING_IN)
        
        # Trigger Celery task for login phase (non-blocking)
        from tasks.forms_runner_tasks import start_runner_phase
        
        start_runner_phase.delay(
            session_id=session_id,
            phase="login",
            stages=login_stages,
            company_id=session["company_id"],
            user_id=session["user_id"],
            product_id=session.get("product_id", 1),
            network_id=session["network_id"],
            form_route_id=session["form_route_id"]
        )
        
        return {
            "success": True,
            "phase": "login",
            "total_stages": len(login_stages),
            "async": True  # Indicates non-blocking execution
        }
    
    def handle_login_phase_complete(self, session_id: str, result: Dict) -> Dict:
        """Handle completion of login phase - start navigation"""
        session = self.get_session(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}
        
        if not result.get("success"):
            self.transition_to(session_id, MapperState.FAILED,
                last_error=result.get("error", "Login failed"),
                completed_at=datetime.utcnow().isoformat()
            )
            return {"success": False, "error": "Login phase failed"}
        
        logger.info(f"[Orchestrator] Login phase complete for session {session_id}")
        return self.start_navigation_phase(session_id)
    
    # ============================================================
    # PHASE 2: NAVIGATION (via Celery - non-blocking)
    # ============================================================
    
    def start_navigation_phase(self, session_id: str) -> Dict:
        """Start the navigation phase using Forms Runner (Celery-based)"""
        session = self.get_session(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}
        
        # Load navigation stages from database
        nav_stages = self._load_navigation_stages(session["form_route_id"])
        
        if not nav_stages:
            # No navigation required - go straight to mapping
            logger.info(f"[Orchestrator] No navigation stages for form_route {session['form_route_id']} - starting mapping")
            return self.start_mapping_phase(session_id)
        
        self.transition_to(session_id, MapperState.NAVIGATING)
        
        # Trigger Celery task for navigation phase (non-blocking)
        from tasks.forms_runner_tasks import start_runner_phase
        
        start_runner_phase.delay(
            session_id=session_id,
            phase="navigate",
            stages=nav_stages,
            company_id=session["company_id"],
            user_id=session["user_id"],
            product_id=session.get("product_id", 1),
            network_id=session["network_id"],
            form_route_id=session["form_route_id"]
        )
        
        return {
            "success": True,
            "phase": "navigate",
            "total_stages": len(nav_stages),
            "async": True
        }
    
    def handle_navigation_phase_complete(self, session_id: str, result: Dict) -> Dict:
        """Handle completion of navigation phase - start mapping"""
        session = self.get_session(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}
        
        if not result.get("success"):
            self.transition_to(session_id, MapperState.FAILED,
                last_error=result.get("error", "Navigation failed"),
                completed_at=datetime.utcnow().isoformat()
            )
            return {"success": False, "error": "Navigation phase failed"}
        
        logger.info(f"[Orchestrator] Navigation phase complete for session {session_id}")
        return self.start_mapping_phase(session_id)
    
    # ============================================================
    # PHASE 3: FORM MAPPING
    # ============================================================
    
    def start_mapping_phase(self, session_id: str) -> Dict:
        """Start the actual form mapping phase"""
        session = self.get_session(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}
        
        # Get config for DOM extraction settings
        config = session.get("config", {})
        
        # Now at the form page - start DOM extraction
        self.transition_to(session_id, MapperState.EXTRACTING_DOM,
            current_path=1
        )
        
        return {
            "success": True,
            "phase": "mapping",
            "agent_task": {
                "task_type": "form_mapper_extract_dom",
                "session_id": session_id,
                "payload": {
                    "use_full_dom": config.get("use_full_dom", True),
                    "use_optimized_dom": config.get("use_optimized_dom", False),
                    "use_forms_dom": config.get("use_forms_dom", False),
                    "include_js": config.get("include_js_in_dom", True)
                }
            }
        }
    
    def handle_dom_extraction_result(self, session_id: str, dom_html: str, screenshot_b64: str) -> Dict:
        """Handle DOM extraction result - trigger AI analysis"""
        session = self.get_session(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}
        
        # Store DOM and screenshot temporarily
        self.redis.setex(f"mapper_dom:{session_id}", 3600, dom_html)
        self.redis.setex(f"mapper_screenshot:{session_id}", 3600, screenshot_b64)
        
        # Calculate DOM hash for change detection
        dom_hash = hashlib.md5(dom_html.encode()).hexdigest()[:16]
        
        # Get config
        config = session.get("config", {})
        
        self.transition_to(session_id, MapperState.ANALYZING,
            current_dom_hash=dom_hash
        )
        
        # Trigger Celery task for AI analysis
        return {
            "success": True,
            "trigger_celery": True,
            "celery_task": "analyze_form_page",
            "celery_args": {
                "session_id": session_id,
                "dom_html": dom_html,
                "screenshot_base64": screenshot_b64,
                "test_cases": session["test_cases"],
                "previous_paths": session.get("previous_paths", []),
                "current_path": session["current_path"],
                # Pass config settings
                "enable_junction_discovery": config.get("enable_junction_discovery", True),
                "max_junction_paths": config.get("max_junction_paths", 5),
                "use_detect_fields_change": config.get("use_detect_fields_change", True),
                "enable_ui_verification": config.get("enable_ui_verification", True)
            }
        }
    
    def handle_ai_analysis_result(self, session_id: str, ai_result: Dict) -> Dict:
        """Handle AI analysis result - get next steps"""
        session = self.get_session(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}
        
        config = session.get("config", {})
        enable_junction_discovery = config.get("enable_junction_discovery", True)
        max_junction_paths = config.get("max_junction_paths", 5)
        
        steps = ai_result.get("steps", [])
        no_more_paths = ai_result.get("no_more_paths", False)
        junctions = ai_result.get("junctions", [])
        
        # If junction discovery is disabled, treat as single path
        if not enable_junction_discovery:
            no_more_paths = True
        
        # Check if we've hit max paths
        current_path = session.get("current_path", 1)
        if current_path >= max_junction_paths:
            no_more_paths = True
            logger.info(f"[Orchestrator] Max junction paths ({max_junction_paths}) reached for session {session_id}")
        
        if not steps:
            # No steps generated - possibly form complete or error
            if no_more_paths:
                return self._complete_all_paths(session_id, session)
            else:
                self.transition_to(session_id, MapperState.FAILED,
                    last_error="AI generated no steps"
                )
                return {"success": False, "error": "AI generated no steps"}
        
        # Store steps and prepare for execution
        all_steps = session.get("all_steps", [])
        all_steps.extend(steps)
        
        self.update_session(session_id, {
            "all_steps": all_steps,
            "current_step_index": len(all_steps) - len(steps)  # Start at first new step
        })
        
        # Execute first step
        return self._execute_next_mapping_step(session_id)
    
    def _execute_next_mapping_step(self, session_id: str) -> Dict:
        """Execute the next mapping step"""
        session = self.get_session(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}
        
        all_steps = session.get("all_steps", [])
        current_index = session["current_step_index"]
        
        if current_index >= len(all_steps):
            # All steps executed - extract DOM again for next batch
            self.transition_to(session_id, MapperState.EXTRACTING_DOM)
            return {
                "success": True,
                "agent_task": {
                    "task_type": "form_mapper_extract_dom",
                    "session_id": session_id,
                    "payload": {}
                }
            }
        
        step = all_steps[current_index]
        
        self.transition_to(session_id, MapperState.EXECUTING_STEP)
        
        return {
            "success": True,
            "agent_task": {
                "task_type": "form_mapper_exec_step",
                "session_id": session_id,
                "payload": {"step": step}
            }
        }
    
    def handle_mapping_step_result(self, session_id: str, result: Dict) -> Dict:
        """Handle result of a mapping step execution"""
        session = self.get_session(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}
        
        if result.get("success"):
            # Advance to next step
            self.update_session(session_id, {
                "current_step_index": session["current_step_index"] + 1,
                "retry_count": 0
            })
            return self._execute_next_mapping_step(session_id)
        
        else:
            # Handle alert or error
            error = result.get("error", "")
            
            if "alert" in error.lower() or result.get("alert_detected"):
                return self._handle_alert(session_id, session, result)
            else:
                return self._handle_mapping_step_error(session_id, session, result)
    
    def _handle_alert(self, session_id: str, session: Dict, result: Dict) -> Dict:
        """Handle alert during mapping"""
        self.transition_to(session_id, MapperState.HANDLING_ALERT)
        
        # Get current DOM and screenshot for AI analysis
        dom_html = self.redis.get(f"mapper_dom:{session_id}")
        screenshot = self.redis.get(f"mapper_screenshot:{session_id}")
        
        return {
            "success": True,
            "trigger_celery": True,
            "celery_task": "handle_alert_recovery",
            "celery_args": {
                "session_id": session_id,
                "alert_text": result.get("alert_text", ""),
                "dom_html": dom_html.decode() if dom_html else "",
                "screenshot_base64": screenshot.decode() if screenshot else "",
                "all_steps": session.get("all_steps", []),
                "current_step_index": session["current_step_index"]
            }
        }
    
    def _handle_mapping_step_error(self, session_id: str, session: Dict, result: Dict) -> Dict:
        """Handle error during mapping step"""
        retry_count = session.get("retry_count", 0)
        config = session.get("config", {})
        max_retries = config.get("max_retries", self.max_retries)
        
        if retry_count < max_retries:
            self.update_session(session_id, {"retry_count": retry_count + 1})
            # Retry the step
            return self._execute_next_mapping_step(session_id)
        else:
            # Max retries - fail
            self.transition_to(session_id, MapperState.FAILED,
                last_error=result.get("error", "Unknown error"),
                completed_at=datetime.utcnow().isoformat()
            )
            return {"success": False, "error": "Max retries exceeded"}
    
    def _complete_all_paths(self, session_id: str, session: Dict) -> Dict:
        """Complete all paths - move to test case assignment"""
        self.transition_to(session_id, MapperState.ASSIGNING_TEST_CASES)
        
        return {
            "success": True,
            "trigger_celery": True,
            "celery_task": "assign_test_cases",
            "celery_args": {
                "session_id": session_id,
                "all_steps": session.get("all_steps", []),
                "test_cases": session.get("test_cases", [])
            }
        }
    
    def complete_session(self, session_id: str, final_steps: List[Dict]) -> Dict:
        """Mark session as complete with final results"""
        self.transition_to(session_id, MapperState.COMPLETED,
            final_steps=final_steps,
            completed_at=datetime.utcnow().isoformat()
        )
        
        # TODO: Persist to form_map_results table
        
        return {"success": True, "state": "completed", "total_steps": len(final_steps)}
    
    # ============================================================
    # RUNNER PHASE COMPLETION HELPERS (Celery-based)
    # ============================================================
    
    def check_runner_phase_complete(self, session_id: str) -> Optional[Dict]:
        """
        Check if runner phase (login/navigate) has completed.
        Called by polling endpoint or webhook.
        
        Returns completion result if done, None if still running.
        """
        result_key = f"runner_phase_complete:{session_id}"
        result = self.redis.get(result_key)
        
        if result:
            self.redis.delete(result_key)
            return json.loads(result)
        
        return None
    
    def poll_and_advance_runner(self, session_id: str) -> Dict:
        """
        Poll for runner completion and advance to next phase if done.
        Convenience method for status polling.
        """
        completion = self.check_runner_phase_complete(session_id)
        
        if not completion:
            # Still running
            session = self.get_session(session_id)
            return {
                "status": "running",
                "phase": session.get("state") if session else "unknown"
            }
        
        phase = completion.get("phase")
        
        if not completion.get("success"):
            return {"status": "failed", "phase": phase, "error": completion.get("error")}
        
        # Phase complete - advance
        if phase == "login":
            return self.handle_login_phase_complete(session_id, completion)
        elif phase == "navigate":
            return self.handle_navigation_phase_complete(session_id, completion)
        
        return {"status": "complete", "phase": phase}
    
    # ============================================================
    # DATABASE HELPERS
    # ============================================================
    
    def _load_login_stages(self, network_id: int) -> List[Dict]:
        """Load login stages from Network table"""
        if not self.db:
            return []
        
        try:
            from models.database import Network
            network = self.db.query(Network).filter(Network.id == network_id).first()
            
            if not network or not network.login_stages:
                return []
            
            return network.login_stages if isinstance(network.login_stages, list) else []
        except Exception as e:
            logger.error(f"[Orchestrator] Failed to load login stages: {e}")
            return []
    
    def _load_navigation_stages(self, form_route_id: int) -> List[Dict]:
        """Load navigation stages from FormPageRoute table"""
        if not self.db:
            return []
        
        try:
            from models.database import FormPageRoute
            route = self.db.query(FormPageRoute).filter(FormPageRoute.id == form_route_id).first()
            
            if not route or not route.navigation_steps:
                return []
            
            return route.navigation_steps if isinstance(route.navigation_steps, list) else []
        except Exception as e:
            logger.error(f"[Orchestrator] Failed to load navigation stages: {e}")
            return []
    
    # ============================================================
    # SESSION CONTROL
    # ============================================================
    
    def cancel_session(self, session_id: str) -> Dict:
        """Cancel a running session"""
        session = self.get_session(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}
        
        self.transition_to(session_id, MapperState.CANCELLED,
            completed_at=datetime.utcnow().isoformat()
        )
        
        return {"success": True, "state": "cancelled"}
    
    def get_session_status(self, session_id: str) -> Dict:
        """Get current session status including runner progress"""
        session = self.get_session(session_id)
        if not session:
            return {"error": "Session not found"}
        
        state = session["state"]
        
        status = {
            "session_id": session_id,
            "state": state,
            "phase": self._get_phase_from_state(state),
            "created_at": session.get("created_at"),
            "updated_at": session.get("updated_at")
        }
        
        # Add phase-specific progress
        if state in [MapperState.LOGGING_IN.value, MapperState.NAVIGATING.value,
                     MapperState.LOGIN_RECOVERING.value, MapperState.NAV_RECOVERING.value]:
            # Get runner status from separate Redis key
            runner_status = self._get_runner_status(session_id)
            if runner_status:
                status["runner_status"] = runner_status.get("status", "unknown")
                status["progress"] = runner_status.get("progress", "")
                if runner_status.get("last_error"):
                    status["last_error"] = runner_status["last_error"]
        elif state == MapperState.EXECUTING_STEP.value:
            status["progress"] = f"Path {session['current_path']}, Step {session['current_step_index'] + 1}"
        
        if session.get("last_error"):
            status["last_error"] = session["last_error"]
        
        if session.get("completed_at"):
            status["completed_at"] = session["completed_at"]
        
        return status
    
    def _get_runner_status(self, session_id: str) -> Optional[Dict]:
        """Get runner status from Redis"""
        runner_key = f"forms_runner:{session_id}"
        runner_state = self.redis.hgetall(runner_key)
        
        if not runner_state:
            return None
        
        decoded = {}
        for k, v in runner_state.items():
            key_str = k.decode() if isinstance(k, bytes) else k
            val_str = v.decode() if isinstance(v, bytes) else v
            decoded[key_str] = val_str
        
        current = int(decoded.get("current_stage_index", 0))
        total = int(decoded.get("total_stages", 0))
        
        return {
            "status": decoded.get("status", "unknown"),
            "progress": f"{current + 1}/{total}" if total > 0 else "",
            "last_error": decoded.get("last_error", "")
        }
    
    def _get_phase_from_state(self, state: str) -> str:
        """Get high-level phase from state"""
        if state in [MapperState.LOGGING_IN.value, MapperState.LOGIN_RECOVERING.value]:
            return "login"
        elif state in [MapperState.NAVIGATING.value, MapperState.NAV_RECOVERING.value]:
            return "navigate"
        elif state in [MapperState.COMPLETED.value, MapperState.FAILED.value, MapperState.CANCELLED.value]:
            return "finished"
        else:
            return "mapping"
    
    # ============================================================
    # ROUTE COMPATIBILITY METHODS
    # ============================================================
    
    def check_and_process_celery_results(self, session_id: str) -> Optional[Dict]:
        """
        Check for pending Celery task results and process them.
        Called by status endpoint to advance state machine.
        """
        # Check runner phase completion
        completion = self.check_runner_phase_complete(session_id)
        if completion:
            phase = completion.get("phase")
            if phase == "login":
                return self.handle_login_phase_complete(session_id, completion)
            elif phase == "navigate":
                return self.handle_navigation_phase_complete(session_id, completion)
            return completion
        
        return None
    
    def process_agent_result(self, session_id: str, result: Dict) -> Dict:
        """
        Process result reported by agent.
        Routes to appropriate handler based on task_type.
        """
        task_type = result.get("task_type", "")
        success = result.get("success", False)
        
        session = self.get_session(session_id)
        if not session:
            return {"status": "error", "error": "Session not found"}
        
        state = session.get("state")
        
        # Route based on current state and task type
        if task_type == "extract_dom":
            return self.handle_dom_extraction_result(
                session_id,
                result.get("dom_html", ""),
                result.get("screenshot_base64", "")
            )
        elif task_type == "execute_step":
            return self.handle_mapping_step_result(session_id, result)
        elif task_type == "runner_step":
            # Runner step results are handled via Redis polling
            return {"status": "ok", "message": "Runner step result received"}
        else:
            logger.warning(f"[Orchestrator] Unknown task_type: {task_type}")
            return {"status": "ok", "message": f"Unhandled task_type: {task_type}"}

