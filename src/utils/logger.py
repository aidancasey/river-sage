"""
Structured logging utilities for CloudWatch compatibility.

This module provides structured JSON logging that works well with
AWS CloudWatch Logs and CloudWatch Insights queries.
"""

import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from enum import Enum

try:
    from opentelemetry import trace as otel_trace
except ImportError:
    otel_trace = None


class LogLevel(Enum):
    """Logging levels."""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class StructuredLogger:
    """
    Structured logger that outputs JSON-formatted logs.

    This logger is designed for AWS Lambda and CloudWatch Logs, making
    it easy to query and analyze logs using CloudWatch Insights.

    Example:
        >>> logger = StructuredLogger(__name__)
        >>> logger.info("Processing started", station_id="inniscarra", count=5)

        Output:
        {
            "timestamp": "2025-12-01T14:05:23.123Z",
            "level": "INFO",
            "message": "Processing started",
            "context": {
                "station_id": "inniscarra",
                "count": 5
            }
        }
    """

    def __init__(self, name: str):
        """
        Initialize structured logger.

        Args:
            name: Logger name (typically __name__ of the module)
        """
        self.logger = logging.getLogger(name)
        self.name = name

    def _log(
        self,
        level: int,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        exc_info: bool = False
    ):
        """
        Log structured message.

        Args:
            level: Logging level
            message: Log message
            context: Additional context as key-value pairs
            exc_info: Include exception information
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": logging.getLevelName(level),
            "logger": self.name,
            "message": message
        }

        # Inject OpenTelemetry trace/span IDs for log-trace correlation
        if otel_trace is not None:
            span = otel_trace.get_current_span()
            span_ctx = span.get_span_context()
            if span_ctx.trace_id:
                log_entry["trace_id"] = format(span_ctx.trace_id, '032x')
                log_entry["span_id"] = format(span_ctx.span_id, '016x')

        if context:
            # Filter out None values
            filtered_context = {
                k: v for k, v in context.items()
                if v is not None
            }
            if filtered_context:
                log_entry["context"] = filtered_context

        # For CloudWatch, log as JSON string
        log_message = json.dumps(log_entry, default=str)

        # Log with exception info if provided
        self.logger.log(level, log_message, exc_info=exc_info)

    def debug(self, message: str, **context):
        """
        Log debug message.

        Args:
            message: Log message
            **context: Additional context as keyword arguments
        """
        self._log(logging.DEBUG, message, context)

    def info(self, message: str, **context):
        """
        Log info message.

        Args:
            message: Log message
            **context: Additional context as keyword arguments
        """
        self._log(logging.INFO, message, context)

    def warning(self, message: str, **context):
        """
        Log warning message.

        Args:
            message: Log message
            **context: Additional context as keyword arguments
        """
        self._log(logging.WARNING, message, context)

    def error(self, message: str, exc_info: bool = False, **context):
        """
        Log error message.

        Args:
            message: Log message
            exc_info: Include exception traceback
            **context: Additional context as keyword arguments
        """
        self._log(logging.ERROR, message, context, exc_info=exc_info)

    def critical(self, message: str, exc_info: bool = False, **context):
        """
        Log critical message.

        Args:
            message: Log message
            exc_info: Include exception traceback
            **context: Additional context as keyword arguments
        """
        self._log(logging.CRITICAL, message, context, exc_info=exc_info)

    def exception(self, message: str, **context):
        """
        Log exception with traceback.

        This should be called from an exception handler.

        Args:
            message: Log message
            **context: Additional context as keyword arguments
        """
        self._log(logging.ERROR, message, context, exc_info=True)


def setup_logging(log_level: str = "INFO", structured: bool = True):
    """
    Configure logging for the application.

    This should be called once at application startup, typically in the
    Lambda handler or main entry point.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        structured: Use structured JSON logging (True for production/Lambda)

    Example:
        >>> setup_logging(log_level="INFO")
    """
    # Convert string to logging level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)

    if structured:
        # Simple format for structured logging (we do JSON ourselves)
        formatter = logging.Formatter('%(message)s')
    else:
        # Human-readable format for local development
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Log the setup
    logger = StructuredLogger(__name__)
    logger.info(
        "Logging configured",
        log_level=log_level,
        structured=structured
    )


class LogContext:
    """
    Context manager for adding context to all logs within a block.

    Example:
        >>> logger = StructuredLogger(__name__)
        >>> with LogContext(request_id="abc-123"):
        ...     logger.info("Processing started")
        ...     # request_id will be included in all logs
    """

    _context: Dict[str, Any] = {}

    def __init__(self, **context):
        """
        Initialize log context.

        Args:
            **context: Context key-value pairs to add to all logs
        """
        self.context = context
        self.previous_context = {}

    def __enter__(self):
        """Enter context manager."""
        # Save previous context
        self.previous_context = LogContext._context.copy()
        # Add new context
        LogContext._context.update(self.context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        # Restore previous context
        LogContext._context = self.previous_context

    @classmethod
    def get_context(cls) -> Dict[str, Any]:
        """Get current context."""
        return cls._context.copy()


# Convenience function for creating loggers
def get_logger(name: str) -> StructuredLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (typically __name__ of the module)

    Returns:
        StructuredLogger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Message", key="value")
    """
    return StructuredLogger(name)
