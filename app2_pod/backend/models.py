from sqlalchemy import Column, String, DateTime, Integer, Index, func
from database import Base


class Delivery(Base):
    """
    One row per POD event.
    An AWB can have multiple deliveries (re-attempts, partial loads).
    """
    __tablename__ = "deliveries"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    awb         = Column(String, nullable=False)
    driver_name = Column(String, nullable=False)
    media_url   = Column(String, nullable=False)    # Cloudinary secure URL
    media_type  = Column(String, nullable=False)    # "image" | "video"
    captured_at = Column(DateTime, server_default=func.now(), nullable=False)
    notes       = Column(String, nullable=True)

    __table_args__ = (
        Index("ix_deliveries_awb", "awb"),
        Index("ix_deliveries_captured_at", "captured_at"),
    )
