# utils/log_sanitizer.py
# Auto-scrubs secrets from all log output
# Prevents API keys and passwords from appearing in logs

import re
import logging
from typing import List, Tuple

# Patterns to scrub (regex, replacement)
SCRUB_PATTERNS: List[Tuple[str, str]] = [
    # Anthropic API keys
    (r'sk-ant-api\d{2}-[A-Za-z0-9\-_]{20,}', 'sk-ant-***REDACTED***'),
    # Generic API keys
    (r'api[_-]?key["\s:=]+["\']?[A-Za-z0-9\-_]{20,}["\']?', 'api_key=***REDACTED***'),
    # Passwords in various formats
    (r'password["\s:=]+["\']?[^"\'\s,}\]]{3,}["\']?', 'password=***REDACTED***'),
    (r'"password"\s*:\s*"[^"]{3,}"', '"password": "***REDACTED***"'),
    # AWS keys
    (r'AKIA[A-Z0-9]{16}', 'AKIA***REDACTED***'),
    (r'aws[_-]?secret[_-]?access[_-]?key["\s:=]+["\']?[A-Za-z0-9/+=]{20,}["\']?', 'aws_secret=***REDACTED***'),
]

# Compile patterns for performance
COMPILED_PATTERNS = [(re.compile(pattern, re.IGNORECASE), replacement)
                     for pattern, replacement in SCRUB_PATTERNS]


def sanitize(text: str) -> str:
    """
    Sanitize text by replacing sensitive patterns with redacted versions.

    Args:
        text: Text that may contain secrets

    Returns:
        Sanitized text with secrets redacted
    """
    if not text:
        return text

    result = text
    for pattern, replacement in COMPILED_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


class SanitizingFormatter(logging.Formatter):
    """
    Logging formatter that automatically sanitizes log messages.
    Wraps any existing formatter to add sanitization.
    """

    def __init__(self, fmt=None, datefmt=None, style='%'):
        super().__init__(fmt, datefmt, style)

    def format(self, record: logging.LogRecord) -> str:
        # Sanitize the message
        original_msg = record.msg
        if isinstance(record.msg, str):
            record.msg = sanitize(record.msg)

        # Sanitize args if present
        if record.args:
            sanitized_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    sanitized_args.append(sanitize(arg))
                else:
                    sanitized_args.append(arg)
            record.args = tuple(sanitized_args)

        # Format with parent
        result = super().format(record)

        # Restore original (in case record is reused)
        record.msg = original_msg

        return result


class SanitizingFilter(logging.Filter):
    """
    Logging filter that sanitizes all log records.
    Can be added to any handler.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = sanitize(record.msg)

        if record.args:
            # Handle dict args (used by Celery's %(name)s style formatting)
            if isinstance(record.args, dict):
                sanitized_args = {}
                for key, value in record.args.items():
                    if isinstance(value, str):
                        sanitized_args[key] = sanitize(value)
                    else:
                        sanitized_args[key] = value
                record.args = sanitized_args
            else:
                # Handle tuple/list args
                sanitized_args = []
                for arg in record.args:
                    if isinstance(arg, str):
                        sanitized_args.append(sanitize(arg))
                    else:
                        sanitized_args.append(arg)
                record.args = tuple(sanitized_args)

        return True


def setup_sanitized_logging():
    """
    Apply sanitizing filter to root logger.
    Call this once at application startup.
    """
    root_logger = logging.getLogger()
    sanitizing_filter = SanitizingFilter()

    # Add filter to all existing handlers
    for handler in root_logger.handlers:
        handler.addFilter(sanitizing_filter)

    # Also add to root logger to catch future handlers
    root_logger.addFilter(sanitizing_filter)

    logging.info("[LogSanitizer] Sanitizing filter applied to all loggers")


def get_sanitizing_handler(handler: logging.Handler) -> logging.Handler:
    """
    Wrap an existing handler with sanitization.

    Args:
        handler: Any logging handler

    Returns:
        Same handler with sanitizing filter added
    """
    handler.addFilter(SanitizingFilter())
    return handler