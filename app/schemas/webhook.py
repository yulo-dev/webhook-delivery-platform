from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional


class WebhookCreate(BaseModel):
    event_type: str
    endpoint: str  # URL string
    user_id: str


class WebhookUpdate(BaseModel):
    endpoint: Optional[str] = None
    status: Optional[str] = None


class WebhookResponse(BaseModel):
    id: str
    user_id: str
    event_type: str
    endpoint_url: str
    status: str
    secret: str
    created_at: datetime

    model_config = {"from_attributes": True}
