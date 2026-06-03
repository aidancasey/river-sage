"""Utility functions and helpers."""

# NOTE: deliberately does NOT re-export from .retry here. retry.py imports
# `requests`, which is bundled with the collector Lambda but not the alerts-api
# Lambda. Eagerly importing it made `from ..utils.logger import StructuredLogger`
# transitively drag in `requests` and crash the alerts-api at runtime
# (ModuleNotFoundError: No module named 'requests'). Consumers that need retry
# import it directly via `from ...utils.retry import retry_with_backoff`.
from .logger import setup_logging, StructuredLogger

__all__ = [
    "setup_logging",
    "StructuredLogger",
]
