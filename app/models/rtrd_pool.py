from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class RTRDPool(Base):
    __tablename__ = "rtrd_pools"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text)
    pool_type = Column(String(10), nullable=False)  # 'rt' or 'rd'
    format_type = Column(Integer, nullable=False)  # 0, 1, or 2
    admin_value = Column(String(50), nullable=False)  # ASN or IP address
    range_start = Column(Integer, nullable=False)
    range_end = Column(Integer, nullable=False)
    next_available = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    allocations = relationship("RTRDAllocation", back_populates="pool", cascade="all, delete-orphan")


class RTRDAllocation(Base):
    __tablename__ = "rtrd_allocations"

    id = Column(Integer, primary_key=True, index=True)
    pool_id = Column(Integer, ForeignKey("rtrd_pools.id", ondelete="CASCADE"), nullable=False)
    value = Column(String(50), nullable=False)  # e.g., '65000:1001'
    assigned_number = Column(Integer, nullable=False)
    description = Column(Text)
    allocated_to = Column(String(255))
    status = Column(String(20), default="allocated")  # 'allocated', 'reserved', 'released'
    allocated_at = Column(DateTime(timezone=True), server_default=func.now())
    released_at = Column(DateTime(timezone=True))

    pool = relationship("RTRDPool", back_populates="allocations")

    class Config:
        unique_together = [("pool_id", "assigned_number")]
