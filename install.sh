#!/bin/bash
set -e

# VISUALS
GREEN='\033[1;32m'
CYAN='\033[1;36m'
NC='\033[0m'

echo -e "${CYAN}/// SI64 WORKER NODE INSTALLER (v1.0.2) ///${NC}"

# 1. CHECK FOR DOCKER
if ! command -v docker &> /dev/null; then
    echo -e "${GREEN}[1/3] Installing Docker...${NC}"
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo -e "Docker installed. Please re-run this script to continue."
    exit 0
else
    echo -e "${GREEN}[1/3] Docker Detected.${NC}"
fi

# 2. GET WALLET
echo -e "${GREEN}[2/3] Identity Provisioning${NC}"
read -p "Enter your SOLANA WALLET address: " SI64_WALLET

if [ -z "$SI64_WALLET" ]; then
    echo "Error: Wallet address is required."
    exit 1
fi

# 3. LAUNCH CONTAINER
echo -e "${GREEN}[3/3] Deploying Worker Node...${NC}"

# Remove old container if exists
docker rm -f si64-worker || true

# Pull and Run (Restart always ensures it runs on boot)
docker run -d \
  --name si64-worker \
  --restart unless-stopped \
  --network host \
  --runtime nvidia \
  -e SI64_WALLET_ADDRESS="$SI64_WALLET" \
  titanorionai/worker-node:v1.0.2

echo -e "\n${CYAN}SUCCESS! Your node is running in the background.${NC}"
echo "To view logs: docker logs -f si64-worker"
