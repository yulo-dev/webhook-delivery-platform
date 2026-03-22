"""
Retry Scheduler
================
Separate process that periodically scans the delivery_attempts table
for events due for retry and re-enqueues them.

Run: python -m app.workers.retry_scheduler
"""
import json
import time
import logging
import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import redis
from app.core.config import REDIS_URL, DELIVERY_QUEUE, SCHEDULER_INTERVAL_SEC
from app.db.database import SessionLocal, init_db
from app.db.models import DeliveryAttempt, WebhookEndpoint

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SCHEDULER] %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def run_scheduler():
    init_db()
    r = redis.from_url(REDIS_URL, decode_responses=True)
    logger.info(f"🔄 Retry scheduler started (interval: {SCHEDULER_INTERVAL_SEC}s)")

    while True:
        db = SessionLocal()
        try:
            now = datetime.now(timezone.utc)

            # Find delivery attempts that are due for retry
            due = (
                db.query(DeliveryAttempt)
                .filter(
                    DeliveryAttempt.status == "retrying",
                    DeliveryAttempt.next_retry_at.isnot(None),
                    DeliveryAttempt.next_retry_at <= now,
                )
                .all()
            )

            if due:
                logger.info(f"Found {len(due)} events due for retry")

            for attempt in due:
                # Look up the endpoint to get URL and secret
                endpoint = (
                    db.query(WebhookEndpoint)
                    .filter(WebhookEndpoint.id == attempt.endpoint_id)
                    .first()
                )
                if not endpoint or endpoint.status != "active":
                    logger.warning(
                        f"Skipping retry for {attempt.id}: "
                        f"endpoint {attempt.endpoint_id} not active"
                    )
                    continue

                # Re-enqueue
                task = json.dumps({
                    "delivery_id": attempt.id,
                    "event_id": attempt.event_id,
                    "endpoint_id": endpoint.id,
                    "endpoint_url": endpoint.endpoint_url,
                    "secret": endpoint.secret,
                    "payload": attempt.payload,
                    "attempt_count": attempt.attempt_count,
                })
                r.lpush(DELIVERY_QUEUE, task)

                # Clear next_retry_at so we don't re-enqueue
                attempt.next_retry_at = None
                db.commit()

                logger.info(
                    f"🔁 Re-enqueued {attempt.id} (attempt #{attempt.attempt_count + 1})"
                )

        except Exception as e:
            logger.exception(f"Scheduler error: {e}")
        finally:
            db.close()

        time.sleep(SCHEDULER_INTERVAL_SEC)


if __name__ == "__main__":
    run_scheduler()
