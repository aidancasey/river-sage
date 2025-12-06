# FR1: Data Source Connection - Implementation Tasks

## Overview
Implement a robust HTTP connection module to download PDF files from ESB Hydro with retry logic and comprehensive error handling.

---

## Task Breakdown

### Phase 1: Project Setup & Configuration

#### Task 1.1: Initialize Python Project Structure
**Priority**: High
**Estimated Effort**: 30 minutes

**Acceptance Criteria:**
- [ ] Create project directory structure:
  ```
  river-data-scraper/
  ├── src/
  │   ├── __init__.py
  │   ├── config/
  │   │   ├── __init__.py
  │   │   └── settings.py
  │   ├── connectors/
  │   │   ├── __init__.py
  │   │   └── http_connector.py
  │   ├── utils/
  │   │   ├── __init__.py
  │   │   ├── retry.py
  │   │   └── logger.py
  │   └── lambda_handler.py
  ├── tests/
  │   ├── __init__.py
  │   ├── test_http_connector.py
  │   └── test_retry.py
  ├── requirements.txt
  ├── requirements-dev.txt
  ├── .env.example
  ├── .gitignore
  └── README.md
  ```
- [ ] Initialize git repository
- [ ] Create `.gitignore` with Python and AWS-specific patterns

**Implementation Notes:**
- Follow Python best practices for package structure
- Separate source code from tests

---

#### Task 1.2: Create Configuration Management System
**Priority**: High
**Estimated Effort**: 1 hour

**Acceptance Criteria:**
- [ ] Create `config/settings.py` with configuration dataclass
- [ ] Support environment variable overrides
- [ ] Define constants for:
  - PDF source URL
  - Connection timeout values
  - Retry configuration (max attempts, backoff multiplier)
  - User agent string
- [ ] Validate required configuration on startup
- [ ] Support multiple data sources via configuration

**Example Configuration:**
```python
from dataclasses import dataclass
from typing import Optional
import os

@dataclass
class DataSourceConfig:
    station_id: str
    name: str
    river: str
    url: str
    enabled: bool = True

@dataclass
class RetryConfig:
    max_attempts: int = 3
    initial_backoff_seconds: float = 1.0
    max_backoff_seconds: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True

@dataclass
class ConnectionConfig:
    timeout_seconds: int = 30
    user_agent: str = "IrishRiversDataCollector/1.0"
    verify_ssl: bool = True

@dataclass
class Settings:
    data_sources: list[DataSourceConfig]
    retry: RetryConfig
    connection: ConnectionConfig
    log_level: str = "INFO"

    @classmethod
    def from_env(cls):
        # Load from environment variables
        pass
```

**Implementation Notes:**
- Use `python-dotenv` for local development
- Use AWS Systems Manager Parameter Store or environment variables for Lambda

---

#### Task 1.3: Define Dependencies
**Priority**: High
**Estimated Effort**: 15 minutes

**Acceptance Criteria:**
- [ ] Create `requirements.txt` with production dependencies:
  ```
  requests>=2.31.0
  boto3>=1.28.0
  tenacity>=8.2.0
  python-dateutil>=2.8.0
  pydantic>=2.0.0
  ```
- [ ] Create `requirements-dev.txt` with development dependencies:
  ```
  pytest>=7.4.0
  pytest-cov>=4.1.0
  pytest-mock>=3.11.0
  responses>=0.23.0
  black>=23.0.0
  flake8>=6.0.0
  mypy>=1.4.0
  ```
- [ ] Document dependency choices in README

**Implementation Notes:**
- Pin major versions, allow minor/patch updates
- `tenacity` provides robust retry mechanisms
- `responses` for mocking HTTP requests in tests

---

### Phase 2: Core HTTP Connection Implementation

#### Task 2.1: Implement Base HTTP Connector Class
**Priority**: High
**Estimated Effort**: 2 hours

**Acceptance Criteria:**
- [ ] Create `HTTPConnector` class in `connectors/http_connector.py`
- [ ] Implement `download_file()` method with signature:
  ```python
  def download_file(
      self,
      url: str,
      timeout: Optional[int] = None
  ) -> bytes:
      """
      Download file from URL and return bytes.

      Args:
          url: The URL to download from
          timeout: Request timeout in seconds (uses config default if None)

      Returns:
          File content as bytes

      Raises:
          ConnectionError: If unable to connect to source
          HTTPError: If HTTP request fails
          TimeoutError: If request times out
      """
  ```
- [ ] Add proper HTTP headers (User-Agent, Accept)
- [ ] Handle HTTP status codes appropriately:
  - 200: Success
  - 404: Resource not found
  - 500-599: Server errors (retriable)
  - 429: Rate limiting (retriable with longer backoff)
- [ ] Stream large files instead of loading into memory
- [ ] Validate response content-type is PDF (if header present)
- [ ] Calculate and return content hash (SHA-256)

**Implementation Example:**
```python
import requests
import hashlib
from typing import Tuple, Optional
import logging

class HTTPConnector:
    def __init__(self, config: ConnectionConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': config.user_agent
        })
        self.logger = logging.getLogger(__name__)

    def download_file(
        self,
        url: str,
        timeout: Optional[int] = None
    ) -> Tuple[bytes, str]:
        """
        Download file and return content with hash.

        Returns:
            Tuple of (file_content, sha256_hash)
        """
        timeout = timeout or self.config.timeout_seconds

        try:
            self.logger.info(f"Downloading from {url}")
            response = self.session.get(
                url,
                timeout=timeout,
                verify=self.config.verify_ssl,
                stream=True
            )
            response.raise_for_status()

            # Check content type if available
            content_type = response.headers.get('Content-Type', '')
            if content_type and 'pdf' not in content_type.lower():
                self.logger.warning(
                    f"Unexpected content type: {content_type}"
                )

            # Download in chunks
            content = b''
            for chunk in response.iter_content(chunk_size=8192):
                content += chunk

            # Calculate hash
            file_hash = hashlib.sha256(content).hexdigest()

            self.logger.info(
                f"Downloaded {len(content)} bytes, hash: {file_hash[:8]}..."
            )

            return content, file_hash

        except requests.exceptions.Timeout as e:
            self.logger.error(f"Timeout downloading from {url}: {e}")
            raise TimeoutError(f"Request timeout: {e}")
        except requests.exceptions.ConnectionError as e:
            self.logger.error(f"Connection error: {e}")
            raise ConnectionError(f"Failed to connect: {e}")
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP error: {e}")
            raise

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()
```

**Implementation Notes:**
- Use `requests.Session()` for connection pooling
- Implement context manager for proper cleanup
- Log all connection attempts and results

---

#### Task 2.2: Implement Retry Logic with Exponential Backoff
**Priority**: High
**Estimated Effort**: 2 hours

**Acceptance Criteria:**
- [ ] Create retry decorator in `utils/retry.py`
- [ ] Implement exponential backoff algorithm:
  - Initial wait: 1 second
  - Backoff multiplier: 2x
  - Maximum wait: 60 seconds
  - Add jitter to prevent thundering herd
- [ ] Support maximum retry attempts (default: 3)
- [ ] Define retriable exceptions:
  - `requests.exceptions.Timeout`
  - `requests.exceptions.ConnectionError`
  - `requests.exceptions.HTTPError` (only 5xx and 429)
- [ ] Log each retry attempt with wait time
- [ ] Track total attempts and elapsed time

**Implementation Using Tenacity:**
```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log
)
import logging
from requests.exceptions import HTTPError, ConnectionError, Timeout

logger = logging.getLogger(__name__)

def is_retriable_http_error(exception):
    """Determine if HTTP error is retriable."""
    if not isinstance(exception, HTTPError):
        return False

    if exception.response is None:
        return True

    status_code = exception.response.status_code
    # Retry on server errors and rate limiting
    return status_code >= 500 or status_code == 429

def create_retry_decorator(config: RetryConfig):
    """Create a retry decorator with specified configuration."""
    return retry(
        stop=stop_after_attempt(config.max_attempts),
        wait=wait_exponential(
            multiplier=config.backoff_multiplier,
            min=config.initial_backoff_seconds,
            max=config.max_backoff_seconds
        ),
        retry=(
            retry_if_exception_type(Timeout) |
            retry_if_exception_type(ConnectionError) |
            retry_if_exception_type(is_retriable_http_error)
        ),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.INFO),
        reraise=True
    )

# Usage example
def download_with_retry(connector: HTTPConnector, url: str, config: RetryConfig):
    """Download file with retry logic."""
    retry_decorator = create_retry_decorator(config)

    @retry_decorator
    def _download():
        return connector.download_file(url)

    return _download()
```

**Alternative Manual Implementation (if avoiding tenacity):**
```python
import time
import random
from typing import Callable, TypeVar, Any

T = TypeVar('T')

class RetryExhausted(Exception):
    """Raised when all retry attempts are exhausted."""
    pass

def retry_with_backoff(
    func: Callable[..., T],
    config: RetryConfig,
    *args,
    **kwargs
) -> T:
    """
    Execute function with exponential backoff retry logic.

    Args:
        func: Function to execute
        config: Retry configuration
        *args, **kwargs: Arguments to pass to func

    Returns:
        Result from successful function execution

    Raises:
        RetryExhausted: If all retries are exhausted
    """
    last_exception = None
    wait_time = config.initial_backoff_seconds

    for attempt in range(1, config.max_attempts + 1):
        try:
            logger.info(f"Attempt {attempt}/{config.max_attempts}")
            result = func(*args, **kwargs)
            if attempt > 1:
                logger.info(f"Succeeded on attempt {attempt}")
            return result

        except (Timeout, ConnectionError) as e:
            last_exception = e
            logger.warning(f"Retriable error on attempt {attempt}: {e}")

        except HTTPError as e:
            if is_retriable_http_error(e):
                last_exception = e
                logger.warning(
                    f"Retriable HTTP error on attempt {attempt}: {e}"
                )
            else:
                # Non-retriable HTTP error, fail immediately
                logger.error(f"Non-retriable HTTP error: {e}")
                raise

        # Don't sleep after the last attempt
        if attempt < config.max_attempts:
            # Add jitter if configured
            if config.jitter:
                jitter = random.uniform(0, wait_time * 0.1)
                actual_wait = wait_time + jitter
            else:
                actual_wait = wait_time

            logger.info(f"Waiting {actual_wait:.2f}s before retry")
            time.sleep(actual_wait)

            # Calculate next wait time with exponential backoff
            wait_time = min(
                wait_time * config.backoff_multiplier,
                config.max_backoff_seconds
            )

    # All retries exhausted
    logger.error(
        f"All {config.max_attempts} retry attempts exhausted"
    )
    raise RetryExhausted(
        f"Failed after {config.max_attempts} attempts"
    ) from last_exception
```

**Implementation Notes:**
- Use `tenacity` library for production-grade retry logic
- Log before each retry with wait time
- Implement jitter to avoid synchronized retries across multiple instances
- Consider rate limiting (429) with longer backoff

---

#### Task 2.3: Add Comprehensive Logging
**Priority**: Medium
**Estimated Effort**: 1 hour

**Acceptance Criteria:**
- [ ] Create structured logging utility in `utils/logger.py`
- [ ] Configure logging format for CloudWatch compatibility:
  ```python
  {
      "timestamp": "2025-12-01T14:05:23Z",
      "level": "INFO",
      "message": "Downloaded PDF successfully",
      "context": {
          "url": "http://...",
          "bytes": 12345,
          "attempt": 1,
          "elapsed_ms": 234
      }
  }
  ```
- [ ] Log the following events:
  - Connection initiation
  - Each retry attempt
  - Success/failure status
  - Download size and duration
  - Hash of downloaded file
- [ ] Support different log levels (DEBUG, INFO, WARNING, ERROR)
- [ ] Redact sensitive information from logs

**Implementation Example:**
```python
import logging
import json
from datetime import datetime
from typing import Any, Dict

class StructuredLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def _log(
        self,
        level: int,
        message: str,
        context: Dict[str, Any] = None
    ):
        """Log structured message."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": logging.getLevelName(level),
            "message": message
        }

        if context:
            log_entry["context"] = context

        # For CloudWatch, log as JSON string
        self.logger.log(level, json.dumps(log_entry))

    def info(self, message: str, **context):
        self._log(logging.INFO, message, context)

    def warning(self, message: str, **context):
        self._log(logging.WARNING, message, context)

    def error(self, message: str, **context):
        self._log(logging.ERROR, message, context)

    def debug(self, message: str, **context):
        self._log(logging.DEBUG, message, context)

# Setup function for Lambda
def setup_logging(log_level: str = "INFO"):
    """Configure logging for the application."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(message)s'  # Simple format since we do JSON ourselves
    )
```

**Implementation Notes:**
- Use JSON format for structured logging in CloudWatch
- Ensure sensitive data (if any) is redacted
- Include correlation IDs for request tracing

---

### Phase 3: Integration & Error Handling

#### Task 3.1: Create Data Source Abstraction
**Priority**: Medium
**Estimated Effort**: 1.5 hours

**Acceptance Criteria:**
- [ ] Create `DataSource` abstract base class
- [ ] Create `PDFDataSource` implementation for ESB Hydro
- [ ] Support multiple data sources via configuration
- [ ] Each data source knows its URL, type, and metadata

**Implementation Example:**
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Tuple
from datetime import datetime

@dataclass
class DownloadResult:
    """Result of a successful download."""
    content: bytes
    content_hash: str
    url: str
    downloaded_at: datetime
    size_bytes: int
    attempt_count: int

class DataSource(ABC):
    """Abstract base class for data sources."""

    def __init__(self, config: DataSourceConfig):
        self.config = config

    @abstractmethod
    def download(self) -> DownloadResult:
        """Download data from source."""
        pass

    @property
    def station_id(self) -> str:
        return self.config.station_id

    @property
    def is_enabled(self) -> bool:
        return self.config.enabled

class PDFDataSource(DataSource):
    """Data source for PDF files via HTTP."""

    def __init__(
        self,
        config: DataSourceConfig,
        connector: HTTPConnector,
        retry_config: RetryConfig
    ):
        super().__init__(config)
        self.connector = connector
        self.retry_config = retry_config
        self.logger = StructuredLogger(__name__)

    def download(self) -> DownloadResult:
        """Download PDF with retry logic."""
        start_time = datetime.utcnow()
        attempt_count = 0

        def _attempt_download():
            nonlocal attempt_count
            attempt_count += 1
            return self.connector.download_file(self.config.url)

        try:
            content, content_hash = retry_with_backoff(
                _attempt_download,
                self.retry_config
            )

            downloaded_at = datetime.utcnow()

            result = DownloadResult(
                content=content,
                content_hash=content_hash,
                url=self.config.url,
                downloaded_at=downloaded_at,
                size_bytes=len(content),
                attempt_count=attempt_count
            )

            self.logger.info(
                f"Successfully downloaded {self.config.name}",
                station_id=self.station_id,
                size_bytes=result.size_bytes,
                hash=content_hash[:8],
                attempts=attempt_count,
                elapsed_ms=int(
                    (downloaded_at - start_time).total_seconds() * 1000
                )
            )

            return result

        except Exception as e:
            self.logger.error(
                f"Failed to download {self.config.name}",
                station_id=self.station_id,
                error=str(e),
                attempts=attempt_count
            )
            raise
```

**Implementation Notes:**
- Design for extensibility (future: weather APIs, other PDFs)
- Each source is independently configurable
- Maintain consistent interface across source types

---

#### Task 3.2: Implement Error Classification & Handling
**Priority**: High
**Estimated Effort**: 1.5 hours

**Acceptance Criteria:**
- [ ] Create custom exception hierarchy:
  ```python
  DataSourceError (base)
  ├── TransientError (retriable)
  │   ├── NetworkTimeoutError
  │   ├── ServerError
  │   └── RateLimitError
  └── PermanentError (not retriable)
      ├── ResourceNotFoundError
      ├── AuthenticationError
      └── InvalidContentError
  ```
- [ ] Map HTTP status codes to exception types
- [ ] Include diagnostic information in exceptions
- [ ] Create error response format:
  ```python
  {
      "success": false,
      "error": {
          "type": "NetworkTimeoutError",
          "message": "Request timed out after 30s",
          "retriable": true,
          "details": {
              "url": "http://...",
              "attempt": 3
          }
      },
      "timestamp": "2025-12-01T14:05:23Z"
  }
  ```

**Implementation Example:**
```python
from typing import Dict, Any, Optional

class DataSourceError(Exception):
    """Base exception for data source errors."""

    def __init__(
        self,
        message: str,
        retriable: bool = False,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.retriable = retriable
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.__class__.__name__,
            "message": self.message,
            "retriable": self.retriable,
            "details": self.details
        }

class TransientError(DataSourceError):
    """Temporary error that may succeed on retry."""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, retriable=True, details=details)

class NetworkTimeoutError(TransientError):
    pass

class ServerError(TransientError):
    pass

class RateLimitError(TransientError):
    pass

class PermanentError(DataSourceError):
    """Permanent error that won't succeed on retry."""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, retriable=False, details=details)

class ResourceNotFoundError(PermanentError):
    pass

class AuthenticationError(PermanentError):
    pass

class InvalidContentError(PermanentError):
    pass

def map_http_error(http_error: HTTPError) -> DataSourceError:
    """Map HTTP error to appropriate DataSourceError."""
    status_code = http_error.response.status_code if http_error.response else None

    if status_code == 404:
        return ResourceNotFoundError(
            f"Resource not found: {http_error}",
            details={"status_code": status_code}
        )
    elif status_code == 401 or status_code == 403:
        return AuthenticationError(
            f"Authentication failed: {http_error}",
            details={"status_code": status_code}
        )
    elif status_code == 429:
        return RateLimitError(
            f"Rate limited: {http_error}",
            details={"status_code": status_code}
        )
    elif status_code and status_code >= 500:
        return ServerError(
            f"Server error: {http_error}",
            details={"status_code": status_code}
        )
    else:
        return PermanentError(
            f"HTTP error: {http_error}",
            details={"status_code": status_code}
        )
```

**Implementation Notes:**
- Clear distinction between retriable and permanent errors
- Include context for debugging
- Map external errors to internal exceptions

---

### Phase 4: Testing

#### Task 4.1: Unit Tests for HTTP Connector
**Priority**: High
**Estimated Effort**: 2 hours

**Acceptance Criteria:**
- [ ] Test successful download
- [ ] Test timeout handling
- [ ] Test connection errors
- [ ] Test various HTTP status codes (404, 500, 429)
- [ ] Test content hash calculation
- [ ] Test streaming download
- [ ] Mock external HTTP calls using `responses` library
- [ ] Achieve >90% code coverage

**Test Example:**
```python
import pytest
import responses
from connectors.http_connector import HTTPConnector
from config.settings import ConnectionConfig

@pytest.fixture
def connector():
    config = ConnectionConfig(
        timeout_seconds=30,
        user_agent="TestAgent/1.0"
    )
    return HTTPConnector(config)

@responses.activate
def test_successful_download(connector):
    """Test successful file download."""
    url = "http://example.com/test.pdf"
    expected_content = b"PDF content"

    responses.add(
        responses.GET,
        url,
        body=expected_content,
        status=200,
        headers={"Content-Type": "application/pdf"}
    )

    content, content_hash = connector.download_file(url)

    assert content == expected_content
    assert len(content_hash) == 64  # SHA-256 hex digest

@responses.activate
def test_timeout_error(connector):
    """Test timeout handling."""
    url = "http://example.com/test.pdf"

    responses.add(
        responses.GET,
        url,
        body=TimeoutError("Connection timeout")
    )

    with pytest.raises(TimeoutError):
        connector.download_file(url)

@responses.activate
def test_server_error(connector):
    """Test 500 server error."""
    url = "http://example.com/test.pdf"

    responses.add(
        responses.GET,
        url,
        status=500
    )

    with pytest.raises(HTTPError):
        connector.download_file(url)
```

**Implementation Notes:**
- Use `responses` library to mock HTTP calls
- Test both success and failure paths
- Verify logging output

---

#### Task 4.2: Unit Tests for Retry Logic
**Priority**: High
**Estimated Effort**: 2 hours

**Acceptance Criteria:**
- [ ] Test retry on transient errors
- [ ] Test exponential backoff timing
- [ ] Test max attempts limit
- [ ] Test immediate failure on permanent errors
- [ ] Test jitter application
- [ ] Verify log messages for each retry

**Test Example:**
```python
import pytest
from unittest.mock import Mock, patch
import time
from utils.retry import retry_with_backoff, RetryConfig
from requests.exceptions import ConnectionError, HTTPError

def test_retry_success_after_failures():
    """Test successful retry after transient failures."""
    mock_func = Mock()
    # Fail twice, succeed on third attempt
    mock_func.side_effect = [
        ConnectionError("Connection failed"),
        ConnectionError("Connection failed"),
        "Success"
    ]

    config = RetryConfig(max_attempts=3)

    result = retry_with_backoff(mock_func, config)

    assert result == "Success"
    assert mock_func.call_count == 3

def test_retry_exhausted():
    """Test failure when all retries exhausted."""
    mock_func = Mock()
    mock_func.side_effect = ConnectionError("Connection failed")

    config = RetryConfig(max_attempts=3)

    with pytest.raises(RetryExhausted):
        retry_with_backoff(mock_func, config)

    assert mock_func.call_count == 3

@patch('time.sleep')
def test_exponential_backoff_timing(mock_sleep):
    """Test exponential backoff wait times."""
    mock_func = Mock()
    mock_func.side_effect = [
        ConnectionError("Fail"),
        ConnectionError("Fail"),
        "Success"
    ]

    config = RetryConfig(
        max_attempts=3,
        initial_backoff_seconds=1.0,
        backoff_multiplier=2.0,
        jitter=False
    )

    retry_with_backoff(mock_func, config)

    # Verify sleep was called with correct backoff times
    assert mock_sleep.call_count == 2
    calls = [call.args[0] for call in mock_sleep.call_args_list]
    assert calls[0] == 1.0  # First backoff
    assert calls[1] == 2.0  # Second backoff
```

**Implementation Notes:**
- Mock `time.sleep` to speed up tests
- Verify retry count and timing
- Test both success and failure scenarios

---

#### Task 4.3: Integration Tests
**Priority**: Medium
**Estimated Effort**: 2 hours

**Acceptance Criteria:**
- [ ] Test end-to-end download from mock server
- [ ] Test with actual ESB Hydro URL (optional, mark as slow)
- [ ] Test configuration loading
- [ ] Test error handling flow
- [ ] Test logging output

**Test Example:**
```python
import pytest
from connectors.http_connector import HTTPConnector
from config.settings import Settings, ConnectionConfig, RetryConfig
from connectors.pdf_data_source import PDFDataSource, DataSourceConfig

@pytest.mark.integration
@responses.activate
def test_end_to_end_download():
    """Test complete download flow."""
    # Setup configuration
    conn_config = ConnectionConfig()
    retry_config = RetryConfig(max_attempts=3)

    source_config = DataSourceConfig(
        station_id="test",
        name="Test Station",
        river="Test River",
        url="http://example.com/test.pdf"
    )

    # Mock HTTP response
    responses.add(
        responses.GET,
        source_config.url,
        body=b"PDF content",
        status=200
    )

    # Execute download
    connector = HTTPConnector(conn_config)
    source = PDFDataSource(source_config, connector, retry_config)

    result = source.download()

    assert result.content == b"PDF content"
    assert result.size_bytes == 11
    assert result.attempt_count == 1

@pytest.mark.slow
@pytest.mark.skipif(
    not pytest.config.getoption("--run-live"),
    reason="Skipping live tests"
)
def test_real_esb_hydro_download():
    """Test download from actual ESB Hydro URL."""
    url = "http://www.esbhydro.ie/Lee/04-Inniscarra-Flow.pdf"

    conn_config = ConnectionConfig()
    connector = HTTPConnector(conn_config)

    content, hash = connector.download_file(url)

    assert len(content) > 0
    assert content[:4] == b'%PDF'  # PDF magic number
```

**Implementation Notes:**
- Separate fast unit tests from slow integration tests
- Make live tests optional with pytest markers
- Use environment variables for test configuration

---

### Phase 5: Documentation & Deployment Preparation

#### Task 5.1: Write Technical Documentation
**Priority**: Medium
**Estimated Effort**: 1 hour

**Acceptance Criteria:**
- [ ] Document all public APIs
- [ ] Add docstrings to all classes and methods
- [ ] Create README.md with:
  - Installation instructions
  - Configuration guide
  - Usage examples
  - Testing instructions
- [ ] Document error codes and handling
- [ ] Add architecture diagram

**Implementation Notes:**
- Use Google-style docstrings
- Include code examples
- Document configuration options

---

#### Task 5.2: Create Lambda Deployment Package
**Priority**: High
**Estimated Effort**: 1.5 hours

**Acceptance Criteria:**
- [ ] Create `lambda_handler.py` entry point
- [ ] Handle Lambda event structure
- [ ] Return proper Lambda response format
- [ ] Add error handling for Lambda context
- [ ] Create deployment script:
  ```bash
  #!/bin/bash
  # deploy.sh
  pip install -r requirements.txt -t package/
  cp -r src/* package/
  cd package && zip -r ../lambda_function.zip . && cd ..
  aws lambda update-function-code \
      --function-name river-data-collector \
      --zip-file fileb://lambda_function.zip
  ```
- [ ] Test Lambda locally using AWS SAM or LocalStack

**Lambda Handler Example:**
```python
import json
from datetime import datetime
from typing import Dict, Any
from config.settings import Settings
from connectors.http_connector import HTTPConnector
from connectors.pdf_data_source import PDFDataSource
from utils.logger import setup_logging, StructuredLogger

logger = StructuredLogger(__name__)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for downloading river data.

    Args:
        event: Lambda event (from EventBridge)
        context: Lambda context

    Returns:
        Response with status and details
    """
    request_id = context.request_id
    setup_logging()

    logger.info(
        "Lambda invocation started",
        request_id=request_id,
        event=event
    )

    try:
        # Load configuration
        settings = Settings.from_env()

        # Download from each enabled source
        results = []
        for source_config in settings.data_sources:
            if not source_config.enabled:
                continue

            try:
                connector = HTTPConnector(settings.connection)
                source = PDFDataSource(
                    source_config,
                    connector,
                    settings.retry
                )

                result = source.download()

                results.append({
                    "station_id": source_config.station_id,
                    "success": True,
                    "size_bytes": result.size_bytes,
                    "hash": result.content_hash,
                    "attempts": result.attempt_count
                })

                # TODO: Save to S3 (FR3)

            except Exception as e:
                logger.error(
                    f"Failed to download from {source_config.name}",
                    station_id=source_config.station_id,
                    error=str(e)
                )
                results.append({
                    "station_id": source_config.station_id,
                    "success": False,
                    "error": str(e)
                })

        success_count = sum(1 for r in results if r["success"])

        response = {
            "statusCode": 200 if success_count > 0 else 500,
            "body": json.dumps({
                "success": success_count > 0,
                "total_sources": len(results),
                "successful": success_count,
                "results": results,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
        }

        logger.info(
            "Lambda invocation completed",
            request_id=request_id,
            success_count=success_count,
            total_count=len(results)
        )

        return response

    except Exception as e:
        logger.error(
            "Lambda invocation failed",
            request_id=request_id,
            error=str(e)
        )
        return {
            "statusCode": 500,
            "body": json.dumps({
                "success": False,
                "error": str(e)
            })
        }
```

**Implementation Notes:**
- Keep Lambda handler thin, delegate to modules
- Handle Lambda-specific event/context
- Return proper status codes

---

#### Task 5.3: Create Monitoring & Alerting Configuration
**Priority**: Medium
**Estimated Effort**: 1 hour

**Acceptance Criteria:**
- [ ] Define CloudWatch metrics to track:
  - Download success rate
  - Download duration
  - Retry count
  - Error types
- [ ] Create CloudWatch dashboard JSON
- [ ] Define alarms:
  - >3 consecutive failures
  - Average duration >30s
  - No successful execution in 2 hours
- [ ] Document alarm response procedures

**CloudWatch Metric Example:**
```python
import boto3

cloudwatch = boto3.client('cloudwatch')

def publish_metrics(result: DownloadResult, station_id: str):
    """Publish custom metrics to CloudWatch."""
    cloudwatch.put_metric_data(
        Namespace='RiverDataCollector',
        MetricData=[
            {
                'MetricName': 'DownloadSuccess',
                'Value': 1.0,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'StationId', 'Value': station_id}
                ]
            },
            {
                'MetricName': 'DownloadDuration',
                'Value': result.duration_ms,
                'Unit': 'Milliseconds',
                'Dimensions': [
                    {'Name': 'StationId', 'Value': station_id}
                ]
            },
            {
                'MetricName': 'RetryCount',
                'Value': result.attempt_count - 1,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'StationId', 'Value': station_id}
                ]
            }
        ]
    )
```

**Implementation Notes:**
- Use custom metrics for business-specific data
- Lambda duration/errors tracked automatically
- Create SNS topic for alerts

---

## Summary Checklist

### Critical Path (Must Complete)
- [ ] Task 1.1: Project structure
- [ ] Task 1.2: Configuration system
- [ ] Task 1.3: Dependencies
- [ ] Task 2.1: HTTP connector
- [ ] Task 2.2: Retry logic
- [ ] Task 3.1: Data source abstraction
- [ ] Task 3.2: Error handling
- [ ] Task 4.1: HTTP connector tests
- [ ] Task 4.2: Retry logic tests
- [ ] Task 5.2: Lambda deployment

### Nice to Have
- [ ] Task 2.3: Structured logging
- [ ] Task 4.3: Integration tests
- [ ] Task 5.1: Documentation
- [ ] Task 5.3: Monitoring configuration

## Estimated Total Effort
- **Critical Path**: ~14 hours
- **Nice to Have**: ~5 hours
- **Total**: ~19 hours (approx 2-3 days for one developer)

## Success Criteria
✅ Can download PDF from ESB Hydro URL
✅ Retries 3 times with exponential backoff on failure
✅ Logs all connection attempts
✅ Returns content and hash on success
✅ Handles errors gracefully
✅ >90% test coverage
✅ Deploys successfully to AWS Lambda

## Next Steps After FR1
Once FR1 is complete, proceed to:
- **FR2**: PDF data extraction (parsing flow values)
- **FR3**: S3 storage implementation
- **FR4**: EventBridge scheduling setup
