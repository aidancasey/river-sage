"""
Unit tests for waterlevel.ie CSV parser.
"""

import pytest
from datetime import datetime
from src.parsers.waterlevel_parser import (
    WaterLevelParser,
    WaterLevelReading,
    ParsedWaterLevelData
)


@pytest.fixture
def parser():
    """Create parser instance."""
    return WaterLevelParser(
        station_name="Waterworks Weir",
        station_id="19102",
        river_name="River Lee"
    )


@pytest.fixture
def sample_level_csv():
    """Sample water level CSV data."""
    return b"""2025-12-06 14:30:00,1.590
2025-12-06 14:15:00,1.585
2025-12-06 14:00:00,1.580
2025-12-06 13:45:00,1.575
2025-12-06 13:30:00,1.570
"""


@pytest.fixture
def sample_temp_csv():
    """Sample temperature CSV data."""
    return b"""2025-12-06 14:30:00,8.5
2025-12-06 14:15:00,8.4
2025-12-06 14:00:00,8.3
2025-12-06 13:45:00,8.2
2025-12-06 13:30:00,8.1
"""


def test_water_level_reading_creation():
    """Test WaterLevelReading dataclass."""
    timestamp = datetime(2025, 12, 6, 14, 30, 0)
    reading = WaterLevelReading(
        timestamp=timestamp,
        water_level_m=1.59,
        temperature_c=8.5
    )

    assert reading.timestamp == timestamp
    assert reading.water_level_m == 1.59
    assert reading.temperature_c == 8.5


def test_water_level_reading_to_dict():
    """Test WaterLevelReading to_dict conversion."""
    timestamp = datetime(2025, 12, 6, 14, 30, 0)
    reading = WaterLevelReading(
        timestamp=timestamp,
        water_level_m=1.59,
        temperature_c=8.5
    )

    data = reading.to_dict()

    assert "timestamp" in data
    assert "water_level_m" in data
    assert "temperature_c" in data
    assert data["water_level_m"] == 1.59
    assert data["temperature_c"] == 8.5


def test_water_level_reading_with_null_values():
    """Test WaterLevelReading with None values."""
    timestamp = datetime(2025, 12, 6, 14, 30, 0)
    reading = WaterLevelReading(
        timestamp=timestamp,
        water_level_m=1.59,
        temperature_c=None
    )

    assert reading.water_level_m == 1.59
    assert reading.temperature_c is None

    data = reading.to_dict()
    assert data["temperature_c"] is None


def test_parse_csv(parser, sample_level_csv):
    """Test CSV parsing."""
    readings = parser._parse_csv(sample_level_csv)

    assert len(readings) == 5
    # Should be sorted descending by timestamp
    assert readings[0][0] > readings[1][0]

    # Check first reading
    timestamp, value = readings[0]
    assert timestamp == datetime(2025, 12, 6, 14, 30, 0)
    assert value == 1.590


def test_parse_csv_with_empty_values(parser):
    """Test CSV parsing with empty values."""
    csv_data = b"""2025-12-06 14:30:00,1.590
2025-12-06 14:15:00,
2025-12-06 14:00:00,1.580
"""

    readings = parser._parse_csv(csv_data)

    assert len(readings) == 3
    # Empty value should be None
    assert readings[1][1] is None


def test_parse_csv_with_invalid_rows(parser):
    """Test CSV parsing skips invalid rows."""
    csv_data = b"""timestamp,value
2025-12-06 14:30:00,1.590
invalid-row
2025-12-06 14:00:00,1.580
2025-12-06 13:45:00,invalid-value
"""

    readings = parser._parse_csv(csv_data)

    # Should only get 2 valid readings
    assert len(readings) == 2
    assert readings[0][1] == 1.590
    assert readings[1][1] == 1.580


def test_combine_readings(parser):
    """Test combining level and temperature readings."""
    level_readings = [
        (datetime(2025, 12, 6, 14, 30, 0), 1.59),
        (datetime(2025, 12, 6, 14, 15, 0), 1.58),
        (datetime(2025, 12, 6, 14, 0, 0), 1.57),
    ]

    temp_readings = [
        (datetime(2025, 12, 6, 14, 30, 0), 8.5),
        (datetime(2025, 12, 6, 14, 15, 0), 8.4),
        (datetime(2025, 12, 6, 14, 0, 0), 8.3),
    ]

    combined = parser._combine_readings(level_readings, temp_readings)

    assert len(combined) == 3
    assert combined[0].water_level_m == 1.59
    assert combined[0].temperature_c == 8.5
    assert combined[1].water_level_m == 1.58
    assert combined[1].temperature_c == 8.4


def test_combine_readings_missing_temperature(parser):
    """Test combining when temperature is missing."""
    level_readings = [
        (datetime(2025, 12, 6, 14, 30, 0), 1.59),
        (datetime(2025, 12, 6, 14, 15, 0), 1.58),
    ]

    temp_readings = [
        (datetime(2025, 12, 6, 14, 30, 0), 8.5),
        # Missing 14:15
    ]

    combined = parser._combine_readings(level_readings, temp_readings)

    assert len(combined) == 2
    assert combined[0].water_level_m == 1.59
    assert combined[0].temperature_c == 8.5
    assert combined[1].water_level_m == 1.58
    assert combined[1].temperature_c is None  # No matching temp


def test_find_matching_temp_exact_match(parser):
    """Test finding temperature with exact timestamp match."""
    temp_dict = {
        datetime(2025, 12, 6, 14, 30, 0): 8.5,
        datetime(2025, 12, 6, 14, 15, 0): 8.4,
    }

    temp = parser._find_matching_temp(datetime(2025, 12, 6, 14, 30, 0), temp_dict)
    assert temp == 8.5


def test_find_matching_temp_within_window(parser):
    """Test finding temperature within 5-minute window."""
    temp_dict = {
        datetime(2025, 12, 6, 14, 30, 0): 8.5,
    }

    # 2 minutes after - should match
    temp = parser._find_matching_temp(datetime(2025, 12, 6, 14, 32, 0), temp_dict)
    assert temp == 8.5


def test_find_matching_temp_outside_window(parser):
    """Test that temperature outside 5-minute window returns None."""
    temp_dict = {
        datetime(2025, 12, 6, 14, 30, 0): 8.5,
    }

    # 10 minutes after - should not match
    temp = parser._find_matching_temp(datetime(2025, 12, 6, 14, 40, 0), temp_dict)
    assert temp is None


def test_find_matching_temp_no_data(parser):
    """Test finding temperature with empty dict."""
    temp = parser._find_matching_temp(datetime(2025, 12, 6, 14, 30, 0), {})
    assert temp is None


def test_parse_full(parser, sample_level_csv, sample_temp_csv):
    """Test full parse with both CSVs."""
    parsed_data = parser.parse(sample_level_csv, sample_temp_csv)

    assert isinstance(parsed_data, ParsedWaterLevelData)
    assert parsed_data.station == "Waterworks Weir"
    assert parsed_data.station_id == "19102"
    assert parsed_data.river == "River Lee"

    # Check current reading (most recent)
    assert parsed_data.current_reading.water_level_m == 1.590
    assert parsed_data.current_reading.temperature_c == 8.5

    # Check historical readings
    assert len(parsed_data.historical_readings) == 4
    assert parsed_data.historical_readings[0].water_level_m == 1.585


def test_parse_with_source_hash(parser, sample_level_csv, sample_temp_csv):
    """Test parse with source hash."""
    source_hash = "abc123def456"
    parsed_data = parser.parse(sample_level_csv, sample_temp_csv, source_hash=source_hash)

    assert parsed_data.source_hash == source_hash


def test_parsed_data_to_dict(parser, sample_level_csv, sample_temp_csv):
    """Test ParsedWaterLevelData to_dict conversion."""
    parsed_data = parser.parse(sample_level_csv, sample_temp_csv)
    data = parsed_data.to_dict()

    assert "station" in data
    assert "station_id" in data
    assert "river" in data
    assert "current_reading" in data
    assert "historical_readings" in data
    assert "reading_count" in data
    assert "parsed_at" in data

    assert data["station"] == "Waterworks Weir"
    assert data["station_id"] == "19102"
    assert data["reading_count"] == 4


def test_parse_empty_csv_raises_error(parser):
    """Test that empty CSV data raises ValueError."""
    empty_csv = b""

    with pytest.raises(ValueError, match="No valid readings found"):
        parser.parse(empty_csv, empty_csv)


def test_parse_invalid_csv_raises_error(parser):
    """Test that completely invalid CSV raises ValueError."""
    invalid_csv = b"completely invalid data\nno valid rows\n"

    with pytest.raises(ValueError, match="No valid readings found"):
        parser.parse(invalid_csv, invalid_csv)


def test_parser_initialization():
    """Test parser initialization with custom values."""
    parser = WaterLevelParser(
        station_name="Test Station",
        station_id="12345",
        river_name="Test River"
    )

    assert parser.station_name == "Test Station"
    assert parser.station_id == "12345"
    assert parser.river_name == "Test River"


def test_parser_default_initialization():
    """Test parser initialization with defaults."""
    parser = WaterLevelParser()

    assert parser.station_name == "Waterworks Weir"
    assert parser.station_id == "19102"
    assert parser.river_name == "River Lee"
