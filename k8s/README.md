# Kubernetes Deployment Guide

Deploy Network Resource Pool Manager to Kubernetes cluster.

## Prerequisites

- Kubernetes cluster (1.20+)
- kubectl configured
- Container registry access (to push the image)

## Quick Deploy

```bash
# 1. Build and push Docker image to your registry
docker build -t your-registry.com/network-pool-manager:latest .
docker push your-registry.com/network-pool-manager:latest

# 2. Update image in api-deployment.yaml
# Change: image: network-pool-manager:latest
# To:     image: your-registry.com/network-pool-manager:latest

# 3. Apply all manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/postgres-pvc.yaml
kubectl apply -f k8s/postgres-deployment.yaml
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/ingress.yaml

# Or apply all at once:
kubectl apply -f k8s/
```

## Step-by-Step Deployment

### Step 1: Create Namespace

```bash
kubectl apply -f k8s/namespace.yaml
kubectl get namespaces | grep network-pool-manager
```

### Step 2: Create ConfigMap and Secret

```bash
# IMPORTANT: Update secret.yaml with secure passwords first!
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
```

### Step 3: Deploy PostgreSQL

```bash
kubectl apply -f k8s/postgres-pvc.yaml
kubectl apply -f k8s/postgres-deployment.yaml

# Wait for PostgreSQL to be ready
kubectl -n network-pool-manager wait --for=condition=ready pod -l app=postgres --timeout=120s
```

### Step 4: Build and Push API Image

```bash
# Build image
docker build -t your-registry.com/network-pool-manager:v1.0.0 .

# Push to registry
docker push your-registry.com/network-pool-manager:v1.0.0

# Update api-deployment.yaml with your image
```

### Step 5: Deploy API

```bash
kubectl apply -f k8s/api-deployment.yaml

# Wait for API to be ready
kubectl -n network-pool-manager wait --for=condition=ready pod -l app=pool-manager-api --timeout=120s
```

### Step 6: Configure Ingress (Optional)

```bash
# Update ingress.yaml with your domain
kubectl apply -f k8s/ingress.yaml
```

## Verify Deployment

```bash
# Check all resources
kubectl -n network-pool-manager get all

# Check pods are running
kubectl -n network-pool-manager get pods

# Check logs
kubectl -n network-pool-manager logs -l app=pool-manager-api -f

# Port-forward for testing (if no ingress)
kubectl -n network-pool-manager port-forward svc/pool-manager-service 8000:80

# Test API
curl http://localhost:8000/health
```

## Configuration

### Update Database Credentials (Production)

Edit `k8s/secret.yaml` before deployment:

```yaml
stringData:
  POSTGRES_USER: "your_secure_user"
  POSTGRES_PASSWORD: "your_secure_password_here"
  DATABASE_URL: "postgresql://your_secure_user:your_secure_password_here@postgres-service:5432/network_pools"
```

For better security, use external secret management:
- AWS Secrets Manager + External Secrets Operator
- HashiCorp Vault
- Azure Key Vault

### Scale API Replicas

```bash
# Scale to 3 replicas
kubectl -n network-pool-manager scale deployment pool-manager-api --replicas=3

# Or edit api-deployment.yaml and apply
```

### Update Ingress Domain

Edit `k8s/ingress.yaml`:

```yaml
spec:
  rules:
    - host: your-domain.example.com  # Change this
```

## Useful Commands

```bash
# View all resources
kubectl -n network-pool-manager get all

# View pod logs
kubectl -n network-pool-manager logs -l app=pool-manager-api

# Describe pod (for debugging)
kubectl -n network-pool-manager describe pod <pod-name>

# Execute into API pod
kubectl -n network-pool-manager exec -it <pod-name> -- /bin/bash

# Connect to PostgreSQL
kubectl -n network-pool-manager exec -it <postgres-pod> -- psql -U poolmanager -d network_pools

# Delete all resources
kubectl delete -f k8s/
```

## Troubleshooting

### Pods not starting

```bash
# Check pod events
kubectl -n network-pool-manager describe pod <pod-name>

# Check logs
kubectl -n network-pool-manager logs <pod-name>
```

### Database connection errors

```bash
# Verify PostgreSQL is running
kubectl -n network-pool-manager get pods -l app=postgres

# Check PostgreSQL logs
kubectl -n network-pool-manager logs -l app=postgres

# Verify secret values
kubectl -n network-pool-manager get secret pool-manager-secret -o yaml
```

### Image pull errors

```bash
# Check if image exists in registry
docker pull your-registry.com/network-pool-manager:latest

# Add imagePullSecrets if using private registry
kubectl -n network-pool-manager create secret docker-registry registry-secret \
  --docker-server=your-registry.com \
  --docker-username=your-user \
  --docker-password=your-password
```

## Manifest Files

| File | Description |
|------|-------------|
| `namespace.yaml` | Creates dedicated namespace |
| `configmap.yaml` | Non-sensitive configuration |
| `secret.yaml` | Database credentials (update for production!) |
| `postgres-pvc.yaml` | Persistent storage for PostgreSQL |
| `postgres-deployment.yaml` | PostgreSQL database + service |
| `api-deployment.yaml` | API deployment (2 replicas) + service |
| `ingress.yaml` | Ingress for external access |
