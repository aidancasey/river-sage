"""
Parser for ESB Hydro flow PDF documents.

Extracts flow rate data from ESB Hydro PDF reports for Inniscarra station.
"""

import io
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import pdfplumber

from ..utils.logger import StructuredLogger

logger = StructuredLogger(__name__)


@dataclass
class FlowReading:
    """Single flow rate reading."""
    timestamp: datetime
    flow_rate_m3s: float
    units: str = "cubic meters per second"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat() + "Z",
            "flow_rate_m3s": self.flow_rate_m3s,
            "units": self.units
        }


@dataclass
class ParsedFlowData:
    """Parsed flow data from PDF."""
    station: str
    river: str
    current_reading: FlowReading
    historical_readings: List[FlowReading]
    parsed_at: datetime
    source_hash: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "station": self.station,
            "river": self.river,
            "current_reading": self.current_reading.to_dict(),
            "historical_readings": [r.to_dict() for r in self.historical_readings],
            "reading_count": len(self.historical_readings),
            "parsed_at": self.parsed_at.isoformat() + "Z",
            "source_hash": self.source_hash
        }


class ESBHydroFlowParser:
    """
    Parser for ESB Hydro flow PDF documents.

    Extracts flow rate data from the Inniscarra Flow PDF published by ESB Hydro.
    The PDF contains:
    - Page 1: Current reading and chart
    - Page 2: Table of last 30 hourly readings

    Example:
        >>> parser = ESBHydroFlowParser(
        ...     station_name="Inniscarra",
        ...     river_name="River Lee"
        ... )
        >>> with open("flow.pdf", "rb") as f:
        ...     data = parser.parse(f.read())
        >>> print(data.current_reading.flow_rate_m3s)
        127.0
    """

    def __init__(self, station_name: str = "Inniscarra", river_name: str = "River Lee"):
        """
        Initialize parser.

        Args:
            station_name: Name of the monitoring station
            river_name: Name of the river
        """
        self.station_name = station_name
        self.river_name = river_name

    def parse(self, pdf_content: bytes, source_hash: Optional[str] = None) -> ParsedFlowData:
        """
        Parse PDF content and extract flow data.

        Args:
            pdf_content: PDF file content as bytes
            source_hash: Optional SHA-256 hash of source PDF

        Returns:
            ParsedFlowData with current and historical readings

        Raises:
            ValueError: If PDF cannot be parsed or data is invalid
            Exception: For other parsing errors
        """
        logger.info(
            "Starting PDF parse",
            station=self.station_name,
            size_bytes=len(pdf_content)
        )

        try:
            # Open PDF from bytes
            pdf_file = io.BytesIO(pdf_content)
            with pdfplumber.open(pdf_file) as pdf:
                if len(pdf.pages) < 2:
                    raise ValueError(f"Expected 2 pages, found {len(pdf.pages)}")

                # Extract current reading from page 1
                current_reading = self._parse_current_reading(pdf.pages[0])

                # Extract historical readings from page 2
                historical_readings = self._parse_historical_readings(pdf.pages[1])

                logger.info(
                    "PDF parsed successfully",
                    station=self.station_name,
                    current_flow=current_reading.flow_rate_m3s,
                    historical_count=len(historical_readings)
                )

                return ParsedFlowData(
                    station=self.station_name,
                    river=self.river_name,
                    current_reading=current_reading,
                    historical_readings=historical_readings,
                    parsed_at=datetime.utcnow(),
                    source_hash=source_hash
                )

        except Exception as e:
            logger.error(
                "Failed to parse PDF",
                station=self.station_name,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            raise

    def _parse_current_reading(self, page) -> FlowReading:
        """
        Parse current reading from page 1.

        Page 1 contains:
        - Title: "Current Total Average Hourly Inniscarra Flow"
        - Table with: timestamp, value, units

        Args:
            page: pdfplumber page object

        Returns:
            FlowReading with current data

        Raises:
            ValueError: If data cannot be extracted
        """
        try:
            tables = page.extract_tables()
            if not tables:
                raise ValueError("No tables found on page 1")

            # First table should have current reading
            first_table = tables[0]
            if not first_table or len(first_table) < 1:
                raise ValueError("First table is empty")

            # Table format: [timestamp, value, units]
            row = first_table[0]
            if len(row) < 3:
                raise ValueError(f"Invalid row format: {row}")

            timestamp_str = row[0].strip()
            value_str = row[1].strip()
            units_str = row[2].strip()

            # Parse timestamp: "05-Dec-25 17:00:00"
            timestamp = self._parse_timestamp(timestamp_str)

            # Parse value
            flow_rate = float(value_str)

            logger.debug(
                "Parsed current reading",
                timestamp=timestamp.isoformat(),
                flow_rate=flow_rate,
                units=units_str
            )

            return FlowReading(
                timestamp=timestamp,
                flow_rate_m3s=flow_rate,
                units=units_str
            )

        except Exception as e:
            logger.error(
                "Failed to parse current reading",
                error=str(e),
                exc_info=True
            )
            raise ValueError(f"Failed to parse current reading: {e}")

    def _parse_historical_readings(self, page) -> List[FlowReading]:
        """
        Parse historical readings from page 2.

        Page 2 contains:
        - Title: "Last 30 readings for Total Average Hourly Inniscarra Flow"
        - Table with headers: Timestamp, Value, Units
        - 30 data rows

        Args:
            page: pdfplumber page object

        Returns:
            List of FlowReading objects

        Raises:
            ValueError: If data cannot be extracted
        """
        try:
            tables = page.extract_tables()
            if not tables:
                raise ValueError("No tables found on page 2")

            # First table should have historical data
            table = tables[0]
            if not table or len(table) < 3:  # Header + title + data
                raise ValueError("Table is too small")

            readings = []

            # Skip first row (title) and second row (headers)
            # Process data rows
            for i, row in enumerate(table[2:], start=1):
                if not row or len(row) < 3:
                    continue

                timestamp_str = row[0]
                value_str = row[1]
                units_str = row[2]

                # Skip if any field is None or empty
                if not all([timestamp_str, value_str, units_str]):
                    logger.debug(f"Skipping empty row {i}")
                    continue

                try:
                    timestamp = self._parse_timestamp(timestamp_str.strip())
                    flow_rate = float(value_str.strip())

                    readings.append(FlowReading(
                        timestamp=timestamp,
                        flow_rate_m3s=flow_rate,
                        units=units_str.strip()
                    ))

                except (ValueError, AttributeError) as e:
                    logger.warning(
                        f"Skipping invalid row {i}",
                        row=row,
                        error=str(e)
                    )
                    continue

            if not readings:
                raise ValueError("No valid readings found in table")

            logger.debug(
                "Parsed historical readings",
                count=len(readings)
            )

            return readings

        except Exception as e:
            logger.error(
                "Failed to parse historical readings",
                error=str(e),
                exc_info=True
            )
            raise ValueError(f"Failed to parse historical readings: {e}")

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """
        Parse timestamp string to datetime.

        Format: "05-Dec-25 17:00:00"
        Converts to: 2025-12-05 17:00:00

        Args:
            timestamp_str: Timestamp string from PDF

        Returns:
            datetime object

        Raises:
            ValueError: If timestamp cannot be parsed
        """
        try:
            # Parse format: "05-Dec-25 17:00:00"
            dt = datetime.strptime(timestamp_str, "%d-%b-%y %H:%M:%S")

            # Convert 2-digit year to 4-digit
            # Assume 00-50 is 2000-2050, 51-99 is 1951-1999
            if dt.year < 1970:
                dt = dt.replace(year=dt.year + 2000)

            return dt

        except ValueError as e:
            logger.error(
                "Failed to parse timestamp",
                timestamp=timestamp_str,
                error=str(e)
            )
            raise ValueError(f"Invalid timestamp format: {timestamp_str}")

    def get_latest_flow(self, parsed_data: ParsedFlowData) -> float:
        """
        Get the latest flow rate value.

        Args:
            parsed_data: Parsed flow data

        Returns:
            Latest flow rate in m³/s
        """
        return parsed_data.current_reading.flow_rate_m3s

    def get_average_flow(self, parsed_data: ParsedFlowData, hours: int = 24) -> float:
        """
        Calculate average flow rate over specified hours.

        Args:
            parsed_data: Parsed flow data
            hours: Number of hours to average (default 24)

        Returns:
            Average flow rate in m³/s
        """
        # Use the most recent readings up to specified hours
        readings = parsed_data.historical_readings[:hours]

        if not readings:
            return parsed_data.current_reading.flow_rate_m3s

        total = sum(r.flow_rate_m3s for r in readings)
        return total / len(readings)

    def get_flow_statistics(self, parsed_data: ParsedFlowData) -> Dict[str, float]:
        """
        Calculate flow statistics.

        Args:
            parsed_data: Parsed flow data

        Returns:
            Dictionary with min, max, mean, current values
        """
        all_values = [r.flow_rate_m3s for r in parsed_data.historical_readings]

        if not all_values:
            return {
                "current": parsed_data.current_reading.flow_rate_m3s,
                "min": parsed_data.current_reading.flow_rate_m3s,
                "max": parsed_data.current_reading.flow_rate_m3s,
                "mean": parsed_data.current_reading.flow_rate_m3s,
                "count": 1
            }

        return {
            "current": parsed_data.current_reading.flow_rate_m3s,
            "min": min(all_values),
            "max": max(all_values),
            "mean": sum(all_values) / len(all_values),
            "count": len(all_values)
        }
