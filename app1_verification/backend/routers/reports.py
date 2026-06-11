"""
Reports router
──────────────
GET /report
  Query params:
    start   (date, required)  — inclusive lower bound
    end     (date, required)  — inclusive upper bound
    page    (int, default 1)
    limit   (int, default 100, max 1000)

Returns paginated verification logs with product details joined.
"""

from datetime import date, datetime, time
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models import VerificationLog

router = APIRouter(prefix="/api", tags=["reports"])


class LogEntry(BaseModel):
    log_id:             int
    wid:                str
    ean:                str
    manufacturing_date: date
    expiry_date:        date
    username:           str
    checked_at:         datetime
    photo_url:          Optional[str]

    class Config:
        from_attributes = True


class ReportResponse(BaseModel):
    start:       date
    end:         date
    page:        int
    limit:       int
    total_count: int
    total_pages: int
    logs:        List[LogEntry]


@router.get("/report", response_model=ReportResponse)
def get_report(
    start: date = Query(..., description="Start date (YYYY-MM-DD), inclusive"),
    end:   date = Query(..., description="End date (YYYY-MM-DD), inclusive"),
    page:  int  = Query(1, ge=1),
    limit: int  = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    if start > end:
        raise HTTPException(status_code=400, detail="'start' must be ≤ 'end'.")

    # Convert to full-day datetimes for the inclusive range
    dt_start = datetime.combine(start, time.min)
    dt_end   = datetime.combine(end,   time.max)

    base_q = (
        db.query(VerificationLog)
        .options(joinedload(VerificationLog.product))
        .filter(
            and_(
                VerificationLog.checked_at >= dt_start,
                VerificationLog.checked_at <= dt_end,
            )
        )
        .order_by(VerificationLog.checked_at.desc())
    )

    total = base_q.count()
    rows  = base_q.offset((page - 1) * limit).limit(limit).all()

    entries = [
        LogEntry(
            log_id=r.id,
            wid=r.wid,
            ean=r.product.ean,
            manufacturing_date=r.product.manufacturing_date,
            expiry_date=r.product.expiry_date,
            username=r.username,
            checked_at=r.checked_at,
            photo_url=r.photo_url,
        )
        for r in rows
    ]

    return ReportResponse(
        start=start,
        end=end,
        page=page,
        limit=limit,
        total_count=total,
        total_pages=-(-total // limit),   # ceiling division
        logs=entries,
    )
