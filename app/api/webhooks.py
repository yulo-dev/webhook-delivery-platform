from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.webhook import WebhookCreate, WebhookUpdate, WebhookResponse
from app.services import registration_service as svc

router = APIRouter(prefix="/v1/webhook", tags=["Webhooks"])


@router.post("", response_model=WebhookResponse, status_code=201)
def register_endpoint(data: WebhookCreate, db: Session = Depends(get_db)):
    """Register a new webhook endpoint for a given event type."""
    ep = svc.create_endpoint(db, data)
    return ep


@router.get("", response_model=list[WebhookResponse])
def list_endpoints(user_id: str | None = None, db: Session = Depends(get_db)):
    """List all webhook endpoints, optionally filtered by user_id."""
    return svc.list_endpoints(db, user_id)


@router.get("/{endpoint_id}", response_model=WebhookResponse)
def get_endpoint(endpoint_id: str, db: Session = Depends(get_db)):
    """Get a specific webhook endpoint by ID."""
    ep = svc.get_endpoint(db, endpoint_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    return ep


@router.put("/{endpoint_id}", response_model=WebhookResponse)
def update_endpoint(endpoint_id: str, data: WebhookUpdate, db: Session = Depends(get_db)):
    """Update an existing webhook endpoint."""
    ep = svc.update_endpoint(db, endpoint_id, data)
    if not ep:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    return ep


@router.delete("/{endpoint_id}")
def delete_endpoint(endpoint_id: str, db: Session = Depends(get_db)):
    """Delete a webhook endpoint."""
    success = svc.delete_endpoint(db, endpoint_id)
    if not success:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    return {"status": "deleted", "id": endpoint_id}
