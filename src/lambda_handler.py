"""
AWS Lambda handler for river data collection.

This is the main entry point for the Lambda function that runs
on a schedule to download and process river data.
"""

import json
from datetime import datetime
from typing import Dict, Any

from .config.settings import Settings, DataSourceType
from .connectors.http_connector import HTTPConnector
from .parsers.esb_hydro_parser import ESBHydroFlowParser
from .parsers.waterlevel_parser import WaterLevelParser
from .storage.s3_storage import S3Storage
from .utils.logger import setup_logging, StructuredLogger
from .utils.retry import retry_with_backoff

logger = StructuredLogger(__name__)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for downloading river data.

    This function is invoked by AWS EventBridge on a schedule.
    It downloads data from all configured sources, processes them,
    and stores the results in S3.

    Args:
        event: Lambda event (from EventBridge scheduler)
        context: Lambda context with runtime information

    Returns:
        Response dictionary with status and details

    Example Event:
        {
            "version": "0",
            "id": "abc-123",
            "detail-type": "Scheduled Event",
            "source": "aws.events",
            "time": "2025-12-01T14:00:00Z"
        }

    Example Response:
        {
            "statusCode": 200,
            "body": {
                "success": true,
                "total_sources": 1,
                "successful": 1,
                "results": [
                    {
                        "station_id": "inniscarra",
                        "success": true,
                        "size_bytes": 12345,
                        "hash": "abc123...",
                        "attempts": 1
                    }
                ],
                "timestamp": "2025-12-01T14:05:23Z"
            }
        }
    """
    request_id = context.request_id if hasattr(context, 'request_id') else 'unknown'

    # Setup logging
    setup_logging()

    logger.info(
        "Lambda invocation started",
        request_id=request_id,
        function_name=context.function_name if hasattr(context, 'function_name') else None,
        event_source=event.get('source'),
        event_time=event.get('time')
    )

    try:
        # Load configuration from environment
        settings = Settings.from_env()

        logger.info(
            "Configuration loaded",
            environment=settings.environment,
            source_count=len(settings.data_sources),
            enabled_sources=len(settings.get_enabled_sources())
        )

        # Process each enabled data source
        results = []
        for source_config in settings.get_enabled_sources():
            try:
                logger.info(
                    f"Processing {source_config.name}",
                    station_id=source_config.station_id,
                    river=source_config.river,
                    url=source_config.url
                )

                # Parse content based on source type
                if source_config.source_type == DataSourceType.PDF:
                    # ESB Hydro PDF parsing
                    with HTTPConnector(settings.connection) as connector:
                        # Download with retry logic
                        def download_fn():
                            return connector.download_file(source_config.url)

                        content, file_hash = retry_with_backoff(
                            download_fn,
                            settings.retry
                        )

                    logger.info(
                        f"Successfully downloaded {source_config.name}",
                        station_id=source_config.station_id,
                        size_bytes=len(content),
                        hash=file_hash[:8] + "..."
                    )

                    parser = ESBHydroFlowParser(
                        station_name=source_config.name,
                        river_name=source_config.river
                    )
                    parsed_data = parser.parse(content, source_hash=file_hash)

                elif source_config.source_type == DataSourceType.API:
                    # Waterlevel.ie CSV parsing
                    # Download both level and temperature CSV
                    level_url = source_config.url.replace("{sensor}", "0001")
                    temp_url = source_config.url.replace("{sensor}", "0002")

                    logger.info(
                        f"Downloading water level data from {source_config.name}",
                        station_id=source_config.station_id,
                        level_url=level_url,
                        temp_url=temp_url
                    )

                    with HTTPConnector(settings.connection) as connector:
                        # Download level CSV
                        def download_level_fn():
                            return connector.download_file(level_url)
                        level_csv, level_hash = retry_with_backoff(
                            download_level_fn,
                            settings.retry
                        )

                        # Download temperature CSV
                        def download_temp_fn():
                            return connector.download_file(temp_url)
                        temp_csv, temp_hash = retry_with_backoff(
                            download_temp_fn,
                            settings.retry
                        )

                    file_hash = f"{level_hash[:16]}+{temp_hash[:16]}"

                    logger.info(
                        f"Successfully downloaded {source_config.name}",
                        station_id=source_config.station_id,
                        level_size_bytes=len(level_csv),
                        temp_size_bytes=len(temp_csv),
                        hash=file_hash
                    )

                    parser = WaterLevelParser(
                        station_name=source_config.name,
                        station_id=source_config.station_id,
                        river_name=source_config.river
                    )
                    parsed_data = parser.parse(level_csv, temp_csv, source_hash=file_hash)

                else:
                    raise ValueError(f"Unsupported source type: {source_config.source_type}")

                # Log parsing success with appropriate metrics
                log_data = {
                    "station_id": source_config.station_id,
                    "reading_count": len(parsed_data.historical_readings)
                }
                if hasattr(parsed_data.current_reading, 'flow_rate_m3s'):
                    log_data["current_flow_m3s"] = parsed_data.current_reading.flow_rate_m3s
                if hasattr(parsed_data.current_reading, 'water_level_m'):
                    log_data["current_level_m"] = parsed_data.current_reading.water_level_m
                if hasattr(parsed_data.current_reading, 'temperature_c'):
                    log_data["current_temp_c"] = parsed_data.current_reading.temperature_c

                logger.info(
                    f"Successfully parsed {source_config.name}",
                    **log_data
                )

                # Upload to S3 (FR3)
                s3_keys = {}
                if settings.s3:
                    storage = S3Storage(settings.s3)

                    # Upload raw data (PDF or CSV)
                    if source_config.source_type == DataSourceType.PDF:
                        raw_key = storage.upload_raw_pdf(
                            content=content,
                            station_id=source_config.station_id,
                            timestamp=parsed_data.current_reading.timestamp,
                            content_hash=file_hash
                        )
                        s3_keys['raw'] = raw_key
                    elif source_config.source_type == DataSourceType.API:
                        # Upload both CSVs as raw data
                        raw_level_key = storage.upload_raw_csv(
                            content=level_csv,
                            station_id=source_config.station_id,
                            timestamp=parsed_data.current_reading.timestamp,
                            sensor_type="level",
                            content_hash=level_hash
                        )
                        raw_temp_key = storage.upload_raw_csv(
                            content=temp_csv,
                            station_id=source_config.station_id,
                            timestamp=parsed_data.current_reading.timestamp,
                            sensor_type="temperature",
                            content_hash=temp_hash
                        )
                        s3_keys['raw_level'] = raw_level_key
                        s3_keys['raw_temp'] = raw_temp_key

                    # Upload parsed JSON
                    parsed_key = storage.upload_parsed_json(
                        parsed_data=parsed_data,
                        station_id=source_config.station_id,
                        compress=True
                    )
                    s3_keys['parsed'] = parsed_key

                    # Update latest aggregated data
                    latest_key = storage.update_latest_aggregated(
                        parsed_data=parsed_data,
                        station_id=source_config.station_id
                    )
                    s3_keys['latest'] = latest_key

                    logger.info(
                        f"Successfully uploaded to S3",
                        station_id=source_config.station_id,
                        s3_keys=list(s3_keys.keys())
                    )
                else:
                    logger.warning(
                        "S3 not configured, skipping upload",
                        station_id=source_config.station_id
                    )

                # Build result dictionary with appropriate fields
                result = {
                    "station_id": source_config.station_id,
                    "success": True,
                    "hash": file_hash,
                    "reading_count": len(parsed_data.historical_readings),
                    "timestamp": parsed_data.current_reading.timestamp.isoformat() + "Z",
                    "s3_keys": s3_keys if settings.s3 else None,
                    "attempts": 1  # TODO: Track actual attempts
                }

                # Add type-specific fields
                if hasattr(parsed_data.current_reading, 'flow_rate_m3s'):
                    result["current_flow_m3s"] = parsed_data.current_reading.flow_rate_m3s
                    result["size_bytes"] = len(content)
                if hasattr(parsed_data.current_reading, 'water_level_m'):
                    result["current_water_level_m"] = parsed_data.current_reading.water_level_m
                if hasattr(parsed_data.current_reading, 'temperature_c'):
                    result["current_temperature_c"] = parsed_data.current_reading.temperature_c

                results.append(result)

            except Exception as e:
                logger.error(
                    f"Failed to process {source_config.name}",
                    station_id=source_config.station_id,
                    error_type=type(e).__name__,
                    error=str(e),
                    exc_info=True
                )

                results.append({
                    "station_id": source_config.station_id,
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__
                })

        # Calculate success metrics
        success_count = sum(1 for r in results if r.get("success", False))
        total_count = len(results)

        response_body = {
            "success": success_count > 0,
            "total_sources": total_count,
            "successful": success_count,
            "failed": total_count - success_count,
            "results": results,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        logger.info(
            "Lambda invocation completed",
            request_id=request_id,
            success_count=success_count,
            total_count=total_count,
            success_rate=f"{(success_count/total_count*100) if total_count > 0 else 0:.1f}%"
        )

        return {
            "statusCode": 200 if success_count > 0 else 500,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps(response_body)
        }

    except Exception as e:
        logger.error(
            "Lambda invocation failed",
            request_id=request_id,
            error_type=type(e).__name__,
            error=str(e),
            exc_info=True
        )

        error_response = {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps(error_response)
        }


# For local testing
if __name__ == "__main__":
    # Mock Lambda context
    class MockContext:
        request_id = "local-test-123"
        function_name = "river-data-collector-local"

    # Mock event
    mock_event = {
        "version": "0",
        "id": "test-event",
        "detail-type": "Scheduled Event",
        "source": "local.test",
        "time": datetime.utcnow().isoformat() + "Z"
    }

    # Run handler
    response = lambda_handler(mock_event, MockContext())
    print(json.dumps(response, indent=2))
