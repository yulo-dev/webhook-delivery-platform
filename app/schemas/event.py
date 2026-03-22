from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Any


class EventCreate(BaseModel):
    user_id: str
    event_type: str
    payload: dict


class EventResponse(BaseModel):
    event_id: str
    status: str
    message: str


class DeliveryResponse(BaseModel):
    id: str
    event_id: str
    endpoint_id: str
    status: str
    attempt_count: int
    response_code: Optional[int]
    error_message: Optional[str]
    next_retry_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class DLQResponse(BaseModel):
    id: str
    event_id: str
    endpoint_id: str
    event_type: str
    final_error: Optional[str]
    attempt_count: int
    created_at: datetime

    model_config = {"from_attributes": True}
