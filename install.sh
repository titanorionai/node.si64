#!/bin/bash
set -e

# --- [ CONFIGURATION ] ---
VERSION="v1.0.2"
IMAGE_NAME="titanorionai/worker-node:v1.0.2"
CONTAINER_NAME="si64-worker"

# --- [ VISUALS ] ---
GREEN='\033[1;32m'
CYAN='\033[1;36m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
NC='\033[0m'

# --- [ UTILITIES ] ---
setup_interruption_trap() {
    trap 'echo -e "\n${RED}>> INSTALLATION ABORTED BY USER.${NC}"; exit 1' SIGINT
}

print_banner() {
    clear
    echo -e "${CYAN}"
    echo "     _____ _____     __     _  _    "
    echo "    / ____|_   _| / /  | || |   "
    echo "   | (___   | |  / /_  | || |_  "
    echo "    \___ \  | | | '_ \ |__   _| "
    echo "    ____) |_| |_| (_) |   | |   "
    echo "   |_____/|_____|\___/    |_|   "
    echo "        NETWORK // SI64.NET      "
    echo -e "${NC}"
    echo -e "${CYAN}/// SOVEREIGN COMPUTE NODE INSTALLER ///${NC}"
    echo "Target Protocol: SI64 (Solana Integrated)"
    echo "Installer Version: ${VERSION}"
    echo "------------------------------------------------"
}

# --- [ 1. SYSTEM RECONNAISSANCE ] ---
check_docker() {
    echo -e "\n${CYAN}[1/4] Scanning Host Capabilities...${NC}"
    
    # Determine execution method (Rootless vs Sudo)
    DOCKER_CMD="docker"
    
    if ! command -v docker &> /dev/null; then
        echo -e "${YELLOW}>> Docker engine not detected. Initiating installation...${NC}"
        
        # Install Docker
        if ! curl -fsSL https://get.docker.com -o get-docker.sh; then
            echo -e "${RED}>> Error: Failed to download Docker installer.${NC}"
            exit 1
        fi
        
        sudo sh get-docker.sh
        rm get-docker.sh
        
        # Add user to group
        sudo usermod -aG docker "$USER"
        echo -e "${GREEN}>> Docker installed successfully.${NC}"
        
        # NOTE: Group changes require re-login. We fallback to sudo for this session.
        DOCKER_CMD="sudo docker"
    else
        echo -e "${GREEN}>> Docker Detected.${NC}"
        # Check permissions
        if ! docker ps >/dev/null 2>&1; then
            echo -e "${YELLOW}>> Notice: Running Docker with sudo privileges.${NC}"
            DOCKER_CMD="sudo docker"
        fi
    fi
}

detect_hardware() {
    echo -e "${CYAN}[2/4] Hardware Acceleration Check...${NC}"
    RUNTIME_FLAG=""
    
    # Check for Jetson (Tegra) or NVIDIA GPU
    if [ -f "/etc/nv_tegra_release" ] || command -v nvidia-smi &> /dev/null; then
        echo -e "${GREEN}>> NVIDIA Hardware Detected. Enabling GPU Runtime.${NC}"
        RUNTIME_FLAG="--runtime nvidia"
    else
        echo -e "${YELLOW}>> Standard CPU Detected. Running in Compatibility Mode.${NC}"
    fi
}

# --- [ 2. IDENTITY PROVISIONING ] ---
configure_identity() {
    echo -e "\n${CYAN}[3/4] Establishing Identity...${NC}"
    
    while true; do
        echo -n "Enter your SOLANA WALLET address to receive rewards: "
        read -r SI64_WALLET
        
        # Basic validation for empty input
        if [ -z "$SI64_WALLET" ]; then
            echo -e "${RED}>> Error: Wallet address cannot be empty.${NC}"
            continue
        fi

        # Length validation (Solana addresses are base58, usually 32-44 chars)
        LEN=${#SI64_WALLET}
        if [ "$LEN" -lt 32 ] || [ "$LEN" -gt 44 ]; then
             echo -e "${YELLOW}>> Warning: Address looks unusual ($LEN chars). Is this a valid Solana address? (y/n)${NC}"
             read -r CONFIRM
             if [[ "$CONFIRM" =~ ^[Yy]$ ]]; then
                 break
             fi
        else
            break
        fi
    done
    
    echo -e "${GREEN}>> Identity Locked: $SI64_WALLET${NC}"
}

# --- [ 3. DEPLOYMENT ] ---
deploy_worker() {
    echo -e "\n${CYAN}[4/4] Launching Containerized Worker...${NC}"

    # Clean up old container
    if $DOCKER_CMD ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo -e ">> Removing previous instance..."
        $DOCKER_CMD rm -f "$CONTAINER_NAME" >/dev/null
    fi

    # Pull latest image
    echo -e ">> Pulling latest image ($IMAGE_NAME)..."
    if ! $DOCKER_CMD pull "$IMAGE_NAME" >/dev/null; then
         echo -e "${RED}>> Error: Failed to pull image. Check internet connection.${NC}"
         exit 1
    fi

    # Run Container
    echo -e ">> Igniting Sentinel..."
    # shellcheck disable=SC2086
    $DOCKER_CMD run -d \
      --name "$CONTAINER_NAME" \
      --restart unless-stopped \
      --network host \
      $RUNTIME_FLAG \
      -e SI64_WALLET_ADDRESS="$SI64_WALLET" \
      "$IMAGE_NAME" >/dev/null

    if [ $? -eq 0 ]; then
        show_summary
    else
        echo -e "${RED}>> DEPLOYMENT FAILED. Check Docker logs.${NC}"
        exit 1
    fi
}

show_summary() {
    echo -e "\n${GREEN}/// DEPLOYMENT SUCCESSFUL ///${NC}"
    echo "------------------------------------------------"
    echo -e "STATUS:  ${GREEN}ONLINE${NC}"
    echo -e "NODE ID: ${CONTAINER_NAME}"
    echo -e "WALLET:  ${SI64_WALLET:0:6}...${SI64_WALLET: -4}"
    if [ -n "$RUNTIME_FLAG" ]; then
        echo -e "MODE:    ${GREEN}NVIDIA GPU ACCELERATED${NC}"
    else
        echo -e "MODE:    ${YELLOW}CPU / STANDARD${NC}"
    fi
    echo "------------------------------------------------"
    echo -e "To view live telemetry:"
    echo -e "${CYAN}${DOCKER_CMD} logs -f ${CONTAINER_NAME}${NC}"
    echo ""
}

# --- [ MAIN EXECUTION FLOW ] ---
setup_interruption_trap
print_banner
check_docker
detect_hardware
configure_identity
deploy_worker
