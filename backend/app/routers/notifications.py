from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_vendor
from app.database import get_db
from app.models import Notification, Vendor
from app.schemas import NotificationOut

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
def list_my_notifications(vendor: Vendor = Depends(get_current_vendor), db: Session = Depends(get_db)):
    return (
        db.query(Notification)
        .filter(Notification.vendor_id == vendor.id, Notification.is_deleted.is_(False))
        .order_by(Notification.server_date.desc())
        .all()
    )


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_read(notification_id: int, vendor: Vendor = Depends(get_current_vendor), db: Session = Depends(get_db)):
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.vendor_id == vendor.id)
        .first()
    )
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification
