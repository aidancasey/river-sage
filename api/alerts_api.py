"""
River Guru Alerts API Lambda Function

Handles WhatsApp flow alert subscription management:
  POST /api/alerts/register  - register a phone number
  POST /api/alerts/optin     - opt in for today's alerts
  GET  /api/alerts/status    - check opt-in status for a phone number
"""

import json
import os
import logging
from typing import Any, Dict

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "river-data-ireland-prod")

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Content-Type": "application/json",
}


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    http_method = event.get("httpMethod", event.get("requestContext", {}).get("http", {}).get("method", ""))

    if http_method == "OPTIONS":
        return cors_response(200, {"message": "OK"})

    path = event.get("path", event.get("rawPath", ""))
    logger.info(f"Alerts API: {http_method} {path}")

    if path.endswith("/register") and http_method == "POST":
        return handle_register(event)
    elif path.endswith("/optin") and http_method == "POST":
        return handle_optin(event)
    elif path.endswith("/status") and http_method == "GET":
        return handle_status(event)
    else:
        return error_response(404, "Endpoint not found")


def handle_register(event: Dict[str, Any]) -> Dict[str, Any]:
    body = parse_body(event)
    if body is None:
        return error_response(400, "Request body must be valid JSON")

    phone = body.get("phone", "").strip()
    if not phone:
        return error_response(400, "phone is required")

    from src.notifications.whatsapp_notifier import register_subscriber

    result = register_subscriber(phone, S3_BUCKET_NAME)
    if not result["success"]:
        return error_response(400, result.get("error", "Registration failed"))

    return cors_response(200, {"message": "Phone number registered", "phone": result["phone"]})


def handle_optin(event: Dict[str, Any]) -> Dict[str, Any]:
    body = parse_body(event)
    if body is None:
        return error_response(400, "Request body must be valid JSON")

    phone = body.get("phone", "").strip()
    if not phone:
        return error_response(400, "phone is required")

    from src.notifications.whatsapp_notifier import opt_in_today

    result = opt_in_today(phone, S3_BUCKET_NAME)
    if not result["success"]:
        return error_response(400, result.get("error", "Opt-in failed"))

    return cors_response(200, {
        "message": "You are opted in for today's alerts",
        "phone": result["phone"],
        "opted_in_until": result["opted_in_until"],
    })


def handle_status(event: Dict[str, Any]) -> Dict[str, Any]:
    query_params = event.get("queryStringParameters") or {}
    phone = query_params.get("phone", "").strip()
    if not phone:
        return error_response(400, "phone query parameter is required")

    from src.notifications.whatsapp_notifier import get_opt_in_status

    result = get_opt_in_status(phone, S3_BUCKET_NAME)
    if "error" in result:
        return error_response(400, result["error"])

    return cors_response(200, result)


def parse_body(event: Dict[str, Any]):
    raw = event.get("body") or "{}"
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


def cors_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps(body),
    }


def error_response(status_code: int, message: str) -> Dict[str, Any]:
    return cors_response(status_code, {"error": message, "statusCode": status_code})
