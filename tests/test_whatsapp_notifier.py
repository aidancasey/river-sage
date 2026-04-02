"""
Tests for SMS flow alert notifier.

Covers:
- Flow change threshold logic
- Alert sending decision logic
- Phone number normalization
"""

import pytest
from unittest.mock import patch, MagicMock

from src.notifications.whatsapp_notifier import (
    send_flow_alert,
    normalize_irish_number,
    FLOW_CHANGE_THRESHOLD_M3S,
)


class TestNormalizeIrishNumber:
    def test_local_format(self):
        assert normalize_irish_number("0831234567") == "+353831234567"

    def test_international_format(self):
        assert normalize_irish_number("+353831234567") == "+353831234567"

    def test_with_spaces(self):
        assert normalize_irish_number("083 123 4567") == "+353831234567"

    def test_invalid_number(self):
        assert normalize_irish_number("012345") is None

    def test_non_mobile_prefix(self):
        assert normalize_irish_number("0211234567") is None


class TestSendFlowAlert:
    """Test the alert decision logic (mocking SNS and S3)."""

    @patch("src.notifications.whatsapp_notifier.boto3")
    def test_no_alert_when_change_below_threshold(self, mock_boto3):
        result = send_flow_alert(
            previous_flow=10.0,
            current_flow=11.0,
            bucket="test-bucket",
        )
        assert result["sent"] == 0
        assert result["skipped"] == "change below threshold"

    @patch("src.notifications.whatsapp_notifier.boto3")
    def test_no_alert_when_change_exactly_at_threshold(self, mock_boto3):
        result = send_flow_alert(
            previous_flow=10.0,
            current_flow=10.0 + FLOW_CHANGE_THRESHOLD_M3S - 0.01,
            bucket="test-bucket",
        )
        assert result["sent"] == 0

    @patch("src.notifications.whatsapp_notifier.get_todays_subscribers")
    @patch("src.notifications.whatsapp_notifier.boto3")
    def test_no_alert_when_no_subscribers(self, mock_boto3, mock_get_subs):
        mock_get_subs.return_value = []
        result = send_flow_alert(
            previous_flow=10.0,
            current_flow=25.0,
            bucket="test-bucket",
        )
        assert result["sent"] == 0
        assert result["skipped"] == "no subscribers today"

    @patch("src.notifications.whatsapp_notifier.get_todays_subscribers")
    @patch("src.notifications.whatsapp_notifier.boto3")
    def test_alert_sent_when_above_threshold(self, mock_boto3, mock_get_subs):
        mock_get_subs.return_value = ["+353831234567"]
        mock_sns = MagicMock()
        mock_boto3.client.return_value = mock_sns

        result = send_flow_alert(
            previous_flow=3.5,
            current_flow=25.0,
            bucket="test-bucket",
        )

        assert result["sent"] == 1
        assert result["change_m3s"] == 21.5
        mock_sns.publish.assert_called_once()
        call_kwargs = mock_sns.publish.call_args[1]
        assert call_kwargs["PhoneNumber"] == "+353831234567"
        assert "increased" in call_kwargs["Message"]
        assert "25.0" in call_kwargs["Message"]

    @patch("src.notifications.whatsapp_notifier.get_todays_subscribers")
    @patch("src.notifications.whatsapp_notifier.boto3")
    def test_alert_sent_on_decrease(self, mock_boto3, mock_get_subs):
        mock_get_subs.return_value = ["+353831234567"]
        mock_sns = MagicMock()
        mock_boto3.client.return_value = mock_sns

        result = send_flow_alert(
            previous_flow=25.0,
            current_flow=10.0,
            bucket="test-bucket",
        )

        assert result["sent"] == 1
        assert result["change_m3s"] == -15.0
        call_kwargs = mock_sns.publish.call_args[1]
        assert "decreased" in call_kwargs["Message"]
