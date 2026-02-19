#!/bin/bash
# run-integration-tests.sh
# Automated integration testing using docker-compose.test.yml
# This script:
#   1. Starts the API service using docker-compose
#   2. Waits for the health check to pass
#   3. Runs integration tests against the containerized API
#   4. Cleans up containers regardless of test outcome

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.test.yml"
API_KEY="${API_KEY:-test-api-key-12345}"
MAX_HEALTH_CHECKS=30
HEALTH_CHECK_INTERVAL=2

echo -e "${YELLOW}Starting StockMon Integration Test Suite${NC}"
echo "========================================"

# Cleanup function (runs on exit)
cleanup() {
    echo -e "\n${YELLOW}Cleaning up containers...${NC}"
    docker-compose -f "$COMPOSE_FILE" down -v
    echo -e "${GREEN}Cleanup complete${NC}"
}

# Register cleanup to run on exit (success or failure)
trap cleanup EXIT

# Step 1: Start API service
echo -e "\n${YELLOW}Step 1: Starting API service...${NC}"
docker-compose -f "$COMPOSE_FILE" up -d --build

# Step 2: Wait for health check to pass
echo -e "\n${YELLOW}Step 2: Waiting for API to be healthy...${NC}"
HEALTHY=0
for i in $(seq 1 $MAX_HEALTH_CHECKS); do
    if docker-compose -f "$COMPOSE_FILE" ps api | grep -q "healthy"; then
        HEALTHY=1
        echo -e "${GREEN}API is healthy after ${i} checks${NC}"
        break
    fi
    echo "Health check ${i}/${MAX_HEALTH_CHECKS}..."
    sleep $HEALTH_CHECK_INTERVAL
done

if [ $HEALTHY -eq 0 ]; then
    echo -e "${RED}ERROR: API failed to become healthy${NC}"
    docker-compose -f "$COMPOSE_FILE" logs api
    exit 1
fi

# Step 3: Verify API is accessible
echo -e "\n${YELLOW}Step 3: Verifying API endpoints...${NC}"
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}Health endpoint: OK${NC}"
else
    echo -e "${RED}ERROR: Health endpoint unreachable${NC}"
    exit 1
fi

if curl -f http://localhost:8000/ > /dev/null 2>&1; then
    echo -e "${GREEN}Root endpoint: OK${NC}"
else
    echo -e "${RED}ERROR: Root endpoint unreachable${NC}"
    exit 1
fi

# Step 4: Run integration tests
echo -e "\n${YELLOW}Step 4: Running integration tests...${NC}"
echo "API_KEY: $API_KEY"
echo "----------------------------------------"

# Set API_KEY for tests and run integration tests
export API_KEY="$API_KEY"
export API_URL="http://localhost:8000/check-alerts"

if pytest tests/test_*_integration.py -v; then
    echo -e "\n${GREEN}All integration tests passed!${NC}"
    exit 0
else
    echo -e "\n${RED}Integration tests failed${NC}"
    echo -e "\n${YELLOW}API logs:${NC}"
    docker-compose -f "$COMPOSE_FILE" logs api
    exit 1
fi
