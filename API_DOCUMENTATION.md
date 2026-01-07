# Network Resource Pool Manager - API Documentation

Base URL: `http://localhost:8000/api/v1`

---

## Table of Contents

1. [IP Pool Management](#ip-pool-management)
   - [Create IP Pool](#create-ip-pool)
   - [List All IP Pools](#list-all-ip-pools)
   - [Get IP Pool Details](#get-ip-pool-details)
   - [Delete IP Pool](#delete-ip-pool)
   - [Allocate IP Block](#allocate-ip-block)
   - [Release IP Block](#release-ip-block)
   - [List Pool Allocations](#list-pool-allocations)

2. [RT/RD Pool Management](#rtrd-pool-management)
   - [Create RT/RD Pool](#create-rtrd-pool)
   - [List All RT/RD Pools](#list-all-rtrd-pools)
   - [Get RT/RD Pool Details](#get-rtrd-pool-details)
   - [Delete RT/RD Pool](#delete-rtrd-pool)
   - [Allocate RT/RD Value](#allocate-rtrd-value)
   - [Release RT/RD Value](#release-rtrd-value)
   - [List RT/RD Allocations](#list-rtrd-allocations)

3. [Reference Tables](#reference-tables)

---

## IP Pool Management

### Create IP Pool

Create a new IP address pool from a CIDR block.

**Endpoint:** `POST /api/v1/ip-pools`

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | Yes | Unique pool name (1-100 chars) |
| description | string | No | Purpose/description of the pool |
| pool_type | string | Yes | `ipv4` or `ipv6` |
| cidr | string | Yes | CIDR notation (e.g., `10.0.0.0/24`) |

**Example Request:**

```bash
curl -X POST http://localhost:8000/api/v1/ip-pools \
  -H "Content-Type: application/json" \
  -d '{
    "name": "datacenter-mgmt",
    "description": "Management network for DC1",
    "pool_type": "ipv4",
    "cidr": "10.100.0.0/24"
  }'
```

**Example Response (201 Created):**

```json
{
  "id": 1,
  "name": "datacenter-mgmt",
  "description": "Management network for DC1",
  "pool_type": "ipv4",
  "cidr": "10.100.0.0/24",
  "network_address": "10.100.0.0",
  "broadcast_address": "10.100.0.255",
  "total_addresses": 256,
  "usable_addresses": 256,
  "allocated_count": 0,
  "available_count": 256,
  "created_at": "2026-01-07T15:30:00Z"
}
```

**IPv6 Example:**

```bash
curl -X POST http://localhost:8000/api/v1/ip-pools \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ipv6-site",
    "description": "IPv6 site allocation",
    "pool_type": "ipv6",
    "cidr": "2001:db8::/48"
  }'
```

**Error Responses:**

| Status | Description |
|--------|-------------|
| 400 | Invalid CIDR notation |
| 409 | Pool name already exists |

---

### List All IP Pools

Get a list of all IP address pools.

**Endpoint:** `GET /api/v1/ip-pools`

**Example Request:**

```bash
curl http://localhost:8000/api/v1/ip-pools
```

**Example Response (200 OK):**

```json
[
  {
    "id": 1,
    "name": "datacenter-mgmt",
    "description": "Management network for DC1",
    "pool_type": "ipv4",
    "cidr": "10.100.0.0/24",
    "network_address": "10.100.0.0",
    "broadcast_address": "10.100.0.255",
    "total_addresses": 256,
    "usable_addresses": 256,
    "allocated_count": 8,
    "available_count": 248,
    "created_at": "2026-01-07T15:30:00Z"
  },
  {
    "id": 2,
    "name": "ipv6-site",
    "description": "IPv6 site allocation",
    "pool_type": "ipv6",
    "cidr": "2001:db8::/48",
    "network_address": "2001:db8::",
    "broadcast_address": null,
    "total_addresses": 1208925819614629174706176,
    "usable_addresses": 1208925819614629174706176,
    "allocated_count": 0,
    "available_count": 1208925819614629174706176,
    "created_at": "2026-01-07T15:35:00Z"
  }
]
```

---

### Get IP Pool Details

Get detailed information about a specific pool including all allocations.

**Endpoint:** `GET /api/v1/ip-pools/{name}`

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| name | string | Pool name |

**Example Request:**

```bash
curl http://localhost:8000/api/v1/ip-pools/datacenter-mgmt
```

**Example Response (200 OK):**

```json
{
  "id": 1,
  "name": "datacenter-mgmt",
  "description": "Management network for DC1",
  "pool_type": "ipv4",
  "cidr": "10.100.0.0/24",
  "network_address": "10.100.0.0",
  "broadcast_address": "10.100.0.255",
  "total_addresses": 256,
  "usable_addresses": 256,
  "allocated_count": 8,
  "available_count": 248,
  "created_at": "2026-01-07T15:30:00Z",
  "allocations": [
    {
      "id": 1,
      "allocated_cidr": "10.100.0.0/30",
      "network_address": "10.100.0.0",
      "broadcast_address": "10.100.0.3",
      "ip_addresses": ["10.100.0.0", "10.100.0.1", "10.100.0.2", "10.100.0.3"],
      "block_size": 4,
      "pool_name": "datacenter-mgmt",
      "pool_type": "ipv4",
      "pool_cidr": "10.100.0.0/24",
      "prefix_length": 30,
      "subnet_mask": "255.255.255.252",
      "description": "Router uplink",
      "allocated_to": "router-01",
      "status": "allocated",
      "allocated_at": "2026-01-07T15:45:00Z"
    }
  ]
}
```

**Error Responses:**

| Status | Description |
|--------|-------------|
| 404 | Pool not found |

---

### Delete IP Pool

Delete an IP pool and all its allocations.

**Endpoint:** `DELETE /api/v1/ip-pools/{name}`

**Example Request:**

```bash
curl -X DELETE http://localhost:8000/api/v1/ip-pools/datacenter-mgmt
```

**Response:** `204 No Content`

**Error Responses:**

| Status | Description |
|--------|-------------|
| 404 | Pool not found |

---

### Allocate IP Block

Allocate a subnet block from the pool with automatic alignment.

**Endpoint:** `POST /api/v1/ip-pools/{name}/allocate`

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| name | string | Pool name |

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| prefix_length | integer | Yes | Subnet prefix (e.g., 30 for /30 = 4 IPs) |
| description | string | No | Purpose/description for allocation |
| allocated_to | string | No | Client/service identifier |

**IPv4 Block Sizes:**

| Prefix | Block Size | Subnet Mask |
|--------|------------|-------------|
| /32 | 1 IP | 255.255.255.255 |
| /31 | 2 IPs | 255.255.255.254 |
| /30 | 4 IPs | 255.255.255.252 |
| /29 | 8 IPs | 255.255.255.248 |
| /28 | 16 IPs | 255.255.255.240 |
| /27 | 32 IPs | 255.255.255.224 |
| /26 | 64 IPs | 255.255.255.192 |
| /25 | 128 IPs | 255.255.255.128 |
| /24 | 256 IPs | 255.255.255.0 |

**Example Request (/30 = 4 IPs):**

```bash
curl -X POST http://localhost:8000/api/v1/ip-pools/datacenter-mgmt/allocate \
  -H "Content-Type: application/json" \
  -d '{
    "prefix_length": 30,
    "description": "Point-to-point link to router",
    "allocated_to": "router-01"
  }'
```

**Example Response (200 OK):**

```json
{
  "id": 1,
  "allocated_cidr": "10.100.0.0/30",
  "network_address": "10.100.0.0",
  "broadcast_address": "10.100.0.3",
  "ip_addresses": [
    "10.100.0.0",
    "10.100.0.1",
    "10.100.0.2",
    "10.100.0.3"
  ],
  "block_size": 4,
  "pool_name": "datacenter-mgmt",
  "pool_type": "ipv4",
  "pool_cidr": "10.100.0.0/24",
  "prefix_length": 30,
  "subnet_mask": "255.255.255.252",
  "description": "Point-to-point link to router",
  "allocated_to": "router-01",
  "status": "allocated",
  "allocated_at": "2026-01-07T15:45:00Z"
}
```

**Example Request (/32 = 1 IP):**

```bash
curl -X POST http://localhost:8000/api/v1/ip-pools/datacenter-mgmt/allocate \
  -H "Content-Type: application/json" \
  -d '{
    "prefix_length": 32,
    "description": "Loopback address",
    "allocated_to": "server-01"
  }'
```

**Example Response (200 OK):**

```json
{
  "id": 2,
  "allocated_cidr": "10.100.0.4/32",
  "network_address": "10.100.0.4",
  "broadcast_address": "10.100.0.4",
  "ip_addresses": ["10.100.0.4"],
  "block_size": 1,
  "pool_name": "datacenter-mgmt",
  "pool_type": "ipv4",
  "pool_cidr": "10.100.0.0/24",
  "prefix_length": 32,
  "subnet_mask": "255.255.255.255",
  "description": "Loopback address",
  "allocated_to": "server-01",
  "status": "allocated",
  "allocated_at": "2026-01-07T15:50:00Z"
}
```

**IPv6 Example (/64 subnet):**

```bash
curl -X POST http://localhost:8000/api/v1/ip-pools/ipv6-site/allocate \
  -H "Content-Type: application/json" \
  -d '{
    "prefix_length": 64,
    "description": "Office LAN",
    "allocated_to": "office-building-1"
  }'
```

**Error Responses:**

| Status | Description |
|--------|-------------|
| 400 | Invalid prefix_length |
| 404 | Pool not found |
| 409 | Pool exhausted - no available blocks |

---

### Release IP Block

Release an allocated block back to the pool.

**Endpoint:** `POST /api/v1/ip-pools/{name}/release`

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| allocated_cidr | string | Yes | CIDR to release (e.g., `10.100.0.0/30`) |

**Example Request:**

```bash
curl -X POST http://localhost:8000/api/v1/ip-pools/datacenter-mgmt/release \
  -H "Content-Type: application/json" \
  -d '{
    "allocated_cidr": "10.100.0.0/30"
  }'
```

**Example Response (200 OK):**

```json
{
  "message": "Block '10.100.0.0/30' released successfully"
}
```

**Error Responses:**

| Status | Description |
|--------|-------------|
| 404 | Pool or block not found |

---

### List Pool Allocations

Get all current allocations for a pool.

**Endpoint:** `GET /api/v1/ip-pools/{name}/allocations`

**Example Request:**

```bash
curl http://localhost:8000/api/v1/ip-pools/datacenter-mgmt/allocations
```

**Example Response (200 OK):**

```json
{
  "pool_name": "datacenter-mgmt",
  "total_allocations": 2,
  "allocations": [
    {
      "id": 1,
      "allocated_cidr": "10.100.0.0/30",
      "network_address": "10.100.0.0",
      "broadcast_address": "10.100.0.3",
      "ip_addresses": ["10.100.0.0", "10.100.0.1", "10.100.0.2", "10.100.0.3"],
      "block_size": 4,
      "pool_name": "datacenter-mgmt",
      "pool_type": "ipv4",
      "pool_cidr": "10.100.0.0/24",
      "prefix_length": 30,
      "subnet_mask": "255.255.255.252",
      "description": "Router uplink",
      "allocated_to": "router-01",
      "status": "allocated",
      "allocated_at": "2026-01-07T15:45:00Z"
    },
    {
      "id": 2,
      "allocated_cidr": "10.100.0.4/32",
      "network_address": "10.100.0.4",
      "broadcast_address": "10.100.0.4",
      "ip_addresses": ["10.100.0.4"],
      "block_size": 1,
      "pool_name": "datacenter-mgmt",
      "pool_type": "ipv4",
      "pool_cidr": "10.100.0.0/24",
      "prefix_length": 32,
      "subnet_mask": "255.255.255.255",
      "description": "Loopback",
      "allocated_to": "server-01",
      "status": "allocated",
      "allocated_at": "2026-01-07T15:50:00Z"
    }
  ]
}
```

---

## RT/RD Pool Management

### Create RT/RD Pool

Create a new Route Target (RT) or Route Distinguisher (RD) pool.

**Endpoint:** `POST /api/v1/rtrd-pools`

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | Yes | Unique pool name (1-100 chars) |
| description | string | No | Purpose/description of the pool |
| pool_type | string | Yes | `rt` (Route Target) or `rd` (Route Distinguisher) |
| format_type | integer | Yes | Format type: 0, 1, or 2 (see table below) |
| admin_value | string | Yes | ASN or IP address |
| range_start | integer | Yes | Start of assigned number range |
| range_end | integer | Yes | End of assigned number range |

**Format Types:**

| Type | Format | Admin Value | Number Range | Example |
|------|--------|-------------|--------------|---------|
| 0 | ASN(2B):Number(4B) | 1-65535 | 0-4294967295 | `65000:1001` |
| 1 | IP(4B):Number(2B) | Valid IPv4 | 0-65535 | `10.0.0.1:100` |
| 2 | ASN(4B):Number(2B) | 1-4294967295 | 0-65535 | `4200000000:100` |

**Example Request (Type 0 - Standard ASN:Number):**

```bash
curl -X POST http://localhost:8000/api/v1/rtrd-pools \
  -H "Content-Type: application/json" \
  -d '{
    "name": "customer-rt-pool",
    "description": "Route targets for customer VPNs",
    "pool_type": "rt",
    "format_type": 0,
    "admin_value": "65000",
    "range_start": 1000,
    "range_end": 1999
  }'
```

**Example Response (201 Created):**

```json
{
  "id": 1,
  "name": "customer-rt-pool",
  "description": "Route targets for customer VPNs",
  "pool_type": "rt",
  "format_type": 0,
  "admin_value": "65000",
  "format_display": "65000:{1000-1999}",
  "range_start": 1000,
  "range_end": 1999,
  "total_values": 1000,
  "allocated_count": 0,
  "available_count": 1000,
  "created_at": "2026-01-07T16:00:00Z"
}
```

**Example Request (Type 1 - IP:Number):**

```bash
curl -X POST http://localhost:8000/api/v1/rtrd-pools \
  -H "Content-Type: application/json" \
  -d '{
    "name": "site-rd-pool",
    "description": "Route distinguishers by site IP",
    "pool_type": "rd",
    "format_type": 1,
    "admin_value": "10.0.0.1",
    "range_start": 1,
    "range_end": 1000
  }'
```

**Error Responses:**

| Status | Description |
|--------|-------------|
| 400 | Invalid format_type, admin_value, or range |
| 409 | Pool name already exists |

---

### List All RT/RD Pools

Get a list of all RT/RD pools.

**Endpoint:** `GET /api/v1/rtrd-pools`

**Example Request:**

```bash
curl http://localhost:8000/api/v1/rtrd-pools
```

**Example Response (200 OK):**

```json
[
  {
    "id": 1,
    "name": "customer-rt-pool",
    "description": "Route targets for customer VPNs",
    "pool_type": "rt",
    "format_type": 0,
    "admin_value": "65000",
    "format_display": "65000:{1000-1999}",
    "range_start": 1000,
    "range_end": 1999,
    "total_values": 1000,
    "allocated_count": 5,
    "available_count": 995,
    "created_at": "2026-01-07T16:00:00Z"
  }
]
```

---

### Get RT/RD Pool Details

Get detailed information about a specific RT/RD pool.

**Endpoint:** `GET /api/v1/rtrd-pools/{name}`

**Example Request:**

```bash
curl http://localhost:8000/api/v1/rtrd-pools/customer-rt-pool
```

**Example Response (200 OK):**

```json
{
  "id": 1,
  "name": "customer-rt-pool",
  "description": "Route targets for customer VPNs",
  "pool_type": "rt",
  "format_type": 0,
  "admin_value": "65000",
  "format_display": "65000:{1000-1999}",
  "range_start": 1000,
  "range_end": 1999,
  "total_values": 1000,
  "allocated_count": 2,
  "available_count": 998,
  "created_at": "2026-01-07T16:00:00Z",
  "allocations": [
    {
      "id": 1,
      "value": "65000:1000",
      "pool_name": "customer-rt-pool",
      "pool_type": "rt",
      "description": "Customer ABC L3VPN",
      "allocated_to": "customer-abc",
      "status": "allocated",
      "allocated_at": "2026-01-07T16:10:00Z"
    },
    {
      "id": 2,
      "value": "65000:1001",
      "pool_name": "customer-rt-pool",
      "pool_type": "rt",
      "description": "Customer XYZ L3VPN",
      "allocated_to": "customer-xyz",
      "status": "allocated",
      "allocated_at": "2026-01-07T16:15:00Z"
    }
  ]
}
```

---

### Delete RT/RD Pool

Delete an RT/RD pool and all its allocations.

**Endpoint:** `DELETE /api/v1/rtrd-pools/{name}`

**Example Request:**

```bash
curl -X DELETE http://localhost:8000/api/v1/rtrd-pools/customer-rt-pool
```

**Response:** `204 No Content`

---

### Allocate RT/RD Value

Allocate the next available RT/RD value from the pool.

**Endpoint:** `POST /api/v1/rtrd-pools/{name}/allocate`

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| description | string | No | Purpose/description |
| allocated_to | string | No | Client/service identifier |

**Example Request:**

```bash
curl -X POST http://localhost:8000/api/v1/rtrd-pools/customer-rt-pool/allocate \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Customer ABC L3VPN",
    "allocated_to": "customer-abc"
  }'
```

**Example Response (200 OK):**

```json
{
  "id": 1,
  "value": "65000:1000",
  "pool_name": "customer-rt-pool",
  "pool_type": "rt",
  "description": "Customer ABC L3VPN",
  "allocated_to": "customer-abc",
  "status": "allocated",
  "allocated_at": "2026-01-07T16:10:00Z"
}
```

**Error Responses:**

| Status | Description |
|--------|-------------|
| 404 | Pool not found |
| 409 | Pool exhausted - no available values |

---

### Release RT/RD Value

Release an RT/RD value back to the pool.

**Endpoint:** `POST /api/v1/rtrd-pools/{name}/release`

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| value | string | Yes | RT/RD value to release (e.g., `65000:1000`) |

**Example Request:**

```bash
curl -X POST http://localhost:8000/api/v1/rtrd-pools/customer-rt-pool/release \
  -H "Content-Type: application/json" \
  -d '{
    "value": "65000:1000"
  }'
```

**Example Response (200 OK):**

```json
{
  "message": "Value '65000:1000' released successfully"
}
```

---

### List RT/RD Allocations

Get all current allocations for an RT/RD pool.

**Endpoint:** `GET /api/v1/rtrd-pools/{name}/allocations`

**Example Request:**

```bash
curl http://localhost:8000/api/v1/rtrd-pools/customer-rt-pool/allocations
```

**Example Response (200 OK):**

```json
{
  "pool_name": "customer-rt-pool",
  "total_allocations": 2,
  "allocations": [
    {
      "id": 1,
      "value": "65000:1000",
      "pool_name": "customer-rt-pool",
      "pool_type": "rt",
      "description": "Customer ABC L3VPN",
      "allocated_to": "customer-abc",
      "status": "allocated",
      "allocated_at": "2026-01-07T16:10:00Z"
    },
    {
      "id": 2,
      "value": "65000:1001",
      "pool_name": "customer-rt-pool",
      "pool_type": "rt",
      "description": "Customer XYZ L3VPN",
      "allocated_to": "customer-xyz",
      "status": "allocated",
      "allocated_at": "2026-01-07T16:15:00Z"
    }
  ]
}
```

---

## Reference Tables

### IPv4 Subnet Reference

| Prefix | Block Size | Subnet Mask | Typical Use |
|--------|------------|-------------|-------------|
| /32 | 1 | 255.255.255.255 | Single host, loopback |
| /31 | 2 | 255.255.255.254 | Point-to-point link (RFC 3021) |
| /30 | 4 | 255.255.255.252 | Point-to-point with network/broadcast |
| /29 | 8 | 255.255.255.248 | Very small network |
| /28 | 16 | 255.255.255.240 | Small network |
| /27 | 32 | 255.255.255.224 | Small network |
| /26 | 64 | 255.255.255.192 | Medium network |
| /25 | 128 | 255.255.255.128 | Medium network |
| /24 | 256 | 255.255.255.0 | Standard subnet (Class C) |
| /23 | 512 | 255.255.254.0 | Large network |
| /22 | 1024 | 255.255.252.0 | Large network |
| /21 | 2048 | 255.255.248.0 | Large network |
| /20 | 4096 | 255.255.240.0 | Very large network |
| /16 | 65536 | 255.255.0.0 | Class B equivalent |

### IPv6 Subnet Reference

| Prefix | Block Size | Typical Use |
|--------|------------|-------------|
| /128 | 1 | Single host |
| /127 | 2 | Point-to-point link |
| /126 | 4 | Point-to-point (alternative) |
| /64 | 2^64 | **Standard subnet** (SLAAC required) |
| /56 | 256 × /64 | Residential/small business allocation |
| /48 | 65536 × /64 | Site allocation |
| /32 | 65536 × /48 | ISP allocation |

### RT/RD Format Reference

| Type | Format | Admin Range | Number Range | Example |
|------|--------|-------------|--------------|---------|
| 0 | 2B ASN : 4B Number | 1-65535 | 0-4294967295 | `65000:100` |
| 1 | 4B IP : 2B Number | Valid IPv4 | 0-65535 | `10.0.0.1:100` |
| 2 | 4B ASN : 2B Number | 1-4294967295 | 0-65535 | `4200000000:100` |

---

## Health Check Endpoints

### Root Health Check

**Endpoint:** `GET /`

```bash
curl http://localhost:8000/
```

**Response:**
```json
{
  "service": "Network Resource Pool Manager",
  "status": "healthy",
  "version": "1.0.0"
}
```

### Detailed Health Check

**Endpoint:** `GET /health`

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "database": "connected"
}
```

---

## Interactive Documentation

When the API is running, access interactive documentation at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
