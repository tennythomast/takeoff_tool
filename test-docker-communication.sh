#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Testing Docker container communication for Dataelan${NC}"
echo "======================================================"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
  echo -e "${RED}Error: Docker is not running. Please start Docker and try again.${NC}"
  exit 1
fi

# Check if docker compose or docker-compose is available
DOCKER_COMPOSE="docker-compose"
if ! command -v docker-compose &> /dev/null; then
  # Try the new docker compose command format
  if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
    echo -e "${YELLOW}Using 'docker compose' command (new format)${NC}"
  else
    echo -e "${RED}Error: Neither docker-compose nor docker compose is available. Please install Docker Desktop or the docker-compose plugin.${NC}"
    exit 1
  fi
else
  echo -e "${YELLOW}Using 'docker-compose' command (legacy format)${NC}"
fi

echo -e "\n${YELLOW}1. Starting Docker containers...${NC}"
$DOCKER_COMPOSE down
$DOCKER_COMPOSE up -d

# Wait for services to be ready
echo -e "\n${YELLOW}2. Waiting for services to start (30 seconds)...${NC}"
sleep 30

# Test backend health endpoint
echo -e "\n${YELLOW}3. Testing backend health endpoint...${NC}"
BACKEND_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health/)
if [ "$BACKEND_HEALTH" == "200" ]; then
  echo -e "${GREEN}✓ Backend health endpoint is accessible (HTTP 200)${NC}"
else
  echo -e "${RED}✗ Backend health endpoint returned HTTP $BACKEND_HEALTH${NC}"
fi

# Test frontend health endpoint
echo -e "\n${YELLOW}4. Testing frontend health endpoint...${NC}"
FRONTEND_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/api/health)
if [ "$FRONTEND_HEALTH" == "200" ]; then
  echo -e "${GREEN}✓ Frontend health endpoint is accessible (HTTP 200)${NC}"
else
  echo -e "${RED}✗ Frontend health endpoint returned HTTP $FRONTEND_HEALTH${NC}"
fi

# Test frontend to backend communication
echo -e "\n${YELLOW}5. Testing frontend to backend communication...${NC}"
FRONTEND_BACKEND_TEST=$(curl -s http://localhost:3000/api/health | grep -o "backendConnected.*true")
if [[ ! -z "$FRONTEND_BACKEND_TEST" ]]; then
  echo -e "${GREEN}✓ Frontend can communicate with backend${NC}"
else
  echo -e "${RED}✗ Frontend cannot communicate with backend${NC}"
  echo "Response from frontend health check:"
  curl -s http://localhost:3000/api/health
  echo ""
fi

# Check Docker container logs for errors
echo -e "\n${YELLOW}6. Checking for errors in container logs...${NC}"
BACKEND_ERRORS=$($DOCKER_COMPOSE logs --tail=50 backend | grep -i "error")
FRONTEND_ERRORS=$($DOCKER_COMPOSE logs --tail=50 frontend | grep -i "error")

if [[ ! -z "$BACKEND_ERRORS" ]]; then
  echo -e "${RED}Backend container has errors:${NC}"
  echo "$BACKEND_ERRORS"
else
  echo -e "${GREEN}✓ No recent errors found in backend logs${NC}"
fi

if [[ ! -z "$FRONTEND_ERRORS" ]]; then
  echo -e "${RED}Frontend container has errors:${NC}"
  echo "$FRONTEND_ERRORS"
else
  echo -e "${GREEN}✓ No recent errors found in frontend logs${NC}"
fi

echo -e "\n${YELLOW}7. Container network information:${NC}"
echo "Docker network details:"

# Get the actual network name (could be dataelan-network or dataelan_dataelan-network)
NETWORK_NAME=$(docker network ls | grep dataelan | head -n 1 | awk '{print $2}')
if [ -z "$NETWORK_NAME" ]; then
  echo -e "${RED}No Dataelan network found${NC}"
else
  echo -e "${GREEN}Found network: $NETWORK_NAME${NC}"
  docker network inspect $NETWORK_NAME | grep -A 20 "Containers"
fi

echo -e "\n${GREEN}Test completed!${NC}"
echo "To view full container logs, run: $DOCKER_COMPOSE logs"
echo "To stop containers, run: $DOCKER_COMPOSE down"
