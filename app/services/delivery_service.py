import json
import random
import time
import logging
from datetime import datetime, timezone, timedelta
import httpx
from sqlalchemy.orm import Session
from app.services.signing_service import sign_payload
from app.db.models import DeliveryAttempt, DeadLetterEvent, WebhookEndpoint
from app.core.config import MAX_IMMEDIATE_RETRIES, RETRY_SLA_HOURS

logger = logging.getLogger(__name__)

# Retryable HTTP status codes
RETRYABLE_CODES = {429, 500, 502, 503, 504}


def deliver_webhook(
    db: Session,
    delivery_id: str,
    endpoint_url: str,
    secret: str,
    payload: str,
    attempt_count: int,
) -> dict:
    """
    Attempt to deliver a webhook via HTTP POST.
    Returns result dict with status and details.
    """
    # Sign the payload
    sig_headers = sign_payload(payload, secret)
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "WebhookPlatform/1.0",
        **sig_headers,
    }

    attempt = db.query(DeliveryAttempt).filter(DeliveryAttempt.id == delivery_id).first()
    if not attempt:
        return {"status": "error", "message": "Delivery attempt not found"}

    attempt.attempt_count = attempt_count + 1
    attempt.status = "retrying"

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(endpoint_url, content=payload, headers=headers)

        attempt.response_code = response.status_code

        if response.status_code < 300:
            # ✅ Success
            attempt.status = "delivered"
            attempt.error_message = None
            attempt.next_retry_at = None
            db.commit()
            logger.info(f"✅ Delivered {delivery_id} to {endpoint_url} (HTTP {response.status_code})")
            return {"status": "delivered", "code": response.status_code}

        elif response.status_code in RETRYABLE_CODES:
            # ⚠️ Retryable error
            attempt.error_message = f"HTTP {response.status_code}"
            return _handle_retryable(db, attempt, f"HTTP {response.status_code}")

        else:
            # ❌ Non-retryable (4xx except 429)
            attempt.error_message = f"HTTP {response.status_code} - non-retryable"
            return _move_to_dlq(db, attempt, f"HTTP {response.status_code}")

    except httpx.TimeoutException:
        attempt.error_message = "Connection timeout"
        return _handle_retryable(db, attempt, "Connection timeout")

    except httpx.ConnectError:
        attempt.error_message = "Connection refused"
        return _handle_retryable(db, attempt, "Connection refused")

    except Exception as e:
        attempt.error_message = str(e)
        return _handle_retryable(db, attempt, str(e))


def _handle_retryable(db: Session, attempt: DeliveryAttempt, error: str) -> dict:
    """Handle retryable errors: immediate retry or schedule for later."""
    if attempt.attempt_count < MAX_IMMEDIATE_RETRIES:
        # Still within immediate retry window
        attempt.status = "retrying"
        attempt.next_retry_at = None  # will be retried immediately with backoff
        db.commit()
        logger.warning(
            f"⚠️ Retry {attempt.attempt_count}/{MAX_IMMEDIATE_RETRIES} "
            f"for {attempt.id}: {error}"
        )
        return {"status": "retrying", "error": error, "attempt": attempt.attempt_count}

    # Check if within SLA window
    age = datetime.now(timezone.utc) - attempt.created_at.replace(tzinfo=timezone.utc)
    if age < timedelta(hours=RETRY_SLA_HOURS):
        # Schedule for later retry (exponential: 15min, 30min, 1h, 2h, 4h...)
        delay_minutes = min(15 * (2 ** (attempt.attempt_count - MAX_IMMEDIATE_RETRIES)), 240)
        attempt.status = "retrying"
        attempt.next_retry_at = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)
        db.commit()
        logger.warning(
            f"🕐 Scheduled retry for {attempt.id} in {delay_minutes}min: {error}"
        )
        return {"status": "scheduled_retry", "retry_in_minutes": delay_minutes}

    # Exceeded SLA → DLQ
    return _move_to_dlq(db, attempt, f"SLA exceeded after {attempt.attempt_count} attempts: {error}")


def _move_to_dlq(db: Session, attempt: DeliveryAttempt, error: str) -> dict:
    """Move a failed event to the Dead Letter Queue."""
    dlq_entry = DeadLetterEvent(
        event_id=attempt.event_id,
        endpoint_id=attempt.endpoint_id,
        user_id=attempt.user_id,
        event_type=attempt.event_type,
        payload=attempt.payload,
        final_error=error,
        attempt_count=attempt.attempt_count,
    )
    db.add(dlq_entry)

    attempt.status = "failed"
    attempt.error_message = error
    attempt.next_retry_at = None

    # Optionally suspend the endpoint
    endpoint = db.query(WebhookEndpoint).filter(WebhookEndpoint.id == attempt.endpoint_id).first()
    if endpoint and attempt.attempt_count >= MAX_IMMEDIATE_RETRIES + 3:
        endpoint.status = "suspended"
        logger.warning(f"🔴 Suspended endpoint {endpoint.id}")

    db.commit()
    logger.error(f"💀 Moved {attempt.id} to DLQ: {error}")
    return {"status": "dlq", "error": error}


def compute_backoff(attempt: int) -> float:
    """Exponential backoff with jitter."""
    base = min(0.1 * (2 ** attempt), 30.0)  # cap at 30 seconds
    jitter = random.uniform(0, base * 0.3)
    return base + jitter
