import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Integer, Text, Enum as SAEnum
from app.db.database import Base


def new_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:12]}"


class WebhookEndpoint(Base):
    __tablename__ = "webhook_endpoints"

    id = Column(String, primary_key=True, default=lambda: new_id("ep_"))
    user_id = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)
    endpoint_url = Column(String, nullable=False)
    secret = Column(String, nullable=False)
    status = Column(String, default="active")  # active | inactive | suspended
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))


class DeliveryAttempt(Base):
    __tablename__ = "delivery_attempts"

    id = Column(String, primary_key=True, default=lambda: new_id("del_"))
    event_id = Column(String, nullable=False, index=True)
    endpoint_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    payload = Column(Text, nullable=False)
    status = Column(String, default="pending")  # pending | delivered | retrying | failed
    attempt_count = Column(Integer, default=0)
    response_code = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    next_retry_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))


class DeadLetterEvent(Base):
    __tablename__ = "dead_letter_events"

    id = Column(String, primary_key=True, default=lambda: new_id("dlq_"))
    event_id = Column(String, nullable=False, index=True)
    endpoint_id = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    payload = Column(Text, nullable=False)
    final_error = Column(Text, nullable=True)
    attempt_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
