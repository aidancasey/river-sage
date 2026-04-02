"""
Tests for WhatsApp flow alert notifier.

Covers:
- Twilio import availability in the collector Lambda context
- Flow change threshold logic
- Alert sending decision logic
- Phone number normalization
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import date

from src.notifications.whatsapp_notifier import (
    send_flow_alert,
    normalize_irish_number,
    FLOW_CHANGE_THRESHOLD_M3S,
)


def test_twilio_is_importable():
    """Twilio must be importable — the collector Lambda sends alerts directly.

    This test would have caught the ModuleNotFoundError that caused the
    missed alert on 2026-04-02 when flow jumped from 3.5 to 25.0 m³/s.
    """
    import twilio.rest  # noqa: F401


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
    """Test the alert decision logic (mocking Twilio and S3)."""

    @patch("src.notifications.whatsapp_notifier.boto3")
    def test_no_alert_when_change_below_threshold(self, mock_boto3):
        result = send_flow_alert(
            previous_flow=10.0,
            current_flow=11.0,
            bucket="test-bucket",
            twilio_account_sid="sid",
            twilio_auth_token="token",
            twilio_from="whatsapp:+14155238886",
        )
        assert result["sent"] == 0
        assert result["skipped"] == "change below threshold"

    @patch("src.notifications.whatsapp_notifier.boto3")
    def test_no_alert_when_change_exactly_at_threshold(self, mock_boto3):
        result = send_flow_alert(
            previous_flow=10.0,
            current_flow=10.0 + FLOW_CHANGE_THRESHOLD_M3S - 0.01,
            bucket="test-bucket",
            twilio_account_sid="sid",
            twilio_auth_token="token",
            twilio_from="whatsapp:+14155238886",
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
            twilio_account_sid="sid",
            twilio_auth_token="token",
            twilio_from="whatsapp:+14155238886",
        )
        assert result["sent"] == 0
        assert result["skipped"] == "no subscribers today"

    @patch("twilio.rest.Client")
    @patch("src.notifications.whatsapp_notifier._update_last_alerted_flow")
    @patch("src.notifications.whatsapp_notifier.get_todays_subscribers")
    @patch("src.notifications.whatsapp_notifier.boto3")
    def test_alert_sent_when_above_threshold(
        self, mock_boto3, mock_get_subs, mock_update_flow, mock_twilio_client
    ):
        mock_get_subs.return_value = ["+353831234567"]
        mock_client_instance = MagicMock()
        mock_twilio_client.return_value = mock_client_instance

        result = send_flow_alert(
            previous_flow=3.5,
            current_flow=25.0,
            bucket="test-bucket",
            twilio_account_sid="sid",
            twilio_auth_token="token",
            twilio_from="whatsapp:+14155238886",
        )

        assert result["sent"] == 1
        assert result["change_m3s"] == 21.5
        mock_client_instance.messages.create.assert_called_once()
        call_kwargs = mock_client_instance.messages.create.call_args[1]
        assert "increased" in call_kwargs["body"]
        assert "25.0" in call_kwargs["body"]

    @patch("twilio.rest.Client")
    @patch("src.notifications.whatsapp_notifier._update_last_alerted_flow")
    @patch("src.notifications.whatsapp_notifier.get_todays_subscribers")
    @patch("src.notifications.whatsapp_notifier.boto3")
    def test_alert_sent_on_decrease(
        self, mock_boto3, mock_get_subs, mock_update_flow, mock_twilio_client
    ):
        mock_get_subs.return_value = ["+353831234567"]
        mock_client_instance = MagicMock()
        mock_twilio_client.return_value = mock_client_instance

        result = send_flow_alert(
            previous_flow=25.0,
            current_flow=10.0,
            bucket="test-bucket",
            twilio_account_sid="sid",
            twilio_auth_token="token",
            twilio_from="whatsapp:+14155238886",
        )

        assert result["sent"] == 1
        assert result["change_m3s"] == -15.0
        call_kwargs = mock_client_instance.messages.create.call_args[1]
        assert "decreased" in call_kwargs["body"]

    @patch("twilio.rest.Client")
    @patch("src.notifications.whatsapp_notifier._update_last_alerted_flow")
    @patch("src.notifications.whatsapp_notifier.get_todays_subscribers")
    @patch("src.notifications.whatsapp_notifier.boto3")
    def test_last_alerted_flow_updated_after_alert(
        self, mock_boto3, mock_get_subs, mock_update_flow, mock_twilio_client
    ):
        mock_get_subs.return_value = ["+353831234567"]
        mock_twilio_client.return_value = MagicMock()

        send_flow_alert(
            previous_flow=3.5,
            current_flow=25.0,
            bucket="test-bucket",
            twilio_account_sid="sid",
            twilio_auth_token="token",
            twilio_from="whatsapp:+14155238886",
        )

        mock_update_flow.assert_called_once_with(
            mock_boto3.client.return_value, "test-bucket", 25.0
        )
