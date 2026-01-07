from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..schemas.rtrd_pool import (
    RTRDPoolCreate,
    RTRDPoolResponse,
    RTRDPoolDetail,
    RTRDAllocationRequest,
    RTRDAllocationResponse,
    RTRDReleaseRequest,
    RTRDAllocationListResponse,
)
from ..services.rtrd_allocator import RTRDAllocatorService

router = APIRouter(prefix="/rtrd-pools", tags=["RT/RD Pools"])


@router.post("", response_model=RTRDPoolResponse, status_code=status.HTTP_201_CREATED)
def create_rtrd_pool(pool_data: RTRDPoolCreate, db: Session = Depends(get_db)):
    """
    Create a new Route Target (RT) or Route Distinguisher (RD) pool.

    - **name**: Unique name for the pool (e.g., "customer-rt-pool")
    - **description**: Purpose/description of this pool
    - **pool_type**: "rt" for Route Target or "rd" for Route Distinguisher
    - **format_type**: 0 (ASN:num), 1 (IP:num), or 2 (4-byte ASN:num)
    - **admin_value**: ASN or IP address (e.g., "65000" or "10.0.0.1")
    - **range_start**: Start of assigned number range
    - **range_end**: End of assigned number range

    Format Types:
    - Type 0: 2-byte ASN : 4-byte number (e.g., 65000:100)
    - Type 1: 4-byte IP : 2-byte number (e.g., 10.0.0.1:100)
    - Type 2: 4-byte ASN : 2-byte number (e.g., 4200000000:100)
    """
    # Check if pool already exists
    existing = RTRDAllocatorService.get_pool_by_name(db, pool_data.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Pool with name '{pool_data.name}' already exists"
        )

    try:
        pool = RTRDAllocatorService.create_pool(db, pool_data)
        stats = RTRDAllocatorService.get_pool_stats(db, pool)

        return RTRDPoolResponse(
            id=pool.id,
            name=pool.name,
            description=pool.description,
            pool_type=pool.pool_type,
            format_type=pool.format_type,
            admin_value=pool.admin_value,
            format_display=stats["format_display"],
            range_start=pool.range_start,
            range_end=pool.range_end,
            total_values=stats["total_values"],
            allocated_count=stats["allocated_count"],
            available_count=stats["available_count"],
            created_at=pool.created_at,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("", response_model=List[RTRDPoolResponse])
def list_rtrd_pools(db: Session = Depends(get_db)):
    """List all RT/RD pools."""
    pools = RTRDAllocatorService.get_all_pools(db)
    result = []

    for pool in pools:
        stats = RTRDAllocatorService.get_pool_stats(db, pool)
        result.append(RTRDPoolResponse(
            id=pool.id,
            name=pool.name,
            description=pool.description,
            pool_type=pool.pool_type,
            format_type=pool.format_type,
            admin_value=pool.admin_value,
            format_display=stats["format_display"],
            range_start=pool.range_start,
            range_end=pool.range_end,
            total_values=stats["total_values"],
            allocated_count=stats["allocated_count"],
            available_count=stats["available_count"],
            created_at=pool.created_at,
        ))

    return result


@router.get("/{name}", response_model=RTRDPoolDetail)
def get_rtrd_pool(name: str, db: Session = Depends(get_db)):
    """Get detailed information about a specific RT/RD pool."""
    pool = RTRDAllocatorService.get_pool_by_name(db, name)
    if not pool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pool '{name}' not found"
        )

    stats = RTRDAllocatorService.get_pool_stats(db, pool)
    allocations = RTRDAllocatorService.get_allocations(db, name)

    allocation_responses = [
        RTRDAllocationResponse(
            id=alloc.id,
            value=alloc.value,
            pool_name=pool.name,
            pool_type=pool.pool_type,
            description=alloc.description,
            allocated_to=alloc.allocated_to,
            status=alloc.status,
            allocated_at=alloc.allocated_at,
        )
        for alloc in allocations
    ]

    return RTRDPoolDetail(
        id=pool.id,
        name=pool.name,
        description=pool.description,
        pool_type=pool.pool_type,
        format_type=pool.format_type,
        admin_value=pool.admin_value,
        format_display=stats["format_display"],
        range_start=pool.range_start,
        range_end=pool.range_end,
        total_values=stats["total_values"],
        allocated_count=stats["allocated_count"],
        available_count=stats["available_count"],
        created_at=pool.created_at,
        allocations=allocation_responses,
    )


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rtrd_pool(name: str, db: Session = Depends(get_db)):
    """Delete an RT/RD pool and all its allocations."""
    if not RTRDAllocatorService.delete_pool(db, name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pool '{name}' not found"
        )


@router.post("/{name}/allocate", response_model=RTRDAllocationResponse)
def allocate_rtrd(
    name: str,
    request: RTRDAllocationRequest,
    db: Session = Depends(get_db)
):
    """
    Allocate the next available RT/RD value from the pool.

    - **description**: Purpose/description for this allocation
    - **allocated_to**: Client/service identifier (e.g., "customer-abc")

    Returns the allocated RT/RD value with details.
    """
    pool = RTRDAllocatorService.get_pool_by_name(db, name)
    if not pool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pool '{name}' not found"
        )

    allocation = RTRDAllocatorService.allocate_value(db, name, request)
    if not allocation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Pool '{name}' is exhausted - no available values"
        )

    return RTRDAllocationResponse(
        id=allocation.id,
        value=allocation.value,
        pool_name=name,
        pool_type=pool.pool_type,
        description=allocation.description,
        allocated_to=allocation.allocated_to,
        status=allocation.status,
        allocated_at=allocation.allocated_at,
    )


@router.post("/{name}/release", status_code=status.HTTP_200_OK)
def release_rtrd(name: str, request: RTRDReleaseRequest, db: Session = Depends(get_db)):
    """
    Release an RT/RD value back to the pool.

    - **value**: The RT/RD value to release (e.g., "65000:1001")
    """
    pool = RTRDAllocatorService.get_pool_by_name(db, name)
    if not pool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pool '{name}' not found"
        )

    if not RTRDAllocatorService.release_value(db, name, request.value):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Value '{request.value}' not found or already released"
        )

    return {"message": f"Value '{request.value}' released successfully"}


@router.get("/{name}/allocations", response_model=RTRDAllocationListResponse)
def list_rtrd_allocations(name: str, db: Session = Depends(get_db)):
    """List all current allocations for a pool."""
    pool = RTRDAllocatorService.get_pool_by_name(db, name)
    if not pool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pool '{name}' not found"
        )

    allocations = RTRDAllocatorService.get_allocations(db, name)

    allocation_responses = [
        RTRDAllocationResponse(
            id=alloc.id,
            value=alloc.value,
            pool_name=name,
            pool_type=pool.pool_type,
            description=alloc.description,
            allocated_to=alloc.allocated_to,
            status=alloc.status,
            allocated_at=alloc.allocated_at,
        )
        for alloc in allocations
    ]

    return RTRDAllocationListResponse(
        pool_name=name,
        total_allocations=len(allocation_responses),
        allocations=allocation_responses,
    )
