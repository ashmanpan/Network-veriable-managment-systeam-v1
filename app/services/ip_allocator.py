import ipaddress
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from datetime import datetime

from ..models.ip_pool import IPPool, IPAllocation
from ..schemas.ip_pool import IPPoolCreate, IPAllocationRequest


class IPAllocatorService:
    """
    Service for managing IP address pools and block allocations.

    Block Allocation Logic:
    - User requests a prefix length (e.g., /30 = 4 IPs, /32 = 1 IP)
    - System finds the next available aligned block
    - Subnet alignment: /30 blocks start at addresses divisible by 4
    - Returns the full block with all IPs

    Alignment Rules (IPv4):
    - /32: Any address (block size = 1)
    - /31: Divisible by 2 (block size = 2)
    - /30: Divisible by 4 (block size = 4)
    - /29: Divisible by 8 (block size = 8)
    - /28: Divisible by 16 (block size = 16)
    - Formula: address % (2^(32-prefix)) == 0
    """

    @staticmethod
    def get_block_size(prefix_length: int, is_ipv4: bool = True) -> int:
        """Calculate block size from prefix length."""
        max_prefix = 32 if is_ipv4 else 128
        return 2 ** (max_prefix - prefix_length)

    @staticmethod
    def get_alignment(prefix_length: int, is_ipv4: bool = True) -> int:
        """Get alignment requirement for a prefix (block must start at multiple of this)."""
        return IPAllocatorService.get_block_size(prefix_length, is_ipv4)

    @staticmethod
    def is_aligned(ip_int: int, prefix_length: int, is_ipv4: bool = True) -> bool:
        """Check if an IP address (as int) is properly aligned for the given prefix."""
        alignment = IPAllocatorService.get_alignment(prefix_length, is_ipv4)
        return ip_int % alignment == 0

    @staticmethod
    def get_subnet_mask(prefix_length: int) -> str:
        """Get dotted decimal subnet mask for IPv4."""
        # Create a network with the prefix to get the netmask
        network = ipaddress.ip_network(f"0.0.0.0/{prefix_length}")
        return str(network.netmask)

    @staticmethod
    def parse_cidr(cidr: str) -> dict:
        """
        Parse CIDR notation and extract network properties.
        """
        network = ipaddress.ip_network(cidr, strict=False)
        is_ipv4 = isinstance(network, ipaddress.IPv4Network)

        return {
            "network": network,
            "network_address": str(network.network_address),
            "broadcast_address": str(network.broadcast_address) if is_ipv4 else None,
            "total_addresses": network.num_addresses,
            "prefix_length": network.prefixlen,
            "is_ipv4": is_ipv4,
            "subnet_mask": str(network.netmask) if is_ipv4 else None,
        }

    @staticmethod
    def create_pool(db: Session, pool_data: IPPoolCreate) -> IPPool:
        """Create a new IP address pool from CIDR."""
        network_info = IPAllocatorService.parse_cidr(pool_data.cidr)

        pool = IPPool(
            name=pool_data.name,
            description=pool_data.description,
            pool_type=pool_data.pool_type.value,
            cidr=pool_data.cidr,
            network_address=network_info["network_address"],
            broadcast_address=network_info["broadcast_address"],
            total_addresses=str(network_info["total_addresses"]),  # Store as string for IPv6 support
            usable_addresses=str(network_info["total_addresses"]),  # Store as string for IPv6 support
            next_available_index=0,
        )

        db.add(pool)
        db.commit()
        db.refresh(pool)
        return pool

    @staticmethod
    def get_pool_by_name(db: Session, name: str) -> Optional[IPPool]:
        """Get pool by name."""
        return db.query(IPPool).filter(IPPool.name == name).first()

    @staticmethod
    def get_all_pools(db: Session) -> List[IPPool]:
        """Get all IP pools."""
        return db.query(IPPool).all()

    @staticmethod
    def delete_pool(db: Session, name: str) -> bool:
        """Delete a pool by name."""
        pool = IPAllocatorService.get_pool_by_name(db, name)
        if pool:
            db.delete(pool)
            db.commit()
            return True
        return False

    @staticmethod
    def get_allocated_addresses(db: Session, pool_id: int) -> set:
        """Get set of all allocated IP addresses (as integers) in a pool."""
        allocations = db.query(IPAllocation).filter(
            IPAllocation.pool_id == pool_id,
            IPAllocation.status == "allocated"
        ).all()

        allocated = set()
        for alloc in allocations:
            # Parse the allocated CIDR and add all IPs in that block
            network = ipaddress.ip_network(alloc.allocated_cidr, strict=False)
            for ip in network:
                allocated.add(int(ip))

        return allocated

    @staticmethod
    def find_next_aligned_block(
        pool_network: ipaddress.IPv4Network | ipaddress.IPv6Network,
        requested_prefix: int,
        allocated_addresses: set
    ) -> Optional[Tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, List[str]]]:
        """
        Find the next available aligned block in the pool.

        Args:
            pool_network: The parent pool network
            requested_prefix: The requested prefix length (e.g., 30 for /30)
            allocated_addresses: Set of already allocated IP addresses (as integers)

        Returns:
            Tuple of (allocated_network, list_of_ip_strings) or None if pool exhausted
        """
        is_ipv4 = isinstance(pool_network, ipaddress.IPv4Network)
        block_size = IPAllocatorService.get_block_size(requested_prefix, is_ipv4)

        # Iterate through all possible aligned blocks in the pool
        # subnets() generates all possible subnets of the given prefix length
        for subnet in pool_network.subnets(new_prefix=requested_prefix):
            # Check if any IP in this block is already allocated
            block_ips = [int(ip) for ip in subnet]
            if not any(ip in allocated_addresses for ip in block_ips):
                # Found an available block
                ip_strings = [str(ip) for ip in subnet]
                return subnet, ip_strings

        return None

    @staticmethod
    def allocate_block(
        db: Session,
        pool_name: str,
        request: IPAllocationRequest
    ) -> Optional[IPAllocation]:
        """
        Allocate a subnet block from the pool.

        Args:
            pool_name: Name of the pool
            request: Allocation request with prefix_length

        Returns:
            IPAllocation object or None if allocation failed
        """
        pool = IPAllocatorService.get_pool_by_name(db, pool_name)
        if not pool:
            return None

        # Parse pool CIDR
        pool_network = ipaddress.ip_network(pool.cidr, strict=False)
        is_ipv4 = isinstance(pool_network, ipaddress.IPv4Network)

        # Validate requested prefix
        max_prefix = 32 if is_ipv4 else 128
        if request.prefix_length < pool_network.prefixlen:
            # Cannot allocate a larger block than the pool
            return None
        if request.prefix_length > max_prefix:
            return None

        # Get already allocated addresses
        allocated_addresses = IPAllocatorService.get_allocated_addresses(db, pool.id)

        # Find next available aligned block
        result = IPAllocatorService.find_next_aligned_block(
            pool_network, request.prefix_length, allocated_addresses
        )

        if not result:
            return None  # Pool exhausted

        allocated_subnet, ip_list = result
        block_size = len(ip_list)

        # Create allocation record
        allocation = IPAllocation(
            pool_id=pool.id,
            allocated_cidr=str(allocated_subnet),
            network_address=str(allocated_subnet.network_address),
            prefix_length=request.prefix_length,
            block_size=block_size,
            description=request.description,
            allocated_to=request.allocated_to,
            status="allocated",
        )

        db.add(allocation)
        db.commit()
        db.refresh(allocation)
        return allocation

    @staticmethod
    def release_block(db: Session, pool_name: str, allocated_cidr: str) -> bool:
        """Release a block back to the pool."""
        pool = IPAllocatorService.get_pool_by_name(db, pool_name)
        if not pool:
            return False

        # Normalize the CIDR
        try:
            network = ipaddress.ip_network(allocated_cidr, strict=False)
            normalized_cidr = str(network)
        except ValueError:
            return False

        allocation = db.query(IPAllocation).filter(
            IPAllocation.pool_id == pool.id,
            IPAllocation.allocated_cidr == normalized_cidr,
            IPAllocation.status == "allocated"
        ).first()

        if allocation:
            allocation.status = "released"
            allocation.released_at = datetime.utcnow()
            db.commit()
            return True

        return False

    @staticmethod
    def get_allocations(db: Session, pool_name: str) -> List[IPAllocation]:
        """Get all allocations for a pool."""
        pool = IPAllocatorService.get_pool_by_name(db, pool_name)
        if not pool:
            return []

        return db.query(IPAllocation).filter(
            IPAllocation.pool_id == pool.id,
            IPAllocation.status == "allocated"
        ).all()

    @staticmethod
    def get_pool_stats(db: Session, pool: IPPool) -> dict:
        """Get allocation statistics for a pool."""
        allocated_addresses = IPAllocatorService.get_allocated_addresses(db, pool.id)
        allocated_count = len(allocated_addresses)
        
        # Convert total_addresses from string to int for arithmetic
        total_addresses = int(pool.total_addresses)

        return {
            "allocated_count": allocated_count,
            "available_count": total_addresses - allocated_count,
        }

    @staticmethod
    def get_subnet_info(cidr: str) -> dict:
        """Get subnet mask information from CIDR."""
        network = ipaddress.ip_network(cidr, strict=False)
        is_ipv4 = isinstance(network, ipaddress.IPv4Network)

        return {
            "prefix_length": network.prefixlen,
            "subnet_mask": str(network.netmask) if is_ipv4 else None,
        }

    @staticmethod
    def get_block_ips(allocated_cidr: str) -> List[str]:
        """Get all IPs in an allocated block."""
        network = ipaddress.ip_network(allocated_cidr, strict=False)
        return [str(ip) for ip in network]

    @staticmethod
    def get_block_info(allocated_cidr: str) -> dict:
        """Get full info about an allocated block."""
        network = ipaddress.ip_network(allocated_cidr, strict=False)
        is_ipv4 = isinstance(network, ipaddress.IPv4Network)

        return {
            "network_address": str(network.network_address),
            "broadcast_address": str(network.broadcast_address) if is_ipv4 else None,
            "ip_addresses": [str(ip) for ip in network],
            "block_size": network.num_addresses,
            "prefix_length": network.prefixlen,
            "subnet_mask": str(network.netmask) if is_ipv4 else None,
        }
