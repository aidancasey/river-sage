"""
Configuration management for river data scraper.

This module provides configuration classes for all components of the system.
Configuration can be loaded from environment variables or passed directly.
"""

import os
import json
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum


class DataSourceType(Enum):
    """Type of data source."""
    PDF = "pdf"
    API = "api"
    HTML = "html"


@dataclass
class DataSourceConfig:
    """Configuration for a single data source."""

    station_id: str
    name: str
    river: str
    url: str
    source_type: DataSourceType = DataSourceType.PDF
    enabled: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "DataSourceConfig":
        """Create configuration from dictionary."""
        # Convert string type to enum if needed
        if "source_type" in data and isinstance(data["source_type"], str):
            data["source_type"] = DataSourceType(data["source_type"])
        return cls(**data)


@dataclass
class RetryConfig:
    """Configuration for retry logic with exponential backoff."""

    max_attempts: int = 3
    initial_backoff_seconds: float = 1.0
    max_backoff_seconds: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True

    def __post_init__(self):
        """Validate configuration values."""
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.initial_backoff_seconds <= 0:
            raise ValueError("initial_backoff_seconds must be positive")
        if self.max_backoff_seconds < self.initial_backoff_seconds:
            raise ValueError("max_backoff_seconds must be >= initial_backoff_seconds")
        if self.backoff_multiplier <= 1:
            raise ValueError("backoff_multiplier must be > 1")


@dataclass
class ConnectionConfig:
    """Configuration for HTTP connections."""

    timeout_seconds: int = 30
    user_agent: str = "IrishRiversDataCollector/1.0"
    verify_ssl: bool = True
    max_redirects: int = 5

    def __post_init__(self):
        """Validate configuration values."""
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.max_redirects < 0:
            raise ValueError("max_redirects must be non-negative")


@dataclass
class S3Config:
    """Configuration for S3 storage."""

    bucket_name: str
    region: str = "eu-west-1"
    raw_prefix: str = "raw"
    parsed_prefix: str = "parsed"
    aggregated_prefix: str = "aggregated"
    enable_encryption: bool = True
    storage_class: str = "STANDARD"

    def get_raw_key(self, station_id: str, timestamp: str, filename: str) -> str:
        """
        Generate S3 key for raw files.

        Args:
            station_id: Station identifier
            timestamp: Timestamp in format YYYYMMDD_HHMMSS
            filename: Base filename

        Returns:
            Full S3 key path
        """
        date_part = timestamp[:8]  # YYYYMMDD
        year = date_part[:4]
        month = date_part[4:6]
        day = date_part[6:8]

        return f"{self.raw_prefix}/{station_id}/{year}/{month}/{day}/{filename}"

    def get_parsed_key(self, station_id: str, year_month: str) -> str:
        """
        Generate S3 key for parsed JSON files.

        Args:
            station_id: Station identifier
            year_month: Year and month in format YYYYMM

        Returns:
            Full S3 key path
        """
        year = year_month[:4]
        month = year_month[4:6]
        return f"{self.parsed_prefix}/{station_id}/{year}/{month}/{station_id}_flow_{year_month}.json"

    def get_latest_key(self, station_id: str) -> str:
        """
        Generate S3 key for latest aggregated data.

        Args:
            station_id: Station identifier

        Returns:
            Full S3 key path
        """
        return f"{self.aggregated_prefix}/{station_id}_latest.json"


@dataclass
class Settings:
    """Main application settings."""

    data_sources: List[DataSourceConfig]
    retry: RetryConfig = field(default_factory=RetryConfig)
    connection: ConnectionConfig = field(default_factory=ConnectionConfig)
    s3: Optional[S3Config] = None
    log_level: str = "INFO"
    environment: str = "production"

    @classmethod
    def from_env(cls) -> "Settings":
        """
        Load configuration from environment variables.

        Environment variables:
            DATA_SOURCES_JSON: JSON string with array of data source configs
            RETRY_MAX_ATTEMPTS: Maximum retry attempts
            RETRY_INITIAL_BACKOFF: Initial backoff in seconds
            CONNECTION_TIMEOUT: Connection timeout in seconds
            S3_BUCKET_NAME: S3 bucket name
            S3_REGION: AWS region
            LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR)
            ENVIRONMENT: Environment name (development, production)

        Returns:
            Configured Settings instance
        """
        # Load data sources
        data_sources_json = os.environ.get("DATA_SOURCES_JSON")
        if data_sources_json:
            try:
                sources_data = json.loads(data_sources_json)
                data_sources = [
                    DataSourceConfig.from_dict(source)
                    for source in sources_data
                ]
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                raise ValueError(f"Invalid DATA_SOURCES_JSON: {e}")
        else:
            # Default to Inniscarra station
            data_sources = [
                DataSourceConfig(
                    station_id="inniscarra",
                    name="Inniscarra",
                    river="River Lee",
                    url="http://www.esbhydro.ie/Lee/04-Inniscarra-Flow.pdf",
                    source_type=DataSourceType.PDF,
                    enabled=True
                )
            ]

        # Load retry configuration
        retry = RetryConfig(
            max_attempts=int(os.environ.get("RETRY_MAX_ATTEMPTS", "3")),
            initial_backoff_seconds=float(
                os.environ.get("RETRY_INITIAL_BACKOFF", "1.0")
            ),
            max_backoff_seconds=float(
                os.environ.get("RETRY_MAX_BACKOFF", "60.0")
            ),
            backoff_multiplier=float(
                os.environ.get("RETRY_BACKOFF_MULTIPLIER", "2.0")
            ),
            jitter=os.environ.get("RETRY_JITTER", "true").lower() == "true"
        )

        # Load connection configuration
        connection = ConnectionConfig(
            timeout_seconds=int(os.environ.get("CONNECTION_TIMEOUT", "30")),
            user_agent=os.environ.get(
                "USER_AGENT",
                "IrishRiversDataCollector/1.0"
            ),
            verify_ssl=os.environ.get("VERIFY_SSL", "true").lower() == "true"
        )

        # Load S3 configuration (optional for local development)
        s3 = None
        bucket_name = os.environ.get("S3_BUCKET_NAME")
        if bucket_name:
            s3 = S3Config(
                bucket_name=bucket_name,
                region=os.environ.get("S3_REGION", "eu-west-1"),
                raw_prefix=os.environ.get("S3_RAW_PREFIX", "raw"),
                parsed_prefix=os.environ.get("S3_PARSED_PREFIX", "parsed"),
                aggregated_prefix=os.environ.get(
                    "S3_AGGREGATED_PREFIX",
                    "aggregated"
                ),
                enable_encryption=os.environ.get(
                    "S3_ENABLE_ENCRYPTION",
                    "true"
                ).lower() == "true",
                storage_class=os.environ.get("S3_STORAGE_CLASS", "STANDARD")
            )

        return cls(
            data_sources=data_sources,
            retry=retry,
            connection=connection,
            s3=s3,
            log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
            environment=os.environ.get("ENVIRONMENT", "production")
        )

    @classmethod
    def from_dict(cls, config_dict: dict) -> "Settings":
        """
        Load configuration from dictionary.

        Args:
            config_dict: Configuration dictionary

        Returns:
            Configured Settings instance
        """
        data_sources = [
            DataSourceConfig.from_dict(source)
            for source in config_dict.get("data_sources", [])
        ]

        retry_config = config_dict.get("retry", {})
        retry = RetryConfig(**retry_config)

        connection_config = config_dict.get("connection", {})
        connection = ConnectionConfig(**connection_config)

        s3_config = config_dict.get("s3")
        s3 = S3Config(**s3_config) if s3_config else None

        return cls(
            data_sources=data_sources,
            retry=retry,
            connection=connection,
            s3=s3,
            log_level=config_dict.get("log_level", "INFO"),
            environment=config_dict.get("environment", "production")
        )

    def get_enabled_sources(self) -> List[DataSourceConfig]:
        """
        Get list of enabled data sources.

        Returns:
            List of enabled DataSourceConfig instances
        """
        return [source for source in self.data_sources if source.enabled]

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() in ("development", "dev", "local")
