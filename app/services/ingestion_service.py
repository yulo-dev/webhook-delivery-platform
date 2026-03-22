import json
import uuid
import redis
import logging
from sqlalchemy.orm import Session
from app.core.config import REDIS_URL, DELIVERY_QUEUE
from app.services.registration_service import find_endpoints_for_event
from app.db.models import DeliveryAttempt

logger = logging.getLogger(__name__)

_redis: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis


def ingest_event(db: Session, user_id: str, event_type: str, payload: dict) -> dict:
    """
    1. Look up all active endpoints for (user_id, event_type)
    2. For each endpoint, create a DeliveryAttempt record
    3. Push delivery tasks to the delivery queue
    """
    endpoints = find_endpoints_for_event(db, user_id, event_type)
    if not endpoints:
        return {"event_id": None, "status": "no_subscribers", "message": "No active endpoints for this event"}

    event_id = f"evt_{uuid.uuid4().hex[:12]}"
    payload_str = json.dumps(payload)
    r = get_redis()
    tasks_created = 0

    for ep in endpoints:
        # Create delivery attempt record
        attempt = DeliveryAttempt(
            event_id=event_id,
            endpoint_id=ep.id,
            user_id=user_id,
            event_type=event_type,
            payload=payload_str,
            status="pending",
        )
        db.add(attempt)
        db.commit()
        db.refresh(attempt)

        # Push to delivery queue
        task = json.dumps({
            "delivery_id": attempt.id,
            "event_id": event_id,
            "endpoint_id": ep.id,
            "endpoint_url": ep.endpoint_url,
            "secret": ep.secret,
            "payload": payload_str,
            "attempt_count": 0,
        })
        r.lpush(DELIVERY_QUEUE, task)
        tasks_created += 1
        logger.info(f"Enqueued delivery {attempt.id} for endpoint {ep.id}")

    return {
        "event_id": event_id,
        "status": "accepted",
        "message": f"Event dispatched to {tasks_created} endpoint(s)",
    }
