"""
Unit tests for the Data API Lambda function.

Tests cover:
- Latest flow endpoint
- Historical flow endpoint
- Error handling
- CORS headers
- Flow status calculation
- Trend calculation
"""

import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import sys
import os

# Add api directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../api'))

from data_api import (
    lambda_handler,
    handle_latest_flow,
    handle_historical_flow,
    get_flow_status,
    calculate_trend,
    cors_response,
    error_response
)


class TestGetFlowStatus:
    """Test flow status calculation based on flow rate thresholds."""

    def test_low_flow(self):
        """Flow < 5 m³/s should be 'low'."""
        assert get_flow_status(3.5) == 'low'
        assert get_flow_status(4.9) == 'low'

    def test_normal_flow(self):
        """Flow 6-20 m³/s should be 'normal'."""
        assert get_flow_status(10) == 'normal'
        assert get_flow_status(15) == 'normal'
        assert get_flow_status(20) == 'normal'

    def test_high_flow(self):
        """Flow 30-60 m³/s should be 'high'."""
        assert get_flow_status(35) == 'high'
        assert get_flow_status(50) == 'high'
        assert get_flow_status(60) == 'high'

    def test_very_high_flow(self):
        """Flow > 100 m³/s should be 'very-high'."""
        assert get_flow_status(105) == 'very-high'
        assert get_flow_status(200) == 'very-high'


class TestCalculateTrend:
    """Test trend calculation from flow values."""

    def test_increasing_trend(self):
        """Significant increase should return 'increasing'."""
        values = [10, 12, 14, 16, 18, 20]
        assert calculate_trend(values) == 'increasing'

    def test_decreasing_trend(self):
        """Significant decrease should return 'decreasing'."""
        values = [20, 18, 16, 14, 12, 10]
        assert calculate_trend(values) == 'decreasing'

    def test_stable_trend(self):
        """Minor changes should return 'stable'."""
        values = [15, 15.5, 14.8, 15.2, 15.1, 15]
        assert calculate_trend(values) == 'stable'

    def test_insufficient_data(self):
        """Less than 4 values should return 'stable'."""
        values = [10, 12]
        assert calculate_trend(values) == 'stable'


class TestCORSResponse:
    """Test CORS response formatting."""

    def test_cors_headers_included(self):
        """Response should include CORS headers."""
        response = cors_response(200, {'message': 'test'})

        assert response['statusCode'] == 200
        assert 'Access-Control-Allow-Origin' in response['headers']
        assert response['headers']['Access-Control-Allow-Origin'] == '*'
        assert 'Content-Type' in response['headers']
        assert response['headers']['Content-Type'] == 'application/json'

    def test_body_serialization(self):
        """Response body should be JSON serialized."""
        response = cors_response(200, {'key': 'value'})
        body = json.loads(response['body'])
        assert body['key'] == 'value'


class TestErrorResponse:
    """Test error response formatting."""

    def test_error_response_format(self):
        """Error response should include error field and status code."""
        response = error_response(404, 'Not found')

        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['error'] == 'Not found'
        assert body['statusCode'] == 404


@patch('data_api.s3_client')
class TestHandleLatestFlow:
    """Test /latest endpoint handler."""

    def test_successful_latest_flow(self, mock_s3):
        """Should return latest flow data from S3."""
        # Mock S3 response
        mock_data = {
            'timestamp': '2025-12-06T14:03:00Z',
            'flow_rate': 15.5,
            'station_name': 'Inniscarra',
            'river': 'River Lee'
        }
        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=lambda: json.dumps(mock_data).encode())
        }

        event = {
            'httpMethod': 'GET',
            'path': '/api/latest',
            'queryStringParameters': None
        }

        response = handle_latest_flow(event)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['currentFlow'] == 15.5
        assert body['stationId'] == 'inniscarra'
        assert body['status'] == 'normal'

    def test_latest_flow_not_found(self, mock_s3):
        """Should return 404 when data not found."""
        mock_s3.get_object.side_effect = mock_s3.exceptions.NoSuchKey(
            {'Error': {'Code': 'NoSuchKey'}}, 'GetObject'
        )
        mock_s3.exceptions = MagicMock()
        mock_s3.exceptions.NoSuchKey = type('NoSuchKey', (Exception,), {})

        event = {
            'httpMethod': 'GET',
            'path': '/api/latest',
            'queryStringParameters': None
        }

        response = handle_latest_flow(event)

        assert response['statusCode'] == 404


@patch('data_api.s3_client')
class TestHandleHistoricalFlow:
    """Test /history endpoint handler."""

    def test_successful_historical_flow(self, mock_s3):
        """Should return historical flow data with statistics."""
        # Mock historical data
        now = datetime.now()
        mock_data = {
            'data_points': [
                {
                    'timestamp': (now - timedelta(hours=i)).isoformat() + 'Z',
                    'flow': 15.0 + i
                }
                for i in range(24, 0, -1)
            ]
        }
        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=lambda: json.dumps(mock_data).encode())
        }

        event = {
            'httpMethod': 'GET',
            'path': '/api/history',
            'queryStringParameters': {'hours': '24'}
        }

        response = handle_historical_flow(event)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'dataPoints' in body
        assert 'statistics' in body
        assert body['statistics']['min'] > 0
        assert body['statistics']['max'] > 0

    def test_historical_flow_with_days_parameter(self, mock_s3):
        """Should support days parameter."""
        mock_data = {
            'data_points': []
        }
        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=lambda: json.dumps(mock_data).encode())
        }

        event = {
            'httpMethod': 'GET',
            'path': '/api/history',
            'queryStringParameters': {'days': '7'}
        }

        response = handle_historical_flow(event)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['timeRange']['hours'] == 168  # 7 days * 24 hours


class TestLambdaHandler:
    """Test main Lambda handler routing."""

    def test_options_request(self):
        """OPTIONS request should return 200 for CORS preflight."""
        event = {
            'httpMethod': 'OPTIONS',
            'path': '/api/latest'
        }

        response = lambda_handler(event, None)

        assert response['statusCode'] == 200

    def test_unknown_path(self):
        """Unknown path should return 404."""
        event = {
            'httpMethod': 'GET',
            'path': '/api/unknown'
        }

        response = lambda_handler(event, None)

        assert response['statusCode'] == 404
