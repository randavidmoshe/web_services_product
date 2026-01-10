# session_logger.py
# Structured logging for Quattera - supports Discovery, Mapping, Runner, and future activity types
# Outputs JSON to stdout for CloudWatch ingestion via Fluent Bit
# Location: web_services_product/api-server/services/session_logger.py

import json
import logging
import traceback
import sys
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from enum import Enum
from functools import lru_cache


class ActivityType(str, Enum):
    """Activity types for logging"""
    DISCOVERY = "discovery"
    MAPPING = "mapping"
    RUNNER = "runner"
    TEST_RUN = "test_run"  # Future


class LogCategory(str, Enum):
    """Log categories for filtering"""
    SESSION = "session"
    STATE_MACHINE = "state_machine"
    MILESTONE = "milestone"
    STEP_EXECUTION = "step_execution"
    AGENT_COMM = "agent_comm"
    CELERY_TASK = "celery_task"
    AI_CALL = "ai_call"
    AI_RESPONSE = "ai_response"
    RECOVERY = "recovery"
    BUDGET = "budget"
    ERROR = "error"
    DEBUG = "debug"


class JsonFormatter(logging.Formatter):
    """
    Custom formatter that outputs JSON log lines.
    Designed for CloudWatch Logs ingestion.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add extra fields if present
        if hasattr(record, "activity_type"):
            log_entry["activity_type"] = record.activity_type
        if hasattr(record, "session_id"):
            log_entry["session_id"] = record.session_id
        if hasattr(record, "company_id"):
            log_entry["company_id"] = record.company_id
        if hasattr(record, "company_name"):
            log_entry["company_name"] = record.company_name
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id
        if hasattr(record, "project_id"):
            log_entry["project_id"] = record.project_id
        if hasattr(record, "network_id"):
            log_entry["network_id"] = record.network_id
        if hasattr(record, "form_route_id"):
            log_entry["form_route_id"] = record.form_route_id
        if hasattr(record, "form_name"):
            log_entry["form_name"] = record.form_name
        if hasattr(record, "state"):
            log_entry["state"] = record.state
        if hasattr(record, "previous_state"):
            log_entry["previous_state"] = record.previous_state
        if hasattr(record, "current_path"):
            log_entry["current_path"] = record.current_path
        if hasattr(record, "current_step"):
            log_entry["current_step"] = record.current_step
        if hasattr(record, "total_steps"):
            log_entry["total_steps"] = record.total_steps
        if hasattr(record, "category"):
            log_entry["category"] = record.category
        if hasattr(record, "extra_data") and record.extra_data:
            log_entry["extra"] = record.extra_data
            
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
            log_entry["stack_trace"] = traceback.format_exception(*record.exc_info)
        
        return json.dumps(log_entry, default=str)


def setup_json_logging():
    """
    Configure root logger to output JSON to stdout.
    Call once at application startup.
    """
    root_logger = logging.getLogger()
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create stdout handler with JSON formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG)  # Allow all levels, filter at handler if needed


class SessionLogger:
    """
    Structured logger for Quattera activity sessions.
    
    Automatically injects session context into every log line.
    Supports debug mode for verbose AI logging.
    
    Usage:
        logger = SessionLogger(
            activity_type=ActivityType.MAPPING,
            session_id="12345",
            company_id=42,
            user_id=789
        )
        
        logger.info("Session started")
        logger.debug("!!! DOM extracted")
        logger.error("Step failed", exc_info=True)
    """
    
    def __init__(
        self,
        activity_type: str,
        session_id: str = None,
        company_id: int = None,
        company_name: str = None,
        user_id: int = None,
        project_id: int = None,
        network_id: int = None,
        form_route_id: int = None,
        form_name: str = None,
        debug_mode: bool = False
    ):
        """
        Initialize SessionLogger with context.
        
        Args:
            activity_type: Type of activity (discovery, mapping, runner, test_run)
            session_id: Session identifier
            company_id: Company ID
            company_name: Company name for easier identification
            user_id: User ID
            project_id: Project ID
            network_id: Network ID
            form_route_id: Form route ID
            form_name: Form name for easier identification
            debug_mode: If True, log full AI prompts/responses
        """
        self.activity_type = activity_type
        self.session_id = str(session_id) if session_id else None
        self.company_id = company_id
        self.company_name = company_name
        self.user_id = user_id
        self.project_id = project_id
        self.network_id = network_id
        self.form_route_id = form_route_id
        self.form_name = form_name
        self.debug_mode = debug_mode
        
        # Dynamic state (can be updated during session)
        self.state = None
        self.previous_state = None
        self.current_path = None
        self.current_step = None
        self.total_steps = None
        
        # Get underlying Python logger
        logger_name = f"quattera.{activity_type}"
        self._logger = logging.getLogger(logger_name)
    
    def update_context(self, **kwargs):
        """
        Update session context dynamically.
        
        Args:
            **kwargs: Any context field to update (state, current_step, etc.)
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def _make_extra(self, category: str = None, extra_data: Dict = None) -> Dict:
        """Build extra dict for log record"""
        extra = {
            "activity_type": self.activity_type,
            "session_id": self.session_id,
            "company_id": self.company_id,
            "company_name": self.company_name,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "network_id": self.network_id,
            "form_route_id": self.form_route_id,
            "form_name": self.form_name,
            "state": self.state,
            "previous_state": self.previous_state,
            "current_path": self.current_path,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "category": category or LogCategory.DEBUG.value,
            "extra_data": extra_data,
        }
        return extra
    
    # ============================================================
    # STANDARD LOG METHODS
    # ============================================================
    
    def debug(self, message: str, category: str = None, **extra_data):
        """Log debug message (includes !!! prints)"""
        extra = self._make_extra(category or LogCategory.DEBUG.value, extra_data or None)
        self._logger.debug(message, extra=extra)
    
    def info(self, message: str, category: str = None, **extra_data):
        """Log info message (key milestones)"""
        extra = self._make_extra(category or LogCategory.MILESTONE.value, extra_data or None)
        self._logger.info(message, extra=extra)
    
    def warning(self, message: str, category: str = None, **extra_data):
        """Log warning message (recoverable issues)"""
        extra = self._make_extra(category or LogCategory.RECOVERY.value, extra_data or None)
        self._logger.warning(message, extra=extra)
    
    def error(self, message: str, category: str = None, exc_info: bool = False, **extra_data):
        """Log error message (failures, crashes)"""
        extra = self._make_extra(category or LogCategory.ERROR.value, extra_data or None)
        self._logger.error(message, extra=extra, exc_info=exc_info)
    
    # ============================================================
    # CONVENIENCE METHODS
    # ============================================================
    
    def session_created(self, **extra_data):
        """Log session creation"""
        self.info(
            f"{self.activity_type.capitalize()} session created",
            category=LogCategory.SESSION.value,
            **extra_data
        )
    
    def session_completed(self, **extra_data):
        """Log session completion"""
        self.info(
            f"{self.activity_type.capitalize()} session completed",
            category=LogCategory.SESSION.value,
            **extra_data
        )
    
    def session_failed(self, error: str, **extra_data):
        """Log session failure"""
        self.error(
            f"{self.activity_type.capitalize()} session failed: {error}",
            category=LogCategory.SESSION.value,
            **extra_data
        )
    
    def state_transition(self, from_state: str, to_state: str, **extra_data):
        """Log state machine transition"""
        self.previous_state = from_state
        self.state = to_state
        self.info(
            f"State: {from_state} → {to_state}",
            category=LogCategory.STATE_MACHINE.value,
            **extra_data
        )
    
    def agent_task_pushed(self, task_type: str, **extra_data):
        """Log agent task push"""
        self.debug(
            f"Pushed agent task: {task_type}",
            category=LogCategory.AGENT_COMM.value,
            **extra_data
        )
    
    def agent_result_received(self, task_type: str, success: bool, **extra_data):
        """Log agent result received"""
        status = "success" if success else "failed"
        self.debug(
            f"Agent result: {task_type} - {status}",
            category=LogCategory.AGENT_COMM.value,
            **extra_data
        )
    
    def celery_task_started(self, task_name: str, **extra_data):
        """Log Celery task start"""
        self.info(
            f"Celery task started: {task_name}",
            category=LogCategory.CELERY_TASK.value,
            **extra_data
        )
    
    def celery_task_completed(self, task_name: str, **extra_data):
        """Log Celery task completion"""
        self.info(
            f"Celery task completed: {task_name}",
            category=LogCategory.CELERY_TASK.value,
            **extra_data
        )
    
    def celery_task_failed(self, task_name: str, error: str, exc_info: bool = True, **extra_data):
        """Log Celery task failure"""
        self.error(
            f"Celery task failed: {task_name} - {error}",
            category=LogCategory.CELERY_TASK.value,
            exc_info=exc_info,
            **extra_data
        )
    
    def step_executing(self, step_num: int, action: str, selector: str = None, **extra_data):
        """Log step execution"""
        self.current_step = step_num
        msg = f"Step {step_num}: {action}"
        if selector:
            msg += f" - {selector}"
        self.debug(msg, category=LogCategory.STEP_EXECUTION.value, **extra_data)
    
    def step_succeeded(self, step_num: int, **extra_data):
        """Log step success"""
        self.debug(
            f"Step {step_num} succeeded",
            category=LogCategory.STEP_EXECUTION.value,
            **extra_data
        )
    
    def step_failed(self, step_num: int, error: str, **extra_data):
        """Log step failure"""
        self.warning(
            f"Step {step_num} failed: {error}",
            category=LogCategory.STEP_EXECUTION.value,
            **extra_data
        )
    
    def path_started(self, path_num: int, total_paths: int = None, **extra_data):
        """Log path start (for junction discovery)"""
        self.current_path = path_num
        msg = f"Path {path_num} started"
        if total_paths:
            msg = f"Path {path_num}/{total_paths} started"
        self.info(msg, category=LogCategory.MILESTONE.value, **extra_data)
    
    def path_completed(self, path_num: int, **extra_data):
        """Log path completion"""
        self.info(
            f"Path {path_num} completed",
            category=LogCategory.MILESTONE.value,
            **extra_data
        )
    
    def ai_call(self, operation: str, prompt_size: int = None, **extra_data):
        """
        Log AI API call.
        If debug_mode is True and prompt is provided in extra_data, logs full prompt.
        """
        msg = f"AI call: {operation}"
        if prompt_size:
            msg += f" ({prompt_size} chars)"
        
        # In debug mode, include full prompt if provided
        if self.debug_mode and "prompt" in extra_data:
            self.debug(msg, category=LogCategory.AI_CALL.value, **extra_data)
        else:
            # Normal mode: truncate prompt if provided
            if "prompt" in extra_data:
                extra_data["prompt_preview"] = extra_data.pop("prompt")[:500] + "..."
            self.debug(msg, category=LogCategory.AI_CALL.value, **extra_data)
    
    def ai_response(self, operation: str, success: bool, tokens: int = None, **extra_data):
        """
        Log AI API response.
        If debug_mode is True and response is provided in extra_data, logs full response.
        """
        status = "success" if success else "failed"
        msg = f"AI response: {operation} - {status}"
        if tokens:
            msg += f" ({tokens} tokens)"
        
        # In debug mode, include full response if provided
        if self.debug_mode and "response" in extra_data:
            self.debug(msg, category=LogCategory.AI_RESPONSE.value, **extra_data)
        else:
            # Normal mode: truncate response if provided
            if "response" in extra_data:
                extra_data["response_preview"] = extra_data.pop("response")[:500] + "..."
            self.debug(msg, category=LogCategory.AI_RESPONSE.value, **extra_data)
    
    def ai_retry(self, operation: str, attempt: int, max_attempts: int, reason: str = None, **extra_data):
        """Log AI retry attempt"""
        msg = f"AI retry: {operation} ({attempt}/{max_attempts})"
        if reason:
            msg += f" - {reason}"
        self.warning(msg, category=LogCategory.AI_CALL.value, **extra_data)
    
    def budget_check(self, used: float, available: float, passed: bool, **extra_data):
        """Log budget check"""
        status = "passed" if passed else "exceeded"
        self.debug(
            f"Budget check {status}: ${used:.2f} used / ${available:.2f} available",
            category=LogCategory.BUDGET.value,
            **extra_data
        )
    
    def budget_exceeded(self, used: float, limit: float, **extra_data):
        """Log budget exceeded error"""
        self.error(
            f"Budget exceeded: ${used:.2f} used / ${limit:.2f} limit",
            category=LogCategory.BUDGET.value,
            **extra_data
        )
    
    def recovery_attempt(self, attempt: int, max_attempts: int, reason: str = None, **extra_data):
        """Log recovery attempt"""
        msg = f"Recovery attempt {attempt}/{max_attempts}"
        if reason:
            msg += f" - {reason}"
        self.info(msg, category=LogCategory.RECOVERY.value, **extra_data)
    
    def recovery_succeeded(self, method: str = None, **extra_data):
        """Log recovery success"""
        msg = "Recovery succeeded"
        if method:
            msg += f" via {method}"
        self.info(msg, category=LogCategory.RECOVERY.value, **extra_data)
    
    def recovery_failed(self, reason: str = None, **extra_data):
        """Log recovery failure"""
        msg = "Recovery failed"
        if reason:
            msg += f": {reason}"
        self.error(msg, category=LogCategory.RECOVERY.value, **extra_data)


# ============================================================
# FACTORY FUNCTION
# ============================================================

def get_session_logger(
    db_session,
    activity_type: str,
    session_id: str,
    company_id: int,
    user_id: int = None,
    project_id: int = None,
    network_id: int = None,
    form_route_id: int = None,
    form_name: str = None
) -> SessionLogger:
    """
    Factory function to create SessionLogger with company debug_mode from DB.
    
    Args:
        db_session: SQLAlchemy database session
        activity_type: Type of activity
        session_id: Session identifier
        company_id: Company ID (used to check debug_mode)
        user_id: User ID
        project_id: Project ID
        network_id: Network ID
        form_route_id: Form route ID
        form_name: Form name
        
    Returns:
        Configured SessionLogger instance
    """
    debug_mode = False
    company_name = None
    
    if db_session and company_id:
        try:
            from models.database import Company
            company = db_session.query(Company).filter(Company.id == company_id).first()
            if company:
                debug_mode = getattr(company, 'debug_mode', False) or False
                company_name = company.name
        except Exception:
            pass  # If we can't check, default to False
    
    return SessionLogger(
        activity_type=activity_type,
        session_id=session_id,
        company_id=company_id,
        company_name=company_name,
        user_id=user_id,
        project_id=project_id,
        network_id=network_id,
        form_route_id=form_route_id,
        form_name=form_name,
        debug_mode=debug_mode
    )
