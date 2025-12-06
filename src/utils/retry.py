"""
Retry logic with exponential backoff.

This module provides retry mechanisms for handling transient failures
when connecting to external services.
"""

import time
import random
import logging
from typing import Callable, TypeVar, Optional
from functools import wraps
from requests.exceptions import HTTPError, ConnectionError, Timeout

from .logger import StructuredLogger

logger = StructuredLogger(__name__)

T = TypeVar('T')


class RetryExhausted(Exception):
    """Raised when all retry attempts are exhausted."""

    def __init__(self, message: str, attempts: int, last_exception: Optional[Exception] = None):
        """
        Initialize RetryExhausted exception.

        Args:
            message: Error message
            attempts: Number of attempts made
            last_exception: The last exception that was raised
        """
        super().__init__(message)
        self.attempts = attempts
        self.last_exception = last_exception


def is_retriable_http_error(exception: Exception) -> bool:
    """
    Determine if an HTTP error is retriable.

    Retriable status codes:
    - 429: Too Many Requests (rate limiting)
    - 500-599: Server errors

    Non-retriable status codes:
    - 400-499 (except 429): Client errors (bad request, not found, etc.)

    Args:
        exception: Exception to check

    Returns:
        True if the error is retriable
    """
    if not isinstance(exception, HTTPError):
        return False

    if exception.response is None:
        return True

    status_code = exception.response.status_code

    # Retry on server errors and rate limiting
    if status_code >= 500:
        return True
    if status_code == 429:
        return True

    # Don't retry on client errors
    return False


def calculate_backoff(
    attempt: int,
    initial_backoff: float,
    multiplier: float,
    max_backoff: float,
    jitter: bool = True
) -> float:
    """
    Calculate backoff time with exponential backoff and optional jitter.

    Args:
        attempt: Current attempt number (1-indexed)
        initial_backoff: Initial backoff time in seconds
        multiplier: Multiplier for exponential backoff
        max_backoff: Maximum backoff time in seconds
        jitter: Add random jitter to prevent thundering herd

    Returns:
        Backoff time in seconds
    """
    # Calculate exponential backoff
    backoff = initial_backoff * (multiplier ** (attempt - 1))

    # Apply maximum
    backoff = min(backoff, max_backoff)

    # Add jitter (±10% of backoff time)
    if jitter:
        jitter_amount = backoff * 0.1
        backoff += random.uniform(-jitter_amount, jitter_amount)

    return max(0, backoff)


def retry_with_backoff(
    func: Callable[..., T],
    retry_config,
    *args,
    **kwargs
) -> T:
    """
    Execute function with exponential backoff retry logic.

    This function will retry on the following exceptions:
    - requests.Timeout
    - requests.ConnectionError
    - requests.HTTPError (only if retriable - 5xx or 429)

    Args:
        func: Function to execute
        retry_config: RetryConfig instance with retry settings
        *args: Positional arguments to pass to func
        **kwargs: Keyword arguments to pass to func

    Returns:
        Result from successful function execution

    Raises:
        RetryExhausted: If all retries are exhausted
        Exception: If a non-retriable exception occurs

    Example:
        >>> from config.settings import RetryConfig
        >>> config = RetryConfig(max_attempts=3)
        >>> result = retry_with_backoff(download_file, config, "http://example.com")
    """
    last_exception = None

    for attempt in range(1, retry_config.max_attempts + 1):
        try:
            logger.debug(
                f"Executing attempt {attempt}/{retry_config.max_attempts}",
                attempt=attempt,
                max_attempts=retry_config.max_attempts
            )

            result = func(*args, **kwargs)

            if attempt > 1:
                logger.info(
                    f"Succeeded after {attempt} attempts",
                    attempt=attempt
                )

            return result

        except (Timeout, ConnectionError) as e:
            # Always retriable
            last_exception = e
            logger.warning(
                f"Retriable error on attempt {attempt}: {type(e).__name__}",
                attempt=attempt,
                error_type=type(e).__name__,
                error_message=str(e)
            )

        except HTTPError as e:
            last_exception = e
            if is_retriable_http_error(e):
                status_code = e.response.status_code if e.response else None
                logger.warning(
                    f"Retriable HTTP error on attempt {attempt}",
                    attempt=attempt,
                    status_code=status_code,
                    error_message=str(e)
                )
            else:
                # Non-retriable HTTP error, fail immediately
                status_code = e.response.status_code if e.response else None
                logger.error(
                    "Non-retriable HTTP error",
                    status_code=status_code,
                    error_message=str(e)
                )
                raise

        except Exception as e:
            # Unknown exception, don't retry
            logger.error(
                "Non-retriable exception",
                error_type=type(e).__name__,
                error_message=str(e),
                exc_info=True
            )
            raise

        # Don't sleep after the last attempt
        if attempt < retry_config.max_attempts:
            backoff_time = calculate_backoff(
                attempt=attempt,
                initial_backoff=retry_config.initial_backoff_seconds,
                multiplier=retry_config.backoff_multiplier,
                max_backoff=retry_config.max_backoff_seconds,
                jitter=retry_config.jitter
            )

            logger.info(
                f"Waiting {backoff_time:.2f}s before retry",
                attempt=attempt,
                backoff_seconds=round(backoff_time, 2)
            )

            time.sleep(backoff_time)

    # All retries exhausted
    logger.error(
        f"All {retry_config.max_attempts} retry attempts exhausted",
        max_attempts=retry_config.max_attempts,
        last_error=str(last_exception) if last_exception else None
    )

    raise RetryExhausted(
        f"Failed after {retry_config.max_attempts} attempts: {last_exception}",
        attempts=retry_config.max_attempts,
        last_exception=last_exception
    )


def retry_decorator(retry_config):
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        retry_config: RetryConfig instance

    Returns:
        Decorated function with retry logic

    Example:
        >>> from config.settings import RetryConfig
        >>> config = RetryConfig(max_attempts=3)
        >>>
        >>> @retry_decorator(config)
        ... def fetch_data(url):
        ...     return requests.get(url)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            return retry_with_backoff(func, retry_config, *args, **kwargs)
        return wrapper
    return decorator


# Alternative: Using tenacity library (if installed)
# This is a more feature-rich option but adds a dependency

try:
    from tenacity import (
        retry,
        stop_after_attempt,
        wait_exponential,
        retry_if_exception_type,
        before_sleep_log,
        after_log
    )

    TENACITY_AVAILABLE = True

    def create_tenacity_retry_decorator(retry_config):
        """
        Create a retry decorator using the tenacity library.

        This provides more advanced retry capabilities but requires
        the tenacity package to be installed.

        Args:
            retry_config: RetryConfig instance

        Returns:
            Tenacity retry decorator
        """
        return retry(
            stop=stop_after_attempt(retry_config.max_attempts),
            wait=wait_exponential(
                multiplier=retry_config.backoff_multiplier,
                min=retry_config.initial_backoff_seconds,
                max=retry_config.max_backoff_seconds
            ),
            retry=(
                retry_if_exception_type(Timeout) |
                retry_if_exception_type(ConnectionError) |
                retry_if_exception_type(is_retriable_http_error)
            ),
            before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING),
            after=after_log(logging.getLogger(__name__), logging.INFO),
            reraise=True
        )

except ImportError:
    TENACITY_AVAILABLE = False

    def create_tenacity_retry_decorator(retry_config):
        """Tenacity not available, fall back to manual retry."""
        raise ImportError(
            "tenacity library not installed. "
            "Use retry_with_backoff() or install with: pip install tenacity"
        )
