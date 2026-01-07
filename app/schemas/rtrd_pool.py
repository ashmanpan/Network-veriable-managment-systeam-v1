from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum
import ipaddress


class RTRDPoolType(str, Enum):
    rt = "rt"  # Route Target
    rd = "rd"  # Route Distinguisher


class FormatType(int, Enum):
    TYPE_0 = 0  # 2-byte ASN : 4-byte number
    TYPE_1 = 1  # 4-byte IP : 2-byte number
    TYPE_2 = 2  # 4-byte ASN : 2-byte number


class RTRDPoolCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Unique pool name")
    description: Optional[str] = Field(None, description="Purpose/description of this pool")
    pool_type: RTRDPoolType = Field(..., description="Type: rt (Route Target) or rd (Route Distinguisher)")
    format_type: FormatType = Field(..., description="Format type: 0 (ASN:num), 1 (IP:num), 2 (4-byte ASN:num)")
    admin_value: str = Field(..., description="Administrative value: ASN or IP address")
    range_start: int = Field(..., ge=0, description="Start of assigned number range")
    range_end: int = Field(..., ge=0, description="End of assigned number range")

    @field_validator("admin_value")
    @classmethod
    def validate_admin_value(cls, v: str, info) -> str:
        return v.strip()

    @model_validator(mode="after")
    def validate_format_and_ranges(self):
        # Validate admin_value based on format_type
        if self.format_type == FormatType.TYPE_0:
            # 2-byte ASN: 1-65535
            try:
                asn = int(self.admin_value)
                if not (1 <= asn <= 65535):
                    raise ValueError("Type 0 ASN must be between 1 and 65535")
            except ValueError:
                raise ValueError("Type 0 admin_value must be a valid 2-byte ASN (1-65535)")
            # 4-byte number range: 0-4294967295
            if not (0 <= self.range_start <= 4294967295) or not (0 <= self.range_end <= 4294967295):
                raise ValueError("Type 0 range must be between 0 and 4294967295")

        elif self.format_type == FormatType.TYPE_1:
            # IP address validation
            try:
                ipaddress.ip_address(self.admin_value)
            except ValueError:
                raise ValueError("Type 1 admin_value must be a valid IP address")
            # 2-byte number range: 0-65535
            if not (0 <= self.range_start <= 65535) or not (0 <= self.range_end <= 65535):
                raise ValueError("Type 1 range must be between 0 and 65535")

        elif self.format_type == FormatType.TYPE_2:
            # 4-byte ASN: 1-4294967295
            try:
                asn = int(self.admin_value)
                if not (1 <= asn <= 4294967295):
                    raise ValueError("Type 2 ASN must be between 1 and 4294967295")
            except ValueError:
                raise ValueError("Type 2 admin_value must be a valid 4-byte ASN")
            # 2-byte number range: 0-65535
            if not (0 <= self.range_start <= 65535) or not (0 <= self.range_end <= 65535):
                raise ValueError("Type 2 range must be between 0 and 65535")

        # Ensure range_start <= range_end
        if self.range_start > self.range_end:
            raise ValueError("range_start must be less than or equal to range_end")

        return self


class RTRDPoolResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    pool_type: str
    format_type: int
    admin_value: str
    format_display: str  # e.g., "65000:{1000-1999}"
    range_start: int
    range_end: int
    total_values: int
    allocated_count: int = 0
    available_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class RTRDPoolDetail(RTRDPoolResponse):
    allocations: List["RTRDAllocationResponse"] = []


class RTRDAllocationRequest(BaseModel):
    description: Optional[str] = Field(None, description="Description/purpose for this allocation")
    allocated_to: Optional[str] = Field(None, max_length=255, description="Client/service identifier")


class RTRDAllocationResponse(BaseModel):
    id: int
    value: str  # e.g., "65000:1001"
    pool_name: str
    pool_type: str
    description: Optional[str]
    allocated_to: Optional[str]
    status: str
    allocated_at: datetime

    class Config:
        from_attributes = True


class RTRDReleaseRequest(BaseModel):
    value: str = Field(..., description="RT/RD value to release (e.g., '65000:1001')")

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: str) -> str:
        if ":" not in v:
            raise ValueError("Value must be in format 'admin:number' (e.g., '65000:1001')")
        return v


class RTRDAllocationListResponse(BaseModel):
    pool_name: str
    total_allocations: int
    allocations: List[RTRDAllocationResponse]


# Update forward references
RTRDPoolDetail.model_rebuild()
