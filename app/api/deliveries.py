from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import DeliveryAttempt, DeadLetterEvent
from app.schemas.event import DeliveryResponse, DLQResponse

router = APIRouter(prefix="/v1/deliveries", tags=["Deliveries"])


@router.get("", response_model=list[DeliveryResponse])
def list_deliveries(
    event_id: str | None = None,
    endpoint_id: str | None = None,
    status: str | None = None,
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
):
    """List delivery attempts with optional filters."""
    q = db.query(DeliveryAttempt)
    if event_id:
        q = q.filter(DeliveryAttempt.event_id == event_id)
    if endpoint_id:
        q = q.filter(DeliveryAttempt.endpoint_id == endpoint_id)
    if status:
        q = q.filter(DeliveryAttempt.status == status)
    return q.order_by(DeliveryAttempt.created_at.desc()).limit(limit).all()


@router.get("/dlq", response_model=list[DLQResponse])
def list_dlq(
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
):
    """List events in the Dead Letter Queue."""
    return (
        db.query(DeadLetterEvent)
        .order_by(DeadLetterEvent.created_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/stats")
def delivery_stats(db: Session = Depends(get_db)):
    """Get delivery statistics."""
    total = db.query(DeliveryAttempt).count()
    delivered = db.query(DeliveryAttempt).filter(DeliveryAttempt.status == "delivered").count()
    retrying = db.query(DeliveryAttempt).filter(DeliveryAttempt.status == "retrying").count()
    failed = db.query(DeliveryAttempt).filter(DeliveryAttempt.status == "failed").count()
    dlq_count = db.query(DeadLetterEvent).count()
    return {
        "total_attempts": total,
        "delivered": delivered,
        "retrying": retrying,
        "failed": failed,
        "dlq": dlq_count,
        "success_rate": f"{(delivered / total * 100):.1f}%" if total > 0 else "N/A",
    }
