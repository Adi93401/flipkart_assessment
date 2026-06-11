"""
POD router
──────────
POST /api/deliveries          → log a new POD event (AWB + media URL + driver)
GET  /api/deliveries          → list all deliveries (paginated)
GET  /api/deliveries/{awb}    → list deliveries for a specific AWB
POST /api/media/upload        → upload photo/video to Cloudinary, return URL
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from cloudinary_helper import upload_media
from database import get_db
from models import Delivery

router = APIRouter(prefix="/api", tags=["pod"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/quicktime", "video/webm"}


# ── schemas ──────────────────────────────────────────────────────────────────

class DeliveryIn(BaseModel):
    awb:         str
    driver_name: str
    media_url:   str
    media_type:  str
    notes:       Optional[str] = None


class DeliveryOut(BaseModel):
    id:          int
    awb:         str
    driver_name: str
    media_url:   str
    media_type:  str
    captured_at: datetime
    notes:       Optional[str]

    class Config:
        from_attributes = True


# ── endpoints ────────────────────────────────────────────────────────────────

@router.post("/media/upload")
async def upload_pod_media(file: UploadFile = File(...)):
    """
    Upload a photo or short video to Cloudinary.
    Returns the secure URL to be stored with the delivery record.
    """
    content_type = file.content_type or ""

    if content_type in ALLOWED_IMAGE_TYPES:
        resource_type = "image"
    elif content_type in ALLOWED_VIDEO_TYPES:
        resource_type = "video"
    else:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported media type: {content_type}. "
                   f"Allowed: JPEG, PNG, WEBP images or MP4/MOV/WEBM videos.",
        )

    file_bytes = await file.read()
    url = upload_media(file_bytes, resource_type=resource_type, folder="pod")
    return {"media_url": url, "media_type": resource_type}


@router.post("/deliveries", response_model=DeliveryOut, status_code=201)
def create_delivery(body: DeliveryIn, db: Session = Depends(get_db)):
    """Persist a completed POD event."""
    delivery = Delivery(
        awb=body.awb.strip().upper(),
        driver_name=body.driver_name.strip(),
        media_url=body.media_url,
        media_type=body.media_type,
        notes=body.notes,
    )
    db.add(delivery)
    db.commit()
    db.refresh(delivery)
    return delivery


@router.get("/deliveries", response_model=dict)
def list_deliveries(
    page:  int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """List all deliveries, most recent first, paginated."""
    q     = db.query(Delivery).order_by(Delivery.captured_at.desc())
    total = q.count()
    rows  = q.offset((page - 1) * limit).limit(limit).all()
    return {
        "page":        page,
        "limit":       limit,
        "total_count": total,
        "total_pages": -(-total // limit),
        "deliveries":  [DeliveryOut.from_orm(r) for r in rows],
    }


@router.get("/deliveries/{awb}", response_model=List[DeliveryOut])
def get_deliveries_by_awb(awb: str, db: Session = Depends(get_db)):
    """Fetch all POD records for a given AWB number."""
    rows = (
        db.query(Delivery)
        .filter(Delivery.awb == awb.strip().upper())
        .order_by(Delivery.captured_at.desc())
        .all()
    )
    if not rows:
        raise HTTPException(status_code=404, detail=f"No deliveries found for AWB '{awb}'.")
    return rows
