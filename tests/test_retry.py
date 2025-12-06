"""
Unit tests for retry logic.

Tests cover exponential backoff, retry exhaustion, retriable vs non-retriable errors.
"""

import pytest
from unittest.mock import Mock, patch
from requests.exceptions import ConnectionError, HTTPError, Timeout

from src.utils.retry import (
    retry_with_backoff,
    RetryExhausted,
    is_retriable_http_error,
    calculate_backoff
)
from src.config.settings import RetryConfig


def test_retry_success_first_attempt():
    """Test successful execution on first attempt."""
    mock_func = Mock(return_value="success")
    config = RetryConfig(max_attempts=3)

    result = retry_with_backoff(mock_func, config)

    assert result == "success"
    assert mock_func.call_count == 1


def test_retry_success_after_failures():
    """Test successful retry after transient failures."""
    mock_func = Mock()
    # Fail twice, succeed on third attempt
    mock_func.side_effect = [
        ConnectionError("Connection failed"),
        ConnectionError("Connection failed"),
        "success"
    ]

    config = RetryConfig(max_attempts=3)

    result = retry_with_backoff(mock_func, config)

    assert result == "success"
    assert mock_func.call_count == 3


def test_retry_exhausted():
    """Test failure when all retries exhausted."""
    mock_func = Mock()
    mock_func.side_effect = ConnectionError("Connection failed")

    config = RetryConfig(max_attempts=3)

    with pytest.raises(RetryExhausted) as exc_info:
        retry_with_backoff(mock_func, config)

    assert mock_func.call_count == 3
    assert exc_info.value.attempts == 3


@patch('time.sleep')
def test_exponential_backoff_timing(mock_sleep):
    """Test exponential backoff wait times."""
    mock_func = Mock()
    mock_func.side_effect = [
        ConnectionError("Fail"),
        ConnectionError("Fail"),
        "success"
    ]

    config = RetryConfig(
        max_attempts=3,
        initial_backoff_seconds=1.0,
        backoff_multiplier=2.0,
        jitter=False
    )

    retry_with_backoff(mock_func, config)

    # Verify sleep was called between attempts
    assert mock_sleep.call_count == 2


def test_is_retriable_http_error_500():
    """Test that 500 errors are retriable."""
    mock_response = Mock()
    mock_response.status_code = 500
    error = HTTPError(response=mock_response)

    assert is_retriable_http_error(error) is True


def test_is_retriable_http_error_429():
    """Test that 429 (rate limit) errors are retriable."""
    mock_response = Mock()
    mock_response.status_code = 429
    error = HTTPError(response=mock_response)

    assert is_retriable_http_error(error) is True


def test_is_retriable_http_error_404():
    """Test that 404 errors are not retriable."""
    mock_response = Mock()
    mock_response.status_code = 404
    error = HTTPError(response=mock_response)

    assert is_retriable_http_error(error) is False


def test_non_retriable_error_immediate_failure():
    """Test that non-retriable errors fail immediately."""
    mock_func = Mock()
    mock_response = Mock()
    mock_response.status_code = 404
    mock_func.side_effect = HTTPError(response=mock_response)

    config = RetryConfig(max_attempts=3)

    with pytest.raises(HTTPError):
        retry_with_backoff(mock_func, config)

    # Should fail immediately without retries
    assert mock_func.call_count == 1


def test_calculate_backoff():
    """Test backoff calculation."""
    # First attempt
    backoff1 = calculate_backoff(
        attempt=1,
        initial_backoff=1.0,
        multiplier=2.0,
        max_backoff=60.0,
        jitter=False
    )
    assert backoff1 == 1.0

    # Second attempt (2^1 * 1.0 = 2.0)
    backoff2 = calculate_backoff(
        attempt=2,
        initial_backoff=1.0,
        multiplier=2.0,
        max_backoff=60.0,
        jitter=False
    )
    assert backoff2 == 2.0

    # Third attempt (2^2 * 1.0 = 4.0)
    backoff3 = calculate_backoff(
        attempt=3,
        initial_backoff=1.0,
        multiplier=2.0,
        max_backoff=60.0,
        jitter=False
    )
    assert backoff3 == 4.0


def test_calculate_backoff_max_limit():
    """Test that backoff respects maximum."""
    backoff = calculate_backoff(
        attempt=10,
        initial_backoff=1.0,
        multiplier=2.0,
        max_backoff=30.0,
        jitter=False
    )
    assert backoff <= 30.0


def test_calculate_backoff_with_jitter():
    """Test that jitter adds randomness."""
    # Run multiple times to check variance
    backoffs = []
    for _ in range(10):
        backoff = calculate_backoff(
            attempt=2,
            initial_backoff=10.0,
            multiplier=2.0,
            max_backoff=60.0,
            jitter=True
        )
        backoffs.append(backoff)

    # With jitter, values should vary
    assert len(set(backoffs)) > 1  # Not all the same
    # All should be close to 20.0 (±10%)
    for b in backoffs:
        assert 18.0 <= b <= 22.0
