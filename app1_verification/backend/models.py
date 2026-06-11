from sqlalchemy import (
    Column, String, Date, DateTime, Integer,
    ForeignKey, Index, func
)
from sqlalchemy.orm import relationship
from database import Base


class Product(Base):
    """
    One row per physical warehouse item.
    WID is the primary key — uniqueness enforced at DB level.
    """
    __tablename__ = "products"

    wid                = Column(String, primary_key=True, index=True)
    ean                = Column(String, nullable=False, index=True)   # barcode ID
    manufacturing_date = Column(Date, nullable=False)
    expiry_date        = Column(Date, nullable=False)

    logs = relationship("VerificationLog", back_populates="product")


class VerificationLog(Base):
    """
    Immutable audit log — every scan event is appended, never updated.
    """
    __tablename__ = "verification_logs"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    wid        = Column(String, ForeignKey("products.wid"), nullable=False)
    username   = Column(String, nullable=False)         # who scanned
    checked_at = Column(DateTime, server_default=func.now(), nullable=False)
    photo_url  = Column(String, nullable=True)          # Cloudinary secure URL

    product = relationship("Product", back_populates="logs")

    __table_args__ = (
        Index("ix_logs_checked_at", "checked_at"),
        Index("ix_logs_wid_checked_at", "wid", "checked_at"),
    )


class ImportJob(Base):
    """
    Tracks background CSV import progress.
    Frontend polls /jobs/{id} to show a live progress bar.
    """
    __tablename__ = "import_jobs"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    filename       = Column(String, nullable=False)
    status         = Column(String, default="pending")   # pending|processing|done|failed
    total_rows     = Column(Integer, default=0)
    processed_rows = Column(Integer, default=0)
    inserted_rows  = Column(Integer, default=0)
    duplicate_rows = Column(Integer, default=0)
    error_message  = Column(String, nullable=True)
    created_at     = Column(DateTime, server_default=func.now())
    finished_at    = Column(DateTime, nullable=True)
