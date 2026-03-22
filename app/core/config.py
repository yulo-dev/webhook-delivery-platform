import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./webhook.db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QUEUE_NAME = "webhook:event_queue"
DELIVERY_QUEUE = "webhook:delivery_queue"
MAX_IMMEDIATE_RETRIES = 5
RETRY_SLA_HOURS = 72  # 3 days
SCHEDULER_INTERVAL_SEC = 60
