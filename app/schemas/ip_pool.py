from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum
import ipaddress


class PoolType(str, Enum):
    ipv4 = "ipv4"
    ipv6 = "ipv6"


class IPPoolCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Unique pool name")
    description: Optional[str] = Field(None, description="Purpose/description of this pool")
    pool_type: PoolType = Field(..., description="Type of IP pool: ipv4 or ipv6")
    cidr: str = Field(..., description="CIDR notation e.g., 192.168.1.0/24 or 2001:db8::/64")

    @field_validator("cidr")
    @classmethod
    def validate_cidr(cls, v: str, info) -> str:
        try:
            network = ipaddress.ip_network(v, strict=False)
            return str(network)
        except ValueError as e:
            raise ValueError("Invalid CIDR notation")


class IPPoolResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    pool_type: str
    cidr: str
    network_address: str
    broadcast_address: Optional[str]
    total_addresses: int | str  # Support both int (IPv4) and str (IPv6)
    usable_addresses: int | str  # Support both int (IPv4) and str (IPv6)
    allocated_count: int = 0
    available_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class IPPoolDetail(IPPoolResponse):
    allocations: List["IPAllocationResponse"] = []


class IPAllocationRequest(BaseModel):
    prefix_length: int = Field(
        ...,
        description="Requested subnet prefix length (e.g., 30 for /30 = 4 IPs, 32 for /32 = 1 IP)"
    )
    description: Optional[str] = Field(None, description="Description/purpose for this allocation")
    allocated_to: Optional[str] = Field(None, max_length=255, description="Client/service identifier")

    @field_validator("prefix_length")
    @classmethod
    def validate_prefix(cls, v: int) -> int:
        # IPv4: 0-32, IPv6: 0-128 (will be validated against pool type in service)
        if not (0 <= v <= 128):
            raise ValueError("prefix_length must be between 0 and 128")
        return v


class IPAllocationResponse(BaseModel):
    id: int
    # Allocated block info
    allocated_cidr: str  # The allocated subnet (e.g., "10.0.0.4/30")
    network_address: str  # First IP of block (e.g., "10.0.0.4")
    broadcast_address: Optional[str]  # Last IP for IPv4 (e.g., "10.0.0.7")
    ip_addresses: List[str]  # All IPs in the block
    block_size: int  # Number of IPs (e.g., 4 for /30)
    # Pool info
    pool_name: str
    pool_type: str  # 'ipv4' or 'ipv6'
    pool_cidr: str  # Full CIDR of the parent pool (e.g., "10.0.0.0/24")
    prefix_length: int  # Allocated prefix (e.g., 30)
    subnet_mask: Optional[str]  # Dotted decimal for IPv4 (e.g., "255.255.255.252")
    # Allocation metadata
    description: Optional[str]
    allocated_to: Optional[str]
    status: str
    allocated_at: datetime

    class Config:
        from_attributes = True


class IPReleaseRequest(BaseModel):
    allocated_cidr: str = Field(..., description="Allocated CIDR to release (e.g., '10.0.0.4/30')")

    @field_validator("allocated_cidr")
    @classmethod
    def validate_cidr(cls, v: str) -> str:
        try:
            ipaddress.ip_network(v, strict=False)
            return v
        except ValueError as e:
            raise ValueError("Invalid CIDR")


class IPAllocationListResponse(BaseModel):
    pool_name: str
    total_allocations: int
    allocations: List[IPAllocationResponse]


# Update forward references
IPPoolDetail.model_rebuild()
