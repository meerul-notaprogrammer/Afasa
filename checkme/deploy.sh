#!/bin/bash
# AFASA 2.0 - Deployment Script
# Run this on the VPS after uploading the fixed docker-compose.yml

set -e  # Exit on error

echo "=========================================="
echo "AFASA 2.0 - Deployment Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Verify we're in the right directory
echo "Step 1: Verifying project directory..."
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}ERROR: docker-compose.yml not found. Are you in /home/meerul/afasa2.0?${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Found docker-compose.yml${NC}"
echo ""

# Step 2: Restart NATS with new healthcheck
echo "Step 2: Restarting NATS with fixed healthcheck..."
docker compose up -d --force-recreate nats
echo -e "${GREEN}✓ NATS restarted${NC}"
echo ""

# Step 3: Wait for NATS to become healthy
echo "Step 3: Waiting for NATS to become healthy (max 30 seconds)..."
COUNTER=0
while [ $COUNTER -lt 30 ]; do
    STATUS=$(docker compose ps nats --format json | grep -o '"Health":"[^"]*"' | cut -d'"' -f4 || echo "starting")
    if [ "$STATUS" = "healthy" ]; then
        echo -e "${GREEN}✓ NATS is healthy!${NC}"
        break
    fi
    echo "  Waiting... ($COUNTER/30) - Status: $STATUS"
    sleep 1
    COUNTER=$((COUNTER + 1))
done

if [ $COUNTER -eq 30 ]; then
    echo -e "${YELLOW}⚠ NATS healthcheck timeout. Checking logs...${NC}"
    docker compose logs --tail=20 nats
    echo ""
    echo -e "${YELLOW}Continuing anyway...${NC}"
fi
echo ""

# Step 4: Restart Keycloak with new start_period
echo "Step 4: Restarting Keycloak with extended start period..."
docker compose up -d --force-recreate keycloak
echo -e "${GREEN}✓ Keycloak restarted${NC}"
echo ""

# Step 5: Start all AFASA services
echo "Step 5: Starting all AFASA services..."
docker compose up -d
echo -e "${GREEN}✓ All services started${NC}"
echo ""

# Step 6: Display service status
echo "Step 6: Service Status"
echo "=========================================="
docker compose ps
echo ""

# Step 7: Check for any unhealthy services
echo "Step 7: Health Check Summary"
echo "=========================================="
UNHEALTHY=$(docker compose ps --format json | grep -c '"Health":"unhealthy"' || echo "0")
HEALTHY=$(docker compose ps --format json | grep -c '"Health":"healthy"' || echo "0")

echo "Healthy services: $HEALTHY"
echo "Unhealthy services: $UNHEALTHY"
echo ""

if [ "$UNHEALTHY" -gt 0 ]; then
    echo -e "${YELLOW}⚠ Some services are unhealthy. Checking logs...${NC}"
    echo ""
    
    # Show logs for unhealthy services
    docker compose ps --format json | grep '"Health":"unhealthy"' | while read -r line; do
        SERVICE=$(echo "$line" | grep -o '"Service":"[^"]*"' | cut -d'"' -f4)
        echo "--- Logs for $SERVICE ---"
        docker compose logs --tail=20 "$SERVICE"
        echo ""
    done
fi

# Step 8: Quick API tests
echo "Step 8: Testing API Endpoints"
echo "=========================================="

# Test NATS
if curl -f -s http://localhost:8222/healthz > /dev/null 2>&1; then
    echo -e "${GREEN}✓ NATS monitoring endpoint${NC}"
else
    echo -e "${RED}✗ NATS monitoring endpoint${NC}"
fi

# Test MinIO
if curl -f -s http://localhost:9000/minio/health/live > /dev/null 2>&1; then
    echo -e "${GREEN}✓ MinIO health endpoint${NC}"
else
    echo -e "${RED}✗ MinIO health endpoint${NC}"
fi

# Test Keycloak
if curl -f -s http://localhost:8080/health/ready > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Keycloak health endpoint${NC}"
else
    echo -e "${YELLOW}⚠ Keycloak health endpoint (may still be starting)${NC}"
fi

echo ""

# Step 9: Display access URLs
echo "=========================================="
echo "AFASA 2.0 Deployment Complete!"
echo "=========================================="
echo ""
echo "Access URLs:"
echo "  Portal:           http://100.88.15.112/"
echo "  Traefik Dashboard: http://192.168.1.110:8081"
echo "  Grafana:          http://192.168.1.110:3001"
echo "  Keycloak:         http://192.168.1.110:8080"
echo "  MinIO Console:    http://192.168.1.110:9001"
echo "  Prometheus:       http://192.168.1.110:9090"
echo ""
echo "Next Steps:"
echo "  1. Check service logs: docker compose logs -f"
echo "  2. Verify API endpoints: curl http://localhost/api/media/health"
echo "  3. Access portal and test login"
echo ""
echo "For troubleshooting, see DEPLOYMENT_PLAN.md"
echo ""
