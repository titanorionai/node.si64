#!/bin/bash
set -e # Exit immediately on error

# --- [ VISUAL PROTOCOLS ] ---
GREEN='\033[1;32m'
CYAN='\033[1;36m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
NC='\033[0m' # No Color

clear
echo -e "${CYAN}"
echo "   _____ _____   __   _  _   "
echo "  / ____|_   _| / /  | || |  "
echo " | (___   | |  / /_  | || |_ "
echo "  \\___ \\  | | | '_ \\ |__   _|"
echo "  ____) |_| |_| (_) |   | |  "
echo " |_____/|_____|\\___/    |_|  "
echo "      NETWORK // SI64.NET    "
echo -e "${NC}"
echo -e "${CYAN}/// SOVEREIGN COMPUTE NODE INSTALLER ///${NC}"
echo "Target Protocol: SI64 (Solana Integrated)"
echo "------------------------------------------------"

# --- [ 1. SYSTEM RECONNAISSANCE ] ---
echo -e "\n${CYAN}[1/5] Scanning Host Capabilities...${NC}"

# Check Architecture
ARCH=$(uname -m)
if [[ "$ARCH" == "aarch64" ]]; then
    echo -e "${GREEN}>> TARGET ARCHITECTURE CONFIRMED: ARM64 (Native)${NC}"
elif [[ "$ARCH" == "x86_64" ]]; then
    echo -e "${YELLOW}>> NOTICE: x86_64 Architecture detected. Running in Compatibility Mode.${NC}"
else
    echo -e "${RED}>> WARNING: Unknown Architecture ($ARCH). Proceeding with caution.${NC}"
fi

# Check Tools
for cmd in python3 git pip3; do
    if ! command -v $cmd &> /dev/null; then
        echo -e "${RED}[ERROR] Missing dependency: $cmd${NC}"
        echo "Please install via: sudo apt install python3-full git python3-pip"
        exit 1
    fi
done

# --- [ 2. DEPLOYMENT ] ---
INSTALL_DIR="$HOME/.si64-core"
# Public SI64 node core repository (sanitized)
REPO_URL="https://github.com/titanorionai/si64-node.git"

if [ -d "$INSTALL_DIR" ]; then
    echo -e "${CYAN}[2/5] Updating Existing Node Logic...${NC}"
    cd "$INSTALL_DIR"
    git pull origin main --quiet
    echo -e "${GREEN}>> Core Updated.${NC}"
else
    echo -e "${CYAN}[2/5] Cloning Core Logic to $INSTALL_DIR...${NC}"
    git clone "$REPO_URL" "$INSTALL_DIR" --quiet
    cd "$INSTALL_DIR"
    echo -e "${GREEN}>> Repository Secured.${NC}"
fi

# --- [ 3. ENVIRONMENT ISOLATION ] ---
echo -e "${CYAN}[3/5] Initializing Neural Environment (venv)...${NC}"

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}>> Virtual Environment Created.${NC}"
fi

source venv/bin/activate
echo -e ">> Installing Neural Dependencies (This may take a moment)..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet --disable-pip-version-check

# --- [ 4. IDENTITY PROVISIONING ] ---
echo -e "${CYAN}[4/5] Establishing Identity...${NC}"
mkdir -p ~/.si64
CONFIG_PATH="$HOME/.si64/config.json"

if [ ! -f "$CONFIG_PATH" ]; then
    echo -e "${YELLOW}>> NO IDENTITY FOUND.${NC}"
    echo -n "Enter your SOLANA WALLET address to receive rewards: "
    read WALLET_ADDR
    
    if [ -z "$WALLET_ADDR" ]; then
        echo -e "${RED}>> Error: Wallet address cannot be empty.${NC}"
        exit 1
    fi

    # Create Config
    cat <<EOF > "$CONFIG_PATH"
{
    "wallet_address": "$WALLET_ADDR",
    "worker_name": "NODE_$(hostname)_$(date +%s)",
    "hardware_class": "DETECTING"
}
EOF
    echo -e "${GREEN}>> Identity Generated: ~/.si64/config.json${NC}"
else
    echo -e "${GREEN}>> Identity Loaded: $(grep "wallet_address" $CONFIG_PATH)${NC}"
fi

# --- [ 5. PERSISTENCE (Optional) ] ---
echo -e "${CYAN}[5/5] Finalizing Launch Protocols...${NC}"

SERVICE_FILE="/etc/systemd/system/si64-node.service"

# Check if Sudo exists before trying systemd
if command -v sudo &> /dev/null; then
    if [ ! -f "$SERVICE_FILE" ]; then
        echo -e "${YELLOW}>> Do you want to auto-start this node on boot? (y/n)${NC}"
        read -r -n 1 response
        echo ""
        if [[ "$response" =~ ^[Yy]$ ]]; then
            echo ">> Creating Systemd Service..."
            
            USER_NAME=$(whoami)
            EXEC_PATH="$INSTALL_DIR/venv/bin/python3"
            SCRIPT_PATH="$INSTALL_DIR/limb/worker_node.py"
            
            sudo bash -c "cat <<EOF > $SERVICE_FILE
[Unit]
Description=SI64 Compute Node
After=network.target

[Service]
User=$USER_NAME
WorkingDirectory=$INSTALL_DIR
ExecStart=$EXEC_PATH $SCRIPT_PATH --connect wss://si64.net/connect
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF"
            
            sudo systemctl daemon-reload
            sudo systemctl enable si64-node
            sudo systemctl start si64-node
            echo -e "${GREEN}>> Service Installed & Started!${NC}"
        fi
    fi
else
    echo -e "${YELLOW}>> 'sudo' not detected. Skipping systemd service creation.${NC}"
    echo ">> You must run the worker manually or configure your own supervisor."
fi

# --- [ LAUNCH SUMMARY ] ---
echo -e "\n${GREEN}/// DEPLOYMENT SUCCESSFUL ///${NC}"
echo "------------------------------------------------"
echo -e "STATUS:  ${GREEN}ONLINE${NC}"
echo -e "IDENTITY: ~/.si64/config.json"
echo "------------------------------------------------"
echo -e "To view your node in action:"
echo -e "${CYAN}tail -f ~/.si64/node.log (if logged)${NC}"
echo -e "OR manual start:"
echo -e "${GREEN}cd $INSTALL_DIR && source venv/bin/activate && python3 limb/worker_node.py --connect wss://si64.net/connect${NC}"
echo ""
