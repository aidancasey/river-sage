"""
River Guru Data API Lambda Function

This Lambda function provides REST API endpoints to access river flow data
stored in S3. It supports two main operations:
1. Get latest flow data
2. Get historical flow data with time range filtering

The API is designed to be called from API Gateway and returns JSON responses
with appropriate CORS headers for web app access.
"""

import json
import os
import boto3
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# Initialize S3 client
s3_client = boto3.client('s3')

# Environment variables
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'river-data-ireland-prod')
S3_REGION = os.environ.get('S3_REGION', 'eu-west-1')

# CORS headers for all responses
CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
    'Access-Control-Allow-Methods': 'GET,OPTIONS',
    'Content-Type': 'application/json'
}


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for API Gateway requests.

    Routes requests to appropriate handlers based on HTTP method and path.

    Args:
        event: API Gateway event object
        context: Lambda context object

    Returns:
        API Gateway response with status code, headers, and body
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")

        # Handle OPTIONS request for CORS preflight
        http_method = event.get('httpMethod', event.get('requestContext', {}).get('http', {}).get('method', ''))
        if http_method == 'OPTIONS':
            return cors_response(200, {'message': 'OK'})

        # Get the resource path
        path = event.get('path', event.get('rawPath', ''))
        logger.info(f"Processing {http_method} request for path: {path}")

        # Route to appropriate handler
        if path.endswith('/latest') or path.endswith('/latest/'):
            return handle_latest_flow(event)
        elif path.endswith('/history') or path.endswith('/history/'):
            return handle_historical_flow(event)
        else:
            return error_response(404, 'Endpoint not found')

    except Exception as e:
        logger.error(f"Unhandled error: {str(e)}", exc_info=True)
        return error_response(500, f'Internal server error: {str(e)}')


def handle_latest_flow(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle GET /latest endpoint - returns the most recent flow data.

    Args:
        event: API Gateway event object

    Returns:
        Response with latest flow data
    """
    try:
        # Query parameters (optional station filter for future)
        query_params = event.get('queryStringParameters') or {}
        station_id = query_params.get('station', 'inniscarra')

        logger.info(f"Fetching latest flow data for station: {station_id}")

        # Read latest aggregated data from S3
        s3_key = f'aggregated/{station_id}_latest.json'

        try:
            response = s3_client.get_object(
                Bucket=S3_BUCKET_NAME,
                Key=s3_key
            )
            data = json.loads(response['Body'].read().decode('utf-8'))

            # Parse Phase 1 data structure
            latest_reading = data.get('latest_reading', {})
            timestamp_str = latest_reading.get('timestamp', '')

            # Calculate data age
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            data_age_minutes = int((datetime.now(timestamp.tzinfo) - timestamp).total_seconds() / 60)

            # Determine flow status based on current flow rate
            flow_rate = latest_reading.get('flow_rate_m3s', 0)
            status = get_flow_status(flow_rate)

            # Format response
            response_data = {
                'stationId': station_id,
                'name': data.get('station', 'Inniscarra'),
                'river': data.get('river', 'River Lee'),
                'currentFlow': flow_rate,
                'unit': 'm³/s',
                'timestamp': timestamp_str,
                'dataAge': data_age_minutes,
                'status': status
            }

            logger.info(f"Successfully fetched latest data: flow={flow_rate}, age={data_age_minutes}min")
            return cors_response(200, response_data)

        except s3_client.exceptions.NoSuchKey:
            logger.warning(f"No data found for station: {station_id}")
            return error_response(404, f'No data found for station: {station_id}')

    except Exception as e:
        logger.error(f"Error fetching latest flow: {str(e)}", exc_info=True)
        return error_response(500, f'Error fetching latest flow data: {str(e)}')


def handle_historical_flow(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle GET /history endpoint - returns historical flow data for a time range.

    Query parameters:
    - station: Station ID (default: inniscarra)
    - hours: Number of hours to look back (default: 24)
    - days: Number of days to look back (overrides hours if provided)

    Args:
        event: API Gateway event object

    Returns:
        Response with historical flow data and statistics
    """
    try:
        # Parse query parameters
        query_params = event.get('queryStringParameters') or {}
        station_id = query_params.get('station', 'inniscarra')

        # Determine time range
        if 'days' in query_params:
            hours = int(query_params['days']) * 24
        else:
            hours = int(query_params.get('hours', 24))

        logger.info(f"Fetching {hours} hours of historical data for station: {station_id}")

        # Read historical data from parsed monthly file
        now = datetime.now()
        # For simplicity, read current month's file (could be extended to read multiple months)
        s3_key = f'parsed/{station_id}/{now.year}/{now.month:02d}/{station_id}_flow_{now.year}{now.month:02d}.json.gz'

        try:
            response = s3_client.get_object(
                Bucket=S3_BUCKET_NAME,
                Key=s3_key
            )

            # Decompress gzip data
            import gzip
            with gzip.GzipFile(fileobj=response['Body']) as gzipfile:
                data = json.loads(gzipfile.read().decode('utf-8'))

            # Filter data points by time range
            from datetime import timezone
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            historical_readings = data.get('historical_readings', [])

            # Convert to API format and filter by time
            filtered_points = []
            for reading in historical_readings:
                timestamp_str = reading.get('timestamp', '')
                reading_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))

                if reading_time >= cutoff_time:
                    filtered_points.append({
                        'timestamp': timestamp_str,
                        'flow': reading.get('flow_rate_m3s', 0)
                    })

            # Sort by timestamp (oldest first)
            filtered_points.sort(key=lambda x: x['timestamp'])

            # Calculate statistics
            if filtered_points:
                flow_values = [point['flow'] for point in filtered_points]
                statistics = {
                    'min': round(min(flow_values), 2),
                    'max': round(max(flow_values), 2),
                    'average': round(sum(flow_values) / len(flow_values), 2),
                    'trend': calculate_trend(flow_values)
                }
            else:
                statistics = {
                    'min': 0,
                    'max': 0,
                    'average': 0,
                    'trend': 'unknown'
                }

            # Format response
            response_data = {
                'stationId': station_id,
                'timeRange': {
                    'start': cutoff_time.isoformat(),
                    'end': datetime.now(timezone.utc).isoformat(),
                    'hours': hours
                },
                'dataPoints': filtered_points,
                'statistics': statistics,
                'count': len(filtered_points)
            }

            logger.info(f"Successfully fetched {len(filtered_points)} historical data points")
            return cors_response(200, response_data)

        except s3_client.exceptions.NoSuchKey:
            logger.warning(f"No historical data found for station: {station_id}")
            return error_response(404, f'No historical data found for station: {station_id}')

    except ValueError as e:
        logger.warning(f"Invalid query parameter: {str(e)}")
        return error_response(400, f'Invalid query parameter: {str(e)}')
    except Exception as e:
        logger.error(f"Error fetching historical flow: {str(e)}", exc_info=True)
        return error_response(500, f'Error fetching historical flow data: {str(e)}')


def get_flow_status(flow_rate: float) -> str:
    """
    Determine the flow status based on the flow rate.

    Thresholds:
    - Low: < 5 m³/s
    - Normal: 6-20 m³/s
    - High: 30-60 m³/s
    - Very High: > 100 m³/s

    Args:
        flow_rate: Current flow rate in m³/s

    Returns:
        Status string: 'low', 'normal', 'high', or 'very-high'
    """
    if flow_rate < 5:
        return 'low'
    elif flow_rate <= 20:
        return 'normal'
    elif flow_rate <= 60:
        return 'high'
    else:
        return 'very-high'


def calculate_trend(values: List[float]) -> str:
    """
    Calculate the trend of flow values over time.

    Uses simple linear regression approach:
    - Compare average of first half vs second half

    Args:
        values: List of flow rate values in chronological order

    Returns:
        Trend string: 'increasing', 'decreasing', or 'stable'
    """
    if len(values) < 4:
        return 'stable'

    mid_point = len(values) // 2
    first_half_avg = sum(values[:mid_point]) / mid_point
    second_half_avg = sum(values[mid_point:]) / (len(values) - mid_point)

    change_percent = ((second_half_avg - first_half_avg) / first_half_avg) * 100

    if change_percent > 10:
        return 'increasing'
    elif change_percent < -10:
        return 'decreasing'
    else:
        return 'stable'


def cors_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create an API Gateway response with CORS headers.

    Args:
        status_code: HTTP status code
        body: Response body dictionary

    Returns:
        API Gateway response object
    """
    return {
        'statusCode': status_code,
        'headers': CORS_HEADERS,
        'body': json.dumps(body, default=str)
    }


def error_response(status_code: int, message: str) -> Dict[str, Any]:
    """
    Create an error response with CORS headers.

    Args:
        status_code: HTTP error status code
        message: Error message

    Returns:
        API Gateway error response object
    """
    return cors_response(status_code, {
        'error': message,
        'statusCode': status_code
    })
