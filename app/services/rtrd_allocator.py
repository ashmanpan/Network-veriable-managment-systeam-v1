from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime

from ..models.rtrd_pool import RTRDPool, RTRDAllocation
from ..schemas.rtrd_pool import RTRDPoolCreate, RTRDAllocationRequest


class RTRDAllocatorService:
    """
    Service for managing RT (Route Target) and RD (Route Distinguisher) pools.

    RT/RD Format Types:
    - Type 0: 2-byte ASN : 4-byte number (e.g., 65000:100)
    - Type 1: 4-byte IP : 2-byte number (e.g., 10.0.0.1:100)
    - Type 2: 4-byte ASN : 2-byte number (e.g., 4200000000:100)

    RT (Route Target): Controls route import/export between VRFs
    RD (Route Distinguisher): Makes VPNv4/VPNv6 prefixes globally unique
    """

    @staticmethod
    def format_value(admin_value: str, assigned_number: int) -> str:
        """Format RT/RD value as admin:number."""
        return f"{admin_value}:{assigned_number}"

    @staticmethod
    def parse_value(value: str) -> tuple:
        """Parse RT/RD value into admin and number parts."""
        parts = value.rsplit(":", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid RT/RD value format: {value}")
        return parts[0], int(parts[1])

    @staticmethod
    def create_pool(db: Session, pool_data: RTRDPoolCreate) -> RTRDPool:
        """Create a new RT/RD pool."""
        pool = RTRDPool(
            name=pool_data.name,
            description=pool_data.description,
            pool_type=pool_data.pool_type.value,
            format_type=pool_data.format_type.value,
            admin_value=pool_data.admin_value,
            range_start=pool_data.range_start,
            range_end=pool_data.range_end,
            next_available=pool_data.range_start,
        )

        db.add(pool)
        db.commit()
        db.refresh(pool)
        return pool

    @staticmethod
    def get_pool_by_name(db: Session, name: str) -> Optional[RTRDPool]:
        """Get pool by name."""
        return db.query(RTRDPool).filter(RTRDPool.name == name).first()

    @staticmethod
    def get_all_pools(db: Session) -> List[RTRDPool]:
        """Get all RT/RD pools."""
        return db.query(RTRDPool).all()

    @staticmethod
    def delete_pool(db: Session, name: str) -> bool:
        """Delete a pool by name."""
        pool = RTRDAllocatorService.get_pool_by_name(db, name)
        if pool:
            db.delete(pool)
            db.commit()
            return True
        return False

    @staticmethod
    def get_allocated_count(db: Session, pool_id: int) -> int:
        """Get count of allocated values in a pool."""
        return db.query(RTRDAllocation).filter(
            RTRDAllocation.pool_id == pool_id,
            RTRDAllocation.status == "allocated"
        ).count()

    @staticmethod
    def allocate_value(
        db: Session,
        pool_name: str,
        request: RTRDAllocationRequest
    ) -> Optional[RTRDAllocation]:
        """
        Allocate the next available RT/RD value from the pool.

        Sequential allocation algorithm:
        1. Start from next_available or range_start
        2. Skip any already allocated numbers
        3. Allocate first available number
        4. Update next_available
        """
        pool = RTRDAllocatorService.get_pool_by_name(db, pool_name)
        if not pool:
            return None

        # Get all currently allocated numbers in this pool
        allocated_numbers = set(
            alloc.assigned_number for alloc in db.query(RTRDAllocation).filter(
                RTRDAllocation.pool_id == pool.id,
                RTRDAllocation.status == "allocated"
            ).all()
        )

        # Find next available number
        start = pool.next_available if pool.next_available else pool.range_start
        total_range = pool.range_end - pool.range_start + 1

        for i in range(total_range):
            # Calculate number with wraparound
            number = pool.range_start + ((start - pool.range_start + i) % total_range)

            if number not in allocated_numbers:
                # Found available number - allocate it
                value = RTRDAllocatorService.format_value(pool.admin_value, number)

                allocation = RTRDAllocation(
                    pool_id=pool.id,
                    value=value,
                    assigned_number=number,
                    description=request.description,
                    allocated_to=request.allocated_to,
                    status="allocated",
                )

                # Update next_available for next allocation
                next_num = number + 1
                if next_num > pool.range_end:
                    next_num = pool.range_start
                pool.next_available = next_num

                db.add(allocation)
                db.commit()
                db.refresh(allocation)
                return allocation

        # Pool exhausted
        return None

    @staticmethod
    def release_value(db: Session, pool_name: str, value: str) -> bool:
        """Release an RT/RD value back to the pool."""
        pool = RTRDAllocatorService.get_pool_by_name(db, pool_name)
        if not pool:
            return False

        # Parse value to get the assigned number
        try:
            _, assigned_number = RTRDAllocatorService.parse_value(value)
        except ValueError:
            return False

        allocation = db.query(RTRDAllocation).filter(
            RTRDAllocation.pool_id == pool.id,
            RTRDAllocation.assigned_number == assigned_number,
            RTRDAllocation.status == "allocated"
        ).first()

        if allocation:
            allocation.status = "released"
            allocation.released_at = datetime.utcnow()
            db.commit()
            return True

        return False

    @staticmethod
    def get_allocations(db: Session, pool_name: str) -> List[RTRDAllocation]:
        """Get all allocations for a pool."""
        pool = RTRDAllocatorService.get_pool_by_name(db, pool_name)
        if not pool:
            return []

        return db.query(RTRDAllocation).filter(
            RTRDAllocation.pool_id == pool.id,
            RTRDAllocation.status == "allocated"
        ).all()

    @staticmethod
    def get_pool_stats(db: Session, pool: RTRDPool) -> dict:
        """Get allocation statistics for a pool."""
        total_values = pool.range_end - pool.range_start + 1
        allocated_count = RTRDAllocatorService.get_allocated_count(db, pool.id)
        return {
            "total_values": total_values,
            "allocated_count": allocated_count,
            "available_count": total_values - allocated_count,
            "format_display": f"{pool.admin_value}:{{{pool.range_start}-{pool.range_end}}}",
        }
