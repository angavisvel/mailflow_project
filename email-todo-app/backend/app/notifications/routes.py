from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import User, Notification
from app.auth.jwt_handler import get_current_user
from app.notifications.service import check_deadlines_and_generate_alerts

router = APIRouter()

class NotificationUpdateSchema(BaseModel):
    is_read: Optional[bool] = True

@router.post("/scan-alerts")
def trigger_alert_scan(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Scans pending tasks and generates notifications for upcoming/overdue deadlines."""
    new_alerts = check_deadlines_and_generate_alerts(user.id, db)
    return {
        "status": "success",
        "new_alerts_count": len(new_alerts),
        "alerts": [
            {
                "id": a.id,
                "title": a.title,
                "type": a.type,
                "task_id": a.task_id
            } for a in new_alerts
        ]
    }

@router.get("/")
def get_notifications(
    unread_only: bool = Query(False, description="Filter to unread notifications only"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetches user notifications sorted by creation date."""
    query = db.query(Notification).filter(Notification.user_id == user.id)
    if unread_only:
        query = query.filter(Notification.is_read == False)
    
    return query.order_by(Notification.created_at.desc()).all()

@router.patch("/{notification_id}/mark-read")
def mark_notification_read(
    notification_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    notice = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == user.id)
        .first()
    )
    if not notice:
        raise HTTPException(status_code=404, detail="Notification not found.")

    notice.is_read = True
    db.commit()
    db.refresh(notice)
    return notice