#!/bin/bash

# Network Pool Manager - Deployment Script
# Following the reference deployment pattern

set -e

# Configuration
APP_NAME="network-pool-manager"
VERSION="1.0.0"
ECR_REGISTRY="567097740753.dkr.ecr.ap-southeast-1.amazonaws.com"
ECR_REPO="apj/can-aaipe"
AWS_REGION="ap-southeast-1"
NAMESPACE="can-aaipe"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Network Pool Manager Deployment${NC}"
echo -e "${BLUE}Version: ${VERSION}${NC}"
echo -e "${BLUE}========================================${NC}"

# Step 1: Navigate to project directory
echo -e "\n${GREEN}Step 1: Navigating to project directory...${NC}"
cd /Users/prathmeshsambrekar/Documents/C-can-aape-v02/Network-veriable-managment-systeam-v1

# Step 2: Build Docker image
echo -e "\n${GREEN}Step 2: Building Docker image...${NC}"
docker buildx build --platform linux/amd64 \
  -t ${APP_NAME}:${VERSION} \
  -f Dockerfile \
  --load .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Image built successfully${NC}"
else
    echo -e "${RED}✗ Image build failed${NC}"
    exit 1
fi

# Step 3: Authenticate with ECR
echo -e "\n${GREEN}Step 3: Authenticating with AWS ECR...${NC}"
aws ecr get-login-password --region ${AWS_REGION} | \
  docker login --username AWS --password-stdin ${ECR_REGISTRY}

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ ECR authentication successful${NC}"
else
    echo -e "${RED}✗ ECR authentication failed${NC}"
    exit 1
fi

# Step 4: Tag image for ECR
echo -e "\n${GREEN}Step 4: Tagging image for ECR...${NC}"
docker tag ${APP_NAME}:${VERSION} \
  ${ECR_REGISTRY}/${ECR_REPO}:${APP_NAME}-${VERSION}

echo -e "${GREEN}✓ Image tagged${NC}"

# Step 5: Push to ECR
echo -e "\n${GREEN}Step 5: Pushing image to ECR...${NC}"
docker push ${ECR_REGISTRY}/${ECR_REPO}:${APP_NAME}-${VERSION}

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Image pushed successfully${NC}"
else
    echo -e "${RED}✗ Image push failed${NC}"
    exit 1
fi

# Step 6: Update deployment file with new version
echo -e "\n${GREEN}Step 6: Updating deployment.yaml with version ${VERSION}...${NC}"
sed -i.bak "s|${APP_NAME}-[0-9]\+\.[0-9]\+\.[0-9]\+|${APP_NAME}-${VERSION}|g" deployment.yaml
echo -e "${GREEN}✓ Deployment file updated${NC}"

# Step 7: Apply deployment to Kubernetes
echo -e "\n${GREEN}Step 7: Applying Kubernetes deployment...${NC}"
kubectl apply -f deployment.yaml

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Deployment applied successfully${NC}"
else
    echo -e "${RED}✗ Deployment failed${NC}"
    exit 1
fi

# Step 8: Wait for deployment to be ready
echo -e "\n${GREEN}Step 8: Waiting for pods to be ready...${NC}"
kubectl wait --for=condition=ready pod \
  -l app=${APP_NAME} \
  -n ${NAMESPACE} \
  --timeout=180s

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ All pods are ready${NC}"
else
    echo -e "${RED}✗ Pods failed to become ready${NC}"
    echo -e "${BLUE}Check pod status with: kubectl get pods -n ${NAMESPACE}${NC}"
fi

# Step 9: Get deployment status
echo -e "\n${GREEN}Step 9: Deployment Status${NC}"
kubectl get deployments -n ${NAMESPACE}
kubectl get pods -n ${NAMESPACE}
kubectl get svc -n ${NAMESPACE}

# Step 10: Get service URL
echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${BLUE}========================================${NC}"

echo -e "\n${BLUE}Service Information:${NC}"
LOAD_BALANCER=$(kubectl get svc pool-manager-service -n ${NAMESPACE} -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

if [ -z "$LOAD_BALANCER" ]; then
    echo -e "${BLUE}LoadBalancer URL: (Pending - check back in a few minutes)${NC}"
    echo -e "${BLUE}Run: kubectl get svc -n ${NAMESPACE} -w${NC}"
else
    echo -e "${GREEN}LoadBalancer URL: http://${LOAD_BALANCER}${NC}"
    echo -e "${GREEN}Health Check: http://${LOAD_BALANCER}/health${NC}"
    echo -e "${GREEN}API Docs: http://${LOAD_BALANCER}/docs${NC}"
fi

echo -e "\n${BLUE}Monitor deployment:${NC}"
echo -e "kubectl get pods -n ${NAMESPACE} -w"

echo -e "\n${BLUE}View logs:${NC}"
echo -e "kubectl logs -n ${NAMESPACE} -l app=${APP_NAME} -f"

echo -e "\n${BLUE}Port forward for local testing:${NC}"
echo -e "kubectl port-forward -n ${NAMESPACE} svc/pool-manager-service 8000:80"

