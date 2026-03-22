"""
Delivery Worker
================
Separate process that consumes from the delivery queue
and sends webhooks to registered endpoints.

Run: python -m app.workers.delivery_worker
"""
import json
import time
import logging
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import redis
from app.core.config import REDIS_URL, DELIVERY_QUEUE, MAX_IMMEDIATE_RETRIES
from app.db.database import SessionLocal, init_db
from app.services.delivery_service import deliver_webhook, compute_backoff

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [WORKER] %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def run_worker():
    init_db()
    r = redis.from_url(REDIS_URL, decode_responses=True)
    logger.info(f"🚀 Delivery worker started, listening on {DELIVERY_QUEUE}")

    while True:
        # Blocking pop from queue (timeout 5s)
        result = r.brpop(DELIVERY_QUEUE, timeout=5)
        if result is None:
            continue

        _, raw = result
        try:
            task = json.loads(raw)
        except json.JSONDecodeError:
            logger.error(f"Invalid task JSON: {raw}")
            continue

        delivery_id = task["delivery_id"]
        endpoint_url = task["endpoint_url"]
        secret = task["secret"]
        payload = task["payload"]
        attempt_count = task.get("attempt_count", 0)

        logger.info(
            f"📨 Processing delivery {delivery_id} → {endpoint_url} "
            f"(attempt {attempt_count + 1})"
        )

        db = SessionLocal()
        try:
            result = deliver_webhook(
                db, delivery_id, endpoint_url, secret, payload, attempt_count
            )

            if result["status"] == "retrying" and attempt_count + 1 < MAX_IMMEDIATE_RETRIES:
                # Re-enqueue with backoff delay
                backoff = compute_backoff(attempt_count)
                logger.info(f"⏳ Backing off {backoff:.2f}s before retry")
                time.sleep(backoff)

                task["attempt_count"] = attempt_count + 1
                r.lpush(DELIVERY_QUEUE, json.dumps(task))

            elif result["status"] == "delivered":
                logger.info(f"✅ {delivery_id} delivered successfully")

            elif result["status"] in ("dlq", "scheduled_retry"):
                logger.info(f"📋 {delivery_id} → {result['status']}")

        except Exception as e:
            logger.exception(f"Worker error processing {delivery_id}: {e}")
        finally:
            db.close()


if __name__ == "__main__":
    run_worker()
