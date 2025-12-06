"""
Unit tests for configuration management.

Tests cover loading from environment variables, validation, and defaults.
"""

import pytest
import os
import json

from src.config.settings import (
    Settings,
    DataSourceConfig,
    RetryConfig,
    ConnectionConfig,
    S3Config,
    DataSourceType
)


def test_retry_config_defaults():
    """Test RetryConfig default values."""
    config = RetryConfig()

    assert config.max_attempts == 3
    assert config.initial_backoff_seconds == 1.0
    assert config.max_backoff_seconds == 60.0
    assert config.backoff_multiplier == 2.0
    assert config.jitter is True


def test_retry_config_validation():
    """Test RetryConfig validation."""
    with pytest.raises(ValueError):
        RetryConfig(max_attempts=0)

    with pytest.raises(ValueError):
        RetryConfig(initial_backoff_seconds=-1)

    with pytest.raises(ValueError):
        RetryConfig(
            initial_backoff_seconds=10.0,
            max_backoff_seconds=5.0
        )


def test_connection_config_defaults():
    """Test ConnectionConfig default values."""
    config = ConnectionConfig()

    assert config.timeout_seconds == 30
    assert config.user_agent == "IrishRiversDataCollector/1.0"
    assert config.verify_ssl is True


def test_data_source_config():
    """Test DataSourceConfig creation."""
    config = DataSourceConfig(
        station_id="inniscarra",
        name="Inniscarra",
        river="River Lee",
        url="http://example.com/test.pdf",
        source_type=DataSourceType.PDF
    )

    assert config.station_id == "inniscarra"
    assert config.name == "Inniscarra"
    assert config.enabled is True


def test_data_source_config_from_dict():
    """Test creating DataSourceConfig from dictionary."""
    data = {
        "station_id": "inniscarra",
        "name": "Inniscarra",
        "river": "River Lee",
        "url": "http://example.com/test.pdf",
        "source_type": "pdf",
        "enabled": True
    }

    config = DataSourceConfig.from_dict(data)

    assert config.station_id == "inniscarra"
    assert config.source_type == DataSourceType.PDF


def test_s3_config_key_generation():
    """Test S3 key path generation."""
    config = S3Config(
        bucket_name="test-bucket",
        region="eu-west-1"
    )

    # Test raw key
    raw_key = config.get_raw_key(
        station_id="inniscarra",
        timestamp="20251201_140523",
        filename="test.pdf"
    )
    assert raw_key == "raw/inniscarra/2025/12/01/test.pdf"

    # Test parsed key
    parsed_key = config.get_parsed_key(
        station_id="inniscarra",
        year_month="202512"
    )
    assert parsed_key == "parsed/inniscarra/2025/12/inniscarra_flow_202512.json"

    # Test latest key
    latest_key = config.get_latest_key(station_id="inniscarra")
    assert latest_key == "aggregated/inniscarra_latest.json"


def test_settings_from_dict():
    """Test creating Settings from dictionary."""
    config_dict = {
        "data_sources": [
            {
                "station_id": "inniscarra",
                "name": "Inniscarra",
                "river": "River Lee",
                "url": "http://example.com/test.pdf",
                "source_type": "pdf"
            }
        ],
        "retry": {
            "max_attempts": 5
        },
        "connection": {
            "timeout_seconds": 60
        },
        "log_level": "DEBUG"
    }

    settings = Settings.from_dict(config_dict)

    assert len(settings.data_sources) == 1
    assert settings.retry.max_attempts == 5
    assert settings.connection.timeout_seconds == 60
    assert settings.log_level == "DEBUG"


def test_settings_get_enabled_sources():
    """Test getting only enabled sources."""
    config_dict = {
        "data_sources": [
            {
                "station_id": "source1",
                "name": "Source 1",
                "river": "River 1",
                "url": "http://example.com/1.pdf",
                "enabled": True
            },
            {
                "station_id": "source2",
                "name": "Source 2",
                "river": "River 2",
                "url": "http://example.com/2.pdf",
                "enabled": False
            },
            {
                "station_id": "source3",
                "name": "Source 3",
                "river": "River 3",
                "url": "http://example.com/3.pdf",
                "enabled": True
            }
        ]
    }

    settings = Settings.from_dict(config_dict)
    enabled = settings.get_enabled_sources()

    assert len(enabled) == 2
    assert enabled[0].station_id == "source1"
    assert enabled[1].station_id == "source3"


def test_settings_is_development():
    """Test development environment detection."""
    settings_dev = Settings(
        data_sources=[],
        environment="development"
    )
    assert settings_dev.is_development() is True

    settings_prod = Settings(
        data_sources=[],
        environment="production"
    )
    assert settings_prod.is_development() is False


def test_settings_from_env_defaults(monkeypatch):
    """Test Settings.from_env() with default values."""
    # Clear environment
    for key in list(os.environ.keys()):
        if key.startswith(('DATA_', 'RETRY_', 'CONNECTION_', 'S3_', 'LOG_')):
            monkeypatch.delenv(key, raising=False)

    settings = Settings.from_env()

    # Should have default Inniscarra source
    assert len(settings.data_sources) == 1
    assert settings.data_sources[0].station_id == "inniscarra"
    assert settings.retry.max_attempts == 3
    assert settings.connection.timeout_seconds == 30


def test_settings_from_env_custom(monkeypatch):
    """Test Settings.from_env() with custom environment variables."""
    # Set custom environment variables
    data_sources = [
        {
            "station_id": "custom",
            "name": "Custom Station",
            "river": "Custom River",
            "url": "http://example.com/custom.pdf",
            "source_type": "pdf"
        }
    ]

    monkeypatch.setenv("DATA_SOURCES_JSON", json.dumps(data_sources))
    monkeypatch.setenv("RETRY_MAX_ATTEMPTS", "5")
    monkeypatch.setenv("CONNECTION_TIMEOUT", "45")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("S3_BUCKET_NAME", "my-bucket")

    settings = Settings.from_env()

    assert len(settings.data_sources) == 1
    assert settings.data_sources[0].station_id == "custom"
    assert settings.retry.max_attempts == 5
    assert settings.connection.timeout_seconds == 45
    assert settings.log_level == "DEBUG"
    assert settings.s3 is not None
    assert settings.s3.bucket_name == "my-bucket"
