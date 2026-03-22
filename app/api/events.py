from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.event import EventCreate, EventResponse
from app.services.ingestion_service import ingest_event

router = APIRouter(prefix="/v1/events", tags=["Events"])


@router.post("", response_model=EventResponse, status_code=202)
def publish_event(data: EventCreate, db: Session = Depends(get_db)):
    """
    Ingest an event from an internal service.
    The platform will fan-out to all registered endpoints.
    """
    result = ingest_event(db, data.user_id, data.event_type, data.payload)
    return EventResponse(**result)
