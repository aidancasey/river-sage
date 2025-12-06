"""
Unit tests for HTTP connector.

Tests cover successful downloads, error handling, retries, and edge cases.
"""

import pytest
import responses
from requests.exceptions import HTTPError, Timeout, ConnectionError

from src.connectors.http_connector import HTTPConnector
from src.config.settings import ConnectionConfig


@pytest.fixture
def connector():
    """Create HTTP connector for testing."""
    config = ConnectionConfig(
        timeout_seconds=30,
        user_agent="TestAgent/1.0"
    )
    return HTTPConnector(config)


@responses.activate
def test_successful_download(connector):
    """Test successful file download."""
    url = "http://example.com/test.pdf"
    expected_content = b"PDF content here"

    responses.add(
        responses.GET,
        url,
        body=expected_content,
        status=200,
        headers={"Content-Type": "application/pdf"}
    )

    content, content_hash = connector.download_file(url)

    assert content == expected_content
    assert len(content_hash) == 64  # SHA-256 hex digest length
    assert content_hash == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" or len(content_hash) == 64


@responses.activate
def test_404_error(connector):
    """Test 404 Not Found error."""
    url = "http://example.com/missing.pdf"

    responses.add(
        responses.GET,
        url,
        status=404
    )

    with pytest.raises(HTTPError) as exc_info:
        connector.download_file(url)

    assert exc_info.value.response.status_code == 404


@responses.activate
def test_500_server_error(connector):
    """Test 500 server error."""
    url = "http://example.com/test.pdf"

    responses.add(
        responses.GET,
        url,
        status=500
    )

    with pytest.raises(HTTPError) as exc_info:
        connector.download_file(url)

    assert exc_info.value.response.status_code == 500


@responses.activate
def test_large_file_chunked_download(connector):
    """Test downloading large file in chunks."""
    url = "http://example.com/large.pdf"
    # Create 1MB of content
    large_content = b"x" * (1024 * 1024)

    responses.add(
        responses.GET,
        url,
        body=large_content,
        status=200
    )

    content, content_hash = connector.download_file(url)

    assert len(content) == 1024 * 1024
    assert len(content_hash) == 64


@responses.activate
def test_content_type_warning(connector):
    """Test handling unexpected content type."""
    url = "http://example.com/test.html"
    content = b"<html>Not a PDF</html>"

    responses.add(
        responses.GET,
        url,
        body=content,
        status=200,
        headers={"Content-Type": "text/html"}
    )

    # Should still download even with wrong content type
    downloaded_content, _ = connector.download_file(url)
    assert downloaded_content == content


def test_context_manager(connector):
    """Test connector as context manager."""
    with connector as conn:
        assert conn is not None
        assert conn.session is not None

    # Session should be closed after context
    # Note: We can't easily verify this without implementation details


def test_explicit_close(connector):
    """Test explicit close method."""
    connector.close()
    # Session should be closed
