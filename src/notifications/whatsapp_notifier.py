"""
WhatsApp flow alert notifier using Twilio.

Sends WhatsApp messages to users who have opted in for today when the
Inniscarra flow rate changes by more than 2 m³/s compared to the previous reading.

State is stored in S3:
  alerts/subscribers.json   - registered phone numbers
  alerts/daily_optins.json  - {phone: date_string} for today's opt-ins
"""

import json
import os
import re
from datetime import date, timezone
from typing import List, Optional
import boto3
from botocore.exceptions import ClientError

from ..utils.logger import StructuredLogger

logger = StructuredLogger(__name__)

# Minimum absolute change in m³/s that triggers an alert
FLOW_CHANGE_THRESHOLD_M3S = 2.0

S3_SUBSCRIBERS_KEY = "alerts/subscribers.json"
S3_DAILY_OPTINS_KEY = "alerts/daily_optins.json"


def normalize_irish_number(raw: str) -> Optional[str]:
    """
    Convert an Irish mobile number to E.164 format (+353...).

    Accepts formats: 083..., 085..., 086..., 087..., 089..., +353...
    Returns None if the number doesn't look valid.
    """
    digits = re.sub(r"\D", "", raw)

    # Already in international format without the +
    if digits.startswith("353") and len(digits) == 12:
        return f"+{digits}"

    # Local format: 08X XXXXXXX (10 digits total)
    if re.match(r"^08[3-9]\d{7}$", digits):
        return f"+353{digits[1:]}"

    return None


def _load_json_from_s3(s3_client, bucket: str, key: str) -> dict:
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        return json.loads(response["Body"].read().decode("utf-8"))
    except ClientError as e:
        if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
            return {}
        raise


def _save_json_to_s3(s3_client, bucket: str, key: str, data: dict) -> None:
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(data, indent=2).encode("utf-8"),
        ContentType="application/json",
        ServerSideEncryption="AES256",
    )


def register_subscriber(phone: str, bucket: str) -> dict:
    """
    Add a phone number to the subscribers list.

    Args:
        phone: Irish mobile number in any supported format
        bucket: S3 bucket name

    Returns:
        dict with 'success' bool and optional 'error' message
    """
    normalized = normalize_irish_number(phone)
    if not normalized:
        return {"success": False, "error": "Invalid Irish mobile number"}

    s3 = boto3.client("s3")
    subscribers = _load_json_from_s3(s3, bucket, S3_SUBSCRIBERS_KEY)

    if normalized not in subscribers:
        subscribers[normalized] = {"registered_at": date.today().isoformat()}
        _save_json_to_s3(s3, bucket, S3_SUBSCRIBERS_KEY, subscribers)
        logger.info("Registered new subscriber", phone_prefix=normalized[:8])
    else:
        logger.info("Subscriber already registered", phone_prefix=normalized[:8])

    return {"success": True, "phone": normalized}


def opt_in_today(phone: str, bucket: str) -> dict:
    """
    Opt a phone number in for today's alerts.

    Args:
        phone: Irish mobile number in any supported format
        bucket: S3 bucket name

    Returns:
        dict with 'success' bool and optional 'error' message
    """
    normalized = normalize_irish_number(phone)
    if not normalized:
        return {"success": False, "error": "Invalid Irish mobile number"}

    s3 = boto3.client("s3")

    # Ensure they are a registered subscriber first
    subscribers = _load_json_from_s3(s3, bucket, S3_SUBSCRIBERS_KEY)
    if normalized not in subscribers:
        # Auto-register on first opt-in
        subscribers[normalized] = {"registered_at": date.today().isoformat()}
        _save_json_to_s3(s3, bucket, S3_SUBSCRIBERS_KEY, subscribers)

    daily_optins = _load_json_from_s3(s3, bucket, S3_DAILY_OPTINS_KEY)
    today = date.today().isoformat()
    daily_optins[normalized] = today
    _save_json_to_s3(s3, bucket, S3_DAILY_OPTINS_KEY, daily_optins)

    logger.info("Opted in for today", date=today, phone_prefix=normalized[:8])
    return {"success": True, "phone": normalized, "opted_in_until": today}


def get_opt_in_status(phone: str, bucket: str) -> dict:
    """
    Check whether a phone number is opted in for today.

    Returns:
        dict with 'opted_in' bool and 'phone' in E.164 format
    """
    normalized = normalize_irish_number(phone)
    if not normalized:
        return {"opted_in": False, "error": "Invalid Irish mobile number"}

    s3 = boto3.client("s3")
    daily_optins = _load_json_from_s3(s3, bucket, S3_DAILY_OPTINS_KEY)
    today = date.today().isoformat()
    opted_in = daily_optins.get(normalized) == today

    return {"opted_in": opted_in, "phone": normalized}


def get_todays_subscribers(bucket: str) -> List[str]:
    """
    Return a list of E.164 phone numbers opted in for today.
    """
    s3 = boto3.client("s3")
    daily_optins = _load_json_from_s3(s3, bucket, S3_DAILY_OPTINS_KEY)
    today = date.today().isoformat()
    return [phone for phone, opted_date in daily_optins.items() if opted_date == today]



def send_flow_alert(
    previous_flow: float,
    current_flow: float,
    bucket: str,
    twilio_account_sid: str,
    twilio_auth_token: str,
    twilio_from: str,
) -> dict:
    """
    Send a WhatsApp alert to all today's opt-in subscribers if the flow
    has changed by more than FLOW_CHANGE_THRESHOLD_M3S.

    Args:
        previous_flow: Previous flow reading in m³/s
        current_flow: New flow reading in m³/s
        bucket: S3 bucket name
        twilio_account_sid: Twilio account SID
        twilio_auth_token: Twilio auth token
        twilio_from: Twilio WhatsApp sender number (e.g. 'whatsapp:+14155238886')

    Returns:
        dict with 'sent' count and 'skipped' reason if no alert needed
    """
    change = current_flow - previous_flow

    if abs(change) < FLOW_CHANGE_THRESHOLD_M3S:
        logger.info(
            "Flow change below threshold, no alert sent",
            change_m3s=round(change, 2),
            threshold=FLOW_CHANGE_THRESHOLD_M3S,
            current_flow=current_flow,
            previous_flow=previous_flow,
        )
        return {"sent": 0, "skipped": "change below threshold", "change_m3s": change}

    direction = "increased" if change > 0 else "decreased"
    message = (
        f"River Lee (Inniscarra) flow alert:\n"
        f"Flow has {direction} by {abs(change):.1f} m³/s\n"
        f"Current flow: {current_flow:.1f} m³/s\n"
        f"Previous: {previous_flow:.1f} m³/s\n\n"
        f"Reply STOP to unsubscribe."
    )

    subscribers = get_todays_subscribers(bucket)
    if not subscribers:
        logger.info("No subscribers opted in for today, skipping alert", change_m3s=round(change, 2))
        return {"sent": 0, "skipped": "no subscribers today", "change_m3s": change}

    from twilio.rest import Client  # imported here so Lambda only needs it when alerting

    s3 = boto3.client("s3")
    client = Client(twilio_account_sid, twilio_auth_token)
    sent_count = 0
    errors = []

    for phone in subscribers:
        try:
            client.messages.create(
                from_=twilio_from,
                to=f"whatsapp:{phone}",
                body=message,
            )
            sent_count += 1
            logger.info("Alert sent", phone_prefix=phone[:8])
        except Exception as e:
            logger.error("Failed to send alert", phone_prefix=phone[:8], error=str(e))
            errors.append(str(e))

    return {
        "sent": sent_count,
        "total_subscribers": len(subscribers),
        "change_m3s": round(change, 2),
        "current_flow": current_flow,
        "previous_flow": previous_flow,
        "errors": errors,
    }
