"""
S3 storage handler for river data.

Manages uploading raw PDFs, parsed JSON data, and aggregated data to S3.
"""

import json
import gzip
from datetime import datetime
from typing import Optional, Dict, Any
import boto3
from botocore.exceptions import ClientError

from ..config.settings import S3Config
from ..parsers.esb_hydro_parser import ParsedFlowData
from ..parsers.waterlevel_parser import ParsedWaterLevelData
from ..utils.logger import StructuredLogger

logger = StructuredLogger(__name__)


class S3Storage:
    """
    S3 storage handler for river flow data.

    Handles three types of storage:
    1. Raw PDFs - Original downloaded files
    2. Parsed JSON - Extracted flow data
    3. Aggregated - Latest readings and daily summaries

    Example:
        >>> config = S3Config(bucket_name="river-data-ireland")
        >>> storage = S3Storage(config)
        >>> storage.upload_raw_pdf(content, "inniscarra", datetime.now())
    """

    def __init__(self, config: S3Config, s3_client=None):
        """
        Initialize S3 storage handler.

        Args:
            config: S3 configuration
            s3_client: Optional boto3 S3 client (for testing)
        """
        self.config = config
        self.s3 = s3_client or boto3.client('s3', region_name=config.region)

        logger.info(
            "S3 storage initialized",
            bucket=config.bucket_name,
            region=config.region
        )

    def upload_raw_pdf(
        self,
        content: bytes,
        station_id: str,
        timestamp: datetime,
        content_hash: str
    ) -> str:
        """
        Upload raw PDF to S3.

        Uploads to: raw/{station_id}/YYYY/MM/DD/{station_id}_flow_{YYYYMMDD_HHMMSS}.pdf

        Args:
            content: PDF file content
            station_id: Station identifier
            timestamp: Timestamp of the data
            content_hash: SHA-256 hash of content

        Returns:
            S3 key of uploaded file

        Raises:
            ClientError: If upload fails
        """
        # Generate filename
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
        filename = f"{station_id}_flow_{timestamp_str}.pdf"

        # Generate S3 key
        s3_key = self.config.get_raw_key(
            station_id=station_id,
            timestamp=timestamp_str,
            filename=filename
        )

        try:
            logger.info(
                "Uploading raw PDF to S3",
                station_id=station_id,
                s3_key=s3_key,
                size_bytes=len(content),
                hash=content_hash[:8] + "..."
            )

            # Prepare put_object kwargs
            put_kwargs = {
                'Bucket': self.config.bucket_name,
                'Key': s3_key,
                'Body': content,
                'ContentType': 'application/pdf',
                'StorageClass': self.config.storage_class,
                'Metadata': {
                    'station-id': station_id,
                    'timestamp': timestamp.isoformat(),
                    'content-hash': content_hash
                }
            }

            # Only add encryption if enabled
            if self.config.enable_encryption:
                put_kwargs['ServerSideEncryption'] = 'AES256'

            # Upload to S3
            self.s3.put_object(**put_kwargs)

            logger.info(
                "Raw PDF uploaded successfully",
                station_id=station_id,
                s3_key=s3_key
            )

            return s3_key

        except ClientError as e:
            logger.error(
                "Failed to upload raw PDF",
                station_id=station_id,
                s3_key=s3_key,
                error=str(e),
                exc_info=True
            )
            raise

    def upload_raw_csv(
        self,
        content: bytes,
        station_id: str,
        timestamp: datetime,
        sensor_type: str,
        content_hash: str
    ) -> str:
        """
        Upload raw CSV data to S3.

        Uploads to: raw/{station_id}/YYYY/MM/DD/{station_id}_{sensor_type}_{YYYYMMDD_HHMMSS}.csv

        Args:
            content: CSV file content
            station_id: Station identifier
            timestamp: Timestamp of the data
            sensor_type: Type of sensor (e.g., "level", "temperature")
            content_hash: SHA-256 hash of content

        Returns:
            S3 key of uploaded file

        Raises:
            ClientError: If upload fails
        """
        # Generate filename
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
        filename = f"{station_id}_{sensor_type}_{timestamp_str}.csv"

        # Generate S3 key
        s3_key = self.config.get_raw_key(
            station_id=station_id,
            timestamp=timestamp_str,
            filename=filename
        )

        try:
            logger.info(
                "Uploading raw CSV to S3",
                station_id=station_id,
                sensor_type=sensor_type,
                s3_key=s3_key,
                size_bytes=len(content),
                hash=content_hash[:8] + "..."
            )

            # Prepare put_object kwargs
            put_kwargs = {
                'Bucket': self.config.bucket_name,
                'Key': s3_key,
                'Body': content,
                'ContentType': 'text/csv',
                'StorageClass': self.config.storage_class,
                'Metadata': {
                    'station-id': station_id,
                    'sensor-type': sensor_type,
                    'timestamp': timestamp.isoformat(),
                    'content-hash': content_hash
                }
            }

            # Only add encryption if enabled
            if self.config.enable_encryption:
                put_kwargs['ServerSideEncryption'] = 'AES256'

            # Upload to S3
            self.s3.put_object(**put_kwargs)

            logger.info(
                "Raw CSV uploaded successfully",
                station_id=station_id,
                sensor_type=sensor_type,
                s3_key=s3_key
            )

            return s3_key

        except ClientError as e:
            logger.error(
                "Failed to upload raw CSV",
                station_id=station_id,
                sensor_type=sensor_type,
                s3_key=s3_key,
                error=str(e),
                exc_info=True
            )
            raise

    def upload_parsed_json(
        self,
        parsed_data,  # ParsedFlowData or ParsedWaterLevelData
        station_id: str,
        compress: bool = True
    ) -> str:
        """
        Upload parsed flow data as JSON to S3.

        Uploads to: parsed/{station_id}/YYYY/MM/{station_id}_flow_{YYYYMM}.json.gz

        Args:
            parsed_data: Parsed flow data
            station_id: Station identifier
            compress: Whether to gzip compress (default True)

        Returns:
            S3 key of uploaded file

        Raises:
            ClientError: If upload fails
        """
        # Generate key for current month
        year_month = parsed_data.current_reading.timestamp.strftime("%Y%m")
        s3_key = self.config.get_parsed_key(station_id, year_month)

        # Add .gz extension if compressing
        if compress:
            s3_key += ".gz"

        try:
            logger.info(
                "Uploading parsed JSON to S3",
                station_id=station_id,
                s3_key=s3_key,
                compress=compress
            )

            # Convert to JSON
            json_data = parsed_data.to_dict()
            json_str = json.dumps(json_data, indent=2)
            json_bytes = json_str.encode('utf-8')

            # Compress if requested
            if compress:
                json_bytes = gzip.compress(json_bytes)

            # Prepare put_object kwargs
            put_kwargs = {
                'Bucket': self.config.bucket_name,
                'Key': s3_key,
                'Body': json_bytes,
                'ContentType': 'application/json',
                'StorageClass': self.config.storage_class,
                'Metadata': {
                    'station-id': station_id,
                    'timestamp': parsed_data.current_reading.timestamp.isoformat(),
                    'reading-count': str(len(parsed_data.historical_readings))
                }
            }

            # Only add ContentEncoding if compressing
            if compress:
                put_kwargs['ContentEncoding'] = 'gzip'

            # Only add encryption if enabled
            if self.config.enable_encryption:
                put_kwargs['ServerSideEncryption'] = 'AES256'

            # Upload to S3
            self.s3.put_object(**put_kwargs)

            logger.info(
                "Parsed JSON uploaded successfully",
                station_id=station_id,
                s3_key=s3_key,
                size_bytes=len(json_bytes)
            )

            return s3_key

        except ClientError as e:
            logger.error(
                "Failed to upload parsed JSON",
                station_id=station_id,
                s3_key=s3_key,
                error=str(e),
                exc_info=True
            )
            raise

    def update_latest_aggregated(
        self,
        parsed_data,  # ParsedFlowData or ParsedWaterLevelData
        station_id: str
    ) -> str:
        """
        Update latest aggregated data file.

        This file contains the most recent reading and is updated every hour.
        Uploads to: aggregated/{station_id}_latest.json

        Args:
            parsed_data: Parsed flow or water level data
            station_id: Station identifier

        Returns:
            S3 key of uploaded file

        Raises:
            ClientError: If upload fails
        """
        s3_key = self.config.get_latest_key(station_id)

        try:
            logger.info(
                "Updating latest aggregated data",
                station_id=station_id,
                s3_key=s3_key
            )

            # Create aggregated data structure
            aggregated = {
                "station": parsed_data.station,
                "river": parsed_data.river,
                "latest_reading": parsed_data.current_reading.to_dict(),
                "statistics": {
                    "historical_readings": len(parsed_data.historical_readings),
                    "time_range_hours": 24
                },
                "updated_at": datetime.utcnow().isoformat() + "Z",
                "source_hash": parsed_data.source_hash
            }

            # Add type-specific statistics
            if hasattr(parsed_data.current_reading, 'flow_rate_m3s'):
                aggregated["statistics"]["current_flow_m3s"] = parsed_data.current_reading.flow_rate_m3s
            if hasattr(parsed_data.current_reading, 'water_level_m'):
                aggregated["statistics"]["current_water_level_m"] = parsed_data.current_reading.water_level_m
            if hasattr(parsed_data.current_reading, 'temperature_c'):
                aggregated["statistics"]["current_temperature_c"] = parsed_data.current_reading.temperature_c

            # Convert to JSON
            json_str = json.dumps(aggregated, indent=2)
            json_bytes = json_str.encode('utf-8')

            # Build metadata dict
            metadata = {
                'station-id': station_id,
                'timestamp': parsed_data.current_reading.timestamp.isoformat()
            }
            if hasattr(parsed_data.current_reading, 'flow_rate_m3s'):
                metadata['flow-rate'] = str(parsed_data.current_reading.flow_rate_m3s)
            if hasattr(parsed_data.current_reading, 'water_level_m'):
                metadata['water-level'] = str(parsed_data.current_reading.water_level_m)
            if hasattr(parsed_data.current_reading, 'temperature_c'):
                metadata['temperature'] = str(parsed_data.current_reading.temperature_c)

            # Prepare put_object kwargs
            put_kwargs = {
                'Bucket': self.config.bucket_name,
                'Key': s3_key,
                'Body': json_bytes,
                'ContentType': 'application/json',
                'CacheControl': 'max-age=1800',  # Cache for 30 minutes
                'StorageClass': 'STANDARD',  # Always standard for frequently accessed
                'Metadata': metadata
            }

            # Only add encryption if enabled
            if self.config.enable_encryption:
                put_kwargs['ServerSideEncryption'] = 'AES256'

            # Upload to S3
            self.s3.put_object(**put_kwargs)

            logger.info(
                "Latest aggregated data updated",
                station_id=station_id,
                s3_key=s3_key
            )

            return s3_key

        except ClientError as e:
            logger.error(
                "Failed to update latest aggregated data",
                station_id=station_id,
                s3_key=s3_key,
                error=str(e),
                exc_info=True
            )
            raise

    def upload_daily_summary(
        self,
        station_id: str,
        date: datetime,
        summary_data: Dict[str, Any]
    ) -> str:
        """
        Upload daily summary statistics.

        Uploads to: aggregated/{station_id}_daily_{YYYYMMDD}.json

        Args:
            station_id: Station identifier
            date: Date for the summary
            summary_data: Dictionary with daily statistics

        Returns:
            S3 key of uploaded file

        Raises:
            ClientError: If upload fails
        """
        date_str = date.strftime("%Y%m%d")
        s3_key = f"{self.config.aggregated_prefix}/{station_id}_daily_{date_str}.json"

        try:
            logger.info(
                "Uploading daily summary",
                station_id=station_id,
                date=date_str,
                s3_key=s3_key
            )

            # Convert to JSON
            json_str = json.dumps(summary_data, indent=2)
            json_bytes = json_str.encode('utf-8')

            # Prepare put_object kwargs
            put_kwargs = {
                'Bucket': self.config.bucket_name,
                'Key': s3_key,
                'Body': json_bytes,
                'ContentType': 'application/json',
                'StorageClass': self.config.storage_class
            }

            # Only add encryption if enabled
            if self.config.enable_encryption:
                put_kwargs['ServerSideEncryption'] = 'AES256'

            # Upload to S3
            self.s3.put_object(**put_kwargs)

            logger.info(
                "Daily summary uploaded",
                station_id=station_id,
                s3_key=s3_key
            )

            return s3_key

        except ClientError as e:
            logger.error(
                "Failed to upload daily summary",
                station_id=station_id,
                s3_key=s3_key,
                error=str(e),
                exc_info=True
            )
            raise

    def get_latest_reading(self, station_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve latest reading from S3.

        Args:
            station_id: Station identifier

        Returns:
            Latest reading data or None if not found

        Raises:
            ClientError: If retrieval fails (other than not found)
        """
        s3_key = self.config.get_latest_key(station_id)

        try:
            logger.debug(
                "Retrieving latest reading",
                station_id=station_id,
                s3_key=s3_key
            )

            response = self.s3.get_object(
                Bucket=self.config.bucket_name,
                Key=s3_key
            )

            content = response['Body'].read()
            data = json.loads(content)

            logger.debug(
                "Latest reading retrieved",
                station_id=station_id
            )

            return data

        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.debug(
                    "No latest reading found",
                    station_id=station_id
                )
                return None
            else:
                logger.error(
                    "Failed to retrieve latest reading",
                    station_id=station_id,
                    error=str(e),
                    exc_info=True
                )
                raise

    def list_historical_files(
        self,
        station_id: str,
        prefix_type: str = "parsed",
        max_files: int = 100
    ) -> list:
        """
        List historical files for a station.

        Args:
            station_id: Station identifier
            prefix_type: Type of files (raw, parsed, aggregated)
            max_files: Maximum number of files to return

        Returns:
            List of S3 keys

        Raises:
            ClientError: If listing fails
        """
        prefix = f"{prefix_type}/{station_id}/"

        try:
            logger.debug(
                "Listing historical files",
                station_id=station_id,
                prefix=prefix
            )

            response = self.s3.list_objects_v2(
                Bucket=self.config.bucket_name,
                Prefix=prefix,
                MaxKeys=max_files
            )

            if 'Contents' not in response:
                return []

            keys = [obj['Key'] for obj in response['Contents']]

            logger.debug(
                "Listed historical files",
                station_id=station_id,
                count=len(keys)
            )

            return keys

        except ClientError as e:
            logger.error(
                "Failed to list historical files",
                station_id=station_id,
                error=str(e),
                exc_info=True
            )
            raise

    def check_bucket_exists(self) -> bool:
        """
        Check if the configured S3 bucket exists.

        Returns:
            True if bucket exists, False otherwise
        """
        try:
            self.s3.head_bucket(Bucket=self.config.bucket_name)
            return True
        except ClientError:
            return False
