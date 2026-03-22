from sqlalchemy.orm import Session
from app.db.models import WebhookEndpoint
from app.services.signing_service import generate_secret
from app.schemas.webhook import WebhookCreate, WebhookUpdate


def create_endpoint(db: Session, data: WebhookCreate) -> WebhookEndpoint:
    ep = WebhookEndpoint(
        user_id=data.user_id,
        event_type=data.event_type,
        endpoint_url=data.endpoint,
        secret=generate_secret(),
        status="active",
    )
    db.add(ep)
    db.commit()
    db.refresh(ep)
    return ep


def get_endpoint(db: Session, endpoint_id: str) -> WebhookEndpoint | None:
    return db.query(WebhookEndpoint).filter(WebhookEndpoint.id == endpoint_id).first()


def list_endpoints(db: Session, user_id: str | None = None) -> list[WebhookEndpoint]:
    q = db.query(WebhookEndpoint)
    if user_id:
        q = q.filter(WebhookEndpoint.user_id == user_id)
    return q.order_by(WebhookEndpoint.created_at.desc()).all()


def update_endpoint(db: Session, endpoint_id: str, data: WebhookUpdate) -> WebhookEndpoint | None:
    ep = get_endpoint(db, endpoint_id)
    if not ep:
        return None
    if data.endpoint is not None:
        ep.endpoint_url = data.endpoint
    if data.status is not None:
        ep.status = data.status
    db.commit()
    db.refresh(ep)
    return ep


def delete_endpoint(db: Session, endpoint_id: str) -> bool:
    ep = get_endpoint(db, endpoint_id)
    if not ep:
        return False
    db.delete(ep)
    db.commit()
    return True


def find_endpoints_for_event(db: Session, user_id: str, event_type: str) -> list[WebhookEndpoint]:
    """Find all active endpoints registered for this user + event_type."""
    return (
        db.query(WebhookEndpoint)
        .filter(
            WebhookEndpoint.user_id == user_id,
            WebhookEndpoint.event_type == event_type,
            WebhookEndpoint.status == "active",
        )
        .all()
    )
