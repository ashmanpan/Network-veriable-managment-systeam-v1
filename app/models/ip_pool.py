from sqlalchemy import Column, Integer, String, BigInteger, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class IPPool(Base):
    __tablename__ = "ip_pools"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text)
    pool_type = Column(String(10), nullable=False)  # 'ipv4' or 'ipv6'
    cidr = Column(String(50), nullable=False)
    network_address = Column(String(50), nullable=False)
    broadcast_address = Column(String(50))
    total_addresses = Column(String(50), nullable=False)  # Changed to String for IPv6 support
    usable_addresses = Column(String(50), nullable=False)  # Changed to String for IPv6 support
    next_available_index = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    allocations = relationship("IPAllocation", back_populates="pool", cascade="all, delete-orphan")


class IPAllocation(Base):
    __tablename__ = "ip_allocations"

    id = Column(Integer, primary_key=True, index=True)
    pool_id = Column(Integer, ForeignKey("ip_pools.id", ondelete="CASCADE"), nullable=False)
    # Block allocation info
    allocated_cidr = Column(String(50), nullable=False)  # e.g., "10.0.0.4/30"
    network_address = Column(String(50), nullable=False)  # e.g., "10.0.0.4"
    prefix_length = Column(Integer, nullable=False)  # e.g., 30
    block_size = Column(Integer, nullable=False)  # e.g., 4
    # Metadata
    description = Column(Text)
    allocated_to = Column(String(255))
    status = Column(String(20), default="allocated")  # 'allocated', 'reserved', 'released'
    allocated_at = Column(DateTime(timezone=True), server_default=func.now())
    released_at = Column(DateTime(timezone=True))

    pool = relationship("IPPool", back_populates="allocations")

    class Config:
        unique_together = [("pool_id", "allocated_cidr")]
