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
from models.database import ActivityLogEntry
from services.s3_storage import generate_presigned_put_url
from services.path_evaluation_service import (
    PathEvaluationService, JunctionsState, create_path_evaluation_service
)
from services.session_logger import SessionLogger, get_session_logger, ActivityType, LogCategory

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)

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
    DOM_CHANGE_GETTING_DOM = "dom_change_getting_dom"
    DOM_CHANGE_REGENERATING_STEPS = "dom_change_regenerating_steps"
    DOM_CHANGE_REGENERATING_VERIFY_STEPS = "dom_change_regenerating_verify_steps"
    DOM_CHANGE_NAVIGATING_BACK = "dom_change_navigating_back"
    NEXT_PATH_NAVIGATING = "next_path_navigating"
    HANDLING_VALIDATION_ERROR = "handling_validation_error"
    PATH_COMPLETE = "path_complete"
    PATH_EVALUATION_AI = "path_evaluation_ai"
    ALL_PATHS_COMPLETE = "all_paths_complete"
    SAVING_RESULT = "saving_result"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SYSTEM_ISSUE = "system_issue"
    NO_MORE_PATHS = "no_more_paths"
    VALIDATION_ERROR_RECOVERY = "validation_error_recovery"
    VALIDATION_ERROR_GETTING_DOM = "validation_error_getting_dom"


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
        self._session_loggers = {}

        # Cache TTL for company config (5 minutes)
        COMPANY_CONFIG_CACHE_TTL = 300

    def _get_logger(self, session_id: str) -> SessionLogger:
        """Get or create session logger with context from session data"""
        if session_id in self._session_loggers:
            return self._session_loggers[session_id]

        session = self.get_session(session_id)
        if not session:
            return SessionLogger(
                activity_type=ActivityType.MAPPING.value,
                session_id=session_id
            )

        logger = get_session_logger(
            db_session=self.db,
            activity_type=ActivityType.MAPPING.value,
            session_id=session_id,
            company_id=session.get("company_id"),
            user_id=session.get("user_id"),
            project_id=session.get("project_id"),
            network_id=session.get("network_id"),
            form_route_id=session.get("form_route_id"),
            form_name=session.get("form_name")
        )
        self._session_loggers[session_id] = logger
        return logger

    def _generate_upload_urls(self, company_id: int, project_id: int, session_id: str,
                              activity_type: str = "mapping", form_route_id: int = 0) -> dict:
        """Generate pre-signed URLs for log and screenshot uploads."""
        try:
            # URL for logs (all logs go to S3)
            logs_s3_key = f"logs/{company_id}/{project_id}/{activity_type}_{session_id}.json"
            logs_url = generate_presigned_put_url(
                s3_key=logs_s3_key,
                content_type='application/json',
                expiration=7200  # 2 hours
            )

            # URL for screenshots zip
            screenshots_zip_s3_key = f"screenshots_temp/{company_id}/{project_id}/{activity_type}_{session_id}.zip"
            screenshots_zip_url = generate_presigned_put_url(
                s3_key=screenshots_zip_s3_key,
                content_type='application/zip',
                expiration=7200  # 2 hours
            )

            # URL for form files zip (only for mapping, uses form_route_id)
            form_files_zip_url = None
            form_files_zip_s3_key = None
            if activity_type == "mapping" and form_route_id:
                form_files_zip_s3_key = f"form_files_temp/{company_id}/{project_id}/{form_route_id}.zip"
                form_files_zip_url = generate_presigned_put_url(
                    s3_key=form_files_zip_s3_key,
                    content_type='application/zip',
                    expiration=7200  # 2 hours
                )

            result = {
                "logs": logs_url,
                "logs_s3_key": logs_s3_key,
                "screenshots_zip": screenshots_zip_url,
                "screenshots_zip_s3_key": screenshots_zip_s3_key
            }

            if form_files_zip_url:
                result["form_files_zip"] = form_files_zip_url
                result["form_files_zip_s3_key"] = form_files_zip_s3_key
                result["form_page_route_id"] = form_route_id

            return result

        except Exception as e:
            logger.error(f"[Orchestrator] Failed to generate upload URLs: {e}")
            return {}

    def _load_company_config(self, company_id: int) -> dict:
        if not self.db:
            return self._get_default_config()

        # Try Redis cache first
        cached_config = self._get_cached_company_config(company_id)
        if cached_config:
            return cached_config

        # Load from DB
        try:
            from models.form_mapper_config_models import get_company_config
            config = get_company_config(self.db, company_id).dict()
            # Cache for next time
            self._cache_company_config(company_id, config)
            return config
        except:
            return self._get_default_config()

    def _load_project_config(self, project_id: int) -> dict:
        """Load project-specific config overrides"""
        if not self.db or not project_id:
            return {}
        try:
            from models.database import Project
            project = self.db.query(Project).filter(Project.id == project_id).first()
            if project and project.form_mapper_config:
                return project.form_mapper_config
        except Exception as e:
            logger.warning(f"[Orchestrator] Failed to load project config: {e}")
        return {}

    def _load_full_config(self, company_id: int, project_id: int = None) -> dict:
        """Load config with hierarchy: global -> company -> project"""
        config = self._get_default_config()
        if company_id:
            company_config = self._load_company_config(company_id)
            config.update(company_config)
        if project_id:
            project_config = self._load_project_config(project_id)
            config.update(project_config)
        return config

    def _get_cached_company_config(self, company_id: int) -> dict:
        """Get company config from Redis cache."""
        if not self.redis:
            return None
        try:
            import json
            key = f"company_config:{company_id}"
            data = self.redis.get(key)
            if data:
                return json.loads(data.decode('utf-8') if isinstance(data, bytes) else data)
        except Exception as e:
            logger.warning(f"[Orchestrator] Failed to get cached config: {e}")
        return None

    def _cache_company_config(self, company_id: int, config: dict) -> None:
        """Cache company config in Redis."""
        if not self.redis:
            return
        try:
            import json
            key = f"company_config:{company_id}"
            self.redis.set(key, json.dumps(config), ex=self.COMPANY_CONFIG_CACHE_TTL)
        except Exception as e:
            logger.warning(f"[Orchestrator] Failed to cache config: {e}")

    def invalidate_company_config_cache(self, company_id: int) -> None:
        """Invalidate cached company config (call when admin updates config)."""
        if not self.redis:
            return
        try:
            key = f"company_config:{company_id}"
            self.redis.delete(key)
            logger.info(f"[Orchestrator] Invalidated config cache for company {company_id}")
        except Exception as e:
            logger.warning(f"[Orchestrator] Failed to invalidate config cache: {e}")




    def _get_default_config(self) -> dict:
        from models.form_mapper_config_models import DEFAULT_FORM_MAPPER_CONFIG
        return DEFAULT_FORM_MAPPER_CONFIG.copy()
    
    def _get_session_key(self, session_id: str) -> str:
        return f"mapper_session:{session_id}"
    
    def create_session(self, session_id=None, user_id=None, company_id=None, network_id=None,
                      form_route_id=None, form_page_route_id=None, test_cases=None, 
                      product_id=1, config=None, base_url=None, project_id=None):

        import uuid
        if form_route_id is None and form_page_route_id is not None:
            form_route_id = form_page_route_id

        # Get form page URL from database (do this once at session creation)
        form_page_url = base_url or ""
        user_provided_inputs = None
        form_name = None
        company_name = None
        if form_route_id and self.db:
            try:
                from models.database import FormPageRoute
                route = self.db.query(FormPageRoute).filter(FormPageRoute.id == form_route_id).first()
                if route:
                    if not form_page_url:
                        form_page_url = route.url or ""
                    project_id = route.project_id
                    form_name = route.form_name
                    if route.user_provided_inputs and route.user_provided_inputs.get("status") == "ready":
                        user_provided_inputs = route.user_provided_inputs
            except Exception as e:
                logger.warning(f"[Orchestrator] Failed to get form page data: {e}")

        # Get company_name (do this once at session creation)
        if company_id and self.db:
            try:
                from models.database import Company
                company = self.db.query(Company).filter(Company.id == company_id).first()
                if company:
                    company_name = company.name
            except Exception as e:
                logger.warning(f"[Orchestrator] Failed to get company name: {e}")

        if session_id is None:
            session_id = str(uuid.uuid4())[:8]
        if test_cases is None:
            test_cases = []
        
        final_config = self._load_full_config(company_id, project_id)
        if config:
            final_config.update(config)
        
        test_context = {"filled_fields": {}, "clicked_elements": [], "selected_options": {},
                       "credentials": {}, "reported_ui_issues": []}
        
        session_state = {
            "session_id": session_id, "user_id": user_id or 0, "company_id": company_id or 0, "company_name": company_name or "",
            "product_id": product_id or 1, "network_id": network_id or 0,
            "form_route_id": form_route_id or 0, "form_page_url": form_page_url, "form_name": form_name or "Unknown Form", "project_id": project_id or 0,
            "state": MapperState.INITIALIZING.value, "previous_state": "",
            "current_step_index": 0, "all_steps": "[]", "executed_steps": "[]",
            "current_dom_hash": "", "current_path": 1,
            "junctions_state": "{}",
            "junction_instructions": "{}", "total_paths": 1,
            "test_cases": json.dumps(test_cases),
            "test_context": json.dumps(test_context), "config": json.dumps(final_config),
            "consecutive_failures": 0, "recovery_failure_history": "[]",
            "critical_fields_checklist": "{}", "field_requirements_for_recovery": "",
            "user_provided_inputs": json.dumps(user_provided_inputs) if user_provided_inputs else "{}",
            "pending_alert_info": "{}", "pending_validation_errors": "{}",
            "pending_screenshot_base64": "", "pending_new_steps": "[]",
            "final_steps": "[]", "last_error": "",
            "upload_urls": json.dumps(
                self._generate_upload_urls(company_id or 0, project_id or 0, session_id, "mapping", form_route_id or 0)),
            "created_at": datetime.utcnow().isoformat(), "updated_at": datetime.utcnow().isoformat(),
            "completed_at": ""
        }
        
        key = self._get_session_key(session_id)
        self.redis.hset(key, mapping=session_state)
        self.redis.expire(key, 86400)
        # Structured logging
        log = self._get_logger(session_id)
        log.session_created(network_id=network_id, form_route_id=form_route_id)
        logger.info(f"[Orchestrator] Created session {session_id} with network_id={network_id}, form_route_id={form_route_id}")

        if user_id:
            self.redis.delete(f"agent:{user_id}")
            logger.info(f"[Orchestrator] Flushed agent queue for user {user_id}")

            # Cancel previous sessions in DB (async)
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
        json_fields = ["all_steps", "executed_steps", "test_cases",
                      "final_steps", "config", "test_context",
                      "recovery_failure_history", "pending_new_steps"]
        dict_fields = ["critical_fields_checklist", "pending_alert_info", "pending_validation_errors", "user_provided_inputs"]
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
            # Structured logging
            log = self._get_logger(session_id)
            log.state_transition(session.get("state", ""), new_state.value)
    
    def _push_agent_task(self, session_id: str, task_type: str, payload: Dict) -> Dict:
        session = self.get_session(session_id)
        # Check if session is cancelled/completed/failed before pushing
        state = session.get("state") if session else None
        if state == "cancelled" and task_type != "form_mapper_close":
            logger.info(f"[Orchestrator] Session {session_id} is {state}, skipping {task_type} push")
            return {"skipped": True, "reason": f"session_{state}"}

        user_id = session.get("user_id", 1) if session else 1
        task = {"task_id": f"mapper_{session_id}_{task_type}_{int(time.time()*1000)}",
                "task_type": task_type, "session_id": session_id, "payload": payload}
        self.redis.lpush(f"agent:{user_id}", json.dumps(task))
        logger.info(f"[Orchestrator] Pushed {task_type} to agent:{user_id}")
        # Structured logging
        log = self._get_logger(session_id)
        log.agent_task_pushed(task_type)
        return task
    
    def _fail_session(self, session_id: str, error: str) -> Dict:
        self.transition_to(session_id, MapperState.FAILED, last_error=error,
                          completed_at=datetime.utcnow().isoformat())
        self._sync_session_status_to_db(session_id, "failed", error)
        session = self.get_session(session_id)
        if session:
            self._push_agent_task(session_id, "form_mapper_close", {
                "complete_logging": True,
                "log_message": f"❌ Mapping failed: {error}",
                "log_level": "error"
            })
        # Structured logging
        log = self._get_logger(session_id)
        log.session_failed(error)
        return {"success": False, "error": error, "state": "failed"}

    # ============================================================
    # PHASE 1 & 2: LOGIN AND NAVIGATION (Forms Runner)
    # ============================================================
    
    def start_login_phase(self, session_id: str) -> Dict:
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}
        network_id = session.get("network_id")
        if not network_id: return self.start_navigation_phase(session_id, is_first_phase=True)
        login_stages = self._load_login_stages(network_id)
        if not login_stages: return self.start_navigation_phase(session_id, is_first_phase=True)
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
            form_route_id=session.get("form_route_id", 0),
            log_message=f"🗺️ Mapping started: {session.get('form_name', 'Unknown Form')}\n🔐 Login started",
            session_context={
                "activity_type": "mapping",
                "session_id": int(session_id),
                "project_id": session.get("project_id"),
                "company_id": session.get("company_id"),
                "user_id": session.get("user_id"),
                "upload_urls": json.loads(session.get("upload_urls", "{}"))
            }
        )
        return {"success": True, "phase": "login", "async": True}
    
    def handle_login_phase_complete(self, session_id: str, result: Dict) -> Dict:
        if not result.get("success"):
            return self._fail_session(session_id, result.get("error", "Login failed"))

        return self.start_navigation_phase(session_id, is_first_phase=False, log_message="✅ Login successful")
    
    def start_navigation_phase(self, session_id: str, is_first_phase: bool = False, log_message: str = None) -> Dict:
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}
        form_route_id = session.get("form_route_id")
        if not form_route_id: return self.start_mapping_phase(session_id, is_first_phase=is_first_phase, log_message=log_message)
        nav_stages = self._load_navigation_stages(form_route_id)
        if not nav_stages: return self.start_mapping_phase(session_id, is_first_phase=is_first_phase, log_message=log_message)
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
            form_route_id=form_route_id,
            log_message=(f"🗺️ Mapping started: {session.get('form_name', 'Unknown Form')}\n" if is_first_phase else "") + (log_message + "\n" if log_message else "") + "🧭 Navigation started",
            session_context={
                "activity_type": "mapping",
                "session_id": int(session_id),
                "project_id": session.get("project_id"),
                "company_id": session.get("company_id"),
                "user_id": session.get("user_id"),
                "upload_urls": json.loads(session.get("upload_urls", "{}"))
            } if is_first_phase else None
        )
        return {"success": True, "phase": "navigate", "async": True}
    
    def handle_navigation_phase_complete(self, session_id: str, result: Dict) -> Dict:
        if not result.get("success"):
            return self._fail_session(session_id, result.get("error", "Navigation failed"))
        if result.get("final_url"):
            self.update_session(session_id, {"base_url": result.get("final_url")})

        return self.start_mapping_phase(session_id, is_first_phase=False, log_message="✅ Navigated to form page")

    # ============================================================
    # PHASE 3: FORM MAPPING - INITIAL
    # ============================================================
    
    def start_mapping_phase(self, session_id: str, is_first_phase: bool = False, log_message: str = None) -> Dict:
        import traceback
        print(f"[TRACE] start_mapping_phase CALLED for session={session_id}")
        print(f"[TRACE] CALL STACK: {traceback.format_stack()[-3:]}")
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}
        config = session.get("config", {})
        self.transition_to(session_id, MapperState.EXTRACTING_INITIAL_DOM, current_path=1)
        log_msg = "🗺️ Mapping started\n" if is_first_phase else ""
        if log_message:
            log_msg += log_message + "\n"
        log_msg += f"📍 Path {session.get('current_path', 1)} started"
        #task = self._push_agent_task(session_id, "form_mapper_extract_dom", {
        #    "use_full_dom": config.get("use_full_dom", True),
        #    "capture_screenshot": config.get("enable_ui_verification", True),
        #    "log_message": log_msg
        #})

        payload = {
            "use_full_dom": config.get("use_full_dom", True),
            "capture_screenshot": config.get("enable_ui_verification", True),
            "log_message": log_msg
        }
        if is_first_phase:
            payload["session_context"] = {
                "activity_type": "mapping",
                "session_id": int(session_id),
                "project_id": session.get("project_id"),
                "company_id": session.get("company_id"),
                "user_id": session.get("user_id"),
                "upload_urls": json.loads(session.get("upload_urls", "{}"))
            }
        task = self._push_agent_task(session_id, "form_mapper_extract_dom", payload)

        return {"success": True, "phase": "mapping", "agent_task": task}

    def handle_initial_dom_result(self, session_id: str, result: Dict) -> Dict:
        logger.info(f"[Orchestrator] handle_initial_dom_result ENTER: session={session_id}, success={result.get('success')}, has_dom={bool(result.get('dom_html'))}, dom_len={len(result.get('dom_html', ''))}")
        # Structured logging
        log = self._get_logger(session_id)
        log.info("Initial DOM received", category="milestone",
                 dom_length=len(result.get('dom_html', '')),
                 success=result.get('success'))
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
            new_issues = []
            test_context = session.get("test_context", {})
            reported = test_context.get("reported_ui_issues", [])
            for issue in ui_issue.split(','):
                issue = issue.strip()
                if issue and issue not in reported:
                    reported.append(issue)
                    new_issues.append(issue)
            test_context["reported_ui_issues"] = reported
            self.update_session(session_id, {"test_context": test_context})
            if new_issues:
                logger.warning(f"[Orchestrator] UI issues: {', '.join(new_issues)}")
                self._push_agent_task(session_id, "form_mapper_log_bug", {
                    "bug_description": ', '.join(new_issues),
                    "log_level": "warning",
                    "screenshot": True,
                    "bug_type": "ui_issue"
                })
            #self._push_agent_task(session_id, "form_mapper_log_bug", {
            #    "log_message": f"🐛 UI Issue: {ui_issue}",
            #    "log_level": "warning",
            #    "screenshot": True,
            #    "bug_type": "ui_issue"
            #})
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
                    "test_cases": session.get("test_cases", []),
                    "current_path": session.get("current_path", 1),
                    "enable_junction_discovery": config.get("enable_junction_discovery", True),
                    "critical_fields_checklist": session.get("critical_fields_checklist", {}),
                    "field_requirements": session.get("field_requirements_for_recovery", ""),
                    "junction_instructions": session.get("junction_instructions", "{}"),
                    "user_provided_inputs": session.get("user_provided_inputs", {})}}
    
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
        # Structured logging
        log = self._get_logger(session_id)
        log.info(f"AI generated {len(steps)} initial steps", category="ai_response",
                 steps_count=len(steps))

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
            # Check if we just finished recovery fix steps
            if session.get("in_recovery_mode"):
                logger.info(f"[Orchestrator] Recovery fix steps complete, getting DOM for regenerate_steps")
                self.update_session(session_id, {"in_recovery_mode": False})
                # Get fresh DOM and screenshot, then regenerate
                self.transition_to(session_id, MapperState.DOM_CHANGE_GETTING_SCREENSHOT)
                task = self._push_agent_task(session_id, "form_mapper_get_screenshot",
                                             {"encode_base64": True, "save_to_folder": False,
                                              "scenario_description": "after_recovery"})
                return {"success": True, "agent_task": task}
            return self._handle_path_complete(session_id)

        step = all_steps[current_index]

        self.transition_to(session_id, MapperState.EXECUTING_STEP)
        task = self._push_agent_task(session_id, "form_mapper_exec_step", {
            "step": step, "step_index": current_index, "total_steps": len(all_steps),
            "current_dom_hash": session.get("current_dom_hash", "")})
        logger.info(f"[Orchestrator] Step {current_index + 1}/{len(all_steps)}: {step.get('action')}")
        # Structured logging
        log = self._get_logger(session_id)
        log.update_context(current_step=current_index + 1, total_steps=len(all_steps))
        log.step_executing(current_index + 1, step.get('action'), step.get('selector'))
        return {"success": True, "agent_task": task}
    
    def handle_step_result(self, session_id: str, result: Dict) -> Dict:
        logger.info(f"[handle_step_result] ENTER session={session_id}, result_success={result.get('success')}")
        # Structured logging
        log = self._get_logger(session_id)
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}
        step = result.get("executed_step") or {}
        selector = step.get('selector') or ''
        description = step.get('description') or ''
        effective_selector = result.get('effective_selector') if result.get('used_full_xpath') else step.get('selector')
        junction_info_str = f", junction_info={step.get('junction_info')}" if step.get('is_junction') or step.get(
            'junction_info') else ""
        # Add extra info for verify actions
        verify_info_str = ""
        error_info_str = ""
        if step.get('action') == 'verify':
            expected = result.get('expected', step.get('value', ''))
            actual = result.get('actual', '')
            verify_info_str = f", expected='{expected}', actual='{actual}'"
            if not result.get('success') and result.get('error'):
                verify_info_str += f", error='{result.get('error')}'"
        if not result.get('success') and step.get('action') != 'verify':
            error_info_str = f", error='{result.get('error', '')}', exception='{result.get('exception', '')}'"
        print(
            f"!!!!!!!!!!!!!!!!!!!! Got a {'PASSED' if result.get('success') else 'FAILED'} result from Agent step: action={step.get('action')}, selector={effective_selector}, description={step.get('description', '')[:40]}, success={result.get('success')}, fields_changed={result.get('fields_changed')}{junction_info_str}{verify_info_str}{error_info_str}")

        # ADD structured log (queryable in CloudWatch)
        # ADD structured log (queryable in CloudWatch)
        log.debug(
            f"!!!!!!!!!!!!!!!!!!!! Got a {'PASSED' if result.get('success') else 'FAILED'} result from Agent step: action={step.get('action')}, selector={effective_selector}, description={step.get('description', '')[:40]}, success={result.get('success')}, fields_changed={result.get('fields_changed')}{junction_info_str}{verify_info_str}{error_info_str}",
            category="debug_trace")


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

        # Verification failure handling
        if step.get("action") == "verify":
            # If locator issue - try AI recovery to fix locator
            if result.get("locator_error"):
                logger.info(f"[Orchestrator] Verify step failed with locator error - attempting AI recovery")
                # Continue to normal recovery flow below
            else:
                # Content mismatch - just skip
                logger.info(f"[Orchestrator] Verification content mismatch, skipping")
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

        # Structured logging
        log = self._get_logger(session_id)
        log.step_failed(session.get("current_step_index", 0) + 1,
                        f"Consecutive failures: {consecutive_failures}/{max_retries}")

        logger.info(
            f"[handle_step_result] consecutive_failures={consecutive_failures}, max_retries={max_retries}, will_fail={consecutive_failures >= max_retries}")

        if consecutive_failures >= max_retries:
            # For verify steps - skip to next step instead of failing session (don't add to executed_steps)
            if step.get("action") == "verify":
                logger.info(f"[Orchestrator] Verify step max retries ({max_retries}) reached - skipping to next step")
                print(f"[Orchestrator] ⚠️ Verify step max retries reached - skipping to next step")
                self.update_session(session_id, {"current_step_index": current_index + 1,
                                                 "consecutive_failures": 0})
                return self._execute_next_step(session_id)
            return self._fail_session(session_id, f"Max consecutive failures ({max_retries}) reached")
        
        # Add to recovery history
        recovery_history = session.get("recovery_failure_history", [])
        recovery_history.append({"action": step.get("action"), "selector": step.get("selector"),
                                "description": step.get("description"), "error": result.get("error")})
        self.update_session(session_id, {"recovery_failure_history": recovery_history})

        logger.info(f"[handle_step_result] STARTING RECOVERY - transitioning to STEP_FAILED_EXTRACTING_DOM")
        # Request fresh DOM for AI recovery
        self.transition_to(session_id, MapperState.STEP_FAILED_EXTRACTING_DOM)
        task = self._push_agent_task(session_id, "form_mapper_extract_dom_for_recovery", {
            "capture_screenshot": True, "save_screenshot": True,
            "scenario_description": f"error_{step.get('description', 'unknown')[:30]}"})
        return {"success": True, "state": "step_failed_extracting_dom", "agent_task": task}
    
    def handle_step_failure_dom_result(self, session_id: str, result: Dict) -> Dict:
        logger.info(
            f"[handle_step_failure_dom_result] ENTER session={session_id}, success={result.get('success')}, has_dom={bool(result.get('dom_html'))}, has_screenshot_path={bool(result.get('screenshot_path'))}")
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}
        if not result.get("success") or not result.get("dom_html"):
            return self._fail_session(session_id, "Failed to extract DOM for recovery")
        dom_html = result.get("dom_html", "")
        screenshot_base64 = result.get("screenshot_base64", "")
        if not screenshot_base64:
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
                    "screenshot_base64": screenshot_base64, "test_cases": session.get("test_cases", []),
                    "test_context": session.get("test_context", {}),
                    "attempt_number": session.get("consecutive_failures", 1),
                    "recovery_failure_history": session.get("recovery_failure_history", [])}}

    def handle_step_failure_recovery_result(self, session_id: str, result: Dict) -> Dict:
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}

        # Check if validation errors were detected - route to validation error recovery
        if result.get("validation_errors_detected"):
            logger.info(f"[Orchestrator] Validation errors detected in step recovery - getting fresh DOM for recovery")
            print(
                f"[Orchestrator] ⚠️ Validation errors detected in step recovery - routing to validation error handler")
            self.update_session(session_id, {"pending_validation_error_recovery": True, "consecutive_failures": 0})
            self.transition_to(session_id, MapperState.VALIDATION_ERROR_GETTING_DOM)
            task = self._push_agent_task(session_id, "form_mapper_extract_dom", {
                "capture_screenshot": True
            })
            return {"success": True, "state": "validation_error_getting_dom", "agent_task": task}

        recovery_steps = result.get("recovery_steps", []) or result.get("steps", [])
        if not recovery_steps:

            # Check if this was a verify step - just skip and continue
            all_steps = session.get("all_steps", [])
            current_index = session.get("current_step_index", 0)
            failed_step = all_steps[current_index] if current_index < len(all_steps) else {}

            if failed_step.get("action") == "verify":
                logger.info(f"[Orchestrator] AI returned 0 recovery steps for verify - skipping and continuing")
                # Structured logging
                log = self._get_logger(session_id)
                log.info("Recovery: skipping verify step (0 recovery steps)", category="recovery")
                print(f"[Orchestrator] ℹ️ AI returned 0 recovery steps for verify - skipping and continuing")
                executed_steps = session.get("executed_steps", [])
                executed_steps.append(failed_step)
                self.update_session(session_id, {
                    "executed_steps": executed_steps,
                    "current_step_index": current_index + 1,
                    "consecutive_failures": 0
                })
                return self._execute_next_step(session_id)


            # 0 recovery steps means "skip this step and regenerate remaining steps"
            logger.info(f"[Orchestrator] AI returned 0 recovery steps - skipping failed step and triggering regenerate")
            # Structured logging
            log = self._get_logger(session_id)
            log.info("Recovery: skipping failed step, triggering regenerate", category="recovery")
            print(f"[Orchestrator] ℹ️ AI returned 0 recovery steps - skipping failed step and triggering regenerate")
            self.update_session(session_id, {
                "consecutive_failures": 0
            })
            # Get fresh DOM and screenshot, then regenerate remaining steps
            self.transition_to(session_id, MapperState.DOM_CHANGE_GETTING_SCREENSHOT)
            task = self._push_agent_task(session_id, "form_mapper_get_screenshot",
                                         {"encode_base64": True, "save_to_folder": False,
                                          "scenario_description": "after_skip_failed_step"})
            return {"success": True, "agent_task": task}

        logger.info(f"[Orchestrator] AI generated {len(recovery_steps)} recovery FIX steps")
        # Structured logging
        log = self._get_logger(session_id)
        log.recovery_succeeded(method="fix_steps")
        log.info(f"AI generated {len(recovery_steps)} recovery steps", category="ai_response",
                 recovery_steps_count=len(recovery_steps))
        all_steps = session.get("all_steps", [])
        current_index = session.get("current_step_index", 0)
        failed_step = all_steps[current_index] if current_index < len(all_steps) else {}

        # For verify steps: insert fixed step, keep remaining steps
        if failed_step.get("action") == "verify":
            new_all_steps = all_steps[:current_index] + recovery_steps + all_steps[current_index + 1:]
            self.update_session(session_id, {
                "all_steps": new_all_steps,
                "current_step_index": current_index,
            })
            return self._execute_next_step(session_id)


        executed_steps = session.get("executed_steps", [])
        # Mark that we're in recovery mode - after these steps, go to regenerate (not path_complete)
        self.update_session(session_id, {
            "all_steps": executed_steps + recovery_steps,
            "current_step_index": len(executed_steps),
            "in_recovery_mode": True
        })
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

        # Clean step for storage: update selector if fallback used, remove full_xpath
        clean_step = step.copy()
        if result.get("used_full_xpath") and result.get("effective_selector"):
            clean_step["selector"] = result.get("effective_selector")
        clean_step.pop("full_xpath", None)

        # Update value if fill_autocomplete used different character
        if step.get("action") == "fill_autocomplete" and result.get("actual_value"):
            clean_step["value"] = result.get("actual_value")

        executed_steps.append(clean_step)
        self.update_session(session_id, {"executed_steps": executed_steps, "consecutive_failures": 0})
        
        # Check for alert
        if result.get("alert_present") or result.get("alert_detected"):
            return self._handle_alert(session_id, result)
        
        # Check for DOM change
        old_hash = session.get("current_dom_hash", "")
        new_hash = result.get("new_dom_hash", "")
        if new_hash and new_hash != old_hash:
            return self._handle_dom_change(session_id, session, step, result, new_hash)

        # DOM didn't change - if step has junction_info, strip it (not a real junction)
        if step.get("is_junction") or step.get("junction_info"):
            if executed_steps:
                executed_steps[-1].pop("is_junction", None)
                executed_steps[-1].pop("junction_info", None)
                self.update_session(session_id, {"executed_steps": executed_steps})

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
        alert_screenshot = result.get("alert_screenshot_base64")  # Screenshot captured while alert was visible
        logger.info(f"[Orchestrator] Alert: {alert_type} - {alert_text[:50]}")
        # Structured logging
        log = self._get_logger(session_id)
        log.warning(f"Alert detected: {alert_type}", category="recovery",
                    alert_type=alert_type, alert_text=alert_text[:100])

        # Add accept_alert to executed
        executed_steps = session.get("executed_steps", [])
        executed_steps.append({"step_number": len(executed_steps) + 1, "action": "accept_alert",
                              "selector": "", "value": "",
                              "description": f"Accept {alert_type}: {alert_text[:50]}..."})
        self.update_session(session_id, {"executed_steps": executed_steps,
                                         "pending_alert_info": {"alert_type": alert_type, "alert_text": alert_text,
                                                               "alert_screenshot_base64": alert_screenshot}})
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
                    "screenshot_base64": pending.get("alert_screenshot_base64") or result.get("screenshot_base64"),
                "test_cases": session.get("test_cases", []),
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
            self._push_agent_task(session_id, "form_mapper_log_bug", {
                "bug_description": result.get('explanation', '')[:100],
                "log_level": "error",
                "screenshot": True,
                "bug_type": "real_bug_alert"
            })
            return {"success": False, "system_issue": True, "explanation": result.get("explanation", "")}
        
        #if not alert_steps:
        #    return self._fail_session(session_id, "AI returned no alert recovery steps")
        
        executed_steps = session.get("executed_steps", [])

        if scenario == "A":
            # Scenario A: simple alert, get fresh DOM and regenerate
            logger.info(f"[Orchestrator] Alert Scenario A: Getting fresh DOM for regenerate")
            # Structured logging
            log = self._get_logger(session_id)
            log.info("Alert recovery: Scenario A - getting fresh DOM", category="recovery")
            config = session.get("config", {})
            self.transition_to(session_id, MapperState.DOM_CHANGE_GETTING_SCREENSHOT)
            task = self._push_agent_task(session_id, "form_mapper_get_screenshot", {
                "scenario": "after_alert_scenario_a"
            })
            return {"success": True, "state": "dom_change_getting_screenshot", "agent_task": task}
        else:
            # Scenario B: navigate back, start fresh
            logger.info(f"[Orchestrator] Alert Scenario B: Starting fresh with {len(alert_steps)} steps")
            # Structured logging
            log = self._get_logger(session_id)
            log.info(f"Alert recovery: Scenario B - {len(alert_steps)} new steps", category="recovery",
                     alert_steps_count=len(alert_steps))
            updates = {"pending_new_steps": alert_steps}
            if result.get("problematic_fields"):
                updates["critical_fields_checklist"] = {f: "MUST FILL" for f in result.get("problematic_fields")}
            if result.get("field_requirements"):
                updates["field_requirements_for_recovery"] = result.get("field_requirements")
            self.update_session(session_id, updates)

            # Get form page URL from session (stored at session creation)
            form_page_url = session.get("form_page_url", "")

            if form_page_url:
                self.transition_to(session_id, MapperState.ALERT_NAVIGATING_BACK)
                task = self._push_agent_task(session_id, "form_mapper_navigate_to_url", {"url": form_page_url})
                return {"success": True, "state": "alert_navigating_back", "agent_task": task}
            else:
                # Fallback: use alert_steps directly (not ideal)
                logger.warning(f"[Orchestrator] No form page URL found, using alert steps directly")
                # Structured logging
                log = self._get_logger(session_id)
                log.warning("Alert recovery: no form URL, using steps directly", category="recovery")
                self.update_session(session_id, {"all_steps": alert_steps, "executed_steps": [],
                                                 "current_step_index": 0})
                return self._execute_next_step(session_id)


    def handle_validation_error_recovery_result(self, session_id: str, result: Dict) -> Dict:
        """Handle result from validation error recovery - same logic as alert recovery"""
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}
        if not result.get("success", True):
            return self._fail_session(session_id, "AI failed to analyze validation errors")

        scenario = result.get("scenario", "B")
        issue_type = result.get("issue_type", "")

        # Real system issue
        if scenario == "B" and issue_type == "real_issue":
            self.transition_to(session_id, MapperState.SYSTEM_ISSUE,
                               last_error=f"Real issue: {result.get('explanation', '')}",
                               completed_at=datetime.utcnow().isoformat())
            self._push_agent_task(session_id, "form_mapper_log_bug", {
                "bug_description": result.get('explanation', '')[:100],
                "log_level": "error",
                "screenshot": True,
                "bug_type": "real_bug_validation"
            })
            return {"success": False, "system_issue": True, "explanation": result.get("explanation", "")}

        # AI issue - navigate back and retry with critical fields
        logger.info(f"[Orchestrator] Validation Error - AI issue, navigating back to retry")
        # Structured logging
        log = self._get_logger(session_id)
        log.info("Validation error recovery: navigating back to retry", category="recovery",
                 problematic_fields=result.get("problematic_fields"))
        updates = {}
        if result.get("problematic_fields"):
            updates["critical_fields_checklist"] = {f: "MUST FILL" for f in result.get("problematic_fields")}
        if result.get("field_requirements"):
            updates["field_requirements_for_recovery"] = result.get("field_requirements")
        if updates:
            self.update_session(session_id, updates)

        form_page_url = session.get("form_page_url", "")
        if form_page_url:
            self.transition_to(session_id, MapperState.ALERT_NAVIGATING_BACK)
            task = self._push_agent_task(session_id, "form_mapper_navigate_to_url", {"url": form_page_url})
            return {"success": True, "state": "alert_navigating_back", "agent_task": task}
        else:
            return self._fail_session(session_id, "No form page URL for retry")



    def handle_navigate_back_result(self, session_id: str, result: Dict) -> Dict:
        #session = self.get_session(session_id)
        #if not session: return {"success": False, "error": "Session not found"}
        #if not result.get("success"):
        #    return self._fail_session(session_id, f"Failed to navigate back: {result.get('error', '')}")
        #new_steps = session.get("pending_new_steps", [])
        #self.update_session(session_id, {"all_steps": new_steps, "executed_steps": [],
        #                                 "current_step_index": 0, "pending_new_steps": []})
        #logger.info(f"[Orchestrator] Navigated back, starting fresh with {len(new_steps)} steps")
        #return self._execute_next_step(session_id)
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}
        if not result.get("success"):
            return self._fail_session(session_id, f"Failed to navigate back: {result.get('error', '')}")

        # Clear old steps and pending_new_steps - we'll generate fresh with critical_fields_checklist
        self.update_session(session_id, {"all_steps": [], "executed_steps": [],
                                         "current_step_index": 0, "pending_new_steps": []})
        logger.info(f"[Orchestrator] Navigated back, extracting DOM for fresh step generation")
        # Structured logging
        log = self._get_logger(session_id)
        log.info("Navigated back, extracting fresh DOM", category="milestone")

        # Extract fresh DOM and screenshot (like initial flow)
        config = session.get("config", {})
        self.transition_to(session_id, MapperState.EXTRACTING_INITIAL_DOM)
        task = self._push_agent_task(session_id, "form_mapper_extract_dom", {
            "use_full_dom": config.get("use_full_dom", True),
            "capture_screenshot": config.get("enable_ui_verification", True)
        })
        return {"success": True, "state": "extracting_initial_dom", "agent_task": task}


    def handle_next_path_navigate_result(self, session_id: str, result: Dict) -> Dict:
        """Handle navigation result for next junction path - then extract DOM"""
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}
        if not result.get("success"):
            return self._fail_session(session_id, f"Failed to navigate for next path: {result.get('error', '')}")

        logger.info(f"[Orchestrator] Navigated to form URL for next path, now extracting DOM")
        print(f"!!!!!!!!!!!!!!!!!!!!!!!!! 🔀 Navigated to form URL, extracting DOM for next path")
        # Structured logging
        log = self._get_logger(session_id)
        log.debug("!!! Navigated to form URL, extracting DOM for next path", category="milestone")

        # Step 2: Extract DOM (reuses existing flow)
        config = session.get("config", {})
        self.transition_to(session_id, MapperState.EXTRACTING_INITIAL_DOM)
        task = self._push_agent_task(session_id, "form_mapper_extract_dom", {
            "use_full_dom": config.get("use_full_dom", True),
            "capture_screenshot": config.get("enable_ui_verification", True)
        })
        return {"success": True, "state": "extracting_initial_dom", "agent_task": task}

    # ============================================================
    # DOM CHANGE HANDLING
    # ============================================================
    
    def _handle_dom_change(self, session_id: str, session: Dict, step: Dict, result: Dict, new_hash: str) -> Dict:
        logger.info(f"[Orchestrator] DOM changed: {new_hash[:16]}...")
        # Structured logging
        log = self._get_logger(session_id)
        log.debug(f"!!! DOM changed: {new_hash[:16]}", category="milestone", dom_hash=new_hash[:16])
        self.update_session(session_id, {"current_dom_hash": new_hash})
        
        # Check for validation errors
        validation_errors = result.get("validation_errors", {})
        if validation_errors.get("has_errors"):
            return self._handle_validation_errors(session_id, validation_errors)
        
        config = session.get("config", {})

        # Check force_regenerate flag OR fields_changed
        force_regenerate = step.get("force_regenerate", False)
        force_regenerate_verify = step.get("force_regenerate_verify", False)

        if force_regenerate_verify:
            print(f"!!!!!!!!!! ✅ Step has force_regenerate_verify=True - proceeding with AI VERIFY regeneration")
            logger.info(f"[Orchestrator] Step has force_regenerate_verify=True, triggering verify regeneration")
            # Structured logging
            log = self._get_logger(session_id)
            log.debug("!!! force_regenerate_verify=True - triggering verify regeneration", category="milestone")
        elif force_regenerate:
            print(f"!!!!!!!!!! 🔄 Step has force_regenerate=True - proceeding with AI regeneration")
            logger.info(f"[Orchestrator] Step has force_regenerate=True, triggering regeneration")
            # Structured logging
            log = self._get_logger(session_id)
            log.debug("!!! force_regenerate=True - triggering regeneration", category="milestone")
        elif config.get("use_detect_fields_change", True):
            should_regen, trigger_reason = self._should_regenerate(step, result, config)
            if not should_regen:
                print(
                    f"!!!!!!!!! ℹ️  DOM changed. Fields detection says no regeneration needed - skipping AI regeneration")
                print(f"!!!!!!!!! 📊 Trigger info: {trigger_reason}")
                logger.info(f"[Orchestrator] Fields detection: skipping regeneration. Reason: {trigger_reason}")
                # Structured logging
                log = self._get_logger(session_id)
                log.debug(f"!!! DOM changed but skipping regeneration: {trigger_reason}", category="milestone",
                          trigger_reason=trigger_reason)
                # Strip is_junction from executed_steps when fields didn't change (for AI path evaluation)
                if step.get("is_junction") or step.get("junction_info"):
                    executed_steps = session.get("executed_steps", [])
                    if executed_steps:
                        executed_steps[-1].pop("is_junction", None)
                        executed_steps[-1].pop("junction_info", None)
                        self.update_session(session_id, {"executed_steps": executed_steps})
                # OLD METHOD commented out - AI path evaluation uses executed_steps directly
                # if (step.get("is_junction") or step.get("junction_info")) and config.get("enable_junction_discovery", True):
                #     from services.path_evaluation_service import JunctionsState, create_path_evaluation_service
                #     path_eval = create_path_evaluation_service(config)
                #     junctions_state_json = session.get("junctions_state", "{}")
                #     junctions_state = JunctionsState.from_dict(
                #         json.loads(junctions_state_json) if junctions_state_json else {})
                #     fields_changed = result.get("fields_changed", False)
                #     junctions_state = path_eval.update_junction_from_step(junctions_state, step, fields_changed)
                #     if not fields_changed:
                #         step.pop("is_junction", None)
                #         step.pop("junction_info", None)
                #     self.update_session(session_id, {"junctions_state": json.dumps(junctions_state.to_dict())})
                #     print(
                #         f"!!!!!!!!!!!!!!!!!!!!!!!!! 🔀 Junction updated (skip regen): {step.get('description')} = {step.get('value')}, fields_changed={fields_changed}")
                #     logger.info(
                #         f"[Orchestrator] Junction updated (skip regen): {step.get('description')}, status={junctions_state.to_dict()}")
                current_index = session.get("current_step_index", 0)
                self.update_session(session_id, {"current_step_index": current_index + 1})
                return self._execute_next_step(session_id)
            else:
                print(
                    f"!!!!!!!!!!! ✅ Dom changed. Fields detection says regeneration needed - proceeding with AI regeneration")
                print(f"!!!!!!!!!!! 📊 Trigger info: {trigger_reason}")
                # Structured logging
                log = self._get_logger(session_id)
                log.debug(f"!!! DOM changed, regeneration needed: {trigger_reason}", category="milestone",
                          trigger_reason=trigger_reason)

        # OLD METHOD commented out - AI path evaluation uses executed_steps directly
        # if (step.get("is_junction") or step.get("junction_info")) and config.get("enable_junction_discovery", True):
        #     from services.path_evaluation_service import JunctionsState, create_path_evaluation_service
        #     path_eval = create_path_evaluation_service(config)
        #     junctions_state_json = session.get("junctions_state", "{}")
        #     junctions_state = JunctionsState.from_dict(
        #         json.loads(junctions_state_json) if junctions_state_json else {})
        #
        #     # Update junction based on fields_changed
        #     fields_changed = result.get("fields_changed", False)
        #     junctions_state = path_eval.update_junction_from_step(junctions_state, step, fields_changed)
        #     if not fields_changed:
        #         step.pop("is_junction", None)
        #         step.pop("junction_info", None)
        #
        #     # Save updated state
        #     self.update_session(session_id, {"junctions_state": json.dumps(junctions_state.to_dict())})
        #     print(
        #         f"!!!!!!!!!!!!!!!!!!!!!!!!! 🔀 Junction updated: {step.get('description')} = {step.get('value')}, fields_changed={fields_changed}")
        #     logger.info(
        #         f"[Orchestrator] Junction updated: {step.get('description')}, status={junctions_state.to_dict()}")
        
        # Get screenshot for UI verification
        if config.get("enable_ui_verification", True):
            self.transition_to(session_id, MapperState.DOM_CHANGE_GETTING_SCREENSHOT)
            task = self._push_agent_task(session_id, "form_mapper_get_screenshot",
                                        {"encode_base64": True, "save_to_folder": False})
            return {"success": True, "state": "dom_change_getting_screenshot", "agent_task": task}
        return self._trigger_regenerate_steps(session_id, None)

    def _should_regenerate(self, step: Dict, result: Dict, config: Dict) -> tuple:
        """
        Decide if regeneration is needed based on agent detection and AI hint.

        Logic:
        1. If fields_changed_dom (method 1) → always regenerate
        2. If fields_changed_js (method 2) → regenerate UNLESS AI said dont_regenerate
        3. Otherwise → don't regenerate

        Returns:
            tuple: (should_regenerate: bool, reason: str)
        """
        fields_changed_dom = result.get("fields_changed_dom", False)
        fields_changed_js = result.get("fields_changed_js", False)
        dont_regenerate = step.get("dont_regenerate", False)
        use_ai_hint = config.get("use_ai_dont_regenerate", True)

        # Backward compatibility: if new fields not present, use old field
        if "fields_changed_dom" not in result and "fields_changed_js" not in result:
            fields_changed = result.get("fields_changed", True)
            return (fields_changed, f"legacy mode: fields_changed={fields_changed}")

        # Build status string
        status = f"dom={fields_changed_dom}, js={fields_changed_js}, ai_dont_regen={dont_regenerate}, use_ai_hint={use_ai_hint}"

        # Method 1 (DOM structure change) always triggers regeneration
        if fields_changed_dom:
            reason = f"DOM structure changed → regenerate ({status})"
            logger.info(f"[Orchestrator] _should_regenerate: {reason}")
            return (True, reason)

        # Method 2 (JS visibility change) - check AI hint
        if fields_changed_js:
            if use_ai_hint and dont_regenerate:
                reason = f"JS visibility changed but AI said dont_regenerate → skip ({status})"
                logger.info(f"[Orchestrator] _should_regenerate: {reason}")
                return (False, reason)
            reason = f"JS visibility changed → regenerate ({status})"
            logger.info(f"[Orchestrator] _should_regenerate: {reason}")
            return (True, reason)

        reason = f"No field changes detected → skip ({status})"
        logger.info(f"[Orchestrator] _should_regenerate: {reason}")
        return (False, reason)


    def handle_dom_change_screenshot_result(self, session_id: str, result: Dict) -> Dict:
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}
        screenshot_base64 = result.get("screenshot_base64", "") if result.get("success") else ""
        if not screenshot_base64:
            logger.warning(f"[Orchestrator] Screenshot failed, skipping UI verification")
            # Structured logging
            log = self._get_logger(session_id)
            log.warning("Screenshot failed, skipping UI verification", category="milestone")
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
            new_issues = []
            test_context = session.get("test_context", {})
            reported = test_context.get("reported_ui_issues", [])
            for issue in ui_issue.split(','):
                issue = issue.strip()
                if issue and issue not in reported:
                    reported.append(issue)
                    new_issues.append(issue)
            test_context["reported_ui_issues"] = reported
            self.update_session(session_id, {"test_context": test_context})
            if new_issues:
                logger.warning(f"[Orchestrator] UI issues: {', '.join(new_issues)}")
                self._push_agent_task(session_id, "form_mapper_log_bug", {
                    "bug_description": ', '.join(new_issues),
                    "log_level": "warning",
                    "screenshot": True,
                    "bug_type": "ui_issue"
                })


        #return self._trigger_regenerate_steps(session_id, session.get("pending_screenshot_base64", ""))

        # Get fresh DOM before regeneration
        self.transition_to(session_id, MapperState.DOM_CHANGE_GETTING_DOM)
        task = self._push_agent_task(session_id, "form_mapper_extract_dom", {})
        return {"success": True, "state": "dom_change_getting_dom", "agent_task": task}


    def handle_dom_change_dom_result(self, session_id: str, result: Dict) -> Dict:
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}

        # Store fresh DOM in Redis
        dom_html = result.get("dom_html", "")
        if dom_html:
            self.redis.setex(f"mapper_dom:{session_id}", 3600, str(dom_html))
            logger.info(f"[Orchestrator] Fresh DOM stored for regeneration: {len(dom_html)} chars")

        # Check if this is a verify regeneration
        all_steps = session.get("all_steps", [])
        current_index = session.get("current_step_index", 0)
        step = all_steps[current_index] if current_index < len(all_steps) else {}

        if step.get("force_regenerate_verify"):
            return self._trigger_regenerate_verify_steps(session_id, session.get("pending_screenshot_base64", ""))

        return self._trigger_regenerate_steps(session_id, session.get("pending_screenshot_base64", ""))


    def _trigger_regenerate_steps(self, session_id: str, screenshot_base64: Optional[str]) -> Dict:
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
                    "enable_junction_discovery": config.get("enable_junction_discovery", True),
                    "junction_instructions": session.get("junction_instructions", "{}"),
                    "user_provided_inputs": session.get("user_provided_inputs", {})}}

    def _trigger_regenerate_verify_steps(self, session_id: str, screenshot_base64: Optional[str]) -> Dict:
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}
        self.transition_to(session_id, MapperState.DOM_CHANGE_REGENERATING_VERIFY_STEPS)
        dom_html = self.redis.get(f"mapper_dom:{session_id}")
        if dom_html: dom_html = dom_html.decode() if isinstance(dom_html, bytes) else dom_html
        return {"success": True, "trigger_celery": True, "celery_task": "regenerate_verify_steps",
                "celery_args": {
                    "session_id": session_id, "dom_html": dom_html,
                    "executed_steps": session.get("executed_steps", []),
                    "test_cases": session.get("test_cases", []),
                    "test_context": session.get("test_context", {}),
                    "screenshot_base64": screenshot_base64}}

    def handle_regenerate_steps_result(self, session_id: str, result: Dict) -> Dict:
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}

        # Check if AI detected validation errors - route to validation error recovery
        if result.get("validation_errors_detected"):
            logger.info(f"[Orchestrator] Validation errors detected, getting fresh DOM for recovery")
            # Structured logging
            log = self._get_logger(session_id)
            log.info("Validation errors in regenerate - getting fresh DOM", category="recovery")
            self.update_session(session_id, {"pending_validation_error_recovery": True})
            self.transition_to(session_id, MapperState.VALIDATION_ERROR_GETTING_DOM)
            task = self._push_agent_task(session_id, "form_mapper_extract_dom", {
                "capture_screenshot": True
            })
            return {"success": True, "state": "validation_error_getting_dom", "agent_task": task}


        config = session.get("config", {})
        if config.get("enable_junction_discovery", True) and result.get("no_more_paths", False):
            if session.get("current_path", 1) > 1:
                logger.info(f"[Orchestrator] AI says no more paths")
                # Structured logging
                log = self._get_logger(session_id)
                log.info("AI says no more paths", category="milestone")
                return self._handle_path_complete(session_id)
        new_steps = result.get("new_steps", []) or result.get("steps", [])
        if not new_steps: return self._handle_path_complete(session_id)
        executed_steps = session.get("executed_steps", [])
        current_index = session.get("current_step_index", 0)
        self.update_session(session_id, {"all_steps": executed_steps + new_steps,
                                         "current_step_index": len(executed_steps)})
        logger.info(f"[Orchestrator] Regenerated {len(new_steps)} steps, continuing from step {len(executed_steps) + 1}")
        # Structured logging
        log = self._get_logger(session_id)
        log.info(f"Regenerated {len(new_steps)} steps", category="ai_response",
                 new_steps_count=len(new_steps), continue_from=len(executed_steps) + 1)
        return self._execute_next_step(session_id)

    def handle_regenerate_verify_steps_result(self, session_id: str, result: Dict) -> Dict:
        """Handle result from regenerate_verify_steps Celery task"""
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}

        if not result.get("success"):
            return self._fail_session(session_id, f"Verify regeneration failed: {result.get('error')}")

        # Check if AI detected validation errors - route to validation error recovery
        if result.get("validation_errors_detected"):
            logger.info(f"[Orchestrator] Validation errors detected in verify, getting fresh DOM for recovery")
            # Structured logging
            log = self._get_logger(session_id)
            log.info("Validation errors in verify regenerate - getting fresh DOM", category="recovery")
            self.update_session(session_id, {"pending_validation_error_recovery": True})
            self.transition_to(session_id, MapperState.VALIDATION_ERROR_GETTING_DOM)
            task = self._push_agent_task(session_id, "form_mapper_extract_dom", {
                "capture_screenshot": True
            })
            return {"success": True, "state": "validation_error_getting_dom", "agent_task": task}

        new_steps = result.get("new_steps", [])
        no_more_paths = result.get("no_more_paths", False)

        # Number steps correctly
        start_step = len(session.get("executed_steps", [])) + 1
        for i, step in enumerate(new_steps):
            step["step_number"] = start_step + i

        # Append new steps after executed steps
        executed_steps = session.get("executed_steps", [])

        self.update_session(session_id, {
            "all_steps": executed_steps + new_steps,
            "current_step_index": len(executed_steps),
            "pending_new_steps": []
        })

        logger.info(
            f"[Orchestrator] Verify regenerated {len(new_steps)} steps, continuing from step {len(executed_steps) + 1}")
        # Structured logging
        log = self._get_logger(session_id)
        log.info(f"Verify regenerated {len(new_steps)} steps", category="ai_response",
                 new_steps_count=len(new_steps), continue_from=len(executed_steps) + 1)

        if no_more_paths:
            self.update_session(session_id, {"no_more_paths": True})

        return self._execute_next_step(session_id)

    # ============================================================
    # VALIDATION ERROR HANDLING
    # ============================================================

    def handle_validation_error_dom_result(self, session_id: str, result: Dict) -> Dict:
        """Handle fresh DOM extraction for validation error recovery"""
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}

        if not result.get("success"):
            return self._fail_session(session_id, f"Failed to extract DOM for validation error recovery")

        dom_html = result.get("dom_html", "")
        screenshot_base64 = result.get("screenshot_base64", "")

        # Store fresh DOM in Redis
        if dom_html:
            self.redis.setex(f"mapper_dom:{session_id}", 3600, str(dom_html))

        self.transition_to(session_id, MapperState.VALIDATION_ERROR_RECOVERY)
        return {
            "success": True,
            "trigger_celery": True,
            "celery_task": "handle_validation_error_recovery",
            "celery_args": {
                "session_id": session_id,
                "executed_steps": session.get("executed_steps", []),
                "dom_html": dom_html,
                "screenshot_base64": screenshot_base64,
                "test_cases": session.get("test_cases", []),
                "test_context": session.get("test_context", {})
            }
        }


    def _handle_validation_errors(self, session_id: str, validation_errors: Dict) -> Dict:
        logger.warning(f"[Orchestrator] Validation errors: {len(validation_errors.get('error_fields', []))} fields")
        # Structured logging
        log = self._get_logger(session_id)
        log.warning(f"Validation errors detected: {len(validation_errors.get('error_fields', []))} fields",
                    category="recovery",
                    error_fields_count=len(validation_errors.get('error_fields', [])))
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
        screenshot_base64 = result.get("screenshot_base64", "")
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
                    "screenshot_base64": screenshot_base64, "test_cases": session.get("test_cases", []),
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
        # Structured logging
        log = self._get_logger(session_id)
        log.info(f"Path complete: {len(executed_steps)} steps", category="milestone", steps_count=len(executed_steps))
        self.update_session(session_id, {"critical_fields_checklist": {},
                                         "field_requirements_for_recovery": ""})
        self.transition_to(session_id, MapperState.PATH_COMPLETE)
        return self._complete_all_paths(session_id)

    def _complete_all_paths(self, session_id: str) -> Dict:
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}
        config = session.get("config", {})
        executed_steps = session.get("executed_steps", [])

        # Evaluate if more paths are needed using new junction system
        if config.get("enable_junction_discovery", True):
            #from services.path_evaluation_service import JunctionsState, PathResult, create_path_evaluation_service
            from models.database import SessionLocal

            #path_eval = create_path_evaluation_service(config)
            #junctions_state_json = session.get("junctions_state", "{}")
            #junctions_state = JunctionsState.from_dict(json.loads(junctions_state_json) if junctions_state_json else {})

            # SCALABLE: Load completed paths from DB (single source of truth)
            db_paths = []  # Initialize
            form_page_route_id = session.get("form_route_id")
            if form_page_route_id:
                db = SessionLocal()
                try:
                    #db_paths = JunctionsState.load_paths_from_db(db, form_page_route_id)
                    db_paths = self._load_junction_paths_from_db(db, form_page_route_id, config)
                    # Replace in-memory paths with DB paths (authoritative source)
                    #junctions_state.paths_completed = db_paths
                    logger.info(f"[Orchestrator] Loaded {len(db_paths)} completed paths from DB")
                finally:
                    db.close()

            # Build junction choices AND junction_steps from current executed steps
            #junction_choices = {}
            #junction_steps = []
            #for step in executed_steps:
            #    if step.get("is_junction"):
            #        junction_info = step.get("junction_info", {})
            #        junction_name = junction_info.get("junction_name", "unknown")
            #        junction_id = f"junction_{junction_name}"
            #        chosen_option = junction_info.get("chosen_option") or step.get("value")

            #        junction_choices[junction_id] = chosen_option
            #        junction_steps.append({
            #            "step_index": step.get("step_number", 0),
            #            "junction_id": junction_id,
            #            "junction_name": junction_name,
            #            "option": chosen_option,
            #            "selector": step.get("selector", ""),
            #            "all_options": junction_info.get("all_options", [])
            #        })

            # Record current path (will be saved to DB shortly)
            #junctions_state = path_eval.complete_path(
            #    junctions_state,
            #    junction_choices,
            #    junction_steps=junction_steps,
            #    result_id=None
            #)

            # Update current_path counter based on DB paths + current
            #junctions_state.current_path = len(junctions_state.paths_completed) + 1

            # Evaluate if more paths needed
            #print(f"!!!!!!!!!!!!!!!!!!!!!!!!! 🔀 BEFORE path evaluation - junctions_state: {junctions_state.to_dict()}")
            print(f"!!!!!!!!!!!!!!!!!!!!!!!!! 🔀 BEFORE path evaluation")
            # Structured logging
            log = self._get_logger(session_id)
            log.debug("!!! BEFORE path evaluation", category="milestone")

            # Check if AI path evaluation is enabled
            if config.get("use_ai_path_evaluation", True):
                # Use AI to determine next path - trigger Celery task
                logger.info(f"[Orchestrator] Using AI path evaluation")
                # Structured logging
                log.info("Using AI path evaluation", category="milestone")

                # Build completed_paths_for_ai from DB paths + current path
                completed_paths_for_ai = db_paths.copy() if db_paths else []

                # Add current path junctions
                current_path_junctions = []
                for step in executed_steps:
                    if step.get("is_junction"):
                        junction_info = step.get("junction_info", {})
                        all_options = junction_info.get("all_options", [])
                        if len(all_options) > config.get("max_options_for_junction", 8):
                            continue
                        current_path_junctions.append({
                            "name": junction_info.get("junction_name", "unknown"),
                            "chosen_option": junction_info.get("chosen_option") or step.get("value"),
                            "all_options": all_options
                        })

                current_path_number = len(completed_paths_for_ai) + 1
                completed_paths_for_ai.append({
                    "path_number": current_path_number,
                    "junctions": current_path_junctions
                })

                # Save state before AI evaluation
                self.update_session(session_id, {
                    "pending_completed_paths": json.dumps(completed_paths_for_ai)
                })

                # Check if we've reached max paths - if so, we're done
                max_paths = config.get("max_junction_paths", 7)
                if len(completed_paths_for_ai) >= max_paths:
                    logger.info(f"[Orchestrator] Max paths ({max_paths}) reached - completing")
                    # Structured logging
                    log = self._get_logger(session_id)
                    log.info(f"Max paths ({max_paths}) reached - completing", category="milestone", max_paths=max_paths)
                    self.transition_to(session_id, MapperState.SAVING_RESULT)
                    path_junctions = self._extract_path_junctions_from_steps(executed_steps)
                    return {
                        "success": True,
                        "state": "saving_result",
                        "trigger_celery": True,
                        "celery_task": "save_mapping_result",
                        "celery_args": {
                            "session_id": session_id,
                            "stages": executed_steps,
                            "path_junctions": path_junctions
                        }
                    }

                self.transition_to(session_id, MapperState.PATH_EVALUATION_AI)
                return {
                    "success": True,
                    "trigger_celery": True,
                    "celery_task": "evaluate_paths_with_ai",
                    "celery_args": {
                        "session_id": session_id,
                        "completed_paths": completed_paths_for_ai,
                        "discover_all_combinations": config.get("ai_discover_all_path_combinations", False),
                        "max_paths": config.get("max_junction_paths", 7)
                    }
                }

            #eval_result = path_eval.evaluate_paths(junctions_state)
            #print(f"!!!!!!!!!!!!!!!!!!!!!!!!! 🔀 AFTER path evaluation - result: {eval_result}")
            #logger.info(f"[Orchestrator] Path evaluation: {eval_result}")

            #if not eval_result["all_paths_complete"]:
            #    # More paths needed - save current path first, then start next
            #    self.update_session(session_id, {
            #        "junctions_state": json.dumps(junctions_state.to_dict()),
            #        "junction_instructions": json.dumps(eval_result["junction_instructions"]),
            #        "current_path": eval_result["next_path_number"],
            #        "total_paths": eval_result["total_paths_needed"]
            #    })
            #    logger.info(
            #        f"[Orchestrator] More paths needed. Starting path {eval_result['next_path_number']} of {eval_result['total_paths_needed']}")
            #    # Save current path result first
            #    self.transition_to(session_id, MapperState.SAVING_RESULT)
            #    path_junctions = []  # Junction info now in junctions_state
            #    return {"success": True, "trigger_celery": True, "celery_task": "save_mapping_result",
            #            "celery_args": {"session_id": session_id, "stages": executed_steps,
            #                            "path_junctions": path_junctions, "continue_to_next_path": True}}

            # All paths complete - save final state
            #self.update_session(session_id, {"junctions_state": json.dumps(junctions_state.to_dict())})

            # Save result and complete
            self.transition_to(session_id, MapperState.SAVING_RESULT)
            path_junctions = self._extract_path_junctions_from_steps(executed_steps)
            return {"success": True, "trigger_celery": True, "celery_task": "save_mapping_result",
                    "celery_args": {"session_id": session_id, "stages": executed_steps,
                                    "path_junctions": path_junctions}}

    def _load_junction_paths_from_db(self, db, form_page_route_id: int, config: Dict) -> List[Dict]:
        """Load completed paths from DB and extract only junctions for AI."""
        from models.form_mapper_models import FormMapResult

        results = db.query(FormMapResult).filter(
            FormMapResult.form_page_route_id == form_page_route_id
        ).order_by(FormMapResult.path_number).all()

        paths = []
        for result in results:
            steps = result.steps or []
            path_junctions = []
            for step in steps:
                if step.get("is_junction"):
                    junction_info = step.get("junction_info", {})
                    all_options = junction_info.get("all_options", [])
                    if len(all_options) > config.get("max_options_for_junction", 8):
                        continue
                    path_junctions.append({
                        "name": junction_info.get("junction_name", "unknown"),
                        "chosen_option": junction_info.get("chosen_option") or step.get("value"),
                        "all_options": all_options
                    })
            paths.append({
                "path_number": result.path_number,
                "junctions": path_junctions
            })

        return paths

    def handle_mapping_complete(self, session_id: str, result: Dict) -> Dict:
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}

        # Check if we need to continue to next path
        if result.get("continue_to_next_path"):
            logger.info(f"[Orchestrator] Path saved, starting next path...")
            # Structured logging
            log = self._get_logger(session_id)
            log.info("Path saved, starting next path", category="milestone")
            current_path = session.get("current_path", 1)
            # Reset for next path
            self.update_session(session_id, {
                "executed_steps": "[]",
                "all_steps": "[]",
                "current_step_index": 0,
            })
            # Start new AI analysis with junction instructions
            return self._restart_for_next_path(session_id)

        final_stages = result.get("stages", session.get("executed_steps", []))
        self.transition_to(session_id, MapperState.COMPLETED, final_steps=final_stages,
                           completed_at=datetime.utcnow().isoformat())
        self._sync_session_status_to_db(session_id, "completed")
        logger.info(f"[Orchestrator] Session {session_id} COMPLETED: {len(final_stages)} steps")
        # Structured logging
        log = self._get_logger(session_id)
        log.session_completed(total_steps=len(final_stages))
        self._push_agent_task(session_id, "form_mapper_close", {
            "log_message": f"✅ Mapping complete - {len(final_stages)} steps",
            "complete_logging": True
        })
        return {"success": True, "state": "completed", "total_steps": len(final_stages)}

    def handle_ai_path_evaluation_result(self, session_id: str, result: Dict) -> Dict:
        """Handle result from AI path evaluation Celery task"""
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}

        config = session.get("config", {})
        executed_steps = session.get("executed_steps", [])
        #junctions_state_json = session.get("junctions_state", "{}")
        #junctions_state = JunctionsState.from_dict(json.loads(junctions_state_json) if junctions_state_json else {})

        logger.info(f"[Orchestrator] AI path evaluation result: {result}")
        print(f"!!!!!!!!!!!!!!!!!!!!!!!!! 🔀 AI path evaluation result: {result}")
        # Structured logging
        log = self._get_logger(session_id)
        log.debug(f"!!! AI path evaluation result: all_paths_complete={result.get('all_paths_complete')}",
                  category="ai_response", all_paths_complete=result.get('all_paths_complete'))

        if not result.get("success"):
            # AI evaluation failed - mark as complete (no fallback to algorithmic)
            logger.warning(f"[Orchestrator] AI path evaluation failed - marking paths complete")
            # Structured logging
            log = self._get_logger(session_id)
            log.warning("AI path evaluation failed - marking paths complete", category="ai_response")
            eval_result = {
                "all_paths_complete": True,
                "next_path_number": 1,
                "junction_instructions": {},
                "total_paths_needed": 0,
                "reason": f"AI path evaluation failed: {result.get('error', 'unknown error')}"
            }
        else:
            # Convert AI result to standard format
            ai_result = result
            if ai_result.get("all_paths_complete", True):
                eval_result = {
                    "all_paths_complete": True,
                    "next_path_number": 1,
                    "junction_instructions": {},
                    "total_paths_needed": 0,
                    "reason": ai_result.get("reason", "AI determined all paths complete")
                }
            else:
                # Convert AI next_path to junction_instructions format
                # AI returns: {"applicationtype": "business"}
                # We need: {"#applicationType": "business"} or {"junction_applicationtype": "business"}
                next_path = ai_result.get("next_path", {})
                junction_instructions = {}

                # Map junction names to selectors from junctions_state
                #for junction_name, option in next_path.items():
                #    # Try to find matching junction by name
                #    normalized_name = junction_name.lower().replace("-", "").replace("_", "")
                #   for jid, junction in junctions_state.junctions.items():
                #        junc_normalized = jid.replace("junction_", "").lower().replace("-", "").replace("_", "")
                #        if junc_normalized == normalized_name:
                #            junction_instructions[junction.selector] = option
                #           break
                #   else:
                #        # Fallback: use junction name as key
                #        junction_instructions[f"junction_{junction_name}"] = option

                # Pass junction names directly to prompter AI
                for junction_name, option in next_path.items():
                    junction_instructions[junction_name] = option

                eval_result = {
                    "all_paths_complete": False,
                    "next_path_number": result.get("next_path_number", 1),
                    "junction_instructions": junction_instructions,
                    "total_paths_needed": ai_result.get("total_paths_estimated", 1),
                    "reason": ai_result.get("reason", "AI determined next path")
                }

        # Continue with standard flow
        if not eval_result["all_paths_complete"]:
            # More paths needed - save current path first, then start next
            self.update_session(session_id, {
                "junction_instructions": json.dumps(eval_result["junction_instructions"]),
                "current_path": eval_result["next_path_number"],
                "total_paths": eval_result["total_paths_needed"]
            })
            logger.info(
                f"[Orchestrator] More paths needed. Starting path {eval_result['next_path_number']} of {eval_result['total_paths_needed']}")
            # Save current path result first
            self.transition_to(session_id, MapperState.SAVING_RESULT)
            path_junctions = self._extract_path_junctions_from_steps(executed_steps)
            return {"success": True, "trigger_celery": True, "celery_task": "save_mapping_result",
                    "celery_args": {"session_id": session_id, "stages": executed_steps,
                                    "path_junctions": path_junctions, "continue_to_next_path": True}}

        # All paths complete - save final state
        #self.update_session(session_id, {"junctions_state": json.dumps(junctions_state.to_dict())})

        # Save result and complete
        self.transition_to(session_id, MapperState.SAVING_RESULT)
        path_junctions = self._extract_path_junctions_from_steps(executed_steps)
        return {"success": True, "trigger_celery": True, "celery_task": "save_mapping_result",
                "celery_args": {"session_id": session_id, "stages": executed_steps,
                                "path_junctions": path_junctions}}

    def _restart_for_next_path(self, session_id: str) -> Dict:
        """Restart mapping for the next junction path"""
        session = self.get_session(session_id)
        if not session: return {"success": False, "error": "Session not found"}

        config = session.get("config", {})
        if isinstance(config, str):
            config = json.loads(config) if config else {}

        form_page_url = session.get("form_page_url", "")

        if not form_page_url:
            logger.error(f"[Orchestrator] No form_page_url found for next path")
            # Structured logging
            log = self._get_logger(session_id)
            log.error("No form_page_url found for next path", category="error")
            return self._fail_session(session_id, "No form_page_url for next path")

        logger.info(f"[Orchestrator] Starting next path - navigating to {form_page_url}")
        print(f"!!!!!!!!!!!!!!!!!! 🔀 Starting next path - navigating to {form_page_url}")
        # Structured logging
        log = self._get_logger(session_id)
        log.debug(f"!!! Starting next path - navigating to {form_page_url}", category="milestone",
                  form_page_url=form_page_url)

        # Step 1: Navigate to form URL
        self.transition_to(session_id, MapperState.NEXT_PATH_NAVIGATING)
        #task = self._push_agent_task(session_id, "form_mapper_navigate_to_url", {"url": form_page_url})
        task = self._push_agent_task(session_id, "form_mapper_navigate_to_url", {
            "url": form_page_url,
            "log_message": f"📍 Path {session.get('current_path', 1)} started"
        })
        return {"success": True, "state": "next_path_navigating", "agent_task": task}

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

        # Push close task to agent to close browser immediately
        session = self.get_session(session_id)
        if session:
            user_id = session.get("user_id")
            if user_id:
                self.redis.delete(f"agent:{user_id}")
                logger.info(f"[Orchestrator] Flushed agent queue for user {user_id}")
                self._push_agent_task(session_id, "form_mapper_close", {
                    "log_message": "⏹️ Mapping cancelled",
                    "log_level": "warning",
                    "complete_logging": True
                })
                logger.info(f"[Orchestrator] Pushed close task for session {session_id}")
                # Structured logging
                log = self._get_logger(session_id)
                log.info("Session cancelled", category="session")

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

    def _extract_path_junctions_from_steps(self, executed_steps: List[Dict]) -> List[Dict]:
        """
        Extract junction choices from executed steps to save in path_junctions.
        This makes junction info visible in the frontend without parsing all steps.
        """
        path_junctions = []
        for step in executed_steps:
            if step.get("is_junction"):
                junction_info = step.get("junction_info", {})
                path_junctions.append({
                    "junction_id": f"junction_{junction_info.get('junction_name', 'unknown')}",
                    "junction_name": junction_info.get("junction_name", "unknown"),
                    "option": junction_info.get("chosen_option") or step.get("value", ""),
                    "selector": step.get("selector", ""),
                    "all_options": junction_info.get("all_options", [])
                })
        return path_junctions

    # ============================================================
    # MAIN ROUTERS
    # ============================================================
    
    def process_agent_result(self, session_id: str, result: Dict) -> Dict:
        """Main router for agent results"""
        logger.info(
            f"[process_agent_result] session_id={session_id}, task_type={result.get('task_type')}, success={result.get('success')}")
        session = self.get_session(session_id)
        if not session:
            logger.error(f"[process_agent_result] SESSION NOT FOUND for {session_id}")
            return {"status": "error", "error": "Session not found"}
        task_type = result.get("task_type", "")
        state = session.get("state", "")
        logger.info(f"[process_agent_result] ROUTING: task_type={task_type}, state={state}")
        # Structured logging
        log = self._get_logger(session_id)
        log.agent_result_received(task_type, result.get("success", False))
        
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
        elif state == MapperState.NEXT_PATH_NAVIGATING.value:
            return self.handle_next_path_navigate_result(session_id, result)
        elif state == MapperState.DOM_CHANGE_GETTING_SCREENSHOT.value:
            validation_errors = session.get("pending_validation_errors", {})
            if validation_errors.get("has_errors"):
                return self.handle_validation_error_screenshot_result(session_id, result)
            return self.handle_dom_change_screenshot_result(session_id, result)
        elif state == MapperState.DOM_CHANGE_GETTING_DOM.value:
            return self.handle_dom_change_dom_result(session_id, result)
        elif state == MapperState.VALIDATION_ERROR_GETTING_DOM.value:
            return self.handle_validation_error_dom_result(session_id, result)
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
        elif task_name == "handle_validation_error_recovery":
            return self.handle_validation_error_recovery_result(session_id, result)
        elif task_name == "regenerate_steps":
            return self.handle_regenerate_steps_result(session_id, result)
        elif task_name == "regenerate_verify_steps":
            return self.handle_regenerate_verify_steps_result(session_id, result)
        elif task_name == "evaluate_paths_with_ai":
            return self.handle_ai_path_evaluation_result(session_id, result)
        elif task_name == "save_mapping_result":
            return self.handle_mapping_complete(session_id, result)
        logger.warning(f"[Orchestrator] Unhandled Celery task: {task_name}")
        return {"status": "ok", "message": f"Unhandled task: {task_name}"}

    # ============================================================
    # RUNNER PHASE HELPERS
    # ============================================================

    def check_runner_phase_complete(self, session_id: str) -> Optional[Dict]:
        result = self.redis.getdel(f"runner_phase_complete:{session_id}")
        if result:
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
                # Navigation completion handled by trigger_mapping_phase Celery task
                return {"status": "complete", "phase": phase}
            return completion

        return None
