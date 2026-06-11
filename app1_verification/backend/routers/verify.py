"""
Verify router
─────────────
GET  /verify/{wid}         → look up product details by WID
POST /verify/{wid}/log     → record a verification event (user + optional photo)
POST /verify/{wid}/upload-photo → upload photo bytes, return Cloudinary URL
"""

from datetime import date as date_type
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from cloudinary_helper import upload_image
from database import get_db
from models import Product, VerificationLog

router = APIRouter(prefix="/api", tags=["verify"])


# ── schemas ─────────────────────────────────────────────────────────────────

class LogRequest(BaseModel):
    username:  str
    photo_url: Optional[str] = None


class ProductOut(BaseModel):
    wid:                str
    ean:                str
    manufacturing_date: date_type
    expiry_date:        date_type
    days_to_expiry:     int
    status:             str   # "ok" | "expiring_soon" | "expired"

    class Config:
        from_attributes = True


# ── helpers ─────────────────────────────────────────────────────────────────

def _expiry_status(expiry: date_type) -> tuple[int, str]:
    today = date_type.today()
    delta = (expiry - today).days
    if delta < 0:
        return delta, "expired"
    if delta <= 30:
        return delta, "expiring_soon"
    return delta, "ok"


# ── endpoints ────────────────────────────────────────────────────────────────

@router.get("/verify/{wid}", response_model=ProductOut)
def get_product(wid: str, db: Session = Depends(get_db)):
    """Return product details for a given WID."""
    product = db.get(Product, wid)
    if not product:
        raise HTTPException(status_code=404, detail=f"WID '{wid}' not found.")

    days, status = _expiry_status(product.expiry_date)
    return ProductOut(
        wid=product.wid,
        ean=product.ean,
        manufacturing_date=product.manufacturing_date,
        expiry_date=product.expiry_date,
        days_to_expiry=days,
        status=status,
    )


@router.post("/verify/{wid}/log")
def log_verification(wid: str, body: LogRequest, db: Session = Depends(get_db)):
    """Append an immutable verification event to the audit log."""
    if not db.get(Product, wid):
        raise HTTPException(status_code=404, detail=f"WID '{wid}' not found.")

    log = VerificationLog(
        wid=wid,
        username=body.username.strip(),
        photo_url=body.photo_url,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return {"log_id": log.id, "message": "Verification logged."}


@router.post("/verify/{wid}/upload-photo")
async def upload_photo(
    wid: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a product inspection photo to Cloudinary and return its URL."""
    if not db.get(Product, wid):
        raise HTTPException(status_code=404, detail=f"WID '{wid}' not found.")

    content = await file.read()
    url = upload_image(content, folder=f"verification/{wid}")
    return {"photo_url": url}
