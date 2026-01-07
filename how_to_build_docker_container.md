# How to Build and Run Docker Container

This guide explains how to build and run the Network Resource Pool Manager using Docker.

## Prerequisites

- Docker installed ([Install Docker](https://docs.docker.com/get-docker/))
- Docker Compose installed ([Install Docker Compose](https://docs.docker.com/compose/install/))

## Quick Start (Recommended)

The easiest way to run the application is using Docker Compose, which starts both the API and PostgreSQL database:

```bash
# Navigate to project directory
cd Network-veriable-pool-manager-v1

# Start all services (API + PostgreSQL)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

The API will be available at:
- **API**: http://localhost:8000
- **Swagger Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Manual Docker Build

If you prefer to build and run containers manually:

### Step 1: Build the API Image

```bash
# Build the Docker image
docker build -t network-pool-manager:latest .

# Verify the image was created
docker images | grep network-pool-manager
```

### Step 2: Start PostgreSQL Database

```bash
# Create a network for containers to communicate
docker network create pool-network

# Start PostgreSQL container
docker run -d \
  --name network-pool-db \
  --network pool-network \
  -e POSTGRES_USER=poolmanager \
  -e POSTGRES_PASSWORD=poolmanager123 \
  -e POSTGRES_DB=network_pools \
  -p 5432:5432 \
  -v postgres_data:/var/lib/postgresql/data \
  postgres:15-alpine
```

### Step 3: Start the API Container

```bash
# Start the API container
docker run -d \
  --name network-pool-api \
  --network pool-network \
  -e DATABASE_URL=postgresql://poolmanager:poolmanager123@network-pool-db:5432/network_pools \
  -p 8000:8000 \
  network-pool-manager:latest
```

---

## Verify Installation

### Check Container Status

```bash
# List running containers
docker ps

# Expected output:
# CONTAINER ID   IMAGE                      STATUS          PORTS
# xxxx           network-pool-manager       Up X minutes    0.0.0.0:8000->8000/tcp
# xxxx           postgres:15-alpine         Up X minutes    0.0.0.0:5432->5432/tcp
```

### Test the API

```bash
# Health check
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","database":"connected"}
```

### Access Swagger Documentation

Open your browser and navigate to: http://localhost:8000/docs

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://poolmanager:poolmanager123@db:5432/network_pools` |

### Custom Database Configuration

To use a different database:

```bash
docker run -d \
  --name network-pool-api \
  -e DATABASE_URL=postgresql://myuser:mypassword@myhost:5432/mydb \
  -p 8000:8000 \
  network-pool-manager:latest
```

---

## Docker Compose Configuration

The `docker-compose.yml` file defines two services:

### Services

1. **db** - PostgreSQL 15 database
   - Port: 5432
   - Credentials: poolmanager / poolmanager123
   - Database: network_pools
   - Data persisted in `postgres_data` volume

2. **api** - FastAPI application
   - Port: 8000
   - Auto-restarts on code changes (development mode)
   - Waits for database to be healthy before starting

### Customizing docker-compose.yml

```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: your_username        # Change this
      POSTGRES_PASSWORD: your_password    # Change this
      POSTGRES_DB: your_database          # Change this
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  api:
    build: .
    ports:
      - "8000:8000"                        # Change host port if needed
    environment:
      DATABASE_URL: postgresql://your_username:your_password@db:5432/your_database
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## Production Deployment

For production environments:

### 1. Use Stronger Credentials

```bash
# Generate secure password
openssl rand -base64 32
```

Update `docker-compose.yml` with secure credentials.

### 2. Remove Development Mode

Edit `Dockerfile` to remove `--reload` flag:

```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 3. Add HTTPS (Reverse Proxy)

Use Nginx or Traefik as a reverse proxy with SSL certificates.

### 4. Resource Limits

Add resource limits in docker-compose.yml:

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
```

---

## Useful Commands

```bash
# View API logs
docker-compose logs -f api

# View database logs
docker-compose logs -f db

# Restart services
docker-compose restart

# Stop and remove containers (keeps data)
docker-compose down

# Stop and remove containers AND data
docker-compose down -v

# Rebuild after code changes
docker-compose up -d --build

# Enter API container shell
docker exec -it network-pool-api /bin/bash

# Enter database container
docker exec -it network-pool-db psql -U poolmanager -d network_pools
```

---

## Troubleshooting

### Database Connection Error

```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Solution**: Wait for database to be ready, or check DATABASE_URL.

```bash
# Check if database is running
docker-compose logs db

# Restart services
docker-compose restart
```

### Port Already in Use

```
Error: bind: address already in use
```

**Solution**: Change the port mapping or stop the conflicting service.

```bash
# Find what's using port 8000
lsof -i :8000

# Use different port
docker run -p 8080:8000 network-pool-manager:latest
```

### Permission Denied

```
Permission denied while trying to connect to Docker daemon
```

**Solution**: Add user to docker group.

```bash
sudo usermod -aG docker $USER
# Log out and back in
```

---

## API Usage Examples

Once running, test the API:

```bash
# Create IPv4 pool
curl -X POST http://localhost:8000/api/v1/ip-pools \
  -H "Content-Type: application/json" \
  -d '{
    "name": "datacenter-pool",
    "description": "DC1 management network",
    "pool_type": "ipv4",
    "cidr": "10.100.0.0/24"
  }'

# Allocate /30 block (4 IPs)
curl -X POST http://localhost:8000/api/v1/ip-pools/datacenter-pool/allocate \
  -H "Content-Type: application/json" \
  -d '{
    "prefix_length": 30,
    "description": "Router link",
    "allocated_to": "router-01"
  }'

# Create RT pool
curl -X POST http://localhost:8000/api/v1/rtrd-pools \
  -H "Content-Type: application/json" \
  -d '{
    "name": "customer-rt",
    "description": "Customer VPN route targets",
    "pool_type": "rt",
    "format_type": 0,
    "admin_value": "65000",
    "range_start": 1000,
    "range_end": 1999
  }'

# Allocate RT value
curl -X POST http://localhost:8000/api/v1/rtrd-pools/customer-rt/allocate \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Customer ABC VPN",
    "allocated_to": "customer-abc"
  }'
```
