"""
Unit tests for ESB Hydro PDF parser.
"""

import pytest
from datetime import datetime
from src.parsers.esb_hydro_parser import (
    ESBHydroFlowParser,
    FlowReading,
    ParsedFlowData
)


@pytest.fixture
def parser():
    """Create parser instance."""
    return ESBHydroFlowParser(
        station_name="Inniscarra",
        river_name="River Lee"
    )


def test_flow_reading_creation():
    """Test FlowReading dataclass."""
    timestamp = datetime(2025, 12, 5, 17, 0, 0)
    reading = FlowReading(
        timestamp=timestamp,
        flow_rate_m3s=127.0,
        units="cubic meters per second"
    )

    assert reading.timestamp == timestamp
    assert reading.flow_rate_m3s == 127.0
    assert reading.units == "cubic meters per second"


def test_flow_reading_to_dict():
    """Test FlowReading to_dict conversion."""
    timestamp = datetime(2025, 12, 5, 17, 0, 0)
    reading = FlowReading(
        timestamp=timestamp,
        flow_rate_m3s=127.0
    )

    data = reading.to_dict()

    assert "timestamp" in data
    assert "flow_rate_m3s" in data
    assert data["flow_rate_m3s"] == 127.0


def test_parse_timestamp(parser):
    """Test timestamp parsing."""
    # Test format: "05-Dec-25 17:00:00"
    timestamp = parser._parse_timestamp("05-Dec-25 17:00:00")

    assert timestamp.year == 2025
    assert timestamp.month == 12
    assert timestamp.day == 5
    assert timestamp.hour == 17
    assert timestamp.minute == 0
    assert timestamp.second == 0


def test_parse_timestamp_invalid(parser):
    """Test invalid timestamp raises error."""
    with pytest.raises(ValueError):
        parser._parse_timestamp("invalid-date")


def test_get_latest_flow(parser):
    """Test getting latest flow value."""
    current = FlowReading(
        timestamp=datetime.now(),
        flow_rate_m3s=127.0
    )
    parsed_data = ParsedFlowData(
        station="Inniscarra",
        river="River Lee",
        current_reading=current,
        historical_readings=[],
        parsed_at=datetime.utcnow()
    )

    latest = parser.get_latest_flow(parsed_data)

    assert latest == 127.0


def test_get_average_flow(parser):
    """Test calculating average flow."""
    current = FlowReading(
        timestamp=datetime.now(),
        flow_rate_m3s=100.0
    )
    historical = [
        FlowReading(datetime.now(), 90.0),
        FlowReading(datetime.now(), 100.0),
        FlowReading(datetime.now(), 110.0),
    ]
    parsed_data = ParsedFlowData(
        station="Inniscarra",
        river="River Lee",
        current_reading=current,
        historical_readings=historical,
        parsed_at=datetime.utcnow()
    )

    avg = parser.get_average_flow(parsed_data, hours=3)

    assert avg == 100.0  # (90 + 100 + 110) / 3


def test_get_flow_statistics(parser):
    """Test flow statistics calculation."""
    current = FlowReading(
        timestamp=datetime.now(),
        flow_rate_m3s=100.0
    )
    historical = [
        FlowReading(datetime.now(), 90.0),
        FlowReading(datetime.now(), 100.0),
        FlowReading(datetime.now(), 110.0),
    ]
    parsed_data = ParsedFlowData(
        station="Inniscarra",
        river="River Lee",
        current_reading=current,
        historical_readings=historical,
        parsed_at=datetime.utcnow()
    )

    stats = parser.get_flow_statistics(parsed_data)

    assert stats["current"] == 100.0
    assert stats["min"] == 90.0
    assert stats["max"] == 110.0
    assert stats["mean"] == 100.0
    assert stats["count"] == 3


def test_parsed_flow_data_to_dict():
    """Test ParsedFlowData to_dict conversion."""
    current = FlowReading(
        timestamp=datetime(2025, 12, 5, 17, 0),
        flow_rate_m3s=127.0
    )
    parsed_data = ParsedFlowData(
        station="Inniscarra",
        river="River Lee",
        current_reading=current,
        historical_readings=[],
        parsed_at=datetime.utcnow(),
        source_hash="abc123"
    )

    data = parsed_data.to_dict()

    assert data["station"] == "Inniscarra"
    assert data["river"] == "River Lee"
    assert "current_reading" in data
    assert "historical_readings" in data
    assert data["reading_count"] == 0
    assert data["source_hash"] == "abc123"


# Integration test with real PDF (slow test)
@pytest.mark.slow
@pytest.mark.skip(reason="Live test - requires network access. Run manually with: pytest -m slow")
def test_parse_real_pdf(parser):
    """Test parsing real ESB Hydro PDF."""
    from src.config.settings import ConnectionConfig, RetryConfig
    from src.connectors.http_connector import HTTPConnector
    from src.utils.retry import retry_with_backoff

    # Download PDF
    url = "http://www.esbhydro.ie/Lee/04-Inniscarra-Flow.pdf"
    conn_config = ConnectionConfig()
    retry_config = RetryConfig()

    with HTTPConnector(conn_config) as connector:
        content, hash = retry_with_backoff(
            lambda: connector.download_file(url),
            retry_config
        )

    # Parse PDF
    parsed_data = parser.parse(content, source_hash=hash)

    # Verify structure
    assert parsed_data.station == "Inniscarra"
    assert parsed_data.river == "River Lee"
    assert parsed_data.current_reading is not None
    assert parsed_data.current_reading.flow_rate_m3s > 0
    assert len(parsed_data.historical_readings) > 0
    assert len(parsed_data.historical_readings) <= 30
    assert parsed_data.source_hash == hash
