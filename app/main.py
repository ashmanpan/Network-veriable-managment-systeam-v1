from fastapi import FastAPI
from contextlib import asynccontextmanager

from .config import get_settings
from .database import create_tables
from .routers import ip_pools_router, rtrd_pools_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create database tables
    create_tables()
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title="Network Resource Pool Manager",
    description="""
## Network Resource Pool Manager API

A microservice for managing network resources including IP pools and L3VPN RT/RD values.

---

### IPv4 Subnet Block Allocation

Create pools and allocate subnet blocks with proper alignment:

| Prefix | Block Size | Subnet Mask | Use Case |
|--------|-----------|-------------|----------|
| /32 | 1 IP | 255.255.255.255 | Single host |
| /31 | 2 IPs | 255.255.255.254 | Point-to-point link |
| /30 | 4 IPs | 255.255.255.252 | Small subnet |
| /29 | 8 IPs | 255.255.255.248 | Small network |
| /28 | 16 IPs | 255.255.255.240 | Medium network |
| /24 | 256 IPs | 255.255.255.0 | Standard subnet |

**Alignment Rule**: /30 blocks start at addresses divisible by 4, /29 by 8, etc.

---

### IPv6 Subnet Block Allocation

Full IPv6 support with standard prefix lengths:

| Prefix | Block Size | Use Case |
|--------|-----------|----------|
| /128 | 1 address | Single host |
| /127 | 2 addresses | Point-to-point link |
| /126 | 4 addresses | Point-to-point (alternative) |
| /64 | 2^64 addresses | **Standard subnet** (recommended) |
| /56 | 256 x /64 subnets | Residential/small business |
| /48 | 65,536 x /64 subnets | Site allocation |

**Best Practice**: /64 is standard for most subnets (required for SLAAC).

---

### L3VPN Route Targets (RT) & Route Distinguishers (RD)

Support for all format types:

| Type | Format | Example |
|------|--------|---------|
| Type 0 | 2-byte ASN : 4-byte number | 65000:100 |
| Type 1 | 4-byte IP : 2-byte number | 10.0.0.1:100 |
| Type 2 | 4-byte ASN : 2-byte number | 4200000000:100 |

---

### Key Features
- Pool-based resource management with names and descriptions
- Automatic subnet alignment for proper block allocation
- Release and reclaim functionality
- Full allocation tracking with descriptions
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# Include routers
app.include_router(ip_pools_router, prefix=settings.api_v1_prefix)
app.include_router(rtrd_pools_router, prefix=settings.api_v1_prefix)


@app.get("/", tags=["Health"])
def root():
    """Health check endpoint."""
    return {
        "service": "Network Resource Pool Manager",
        "status": "healthy",
        "version": "1.0.0",
    }


@app.get("/health", tags=["Health"])
def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "database": "connected",
    }
