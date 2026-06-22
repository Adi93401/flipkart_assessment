import csv
import os
import tempfile
from datetime import datetime, date
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import text
import aiofiles
from sqlalchemy.orm import Session

from database import get_db, engine
from models import ImportJob

router = APIRouter(prefix="/api", tags=["upload"])

CHUNK_SIZE = 5_000   # rows committed per transaction


class RecentUploadOut(BaseModel):
    id: int
    filename: str
    status: str
    uploaded_by: Optional[str] = None
    total_rows: int
    processed_rows: int
    inserted_rows: int
    duplicate_rows: int
    created_at: datetime
    finished_at: Optional[datetime] = None


# ── helpers ────────────────────────────────────────────────────────────────

def _count_rows(path: str) -> int:
    """Count data rows (excluding header) without loading into memory."""
    count = 0
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        next(reader, None)      # skip header
        for _ in reader:
            count += 1
    return count


def _parse_date(value: str) -> date:
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognised date format: {value!r}")


def _process_csv(job_id: int, tmp_path: str):
    """
    Background thread: streams the CSV in chunks and upserts rows.
    Uses raw SQL for INSERT … ON CONFLICT DO NOTHING so a single
    duplicate WID does NOT abort the whole batch.
    """
    from database import SessionLocal

    db = SessionLocal()
    job = db.get(ImportJob, job_id)
    if not job:
        return

    job.status = "processing"
    job.total_rows = _count_rows(tmp_path)
    db.commit()

    inserted = 0
    duplicates = 0
    processed = 0
    chunk: list[dict] = []

    def flush(chunk):
        nonlocal inserted, duplicates
        if not chunk:
            return
        # PostgreSQL / SQLite both support ON CONFLICT DO NOTHING
        stmt = text("""
            INSERT INTO products (wid, ean, manufacturing_date, expiry_date)
            VALUES (:wid, :ean, :manufacturing_date, :expiry_date)
            ON CONFLICT (wid) DO NOTHING
        """)
        result = db.execute(stmt, chunk)
        db.commit()
        inserted   += result.rowcount
        duplicates += len(chunk) - result.rowcount

    try:
        with open(tmp_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            expected = {"WID", "EAN", "Manufacturing_Date", "Expiry_Date"}
            if not expected.issubset(set(reader.fieldnames or [])):
                raise ValueError(f"CSV missing columns. Expected: {expected}")

            for row in reader:
                chunk.append({
                    "wid":               row["WID"].strip(),
                    "ean":               row["EAN"].strip(),
                    "manufacturing_date": _parse_date(row["Manufacturing_Date"]),
                    "expiry_date":        _parse_date(row["Expiry_Date"]),
                })
                processed += 1

                if len(chunk) >= CHUNK_SIZE:
                    flush(chunk)
                    chunk.clear()
                    job.processed_rows = processed
                    job.inserted_rows  = inserted
                    job.duplicate_rows = duplicates
                    db.commit()

            flush(chunk)   # final partial chunk

        job.processed_rows = processed
        job.inserted_rows  = inserted
        job.duplicate_rows = duplicates
        job.status         = "done"
        job.finished_at    = datetime.utcnow()

    except Exception as exc:
        db.rollback()
        job.status        = "failed"
        job.error_message = str(exc)
        job.finished_at   = datetime.utcnow()

    finally:
        db.commit()
        db.close()
        try:
            os.remove(tmp_path)
        except OSError:
            pass


# ── endpoints ───────────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    username: str = Form(default=""),
    db: Session = Depends(get_db),
):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
    tmp.close()

    # Stream the incoming bytes to disk in 1 MB chunks
    # Never loads the full 450 MB into RAM
    async with aiofiles.open(tmp.name, "wb") as f:
        while chunk := await file.read(1024 * 1024):   # 1 MB at a time
            await f.write(chunk)

    job = ImportJob(
        filename=file.filename,
        status="pending",
        uploaded_by=username.strip() or "Unknown",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(_process_csv, job.id, tmp.name)
    return {
        "job_id": job.id,
        "message": "Upload accepted.",
        "uploaded_by": job.uploaded_by,
    }


@router.get("/uploads", response_model=list[RecentUploadOut])
def list_uploads(limit: int = 10, db: Session = Depends(get_db)):
    rows = db.query(ImportJob).order_by(ImportJob.created_at.desc()).limit(limit).all()
    return [
        RecentUploadOut(
            id=row.id,
            filename=row.filename,
            status=row.status,
            uploaded_by=row.uploaded_by,
            total_rows=row.total_rows,
            processed_rows=row.processed_rows,
            inserted_rows=row.inserted_rows,
            duplicate_rows=row.duplicate_rows,
            created_at=row.created_at,
            finished_at=row.finished_at,
        )
        for row in rows
    ]


@router.get("/jobs/{job_id}")
def get_job_status(job_id: int, db: Session = Depends(get_db)):
    """Poll this endpoint to track background import progress."""
    job = db.get(ImportJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    pct = 0
    if job.total_rows and job.total_rows > 0:
        pct = round((job.processed_rows / job.total_rows) * 100, 1)

    return {
        "job_id":        job.id,
        "filename":      job.filename,
        "status":        job.status,
        "total_rows":    job.total_rows,
        "processed_rows": job.processed_rows,
        "inserted_rows": job.inserted_rows,
        "duplicate_rows": job.duplicate_rows,
        "progress_pct":  pct,
        "error_message": job.error_message,
        "created_at":    job.created_at,
        "finished_at":   job.finished_at,
    }
