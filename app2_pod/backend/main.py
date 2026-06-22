"""
App 2 — Proof of Delivery (POD)
FastAPI entry point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine
from models import Base
from routers.pod import router as pod_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="POD API",
    description="Scan AWB, upload proof-of-delivery media, and retrieve delivery history.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pod_router)


@app.get("/health")
def health():
    return {"status": "ok"}


# uvicorn main:app --host 0.0.0.0 --port 8001 --timeout-keep-alive 300 --limit-max-requests 0