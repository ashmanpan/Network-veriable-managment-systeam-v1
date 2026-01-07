from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..schemas.ip_pool import (
    IPPoolCreate,
    IPPoolResponse,
    IPPoolDetail,
    IPAllocationRequest,
    IPAllocationResponse,
    IPReleaseRequest,
    IPAllocationListResponse,
)
from ..services.ip_allocator import IPAllocatorService

router = APIRouter(prefix="/ip-pools", tags=["IP Pools"])


def build_allocation_response(alloc, pool) -> IPAllocationResponse:
    """Helper to build IPAllocationResponse from allocation and pool."""
    block_info = IPAllocatorService.get_block_info(alloc.allocated_cidr)

    return IPAllocationResponse(
        id=alloc.id,
        allocated_cidr=alloc.allocated_cidr,
        network_address=block_info["network_address"],
        broadcast_address=block_info["broadcast_address"],
        ip_addresses=block_info["ip_addresses"],
        block_size=block_info["block_size"],
        pool_name=pool.name,
        pool_type=pool.pool_type,
        pool_cidr=pool.cidr,
        prefix_length=block_info["prefix_length"],
        subnet_mask=block_info["subnet_mask"],
        description=alloc.description,
        allocated_to=alloc.allocated_to,
        status=alloc.status,
        allocated_at=alloc.allocated_at,
    )


@router.post("", response_model=IPPoolResponse, status_code=status.HTTP_201_CREATED)
def create_ip_pool(pool_data: IPPoolCreate, db: Session = Depends(get_db)):
    """
    Create a new IP address pool.

    - **name**: Unique name for the pool (e.g., "datacenter-mgmt")
    - **description**: Purpose/description of this pool
    - **pool_type**: Type of pool - "ipv4" or "ipv6"
    - **cidr**: CIDR notation (e.g., "10.0.0.0/24" or "2001:db8::/64")

    The pool can then be used to allocate subnet blocks of various sizes.
    """
    existing = IPAllocatorService.get_pool_by_name(db, pool_data.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Pool with name '{pool_data.name}' already exists"
        )

    try:
        pool = IPAllocatorService.create_pool(db, pool_data)
        stats = IPAllocatorService.get_pool_stats(db, pool)

        return IPPoolResponse(
            id=pool.id,
            name=pool.name,
            description=pool.description,
            pool_type=pool.pool_type,
            cidr=pool.cidr,
            network_address=pool.network_address,
            broadcast_address=pool.broadcast_address,
            total_addresses=pool.total_addresses,
            usable_addresses=pool.usable_addresses,
            allocated_count=stats["allocated_count"],
            available_count=stats["available_count"],
            created_at=pool.created_at,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("", response_model=List[IPPoolResponse])
def list_ip_pools(db: Session = Depends(get_db)):
    """List all IP address pools."""
    pools = IPAllocatorService.get_all_pools(db)
    result = []

    for pool in pools:
        stats = IPAllocatorService.get_pool_stats(db, pool)
        result.append(IPPoolResponse(
            id=pool.id,
            name=pool.name,
            description=pool.description,
            pool_type=pool.pool_type,
            cidr=pool.cidr,
            network_address=pool.network_address,
            broadcast_address=pool.broadcast_address,
            total_addresses=pool.total_addresses,
            usable_addresses=pool.usable_addresses,
            allocated_count=stats["allocated_count"],
            available_count=stats["available_count"],
            created_at=pool.created_at,
        ))

    return result


@router.get("/{name}", response_model=IPPoolDetail)
def get_ip_pool(name: str, db: Session = Depends(get_db)):
    """Get detailed information about a specific IP pool including all allocations."""
    pool = IPAllocatorService.get_pool_by_name(db, name)
    if not pool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pool '{name}' not found"
        )

    stats = IPAllocatorService.get_pool_stats(db, pool)
    allocations = IPAllocatorService.get_allocations(db, name)

    allocation_responses = [
        build_allocation_response(alloc, pool)
        for alloc in allocations
    ]

    return IPPoolDetail(
        id=pool.id,
        name=pool.name,
        description=pool.description,
        pool_type=pool.pool_type,
        cidr=pool.cidr,
        network_address=pool.network_address,
        broadcast_address=pool.broadcast_address,
        total_addresses=pool.total_addresses,
        usable_addresses=pool.usable_addresses,
        allocated_count=stats["allocated_count"],
        available_count=stats["available_count"],
        created_at=pool.created_at,
        allocations=allocation_responses,
    )


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ip_pool(name: str, db: Session = Depends(get_db)):
    """Delete an IP pool and all its allocations."""
    if not IPAllocatorService.delete_pool(db, name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pool '{name}' not found"
        )


@router.post("/{name}/allocate", response_model=IPAllocationResponse)
def allocate_block(
    name: str,
    request: IPAllocationRequest,
    db: Session = Depends(get_db)
):
    """
    Allocate a subnet block from the pool.

    - **prefix_length**: Requested prefix (e.g., 30 for /30 = 4 IPs, 32 for /32 = 1 IP)
    - **description**: Purpose/description for this allocation
    - **allocated_to**: Client/service identifier (e.g., "customer-abc")

    Block sizes (IPv4):
    - /32 = 1 IP
    - /31 = 2 IPs (point-to-point)
    - /30 = 4 IPs
    - /29 = 8 IPs
    - /28 = 16 IPs

    Blocks are automatically aligned to proper subnet boundaries.
    """
    pool = IPAllocatorService.get_pool_by_name(db, name)
    if not pool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pool '{name}' not found"
        )

    # Validate prefix_length against pool type
    pool_info = IPAllocatorService.parse_cidr(pool.cidr)
    max_prefix = 32 if pool_info["is_ipv4"] else 128

    if request.prefix_length > max_prefix:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"prefix_length cannot exceed {max_prefix} for {pool.pool_type}"
        )

    if request.prefix_length < pool_info["prefix_length"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot allocate /{request.prefix_length} from pool /{pool_info['prefix_length']} - requested block is larger than pool"
        )

    allocation = IPAllocatorService.allocate_block(db, name, request)
    if not allocation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Pool '{name}' has no available /{request.prefix_length} blocks"
        )

    return build_allocation_response(allocation, pool)


@router.post("/{name}/release", status_code=status.HTTP_200_OK)
def release_block(name: str, request: IPReleaseRequest, db: Session = Depends(get_db)):
    """
    Release an allocated block back to the pool.

    - **allocated_cidr**: The CIDR to release (e.g., "10.0.0.4/30")
    """
    pool = IPAllocatorService.get_pool_by_name(db, name)
    if not pool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pool '{name}' not found"
        )

    if not IPAllocatorService.release_block(db, name, request.allocated_cidr):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block '{request.allocated_cidr}' not found or already released"
        )

    return {"message": f"Block '{request.allocated_cidr}' released successfully"}


@router.get("/{name}/allocations", response_model=IPAllocationListResponse)
def list_allocations(name: str, db: Session = Depends(get_db)):
    """List all current allocations for a pool."""
    pool = IPAllocatorService.get_pool_by_name(db, name)
    if not pool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pool '{name}' not found"
        )

    allocations = IPAllocatorService.get_allocations(db, name)

    allocation_responses = [
        build_allocation_response(alloc, pool)
        for alloc in allocations
    ]

    return IPAllocationListResponse(
        pool_name=name,
        total_allocations=len(allocation_responses),
        allocations=allocation_responses,
    )
