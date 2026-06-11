"""
App 1 — Product Verification System
FastAPI entry point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from database import engine
from models import Base
from routers import upload, verify, reports

# Create all tables on startup (safe to call repeatedly — skips existing tables)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Product Verification API",
    description="Bulk CSV ingest, WID-based product lookup, and verification audit logs.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # tighten to your Streamlit URL in production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    BaseHTTPMiddleware,
    dispatch=lambda req, call_next: call_next(req)
)

app.include_router(upload.router)
app.include_router(verify.router)
app.include_router(reports.router)


@app.get("/health")
def health():
    return {"status": "ok"}
