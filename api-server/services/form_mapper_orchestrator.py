# form_mapper_orchestrator.py
# COMPLETE STATE MACHINE - Matches original form_mapper_main.py algorithm
# SCALABLE: Designed for 100K+ concurrent users with Celery task chains

import time
import json
import logging
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class MapperState(str, Enum):
    """States in the form mapper state machine"""
    INITIALIZING = "initializing"
    LOGGING_IN = "logging_in"
    LOGIN_RECOVERING = "login_recovering"
    NAVIGATING = "navigating"
    NAV_RECOVERING = "nav_recovering"
    EXTRACTING_INITIAL_DOM = "extracting_initial_dom"
    INITIAL_UI_VERIFICATION = "initial_ui_verification"
    GETTING_INITIAL_SCREENSHOT = "getting_initial_screenshot"
    GENERATING_INITIAL_STEPS = "generating_initial_steps"
    EXECUTING_STEP = "executing_step"
    STEP_FAILED_EXTRACTING_DOM = "step_failed_extracting_dom"
    STEP_FAILED_AI_RECOVERY = "step_failed_ai_recovery"
    ALERT_EXTRACTING_DOM = "alert_extracting_dom"
    ALERT_AI_RECOVERY = "alert_ai_recovery"
    ALERT_NAVIGATING_BACK = "alert_navigating_back"
    DOM_CHANGE_GETTING_SCREENSHOT = "dom_change_getting_screenshot"
    DOM_CHANGE_UI_VERIFICATION = "dom_change_ui_verification"
    DOM_CHANGE_REGENERATING_STEPS = "dom_change_regenerating_steps"
    DOM_CHANGE_NAVIGATING_BACK = "dom_change_navigating_back"
    HANDLING_VALIDATION_ERROR = "handling_validation_error"
    PATH_COMPLETE = "path_complete"
    ALL_PATHS_COMPLETE = "all_paths_complete"
    ASSIGNING_TEST_CASES = "assigning_test_cases"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SYSTEM_ISSUE = "system_issue"
    NO_MORE_PATHS = "no_more_paths"


class SessionStatus:
    INITIALIZING = "initializing"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FormMapperOrchestrator:
    """Distributed Form Mapper Orchestrator - scalable for 100K+ users"""
    
    def __init__(self, redis_client_or_db, db_session=None):
        import redis
        import os
        
        if hasattr(redis_client_or_db, 'query'):
            self.db = redis_client_or_db
            self.redis = redis.Redis(host=os.getenv("REDIS_HOST", "redis"),
                                     port=int(os.getenv("REDIS_PORT", 6379)), db=0, decode_responses=False)
        else:
            self.redis = redis_client_or_db
            self.db = db_session
        self.max_retries = 3
        self.max_paths = 50
    
    def _load_company_config(self, company_id: int) -> dict:
        if not self.db:
            return self._get_default_config()
        try:
            from models.form_mapper_config_models import get_company_config
            return get_company_config(self.db, company_id).dict()
        except:
            return self._get_default_config()
    
    def _get_default_config(self) -> dict:
        return {"enable_ui_verification": True, "max_retries": 3, "use_detect_fields_change": True,
                "use_full_dom": True, "enable_junction_discovery": True, "max_junction_paths": 5}
    
    def _get_session_key(self, session_id: str) -> str:
        return f"mapper_session:{session_id}"
    
    def create_session(self, session_id=None, user_id=None, company_id=None, network_id=None,
                      form_route_id=None, form_page_route_id=None, test_cases=None, 
                      product_id=1, config=None, base_url=None):

        import uuid
        if form_route_id is None and form_page_route_id is not None:
            form_route_id = form_page_route_id
        print(f"[DEBUG] create_session: network_id={network_id}, form_route_id={form_route_id}")
        if session_id is None:
            session_id = str(uuid.uuid4())[:8]
        if test_cases is None:
            test_cases = []
        
        company_config = self._load_company_config(company_id) if company_id else self._get_default_config()
        if config:
            company_config.update(config)
        
        test_context = {"filled_fields": {}, "clicked_elements": [], "selected_options": {},
                       "credentials": {}, "reported_ui_issues": []}
        
        session_state = {
            "session_id": session_id, "user_id": user_id or 0, "company_id": company_id or 0,
            "product_id": product_id or 1, "network_id": network_id or 0,
            "form_route_id": form_route_id or 0, "base_url": base_url or "",
            "state": MapperState.INITIALIZING.value, "previous_state": "",
            "current_step_index": 0, "all_steps": "[]", "executed_steps": "[]",
            "current_dom_hash": "", "current_path": 0, "previous_paths": "[]",
            "current_path_junctions": "[]", "test_cases": json.dumps(test_cases),
            "test_context": json.dumps(test_context), "config": json.dumps(company_config),
            "consecutive_failures": 0, "recovery_failure_history": "[]",
            "critical_fields_checklist": "{}", "field_requirements_for_recovery": "",
            "pending_alert_info": "{}", "pending_validation_errors": "{}",
            "pending_screenshot_base64": "", "pending_new_steps": "[]",
            "final_steps": "[]", "last_error": "",
            "created_at": datetime.utcnow().isoformat(), "updated_at": datetime.utcnow().isoformat(),
            "completed_at": ""
        }
        
        key = self._get_session_key(session_id)
        self.redis.hset(key, mapping=session_state)
        self.redis.expire(key, 86400)
        logger.info(f"[Orchestrator] Created session {session_id} with network_id={network_id}, form_route_id={form_route_id}")
        if form_route_id:
            from tasks.form_mapper_tasks import cancel_previous_sessions_for_route
            cancel_previous_sessions_for_route.delay(form_route_id, session_id)
        
        class SessionResult:
            def __init__(self, sid, state): self.id = sid; self.status = state
        return SessionResult(session_id, MapperState.INITIALIZING.value)
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        data = self.redis.hgetall(self._get_session_key(session_id))
        if not data:
            return None
        decoded = {}
        json_fields = ["all_steps", "executed_steps", "test_cases", "previous_paths",
                      "current_path_junctions", "final_steps", "config", "test_context",
                      "recovery_failure_history", "pending_new_steps"]
        dict_fields = ["critical_fields_checklist", "pending_alert_info", "pending_validation_errors"]
        int_fields = ["current_step_index", "current_path", "user_id", "company_id",
                     "network_id", "form_route_id", "product_id", "consecutive_failures"]
        for k, v in data.items():
            ks = k.decode() if isinstance(k, bytes) else k
            vs = v.decode() if isinstance(v, bytes) else v
            if ks in json_fields:
                try: decoded[ks] = json.loads(vs) if vs else []
                except: decoded[ks] = []
            elif ks in dict_fields:
                try: decoded[ks] = json.loads(vs) if vs else {}
                except: decoded[ks] = {}
            elif ks in int_fields:
                try: decoded[ks] = int(vs) if vs else 0
                except: decoded[ks] = 0
            else: decoded[ks] = vs
        return decoded
    
    def update_session(self, session_id: str, updates: Dict) -> None:
        serialized = {}
        for k, v in updates.items():
            if isinstance(v, (list, dict)): serialized[k] = json.dumps(v)
            elif v is None: serialized[k] = ""
            else: serialized[k] = str(v)
        serialized["updated_at"] = datetime.utcnow().isoformat()
        self.redis.hset(self._get_session_key(session_id), mapping=serialized)

    def _sync_session_status_to_db(self, session_id: str, status: str, error: str = None) -> None:
        """Queue async task to sync session status to database (scalable)"""
        try:
            from tasks.form_mapper_tasks import sync_mapper_session_status
            sync_mapper_session_status.delay(session_id, status, error)
        except Exception as e:
            logger.error(f"[Orchestrator] Failed to queue DB sync: {e}")

    def transition_to(self, session_id: str, new_state: MapperState, **kwargs) -> None:
        session = self.get_session(session_id)
        if session:
            updates = {"previous_state": session.get("state", ""), "state": new_state.value}
            updates.update(kwargs)
            self.update_session(session_id, updates)
            logger.info(f"[Orchestrator] {session_id}: {session.get('state')} -> {new_state.value}")
    
    def _push_agent_task(self, session_id: str, task_type: str, payload: Dict) -> Dict:
        session = self.get_session(session_id)
        user_id = session.get("user_id", 1) if session else 1
        task = {"task_id": f"mapper_{session_id}_{task_type}_{int(time.time()*1000)}",
                "task_type": task_type, "session_id": session_id, "payload": payload}
        self.redis.lpush(f"agent:{user_id}", json.dumps(task))
        logger.info(f"[Orchestrator] Pushed {task_type} to agent:{user_id}")
        return task
    
    def _fail_session(self, session_id: str, error: str) -> Dict:
        self.transition_to(session_id, MapperState.FAILED, last_error=error,
                          completed_at=datetime.utcnow().isoformat())
        self._sync_session_status_to_db(session_id, "failed", error)
        return {"success": False, "error": error, "state": "failed"}

    # ============================================================
    # PHASE 1 & 2: LOGIN AND NAVIGATION (Forms Runner)
    # ============================================================
    
    def start_login_phase(self, session_id: str) -> Dict:
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}
        network_id = session.get("network_id")
        if not network_id: return self.start_navigation_phase(session_id)
        login_stages = self._load_login_stages(network_id)
        if not login_stages: return self.start_navigation_phase(session_id)
        self.transition_to(session_id, MapperState.LOGGING_IN)
        from tasks.forms_runner_tasks import start_runner_phase
        start_runner_phase.delay(
            session_id=str(session_id),
            phase="login",
            stages=login_stages,
            company_id=session.get("company_id", 0),
            user_id=session.get("user_id", 0),
            product_id=session.get("product_id", 1),
            network_id=network_id,
            form_route_id=session.get("form_route_id", 0)
        )
        return {"success": True, "phase": "login", "async": True}
    
    def handle_login_phase_complete(self, session_id: str, result: Dict) -> Dict:
        if not result.get("success"):
            return self._fail_session(session_id, result.get("error", "Login failed"))
        return self.start_navigation_phase(session_id)
    
    def start_navigation_phase(self, session_id: str) -> Dict:
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}
        form_route_id = session.get("form_route_id")
        if not form_route_id: return self.start_mapping_phase(session_id)
        nav_stages = self._load_navigation_stages(form_route_id)
        if not nav_stages: return self.start_mapping_phase(session_id)
        self.transition_to(session_id, MapperState.NAVIGATING)
        from tasks.forms_runner_tasks import start_runner_phase
        start_runner_phase.delay(
            session_id=str(session_id),
            phase="navigate",
            stages=nav_stages,
            company_id=session.get("company_id", 0),
            user_id=session.get("user_id", 0),
            product_id=session.get("product_id", 1),
            network_id=session.get("network_id", 0),
            form_route_id=form_route_id
        )
        return {"success": True, "phase": "navigate", "async": True}
    
    def handle_navigation_phase_complete(self, session_id: str, result: Dict) -> Dict:
        if not result.get("success"):
            return self._fail_session(session_id, result.get("error", "Navigation failed"))
        if result.get("final_url"):
            self.update_session(session_id, {"base_url": result.get("final_url")})
        return self.start_mapping_phase(session_id)

    # ============================================================
    # PHASE 3: FORM MAPPING - INITIAL
    # ============================================================
    
    def start_mapping_phase(self, session_id: str) -> Dict:
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}
        config = session.get("config", {})
        self.transition_to(session_id, MapperState.EXTRACTING_INITIAL_DOM, current_path=1)
        task = self._push_agent_task(session_id, "form_mapper_extract_dom", {
            "use_full_dom": config.get("use_full_dom", True),
            "capture_screenshot": config.get("enable_ui_verification", True)
        })
        return {"success": True, "phase": "mapping", "agent_task": task}

    def handle_initial_dom_result(self, session_id: str, result: Dict) -> Dict:
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}
        if not result.get("success"):
            return self._fail_session(session_id, result.get("error", "DOM extraction failed"))
        dom_html = result.get("dom_html", "")
        if not dom_html: return self._fail_session(session_id, "No DOM returned")

        dom_str = json.dumps(dom_html) if isinstance(dom_html, dict) else str(dom_html)
        self.redis.setex(f"mapper_dom:{session_id}", 3600, dom_str)
        dom_hash = hashlib.md5(dom_str.encode()).hexdigest()[:16]
        self.update_session(session_id, {"current_dom_hash": dom_hash})
        config = session.get("config", {})

        # Get screenshot for UI verification
        if config.get("enable_ui_verification", True):
            self.transition_to(session_id, MapperState.GETTING_INITIAL_SCREENSHOT)
            task = self._push_agent_task(session_id, "form_mapper_get_screenshot", {
                "scenario": "initial_form_state"
            })
            return {"success": True, "phase": "getting_screenshot", "agent_task": task}

        # Skip screenshot, go directly to generate steps
        return self._trigger_generate_initial_steps(session_id, dom_html, "")

    def handle_initial_screenshot_result(self, session_id: str, result: Dict) -> Dict:
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}

        screenshot_base64 = result.get("screenshot_base64", "") if result.get("success") else ""
        self.update_session(session_id, {"pending_screenshot_base64": screenshot_base64 or ""})

        config = session.get("config", {})
        dom_html = self.redis.get(f"mapper_dom:{session_id}")
        if dom_html: dom_html = dom_html.decode() if isinstance(dom_html, bytes) else dom_html

        # If screenshot captured, do UI verification
        if screenshot_base64:
            self.transition_to(session_id, MapperState.INITIAL_UI_VERIFICATION)
            test_context = session.get("test_context", {})
            return {"success": True, "trigger_celery": True, "celery_task": "verify_ui_visual",
                    "celery_args": {"session_id": session_id, "screenshot_base64": screenshot_base64,
                                    "previously_reported_issues": test_context.get("reported_ui_issues", [])}}

        # No screenshot, skip to generate steps
        return self._trigger_generate_initial_steps(session_id, dom_html, screenshot_base64)

    def handle_initial_ui_verification_result(self, session_id: str, result: Dict) -> Dict:
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}
        ui_issue = result.get("ui_issue", "")
        if ui_issue:
            test_context = session.get("test_context", {})
            reported = test_context.get("reported_ui_issues", [])
            for issue in ui_issue.split(','):
                issue = issue.strip()
                if issue and issue not in reported: reported.append(issue)
            test_context["reported_ui_issues"] = reported
            self.update_session(session_id, {"test_context": test_context})
            logger.warning(f"[Orchestrator] UI issues: {ui_issue}")
            self._push_agent_task(session_id, "form_mapper_save_screenshot_and_log",
                                  {"ui_issue": ui_issue,
                                   "scenario": "initial_ui_verification"})
        dom_html = self.redis.get(f"mapper_dom:{session_id}")
        if dom_html: dom_html = dom_html.decode() if isinstance(dom_html, bytes) else dom_html
        return self._trigger_generate_initial_steps(session_id, dom_html,
                                                    session.get("pending_screenshot_base64", ""))
    
    def _trigger_generate_initial_steps(self, session_id: str, dom_html: str, screenshot_base64: str) -> Dict:
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}
        config = session.get("config", {})
        self.transition_to(session_id, MapperState.GENERATING_INITIAL_STEPS)
        return {"success": True, "trigger_celery": True, "celery_task": "analyze_form_page",
                "celery_args": {
                    "session_id": session_id, "dom_html": dom_html, "screenshot_base64": screenshot_base64,
                    "test_cases": session.get("test_cases", []), "previous_paths": session.get("previous_paths", []),
                    "current_path": session.get("current_path", 1),
                    "enable_junction_discovery": config.get("enable_junction_discovery", True),
                    "critical_fields_checklist": session.get("critical_fields_checklist", {}),
                    "field_requirements": session.get("field_requirements_for_recovery", ""),
                    "current_path_junctions": session.get("current_path_junctions", [])}}
    
    def handle_generate_initial_steps_result(self, session_id: str, result: Dict) -> Dict:
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}
        if result.get("no_more_paths", False) and session.get("current_path", 1) > 1:
            self.transition_to(session_id, MapperState.NO_MORE_PATHS)
            return self._complete_all_paths(session_id)
        steps = result.get("steps", [])
        if not steps: return self._fail_session(session_id, "AI generated no steps")
        self.update_session(session_id, {"all_steps": steps, "executed_steps": [],
                                         "current_step_index": 0, "consecutive_failures": 0})
        logger.info(f"[Orchestrator] Generated {len(steps)} initial steps")
        return self._execute_next_step(session_id)

    # ============================================================
    # STEP EXECUTION LOOP
    # ============================================================
    
    def _execute_next_step(self, session_id: str) -> Dict:
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}
        all_steps = session.get("all_steps", [])
        current_index = session.get("current_step_index", 0)
        if current_index >= len(all_steps):
            return self._handle_path_complete(session_id)
        step = all_steps[current_index]

        self.transition_to(session_id, MapperState.EXECUTING_STEP)
        task = self._push_agent_task(session_id, "form_mapper_exec_step", {
            "step": step, "step_index": current_index, "total_steps": len(all_steps),
            "current_dom_hash": session.get("current_dom_hash", "")})
        logger.info(f"[Orchestrator] Step {current_index + 1}/{len(all_steps)}: {step.get('action')}")
        return {"success": True, "agent_task": task}
    
    def handle_step_result(self, session_id: str, result: Dict) -> Dict:
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}
        step = result.get("executed_step") or {}
        selector = step.get('selector') or ''
        description = step.get('description') or ''
        print(f"!!!!!!!!!!!!!!!!!!!!!!!!! Got result from Agent step: action={step.get('action')}, selector={selector[:30]}, description={description[:40]}, success={result.get('success')}, fields_changed={result.get('fields_changed')}")
        if not result.get("success"):
            return self._handle_step_failure(session_id, result)
        return self._handle_step_success(session_id, result)

    # ============================================================
    # STEP FAILURE HANDLING
    # ============================================================
    
    def _handle_step_failure(self, session_id: str, result: Dict) -> Dict:
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}
        all_steps = session.get("all_steps", [])
        current_index = session.get("current_step_index", 0)
        step = all_steps[current_index] if current_index < len(all_steps) else {}
        
        # Verification failure - just skip
        if step.get("action") == "verify":
            logger.info(f"[Orchestrator] Verification failed, skipping")
            executed_steps = session.get("executed_steps", [])
            executed_steps.append(step)
            self.update_session(session_id, {"executed_steps": executed_steps,
                                             "current_step_index": current_index + 1,
                                             "consecutive_failures": 0})
            return self._execute_next_step(session_id)
        
        # Increment consecutive failures
        consecutive_failures = session.get("consecutive_failures", 0) + 1
        config = session.get("config", {})
        max_retries = config.get("max_retries", self.max_retries)
        self.update_session(session_id, {"consecutive_failures": consecutive_failures})
        logger.warning(f"[Orchestrator] Step failed. Consecutive: {consecutive_failures}/{max_retries}")
        
        if consecutive_failures >= max_retries:
            return self._fail_session(session_id, f"Max consecutive failures ({max_retries}) reached")
        
        # Add to recovery history
        recovery_history = session.get("recovery_failure_history", [])
        recovery_history.append({"action": step.get("action"), "selector": step.get("selector"),
                                "description": step.get("description"), "error": result.get("error")})
        self.update_session(session_id, {"recovery_failure_history": recovery_history})
        
        # Request fresh DOM for AI recovery
        self.transition_to(session_id, MapperState.STEP_FAILED_EXTRACTING_DOM)
        task = self._push_agent_task(session_id, "form_mapper_extract_dom_for_recovery", {
            "capture_screenshot": True, "save_screenshot": True,
            "scenario_description": f"error_{step.get('description', 'unknown')[:30]}"})
        return {"success": True, "state": "step_failed_extracting_dom", "agent_task": task}
    
    def handle_step_failure_dom_result(self, session_id: str, result: Dict) -> Dict:
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}
        if not result.get("success") or not result.get("dom_html"):
            return self._fail_session(session_id, "Failed to extract DOM for recovery")
        dom_html = result.get("dom_html", "")
        screenshot_path = result.get("screenshot_path", "")
        if not screenshot_path:
            return self._fail_session(session_id, "Failed to capture screenshot for recovery")
        
        self.redis.setex(f"mapper_dom:{session_id}", 3600, str(dom_html))
        all_steps = session.get("all_steps", [])
        current_index = session.get("current_step_index", 0)
        failed_step = all_steps[current_index] if current_index < len(all_steps) else {}
        
        self.transition_to(session_id, MapperState.STEP_FAILED_AI_RECOVERY)
        return {"success": True, "trigger_celery": True, "celery_task": "analyze_failure_and_recover",
                "celery_args": {
                    "session_id": session_id, "failed_step": failed_step,
                    "executed_steps": session.get("executed_steps", []), "fresh_dom": dom_html,
                    "screenshot_path": screenshot_path, "test_cases": session.get("test_cases", []),
                    "test_context": session.get("test_context", {}),
                    "attempt_number": session.get("consecutive_failures", 1),
                    "recovery_failure_history": session.get("recovery_failure_history", [])}}
    
    def handle_step_failure_recovery_result(self, session_id: str, result: Dict) -> Dict:
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}
        recovery_steps = result.get("steps", [])
        if not recovery_steps:
            return self._fail_session(session_id, "AI failed to generate recovery steps")
        logger.info(f"[Orchestrator] AI generated {len(recovery_steps)} recovery steps")
        executed_steps = session.get("executed_steps", [])
        self.update_session(session_id, {"all_steps": executed_steps + recovery_steps,
                                         "current_step_index": len(executed_steps)})
        return self._execute_next_step(session_id)

    # ============================================================
    # STEP SUCCESS HANDLING
    # ============================================================
    
    def _handle_step_success(self, session_id: str, result: Dict) -> Dict:
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}
        all_steps = session.get("all_steps", [])
        current_index = session.get("current_step_index", 0)
        step = all_steps[current_index] if current_index < len(all_steps) else {}
        
        # Reset failures, add to executed
        executed_steps = session.get("executed_steps", [])
        executed_steps.append(step)
        self.update_session(session_id, {"executed_steps": executed_steps, "consecutive_failures": 0})
        
        # Check for alert
        if result.get("alert_present") or result.get("alert_detected"):
            return self._handle_alert(session_id, result)
        
        # Check for DOM change
        old_hash = session.get("current_dom_hash", "")
        new_hash = result.get("new_dom_hash", "")
        if new_hash and new_hash != old_hash:
            return self._handle_dom_change(session_id, session, step, result, new_hash)
        
        # Move to next step
        self.update_session(session_id, {"current_step_index": current_index + 1})
        return self._execute_next_step(session_id)

    # ============================================================
    # ALERT HANDLING
    # ============================================================
    
    def _handle_alert(self, session_id: str, result: Dict) -> Dict:
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}
        alert_type = result.get("alert_type", "alert")
        alert_text = result.get("alert_text", "")
        logger.info(f"[Orchestrator] Alert: {alert_type} - {alert_text[:50]}")
        
        # Add accept_alert to executed
        executed_steps = session.get("executed_steps", [])
        executed_steps.append({"step_number": len(executed_steps) + 1, "action": "accept_alert",
                              "selector": "", "value": "",
                              "description": f"Accept {alert_type}: {alert_text[:50]}..."})
        self.update_session(session_id, {"executed_steps": executed_steps,
                                         "pending_alert_info": {"alert_type": alert_type, "alert_text": alert_text}})
        self.transition_to(session_id, MapperState.ALERT_EXTRACTING_DOM)
        task = self._push_agent_task(session_id, "form_mapper_extract_dom_for_alert",
                                    {"alert_type": alert_type, "alert_text": alert_text})
        return {"success": True, "state": "alert_extracting_dom", "agent_task": task}
    
    def handle_alert_dom_result(self, session_id: str, result: Dict) -> Dict:
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}
        if not result.get("success"):
            return self._fail_session(session_id, "Failed to extract DOM after alert")
        dom_html = result.get("dom_html", "")
        self.redis.setex(f"mapper_dom:{session_id}", 3600, str(dom_html))
        pending = session.get("pending_alert_info", {})
        alert_info = {"success": True, "alert_present": True,
                     "alert_type": pending.get("alert_type", "alert"),
                     "alert_text": pending.get("alert_text", "")}
        self.transition_to(session_id, MapperState.ALERT_AI_RECOVERY)
        return {"success": True, "trigger_celery": True, "celery_task": "handle_alert_recovery",
                "celery_args": {
                    "session_id": session_id, "alert_info": alert_info,
                    "executed_steps": session.get("executed_steps", []), "dom_html": dom_html,
                    "screenshot_path": None, "test_cases": session.get("test_cases", []),
                    "test_context": session.get("test_context", {}),
                    "step_where_alert_appeared": len(session.get("executed_steps", [])),
                    "include_accept_step": False, "gathered_error_info": None}}
    
    def handle_alert_recovery_result(self, session_id: str, result: Dict) -> Dict:
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}
        if not result.get("success", True):
            return self._fail_session(session_id, "AI failed to generate alert recovery")
        scenario = result.get("scenario", "A")
        issue_type = result.get("issue_type", "")
        alert_steps = result.get("steps", [])
        
        # Real system issue
        if scenario == "B" and issue_type == "real_issue":
            self.transition_to(session_id, MapperState.SYSTEM_ISSUE,
                              last_error=f"Real issue: {result.get('explanation', '')}",
                              completed_at=datetime.utcnow().isoformat())
            return {"success": False, "system_issue": True, "explanation": result.get("explanation", "")}
        
        if not alert_steps:
            return self._fail_session(session_id, "AI returned no alert recovery steps")
        
        executed_steps = session.get("executed_steps", [])
        
        if scenario == "A":
            # Scenario A: append and continue
            logger.info(f"[Orchestrator] Alert Scenario A: Appending {len(alert_steps)} steps")
            self.update_session(session_id, {"all_steps": executed_steps + alert_steps,
                                             "current_step_index": len(executed_steps)})
            return self._execute_next_step(session_id)
        else:
            # Scenario B: navigate back, start fresh
            logger.info(f"[Orchestrator] Alert Scenario B: Starting fresh with {len(alert_steps)} steps")
            updates = {"pending_new_steps": alert_steps}
            if result.get("problematic_fields"):
                updates["critical_fields_checklist"] = {f: "MUST FILL" for f in result.get("problematic_fields")}
            if result.get("field_requirements"):
                updates["field_requirements_for_recovery"] = result.get("field_requirements")
            self.update_session(session_id, updates)
            
            base_url = session.get("base_url", "")
            if base_url:
                self.transition_to(session_id, MapperState.ALERT_NAVIGATING_BACK)
                task = self._push_agent_task(session_id, "form_mapper_navigate_to_url", {"url": base_url})
                return {"success": True, "state": "alert_navigating_back", "agent_task": task}
            else:
                self.update_session(session_id, {"all_steps": alert_steps, "executed_steps": [],
                                                 "current_step_index": 0})
                return self._execute_next_step(session_id)
    
    def handle_navigate_back_result(self, session_id: str, result: Dict) -> Dict:
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}
        if not result.get("success"):
            return self._fail_session(session_id, f"Failed to navigate back: {result.get('error', '')}")
        new_steps = session.get("pending_new_steps", [])
        self.update_session(session_id, {"all_steps": new_steps, "executed_steps": [],
                                         "current_step_index": 0, "pending_new_steps": []})
        logger.info(f"[Orchestrator] Navigated back, starting fresh with {len(new_steps)} steps")
        return self._execute_next_step(session_id)

    # ============================================================
    # DOM CHANGE HANDLING
    # ============================================================
    
    def _handle_dom_change(self, session_id: str, session: Dict, step: Dict, result: Dict, new_hash: str) -> Dict:
        logger.info(f"[Orchestrator] DOM changed: {new_hash[:16]}...")
        self.update_session(session_id, {"current_dom_hash": new_hash})
        
        # Check for validation errors
        validation_errors = result.get("validation_errors", {})
        if validation_errors.get("has_errors"):
            return self._handle_validation_errors(session_id, validation_errors)
        
        config = session.get("config", {})
        
        # Check fields_changed
        if config.get("use_detect_fields_change", True):
            if not result.get("fields_changed", True):
                print(
                    f"!!!!!!!!!!!!!!!!!!!!!!!!! ℹ️  We are using Fields Detection and Fields did not change - skipping AI regeneration")
                logger.info(f"[Orchestrator] Fields unchanged, skipping regeneration")
                current_index = session.get("current_step_index", 0)
                self.update_session(session_id, {"current_step_index": current_index + 1})
                return self._execute_next_step(session_id)
            else:
                print(
                    f"!!!!!!!!!!!!!!!!!!!!!!!!! ✅ We are using Fields Detection and Fields changed - proceeding with AI regeneration")
        # Track junction
        if config.get("enable_junction_discovery", True):
            action = step.get("action", "").lower()
            if action in ["select", "check", "click"]:
                junctions = session.get("current_path_junctions", [])
                junctions.append({"field": step.get("description", "Unknown"),
                                 "selector": step.get("selector", ""),
                                 "value": step.get("value", ""), "action": action})
                self.update_session(session_id, {"current_path_junctions": junctions})
                print(f"!!!!!!!!!!!!!!!!!!!!!!!!! 🔀 Junction detected: {step.get('description')} = {step.get('value')}")
                logger.info(f"[Orchestrator] Junction: {step.get('description')}")
        
        # Get screenshot for UI verification
        if config.get("enable_ui_verification", True):
            print(f"!!!!!!!!!!!!!!!!!!!!!!!!! 📸 Capturing screenshot for UI verification...")
            self.transition_to(session_id, MapperState.DOM_CHANGE_GETTING_SCREENSHOT)
            task = self._push_agent_task(session_id, "form_mapper_get_screenshot",
                                        {"encode_base64": True, "save_to_folder": False})
            return {"success": True, "state": "dom_change_getting_screenshot", "agent_task": task}
        print(f"!!!!!!!!!!!!!!!!!!!!!!!!! 🔄 Triggering regenerate_steps...")
        return self._trigger_regenerate_steps(session_id, None)
    
    def handle_dom_change_screenshot_result(self, session_id: str, result: Dict) -> Dict:
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}
        screenshot_base64 = result.get("screenshot_base64", "") if result.get("success") else ""
        if not screenshot_base64:
            logger.warning(f"[Orchestrator] Screenshot failed, skipping UI verification")
            return self._trigger_regenerate_steps(session_id, None)
        self.update_session(session_id, {"pending_screenshot_base64": screenshot_base64})
        self.transition_to(session_id, MapperState.DOM_CHANGE_UI_VERIFICATION)
        test_context = session.get("test_context", {})
        return {"success": True, "trigger_celery": True, "celery_task": "verify_ui_visual",
                "celery_args": {"session_id": session_id, "screenshot_base64": screenshot_base64,
                               "previously_reported_issues": test_context.get("reported_ui_issues", [])}}
    
    def handle_dom_change_ui_verification_result(self, session_id: str, result: Dict) -> Dict:
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}
        ui_issue = result.get("ui_issue", "")
        if ui_issue:
            test_context = session.get("test_context", {})
            reported = test_context.get("reported_ui_issues", [])
            for issue in ui_issue.split(','):
                issue = issue.strip()
                if issue and issue not in reported: reported.append(issue)
            test_context["reported_ui_issues"] = reported
            self.update_session(session_id, {"test_context": test_context})
            logger.warning(f"[Orchestrator] UI issues: {ui_issue}")
            self._push_agent_task(session_id, "form_mapper_save_screenshot_and_log",
                                 {"scenario_description": "ui_issue",
                                  "log_message": f"UI ISSUE (after DOM change): {ui_issue}", "log_level": "warning"})
        return self._trigger_regenerate_steps(session_id, session.get("pending_screenshot_base64", ""))
    
    def _trigger_regenerate_steps(self, session_id: str, screenshot_base64: Optional[str]) -> Dict:
        print(f"!!!!!!!!!!!!!!!!!!!!!!!!! 🔄 Regenerating remaining steps...")
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}
        self.transition_to(session_id, MapperState.DOM_CHANGE_REGENERATING_STEPS)
        dom_html = self.redis.get(f"mapper_dom:{session_id}")
        if dom_html: dom_html = dom_html.decode() if isinstance(dom_html, bytes) else dom_html
        config = session.get("config", {})
        return {"success": True, "trigger_celery": True, "celery_task": "regenerate_steps",
                "celery_args": {
                    "session_id": session_id, "dom_html": dom_html,
                    "executed_steps": session.get("executed_steps", []),
                    "test_cases": session.get("test_cases", []),
                    "test_context": session.get("test_context", {}),
                    "screenshot_base64": screenshot_base64,
                    "critical_fields_checklist": session.get("critical_fields_checklist", {}),
                    "field_requirements": session.get("field_requirements_for_recovery", ""),
                    "previous_paths": session.get("previous_paths", []),
                    "current_path_junctions": session.get("current_path_junctions", []),
                    "enable_junction_discovery": config.get("enable_junction_discovery", True)}}
    
    def handle_regenerate_steps_result(self, session_id: str, result: Dict) -> Dict:
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}
        config = session.get("config", {})
        if config.get("enable_junction_discovery", True) and result.get("no_more_paths", False):
            if session.get("current_path", 1) > 1:
                logger.info(f"[Orchestrator] AI says no more paths")
                return self._handle_path_complete(session_id)
        new_steps = result.get("new_steps", []) or result.get("steps", [])
        if not new_steps: return self._handle_path_complete(session_id)
        executed_steps = session.get("executed_steps", [])
        current_index = session.get("current_step_index", 0)
        self.update_session(session_id, {"all_steps": executed_steps + new_steps,
                                         "current_step_index": len(executed_steps)})
        logger.info(f"[Orchestrator] Regenerated {len(new_steps)} steps, continuing from step {len(executed_steps) + 1}")
        return self._execute_next_step(session_id)
    
    # ============================================================
    # VALIDATION ERROR HANDLING
    # ============================================================
    
    def _handle_validation_errors(self, session_id: str, validation_errors: Dict) -> Dict:
        logger.warning(f"[Orchestrator] Validation errors: {len(validation_errors.get('error_fields', []))} fields")
        self.update_session(session_id, {"pending_validation_errors": validation_errors})
        self.transition_to(session_id, MapperState.DOM_CHANGE_GETTING_SCREENSHOT)
        task = self._push_agent_task(session_id, "form_mapper_get_screenshot",
                                    {"encode_base64": False, "save_to_folder": True,
                                     "scenario_description": "validation_error"})
        return {"success": True, "state": "getting_screenshot_for_validation", "agent_task": task}
    
    def handle_validation_error_screenshot_result(self, session_id: str, result: Dict) -> Dict:
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}
        if not result.get("success"):
            return self._fail_session(session_id, "Failed to capture screenshot for validation errors")
        screenshot_path = result.get("screenshot_path", "")
        validation_errors = session.get("pending_validation_errors", {})
        dom_html = self.redis.get(f"mapper_dom:{session_id}")
        if dom_html: dom_html = dom_html.decode() if isinstance(dom_html, bytes) else dom_html
        validation_info = {"success": True, "alert_present": False, "alert_type": "validation_error",
                         "alert_text": f"Validation errors: {', '.join(validation_errors.get('error_messages', [])[:3])}"}
        gathered = {"error_fields": validation_errors.get("error_fields", []),
                   "error_messages": validation_errors.get("error_messages", [])}
        self.transition_to(session_id, MapperState.HANDLING_VALIDATION_ERROR)
        return {"success": True, "trigger_celery": True, "celery_task": "handle_alert_recovery",
                "celery_args": {
                    "session_id": session_id, "alert_info": validation_info,
                    "executed_steps": session.get("executed_steps", []), "dom_html": dom_html,
                    "screenshot_path": screenshot_path, "test_cases": session.get("test_cases", []),
                    "test_context": session.get("test_context", {}),
                    "step_where_alert_appeared": len(session.get("executed_steps", [])),
                    "include_accept_step": False, "gathered_error_info": gathered}}

    # ============================================================
    # PATH COMPLETION
    # ============================================================
    
    def _handle_path_complete(self, session_id: str) -> Dict:
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}
        executed_steps = session.get("executed_steps", [])
        logger.info(f"[Orchestrator] Path complete: {len(executed_steps)} steps")
        self.update_session(session_id, {"critical_fields_checklist": {},
                                         "field_requirements_for_recovery": ""})
        self.transition_to(session_id, MapperState.PATH_COMPLETE)
        return self._complete_all_paths(session_id)
    
    def _complete_all_paths(self, session_id: str) -> Dict:
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}
        self.transition_to(session_id, MapperState.ASSIGNING_TEST_CASES)
        executed_steps = session.get("executed_steps", [])
        return {"success": True, "trigger_celery": True, "celery_task": "assign_test_cases",
                "celery_args": {"session_id": session_id, "stages": executed_steps,
                               "test_cases": session.get("test_cases", [])}}
    
    def handle_test_case_assignment_result(self, session_id: str, result: Dict) -> Dict:
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}
        final_stages = result.get("stages", session.get("executed_steps", []))
        self.transition_to(session_id, MapperState.COMPLETED, final_steps=final_stages,
                          completed_at=datetime.utcnow().isoformat())
        self._sync_session_status_to_db(session_id, "completed")
        logger.info(f"[Orchestrator] Session {session_id} COMPLETED: {len(final_stages)} steps")
        return {"success": True, "state": "completed", "total_steps": len(final_stages)}

    # ============================================================
    # DATABASE HELPERS
    # ============================================================
    
    def _load_login_stages(self, network_id: int) -> List[Dict]:
        if not self.db: return []
        try:
            from models.database import Network
            network = self.db.query(Network).filter(Network.id == network_id).first()
            if not network or not network.login_stages: return []
            return network.login_stages if isinstance(network.login_stages, list) else []
        except: return []
    
    def _load_navigation_stages(self, form_route_id: int) -> List[Dict]:
        if not self.db: return []
        try:
            from models.database import FormPageRoute
            route = self.db.query(FormPageRoute).filter(FormPageRoute.id == form_route_id).first()
            if not route or not route.navigation_steps: return []
            return route.navigation_steps if isinstance(route.navigation_steps, list) else []
        except: return []

    # ============================================================
    # SESSION CONTROL
    # ============================================================
    
    def cancel_session(self, session_id: str) -> Dict:
        self.transition_to(session_id, MapperState.CANCELLED, completed_at=datetime.utcnow().isoformat())
        return {"success": True, "state": "cancelled"}
    
    def get_session_status(self, session_id: str) -> Dict:
        session = self.get_session(session_id)
        if not session: return {"error": "Session not found"}
        state = session.get("state", "unknown")
        return {"session_id": session_id, "state": state,
                "phase": self._get_phase_from_state(state),
                "current_step": session.get("current_step_index", 0),
                "total_steps": len(session.get("all_steps", [])),
                "executed_steps": len(session.get("executed_steps", [])),
                "last_error": session.get("last_error", ""),
                "created_at": session.get("created_at"),
                "updated_at": session.get("updated_at"),
                "completed_at": session.get("completed_at")}
    
    def _get_phase_from_state(self, state: str) -> str:
        if state in [MapperState.LOGGING_IN.value, MapperState.LOGIN_RECOVERING.value]: return "login"
        elif state in [MapperState.NAVIGATING.value, MapperState.NAV_RECOVERING.value]: return "navigate"
        elif state in [MapperState.COMPLETED.value, MapperState.FAILED.value,
                      MapperState.CANCELLED.value, MapperState.SYSTEM_ISSUE.value]: return "finished"
        return "mapping"

    # ============================================================
    # MAIN ROUTERS
    # ============================================================
    
    def process_agent_result(self, session_id: str, result: Dict) -> Dict:
        """Main router for agent results"""
        session = self.get_session(session_id)
        if not session: return {"status": "error", "error": "Session not found"}
        task_type = result.get("task_type", "")
        state = session.get("state", "")
        logger.info(f"[Orchestrator] Processing {task_type} in state {state}")
        
        if state == MapperState.EXTRACTING_INITIAL_DOM.value:
            return self.handle_initial_dom_result(session_id, result)
        elif state == MapperState.GETTING_INITIAL_SCREENSHOT.value:
            return self.handle_initial_screenshot_result(session_id, result)
        elif state == MapperState.EXECUTING_STEP.value:
            return self.handle_step_result(session_id, result)
        elif state == MapperState.STEP_FAILED_EXTRACTING_DOM.value:
            return self.handle_step_failure_dom_result(session_id, result)
        elif state == MapperState.ALERT_EXTRACTING_DOM.value:
            return self.handle_alert_dom_result(session_id, result)
        elif state in [MapperState.ALERT_NAVIGATING_BACK.value, MapperState.DOM_CHANGE_NAVIGATING_BACK.value]:
            return self.handle_navigate_back_result(session_id, result)
        elif state == MapperState.DOM_CHANGE_GETTING_SCREENSHOT.value:
            validation_errors = session.get("pending_validation_errors", {})
            if validation_errors.get("has_errors"):
                return self.handle_validation_error_screenshot_result(session_id, result)
            return self.handle_dom_change_screenshot_result(session_id, result)
        else:
            logger.warning(f"[Orchestrator] Unhandled state {state} for task {task_type}")
            return {"status": "ok", "message": f"Unhandled: {state}/{task_type}"}
    
    def process_celery_result(self, session_id: str, task_name: str, result: Dict) -> Dict:
        """Router for Celery task results"""
        session = self.get_session(session_id)
        if not session: return {"status": "error", "error": "Session not found"}
        state = session.get("state", "")
        logger.info(f"[Orchestrator] Processing Celery {task_name} in state {state}")
        
        if task_name == "verify_ui_visual":
            if state == MapperState.INITIAL_UI_VERIFICATION.value:
                return self.handle_initial_ui_verification_result(session_id, result)
            elif state == MapperState.DOM_CHANGE_UI_VERIFICATION.value:
                return self.handle_dom_change_ui_verification_result(session_id, result)
        elif task_name == "analyze_form_page":
            return self.handle_generate_initial_steps_result(session_id, result)
        elif task_name == "analyze_failure_and_recover":
            return self.handle_step_failure_recovery_result(session_id, result)
        elif task_name == "handle_alert_recovery":
            return self.handle_alert_recovery_result(session_id, result)
        elif task_name == "regenerate_steps":
            return self.handle_regenerate_steps_result(session_id, result)
        elif task_name == "assign_test_cases":
            return self.handle_test_case_assignment_result(session_id, result)
        logger.warning(f"[Orchestrator] Unhandled Celery task: {task_name}")
        return {"status": "ok", "message": f"Unhandled task: {task_name}"}

    # ============================================================
    # RUNNER PHASE HELPERS
    # ============================================================
    
    def check_runner_phase_complete(self, session_id: str) -> Optional[Dict]:
        result = self.redis.get(f"runner_phase_complete:{session_id}")
        if result:
            self.redis.delete(f"runner_phase_complete:{session_id}")
            return json.loads(result)
        return None
    
    def poll_and_advance_runner(self, session_id: str) -> Dict:
        completion = self.check_runner_phase_complete(session_id)
        if not completion:
            session = self.get_session(session_id)
            return {"status": "running", "phase": session.get("state") if session else "unknown"}
        phase = completion.get("phase")
        if not completion.get("success"):
            return {"status": "failed", "phase": phase, "error": completion.get("error")}
        if phase == "login": return self.handle_login_phase_complete(session_id, completion)
        elif phase == "navigate": return self.handle_navigation_phase_complete(session_id, completion)
        return {"status": "complete", "phase": phase}

    def check_and_process_celery_results(self, session_id: str) -> Optional[Dict]:
        """
        Check for pending Celery task results and process them.
        Called by status endpoint to advance state machine.
        """
        # Check runner phase completion (login/navigate)
        completion = self.check_runner_phase_complete(session_id)
        if completion:
            phase = completion.get("phase")
            if phase == "login":
                return self.handle_login_phase_complete(session_id, completion)
            elif phase == "navigate":
                return self.handle_navigation_phase_complete(session_id, completion)
            return completion

        return None
