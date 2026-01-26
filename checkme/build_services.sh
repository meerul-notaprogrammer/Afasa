#!/bin/bash

# AFASA 2.0 - Resilient Build Script with Progress Indicators
# This script builds services one at a time with clear progress tracking

set -e  # Exit on error

# Enable BuildKit for better progress
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Color codes for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Services to build
SERVICES=(
    "afasa-ops"
    "afasa-telegram"
    "afasa-vision-yolo"
    "afasa-report"
    "afasa-tb-adapter"
)

TOTAL_SERVICES=${#SERVICES[@]}
CURRENT=0

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         AFASA 2.0 - Service Build Script              ║${NC}"
echo -e "${BLUE}║     Building ${TOTAL_SERVICES} services with progress tracking       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Log file
LOG_FILE="build_$(date +%Y%m%d_%H%M%S).log"
echo -e "${YELLOW}📝 Logging to: ${LOG_FILE}${NC}\n"

# Build each service
for SERVICE in "${SERVICES[@]}"; do
    CURRENT=$((CURRENT + 1))
    
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}[${CURRENT}/${TOTAL_SERVICES}] Building: ${SERVICE}${NC}"
    echo -e "${GREEN}Progress: $(awk "BEGIN {printf \"%.1f\", (${CURRENT}-1)/${TOTAL_SERVICES}*100}")%${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    START_TIME=$(date +%s)
    
    # Build with plain progress output
    if docker compose build --progress=plain "$SERVICE" 2>&1 | tee -a "$LOG_FILE"; then
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))
        
        echo ""
        echo -e "${GREEN}✅ ${SERVICE} built successfully in ${DURATION}s${NC}"
        echo -e "${GREEN}Overall Progress: $(awk "BEGIN {printf \"%.1f\", ${CURRENT}/${TOTAL_SERVICES}*100}")%${NC}"
        echo ""
    else
        echo ""
        echo -e "${RED}❌ Failed to build ${SERVICE}${NC}"
        echo -e "${RED}Check ${LOG_FILE} for details${NC}"
        exit 1
    fi
    
    # Brief pause between builds
    sleep 2
done

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              ✅ ALL SERVICES BUILT! ✅                  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  1. Run: ${GREEN}docker compose up -d${NC}"
echo -e "  2. Check status: ${GREEN}docker compose ps${NC}"
echo ""
