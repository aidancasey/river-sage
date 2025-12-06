"""
HTTP connector for downloading files from remote sources.

This module provides a robust HTTP client with proper error handling,
timeouts, and integration with the retry mechanism.
"""

import requests
import hashlib
from typing import Tuple, Optional
from ..config.settings import ConnectionConfig
from ..utils.logger import StructuredLogger

logger = StructuredLogger(__name__)


class HTTPConnector:
    """
    HTTP connector for downloading files with proper error handling.

    This connector manages HTTP sessions, handles various response codes,
    and calculates content hashes for verification.

    Example:
        >>> config = ConnectionConfig()
        >>> connector = HTTPConnector(config)
        >>> content, hash = connector.download_file("http://example.com/file.pdf")
    """

    def __init__(self, config: ConnectionConfig):
        """
        Initialize HTTP connector.

        Args:
            config: Connection configuration
        """
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': config.user_agent,
            'Accept': '*/*'
        })
        logger.info(
            "HTTP connector initialized",
            user_agent=config.user_agent,
            timeout=config.timeout_seconds
        )

    def download_file(
        self,
        url: str,
        timeout: Optional[int] = None
    ) -> Tuple[bytes, str]:
        """
        Download file from URL and return content with hash.

        Args:
            url: The URL to download from
            timeout: Request timeout in seconds (uses config default if None)

        Returns:
            Tuple of (file_content, sha256_hash)

        Raises:
            ConnectionError: If unable to connect to source
            requests.exceptions.HTTPError: If HTTP request fails
            requests.exceptions.Timeout: If request times out

        Example:
            >>> connector = HTTPConnector(config)
            >>> content, hash = connector.download_file(
            ...     "http://www.esbhydro.ie/Lee/04-Inniscarra-Flow.pdf"
            ... )
        """
        timeout = timeout or self.config.timeout_seconds

        try:
            logger.info(f"Downloading from {url}", url=url, timeout=timeout)

            response = self.session.get(
                url,
                timeout=timeout,
                verify=self.config.verify_ssl,
                stream=True,
                allow_redirects=True
            )
            response.raise_for_status()

            # Check content type if available
            content_type = response.headers.get('Content-Type', '')
            if content_type:
                logger.debug(
                    "Response content type",
                    content_type=content_type,
                    url=url
                )

            # Download in chunks to handle large files
            content = b''
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:  # Filter out keep-alive chunks
                    content += chunk

            # Calculate SHA-256 hash
            file_hash = hashlib.sha256(content).hexdigest()

            logger.info(
                "Download successful",
                url=url,
                size_bytes=len(content),
                hash=file_hash[:8] + "...",
                content_type=content_type
            )

            return content, file_hash

        except requests.exceptions.Timeout as e:
            logger.error(
                "Request timeout",
                url=url,
                timeout=timeout,
                error=str(e)
            )
            raise

        except requests.exceptions.ConnectionError as e:
            logger.error(
                "Connection error",
                url=url,
                error=str(e)
            )
            raise

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else None
            logger.error(
                "HTTP error",
                url=url,
                status_code=status_code,
                error=str(e)
            )
            raise

        except Exception as e:
            logger.error(
                "Unexpected error during download",
                url=url,
                error_type=type(e).__name__,
                error=str(e),
                exc_info=True
            )
            raise

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close session."""
        self.session.close()
        logger.debug("HTTP connector session closed")

    def close(self):
        """Explicitly close the session."""
        self.session.close()
