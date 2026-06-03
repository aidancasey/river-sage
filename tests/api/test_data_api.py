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

import gzip
import json
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
from io import BytesIO
import sys
import os

# Add api directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../api'))

from data_api import (
    lambda_handler,
    handle_latest_flow,
    handle_historical_flow,
    handle_flow_summary,
    get_flow_status,
    calculate_trend,
    cors_response,
    error_response,
    _trend_from_delta,
    _age_note,
    _relative_age,
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
        """Should return latest flow data from all stations."""
        # Mock S3 aggregated station data
        mock_data = {
            'station': 'Inniscarra Dam',
            'river': 'River Lee',
            'latest_reading': {
                'timestamp': '2025-12-06T14:03:00Z',
                'flow_rate_m3s': 15.5
            }
        }
        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=lambda: json.dumps(mock_data).encode())
        }
        # Set up NoSuchKey exception class so except clauses work
        mock_s3.exceptions.NoSuchKey = type('NoSuchKey', (Exception,), {})

        event = {
            'httpMethod': 'GET',
            'path': '/api/latest',
            'queryStringParameters': {'station': 'inniscarra'}
        }

        response = handle_latest_flow(event)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'stations' in body
        assert len(body['stations']) == 1
        assert body['stations'][0]['stationId'] == 'inniscarra'
        assert body['stations'][0]['flowRate'] == 15.5
        assert body['stations'][0]['status'] == 'normal'

    def test_latest_flow_not_found(self, mock_s3):
        """Should return 404 when no data available from any station."""
        NoSuchKey = type('NoSuchKey', (Exception,), {})
        mock_s3.exceptions.NoSuchKey = NoSuchKey
        mock_s3.get_object.side_effect = NoSuchKey(
            {'Error': {'Code': 'NoSuchKey'}}, 'GetObject'
        )

        event = {
            'httpMethod': 'GET',
            'path': '/api/latest',
            'queryStringParameters': {'station': 'inniscarra'}
        }

        response = handle_latest_flow(event)

        assert response['statusCode'] == 404


def _make_gzipped_s3_body(data: dict) -> MagicMock:
    """Helper to create a gzipped S3 Body mock matching how GzipFile reads it."""
    buf = BytesIO()
    with gzip.GzipFile(fileobj=buf, mode='wb') as gz:
        gz.write(json.dumps(data).encode())
    buf.seek(0)
    return buf


@patch('data_api.s3_client')
class TestHandleHistoricalFlow:
    """Test /history endpoint handler."""

    def test_successful_historical_flow(self, mock_s3):
        """Should return historical flow data with statistics."""
        now = datetime.now(timezone.utc)
        mock_data = {
            'historical_readings': [
                {
                    'timestamp': (now - timedelta(hours=i)).isoformat(),
                    'flow_rate_m3s': 15.0 + i
                }
                for i in range(24, 0, -1)
            ]
        }
        mock_s3.get_object.return_value = {
            'Body': _make_gzipped_s3_body(mock_data)
        }
        mock_s3.exceptions.NoSuchKey = type('NoSuchKey', (Exception,), {})

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
        now = datetime.now(timezone.utc)
        mock_data = {
            'historical_readings': [
                {
                    'timestamp': (now - timedelta(hours=i)).isoformat(),
                    'flow_rate_m3s': 10.0 + i
                }
                for i in range(48, 0, -1)
            ]
        }
        mock_s3.get_object.return_value = {
            'Body': _make_gzipped_s3_body(mock_data)
        }
        mock_s3.exceptions.NoSuchKey = type('NoSuchKey', (Exception,), {})

        event = {
            'httpMethod': 'GET',
            'path': '/api/history',
            'queryStringParameters': {'days': '7'}
        }

        response = handle_historical_flow(event)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['timeRange']['hours'] == 168  # 7 days * 24 hours


class TestTrendFromDelta:
    """Test the hourly trend mapping (with the 0.1 m³/s deadband)."""

    def test_rising(self):
        assert _trend_from_delta(0.4) == ('rising', '↑')
        assert _trend_from_delta(0.1) == ('rising', '↑')

    def test_falling(self):
        assert _trend_from_delta(-0.4) == ('falling', '↓')
        assert _trend_from_delta(-0.1) == ('falling', '↓')

    def test_steady_within_deadband(self):
        assert _trend_from_delta(0.0) == ('steady', '→')
        assert _trend_from_delta(0.05) == ('steady', '→')
        assert _trend_from_delta(-0.09) == ('steady', '→')

    def test_steady_when_unknown(self):
        assert _trend_from_delta(None) == ('steady', '→')


class TestAgeNote:
    """Test the staleness note (silent <= 90 min)."""

    def test_fresh_is_silent(self):
        assert _age_note(0) == ''
        assert _age_note(90) == ''
        assert _age_note(None) == ''

    def test_minutes_between_90_and_120(self):
        assert _age_note(95) == '  (95m old)'
        assert _age_note(119) == '  (119m old)'

    def test_hours_beyond_2(self):
        assert _age_note(120) == '  (2h old)'
        assert _age_note(180) == '  (3h old)'


class TestRelativeAge:
    """Test the relative freshness string used on the card."""

    def test_just_now(self):
        assert _relative_age(0) == 'just now'

    def test_minutes(self):
        assert _relative_age(40) == '40m ago'
        assert _relative_age(59) == '59m ago'

    def test_hours(self):
        assert _relative_age(120) == '2h ago'
        assert _relative_age(180) == '3h ago'

    def test_none(self):
        assert _relative_age(None) == ''


@patch('data_api.s3_client')
class TestHandleFlowSummary:
    """Test /summary endpoint handler."""

    def _setup_s3(self, mock_s3, latest_json, hist_readings, now):
        """Wire get_object to return the aggregated latest JSON and the parsed
        monthly gz only for the current month (so points aren't duplicated)."""
        ym = now.strftime('%Y%m')
        hist_data = {'historical_readings': hist_readings}

        def side_effect(Bucket=None, Key=None):
            if 'aggregated' in Key:
                return {'Body': MagicMock(read=lambda: json.dumps(latest_json).encode())}
            if 'parsed' in Key and ym in Key:
                return {'Body': _make_gzipped_s3_body(hist_data)}
            raise mock_s3.exceptions.NoSuchKey()

        mock_s3.exceptions.NoSuchKey = type('NoSuchKey', (Exception,), {})
        mock_s3.get_object.side_effect = side_effect

    def test_rising_summary(self, mock_s3):
        now = datetime.now(timezone.utc)
        latest_json = {
            'station': 'Inniscarra Dam',
            'river': 'River Lee',
            'latest_reading': {'timestamp': now.isoformat(), 'flow_rate_m3s': 6.3},
        }
        hist = [
            {'timestamp': (now - timedelta(hours=1)).isoformat(), 'flow_rate_m3s': 5.9},
            {'timestamp': now.isoformat(), 'flow_rate_m3s': 6.3},
        ]
        self._setup_s3(mock_s3, latest_json, hist, now)

        response = handle_flow_summary({'httpMethod': 'GET', 'path': '/api/flow/summary',
                                        'queryStringParameters': None})

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['river'] == 'River Lee'
        assert body['flow'] == 6.3
        assert body['trend'] == 'rising'
        assert body['arrow'] == '↑'
        assert body['changeLastHour'] == 0.4
        assert 'River Lee' in body['display']
        assert '6.3' in body['display']
        assert 'rising' in body['display']
        assert 'old)' not in body['display']  # fresh -> no age note
        # Multi-line emoji card for the watch result sheet
        assert body['emoji'] == '⬆️'
        assert body['card'].startswith('🌊 River Lee')
        assert '6.3 m³/s' in body['card']
        assert '⬆️ rising (last hr)' in body['card']
        assert '\n' in body['card']  # multi-line
        # Clean spoken phrase for Siri (no emoji/symbols)
        assert 'cubic metres per second' in body['spoken']
        assert '🌊' not in body['spoken']
        assert '↑' not in body['spoken']

    def test_stale_data_shows_age_note(self, mock_s3):
        now = datetime.now(timezone.utc)
        latest_json = {
            'station': 'Inniscarra Dam',
            'river': 'River Lee',
            # 3h old reading -> dataAge ~180 min
            'latest_reading': {'timestamp': (now - timedelta(hours=3)).isoformat(),
                               'flow_rate_m3s': 6.3},
        }
        # only one recent point -> trend steady
        hist = [{'timestamp': (now - timedelta(hours=3)).isoformat(), 'flow_rate_m3s': 6.3}]
        self._setup_s3(mock_s3, latest_json, hist, now)

        response = handle_flow_summary({'httpMethod': 'GET', 'path': '/api/flow/summary',
                                        'queryStringParameters': None})

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['trend'] == 'steady'
        assert 'old)' in body['display']

    def test_unknown_station(self, mock_s3):
        response = handle_flow_summary({'httpMethod': 'GET', 'path': '/api/flow/summary',
                                        'queryStringParameters': {'station': 'nope'}})
        assert response['statusCode'] == 404


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
