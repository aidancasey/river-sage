#!/usr/bin/env python3
"""
Backfill historical data from raw PDF files stored in S3.

This script reads all raw PDFs for a station, parses them, and rebuilds
the monthly historical data files with all readings merged together.
"""

import boto3
import gzip
import json
import io
from datetime import datetime
from collections import defaultdict
import sys
import os
import pdfplumber
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class FlowReading:
    """Single flow rate reading."""
    timestamp: datetime
    flow_rate_m3s: float
    units: str = "cubic meters per second"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat() + "Z",
            "flow_rate_m3s": self.flow_rate_m3s,
            "units": self.units
        }


class SimpleESBParser:
    """Simple PDF parser for ESB Hydro flow PDFs."""

    def __init__(self, station_name: str, river_name: str):
        self.station_name = station_name
        self.river_name = river_name

    def parse(self, pdf_content: bytes):
        """Parse PDF and extract flow readings."""
        pdf_file = io.BytesIO(pdf_content)
        with pdfplumber.open(pdf_file) as pdf:
            if len(pdf.pages) < 2:
                raise ValueError(f"Expected 2 pages, found {len(pdf.pages)}")

            # Extract current reading from page 1
            current_reading = self._parse_current_reading(pdf.pages[0])

            # Extract historical readings from page 2
            historical_readings = self._parse_historical_readings(pdf.pages[1])

            return type('ParsedData', (), {
                'station': self.station_name,
                'river': self.river_name,
                'current_reading': current_reading,
                'historical_readings': historical_readings
            })()

    def _parse_current_reading(self, page) -> FlowReading:
        tables = page.extract_tables()
        if not tables:
            raise ValueError("No tables found on page 1")

        row = tables[0][0]
        if len(row) < 3:
            raise ValueError(f"Invalid row format: {row}")

        timestamp = self._parse_timestamp(row[0].strip())
        flow_rate = float(row[1].strip())

        return FlowReading(timestamp=timestamp, flow_rate_m3s=flow_rate)

    def _parse_historical_readings(self, page) -> List[FlowReading]:
        tables = page.extract_tables()
        if not tables:
            raise ValueError("No tables found on page 2")

        table = tables[0]
        readings = []

        for row in table[2:]:  # Skip title and header rows
            if not row or len(row) < 3:
                continue
            if not all([row[0], row[1], row[2]]):
                continue

            try:
                timestamp = self._parse_timestamp(row[0].strip())
                flow_rate = float(row[1].strip())
                readings.append(FlowReading(timestamp=timestamp, flow_rate_m3s=flow_rate))
            except (ValueError, AttributeError):
                continue

        return readings

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        dt = datetime.strptime(timestamp_str, "%d-%b-%y %H:%M:%S")
        if dt.year < 1970:
            dt = dt.replace(year=dt.year + 2000)
        return dt


def backfill_station(bucket_name: str, station_id: str, station_name: str, river_name: str):
    """Backfill historical data for a single station."""
    s3 = boto3.client('s3', region_name='eu-west-1')
    parser = SimpleESBParser(station_name=station_name, river_name=river_name)

    # List all raw PDFs for this station
    prefix = f'raw/{station_id}/'
    print(f"Listing PDFs in s3://{bucket_name}/{prefix}")

    paginator = s3.get_paginator('list_objects_v2')
    pdf_keys = []

    for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
        for obj in page.get('Contents', []):
            if obj['Key'].endswith('.pdf'):
                pdf_keys.append(obj['Key'])

    print(f"Found {len(pdf_keys)} PDF files")

    # Group readings by month
    monthly_readings = defaultdict(dict)  # {year_month: {timestamp: reading}}

    # Process each PDF
    for i, s3_key in enumerate(sorted(pdf_keys)):
        try:
            print(f"Processing ({i+1}/{len(pdf_keys)}): {s3_key}")

            # Download PDF
            response = s3.get_object(Bucket=bucket_name, Key=s3_key)
            pdf_content = response['Body'].read()

            # Parse PDF
            parsed_data = parser.parse(pdf_content)

            # Add all readings to appropriate month
            for reading in parsed_data.historical_readings:
                timestamp = reading.timestamp
                year_month = timestamp.strftime("%Y%m")
                timestamp_str = reading.to_dict()['timestamp']

                # Store reading (deduplicates by timestamp)
                monthly_readings[year_month][timestamp_str] = reading.to_dict()

            # Also add current reading
            current = parsed_data.current_reading
            year_month = current.timestamp.strftime("%Y%m")
            timestamp_str = current.to_dict()['timestamp']
            monthly_readings[year_month][timestamp_str] = current.to_dict()

        except Exception as e:
            print(f"  Error processing {s3_key}: {e}")
            continue

    # Write monthly files
    for year_month, readings_dict in sorted(monthly_readings.items()):
        # Sort readings by timestamp (newest first)
        all_readings = sorted(
            readings_dict.values(),
            key=lambda x: x['timestamp'],
            reverse=True
        )

        # Get station/river from last parsed data
        year = int(year_month[:4])
        month = int(year_month[4:])

        # Build the data structure
        data = {
            "station": station_name,
            "river": river_name,
            "current_reading": all_readings[0] if all_readings else None,
            "historical_readings": all_readings,
            "reading_count": len(all_readings),
            "parsed_at": datetime.utcnow().isoformat() + "Z",
            "source_hash": "backfill"
        }

        # Upload to S3
        s3_key = f'parsed/{station_id}/{year}/{month:02d}/{station_id}_flow_{year_month}.json.gz'

        json_str = json.dumps(data, indent=2)
        json_bytes = gzip.compress(json_str.encode('utf-8'))

        s3.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=json_bytes,
            ContentType='application/json',
            ContentEncoding='gzip'
        )

        print(f"Uploaded {s3_key} with {len(all_readings)} readings")

    print(f"\nBackfill complete for {station_id}")
    return monthly_readings


def backfill_water_level_station(bucket_name: str, station_id: str, station_name: str, river_name: str):
    """Backfill historical water level data from CSV files."""
    s3 = boto3.client('s3', region_name='eu-west-1')

    # List all raw CSVs for this station
    prefix = f'raw/{station_id}/'
    print(f"Listing CSVs in s3://{bucket_name}/{prefix}")

    paginator = s3.get_paginator('list_objects_v2')
    level_files = []
    temp_files = []

    for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
        for obj in page.get('Contents', []):
            key = obj['Key']
            if '_level_' in key and key.endswith('.csv'):
                level_files.append(key)
            elif '_temperature_' in key and key.endswith('.csv'):
                temp_files.append(key)

    print(f"Found {len(level_files)} level files and {len(temp_files)} temperature files")

    # Group readings by month
    monthly_readings = defaultdict(dict)  # {year_month: {timestamp: reading}}

    # Process each level CSV and find matching temperature CSV
    for i, level_key in enumerate(sorted(level_files)):
        try:
            print(f"Processing ({i+1}/{len(level_files)}): {level_key}")

            # Download level CSV
            response = s3.get_object(Bucket=bucket_name, Key=level_key)
            level_csv = response['Body'].read()

            # Find matching temperature file
            # Convert lee_waterworks_level_20251206_213000.csv to lee_waterworks_temperature_20251206_213000.csv
            temp_key = level_key.replace('_level_', '_temperature_')
            temp_csv = None
            if temp_key in temp_files:
                try:
                    response = s3.get_object(Bucket=bucket_name, Key=temp_key)
                    temp_csv = response['Body'].read()
                except:
                    pass

            # Parse level CSV
            level_readings = parse_csv(level_csv)

            # Parse temperature CSV if available
            temp_readings = parse_csv(temp_csv) if temp_csv else {}

            # Combine readings
            for timestamp, level in level_readings.items():
                year_month = timestamp.strftime("%Y%m")

                # Find matching temperature (within 2 hours)
                temp = find_matching_temp(timestamp, temp_readings)

                reading = {
                    "timestamp": timestamp.isoformat() + "Z",
                    "water_level_m": level,
                    "temperature_c": temp
                }

                # Store (deduplicates by timestamp)
                monthly_readings[year_month][reading['timestamp']] = reading

        except Exception as e:
            print(f"  Error processing {level_key}: {e}")
            continue

    # Write monthly files
    for year_month, readings_dict in sorted(monthly_readings.items()):
        # Sort readings by timestamp (newest first)
        all_readings = sorted(
            readings_dict.values(),
            key=lambda x: x['timestamp'],
            reverse=True
        )

        year = int(year_month[:4])
        month = int(year_month[4:])

        # Build the data structure
        data = {
            "station": station_name,
            "station_id": station_id,
            "river": river_name,
            "current_reading": all_readings[0] if all_readings else None,
            "historical_readings": all_readings,
            "reading_count": len(all_readings),
            "parsed_at": datetime.utcnow().isoformat() + "Z",
            "source_hash": "backfill"
        }

        # Upload to S3
        s3_key = f'parsed/{station_id}/{year}/{month:02d}/{station_id}_flow_{year_month}.json.gz'

        json_str = json.dumps(data, indent=2)
        json_bytes = gzip.compress(json_str.encode('utf-8'))

        s3.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=json_bytes,
            ContentType='application/json',
            ContentEncoding='gzip'
        )

        print(f"Uploaded {s3_key} with {len(all_readings)} readings")

    print(f"\nBackfill complete for {station_id}")


def parse_csv(csv_content: bytes) -> Dict[datetime, float]:
    """Parse CSV content into dict of timestamp -> value."""
    readings = {}

    if not csv_content:
        return readings

    try:
        text = csv_content.decode('utf-8')
    except UnicodeDecodeError:
        text = csv_content.decode('latin-1')

    import csv as csv_module
    reader = csv_module.reader(io.StringIO(text))

    for row in reader:
        if len(row) < 2:
            continue
        try:
            timestamp_str = row[0].strip()
            value_str = row[1].strip()

            # Try with seconds first, then without
            try:
                timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M")

            value = float(value_str) if value_str else None
            if value is not None:
                readings[timestamp] = value
        except (ValueError, IndexError):
            continue

    return readings


def find_matching_temp(timestamp: datetime, temp_dict: Dict[datetime, float]) -> Optional[float]:
    """Find temperature reading within 2 hours of timestamp."""
    if timestamp in temp_dict:
        return temp_dict[timestamp]

    best_temp = None
    best_diff = float('inf')

    for temp_ts, temp_val in temp_dict.items():
        diff = abs((timestamp - temp_ts).total_seconds())
        if diff <= 7200 and diff < best_diff:  # 2 hours
            best_temp = temp_val
            best_diff = diff

    return best_temp


def main():
    bucket_name = 'river-data-ireland-prod'

    # Backfill Inniscarra (River Lee) - flow data from PDFs
    print("=" * 60)
    print("Backfilling Inniscarra Dam (River Lee) - Flow Data")
    print("=" * 60)
    backfill_station(
        bucket_name=bucket_name,
        station_id='inniscarra',
        station_name='Inniscarra Dam',
        river_name='River Lee'
    )

    # Backfill Lee Waterworks (River Lee) - water level from CSVs
    print("\n" + "=" * 60)
    print("Backfilling Lee Waterworks (River Lee) - Water Level Data")
    print("=" * 60)
    backfill_water_level_station(
        bucket_name=bucket_name,
        station_id='lee_waterworks',
        station_name='Waterworks Weir',
        river_name='River Lee'
    )


if __name__ == '__main__':
    main()
