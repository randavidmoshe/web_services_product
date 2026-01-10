# logging_config.py
# Logging configuration for Quattera
# Location: web_services_product/api-server/utils/logging_config.py

import os
import logging
from services.session_logger import setup_json_logging

# Log level from environment variable
# Options: DEBUG, INFO, WARNING, ERROR
# Production default: INFO (no debug noise)
# Debugging: DEBUG (includes !!! prints)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Map string to logging level
LOG_LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
}


def configure_logging():
    """
    Configure logging for the application.
    Call once at application startup (e.g., in main.py or app initialization).
    
    Usage:
        from config.logging_config import configure_logging
        configure_logging()
    """
    # Setup JSON logging to stdout
    setup_json_logging()
    
    # Set root log level from environment
    level = LOG_LEVEL_MAP.get(LOG_LEVEL, logging.INFO)
    logging.getLogger().setLevel(level)
    
    # Set level for quattera loggers
    logging.getLogger("quattera").setLevel(level)
    
    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.INFO)
    logging.getLogger("kombu").setLevel(logging.WARNING)
    logging.getLogger("redis").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    
    print(f"[Logging] Configured with level: {LOG_LEVEL}")


def get_log_level() -> str:
    """Get current log level as string"""
    return LOG_LEVEL


def is_debug_enabled() -> bool:
    """Check if debug logging is enabled"""
    return LOG_LEVEL == "DEBUG"
