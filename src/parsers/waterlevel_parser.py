"""
Parser for waterlevel.ie CSV data.

Extracts water level and temperature data from waterlevel.ie API.
Station 19102 is Waterworks Weir on the River Lee.
"""

import csv
import io
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

from ..utils.logger import StructuredLogger

logger = StructuredLogger(__name__)


@dataclass
class WaterLevelReading:
    """Single water level reading with temperature."""
    timestamp: datetime
    water_level_m: Optional[float]  # meters
    temperature_c: Optional[float]  # celsius

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat() + "Z",
            "water_level_m": self.water_level_m,
            "temperature_c": self.temperature_c
        }


@dataclass
class ParsedWaterLevelData:
    """Parsed water level and temperature data."""
    station: str
    station_id: str
    river: str
    current_reading: WaterLevelReading
    historical_readings: List[WaterLevelReading]
    parsed_at: datetime
    source_hash: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "station": self.station,
            "station_id": self.station_id,
            "river": self.river,
            "current_reading": self.current_reading.to_dict(),
            "historical_readings": [r.to_dict() for r in self.historical_readings],
            "reading_count": len(self.historical_readings),
            "parsed_at": self.parsed_at.isoformat() + "Z",
            "source_hash": self.source_hash
        }


class WaterLevelParser:
    """
    Parser for waterlevel.ie CSV data.

    Fetches and parses water level and temperature data from waterlevel.ie API.
    Station 19102 is Waterworks Weir on the River Lee.

    The CSV format from waterlevel.ie is:
        timestamp,value
        2025-12-06 14:30:00,1.590
        2025-12-06 14:15:00,1.585
        ...

    Example:
        >>> parser = WaterLevelParser(
        ...     station_name="Waterworks Weir",
        ...     station_id="19102",
        ...     river_name="River Lee"
        ... )
        >>> data = parser.parse(level_csv, temp_csv)
        >>> print(data.current_reading.water_level_m)
        1.590
    """

    def __init__(
        self,
        station_name: str = "Waterworks Weir",
        station_id: str = "19102",
        river_name: str = "River Lee"
    ):
        """
        Initialize parser.

        Args:
            station_name: Name of the monitoring station
            station_id: Waterlevel.ie station ID
            river_name: Name of the river
        """
        self.station_name = station_name
        self.station_id = station_id
        self.river_name = river_name

    def parse(
        self,
        level_csv: bytes,
        temp_csv: bytes,
        source_hash: Optional[str] = None
    ) -> ParsedWaterLevelData:
        """
        Parse CSV content and extract water level and temperature data.

        Args:
            level_csv: Water level CSV content (sensor 0001)
            temp_csv: Temperature CSV content (sensor 0002)
            source_hash: Optional hash of source data

        Returns:
            ParsedWaterLevelData with current and historical readings

        Raises:
            ValueError: If CSV cannot be parsed or data is invalid
        """
        logger.info(
            f"Parsing water level data for {self.station_name}",
            station=self.station_name,
            station_id=self.station_id
        )

        try:
            # Parse both CSVs
            level_readings = self._parse_csv(level_csv)
            temp_readings = self._parse_csv(temp_csv)

            logger.debug(
                "Parsed CSV files",
                level_count=len(level_readings),
                temp_count=len(temp_readings)
            )

            # Combine readings by timestamp
            combined = self._combine_readings(level_readings, temp_readings)

            if not combined:
                raise ValueError("No valid readings found in CSV data")

            # Most recent reading is current
            current_reading = combined[0]
            historical_readings = combined[1:]  # Rest are historical

            parsed_data = ParsedWaterLevelData(
                station=self.station_name,
                station_id=self.station_id,
                river=self.river_name,
                current_reading=current_reading,
                historical_readings=historical_readings,
                parsed_at=datetime.utcnow(),
                source_hash=source_hash
            )

            logger.info(
                f"Successfully parsed {self.station_name}",
                station_id=self.station_id,
                current_level=current_reading.water_level_m,
                current_temp=current_reading.temperature_c,
                reading_count=len(historical_readings)
            )

            return parsed_data

        except Exception as e:
            logger.error(
                f"Failed to parse water level data for {self.station_name}",
                station_id=self.station_id,
                error=str(e),
                exc_info=True
            )
            raise ValueError(f"Failed to parse CSV data: {e}")

    def _parse_csv(self, csv_content: bytes) -> List[tuple]:
        """
        Parse CSV content into list of (timestamp, value) tuples.

        Args:
            csv_content: CSV file content as bytes

        Returns:
            List of (datetime, float) tuples sorted by timestamp descending
        """
        readings = []

        try:
            text = csv_content.decode('utf-8')
        except UnicodeDecodeError:
            logger.warning("Failed to decode as UTF-8, trying latin-1")
            text = csv_content.decode('latin-1')

        reader = csv.reader(io.StringIO(text))

        for row in reader:
            if len(row) < 2:
                continue

            try:
                # CSV format: timestamp,value
                # Example: 2025-12-06 14:30:00,1.590
                timestamp_str = row[0].strip()
                value_str = row[1].strip()

                # Parse timestamp (waterlevel.ie uses UTC)
                # Try with seconds first, then without
                try:
                    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M")

                # Parse value (may be empty or invalid)
                value = float(value_str) if value_str else None

                readings.append((timestamp, value))

            except (ValueError, IndexError) as e:
                # Skip invalid rows (including header rows)
                logger.debug(f"Skipping invalid CSV row: {row}, error: {e}")
                continue

        # Sort by timestamp descending (most recent first)
        readings.sort(key=lambda x: x[0], reverse=True)

        logger.debug(f"Parsed {len(readings)} readings from CSV")

        return readings

    def _combine_readings(
        self,
        level_readings: List[tuple],
        temp_readings: List[tuple]
    ) -> List[WaterLevelReading]:
        """
        Combine level and temperature readings by timestamp.

        Args:
            level_readings: List of (timestamp, level) tuples
            temp_readings: List of (timestamp, temp) tuples

        Returns:
            List of WaterLevelReading objects sorted by timestamp descending
        """
        # Create lookup dict for temperature readings
        temp_dict = {ts: val for ts, val in temp_readings}

        combined = []

        for timestamp, level in level_readings:
            # Find matching temperature reading (within 5 minutes)
            temp = self._find_matching_temp(timestamp, temp_dict)

            combined.append(WaterLevelReading(
                timestamp=timestamp,
                water_level_m=level,
                temperature_c=temp
            ))

        logger.debug(f"Combined {len(combined)} readings")

        return combined

    def _find_matching_temp(
        self,
        timestamp: datetime,
        temp_dict: Dict[datetime, Optional[float]]
    ) -> Optional[float]:
        """
        Find temperature reading that matches timestamp (within 2 hours).

        Temperature readings are hourly but may lag behind water level readings.
        We use a 2-hour window to ensure we capture the most recent temperature.

        Args:
            timestamp: Target timestamp
            temp_dict: Dictionary of timestamp -> temperature

        Returns:
            Temperature value or None if no match found
        """
        # Exact match
        if timestamp in temp_dict:
            return temp_dict[timestamp]

        # Find closest within 2 hours (temperature readings are hourly and may lag)
        best_temp = None
        best_diff = float('inf')

        for temp_ts, temp_val in temp_dict.items():
            diff = abs((timestamp - temp_ts).total_seconds())
            if diff <= 7200 and diff < best_diff:  # 2 hours
                best_temp = temp_val
                best_diff = diff

        return best_temp
