"""
AWS Lambda handler for river data collection.

This is the main entry point for the Lambda function that runs
on a schedule to download and process river data.
"""

import json
from datetime import datetime
from typing import Dict, Any

from .config.settings import Settings
from .connectors.http_connector import HTTPConnector
from .parsers.esb_hydro_parser import ESBHydroFlowParser
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

                # Create HTTP connector
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

                # Parse PDF content (FR2)
                parser = ESBHydroFlowParser(
                    station_name=source_config.name,
                    river_name=source_config.river
                )

                parsed_data = parser.parse(content, source_hash=file_hash)

                logger.info(
                    f"Successfully parsed {source_config.name}",
                    station_id=source_config.station_id,
                    current_flow=parsed_data.current_reading.flow_rate_m3s,
                    reading_count=len(parsed_data.historical_readings)
                )

                # Upload to S3 (FR3)
                s3_keys = {}
                if settings.s3:
                    storage = S3Storage(settings.s3)

                    # Upload raw PDF
                    raw_key = storage.upload_raw_pdf(
                        content=content,
                        station_id=source_config.station_id,
                        timestamp=parsed_data.current_reading.timestamp,
                        content_hash=file_hash
                    )
                    s3_keys['raw'] = raw_key

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

                results.append({
                    "station_id": source_config.station_id,
                    "success": True,
                    "size_bytes": len(content),
                    "hash": file_hash,
                    "current_flow_m3s": parsed_data.current_reading.flow_rate_m3s,
                    "reading_count": len(parsed_data.historical_readings),
                    "timestamp": parsed_data.current_reading.timestamp.isoformat() + "Z",
                    "s3_keys": s3_keys if settings.s3 else None,
                    "attempts": 1  # TODO: Track actual attempts
                })

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
