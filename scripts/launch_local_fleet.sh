#!/bin/bash
# TITAN PROTOCOL | LOCAL FLEET LAUNCHER
# Spawns N local worker limbs against the local Brain for testing.

set -e

# Determine repo root (one level up from this script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "$ROOT_DIR"

if [ ! -d "venv" ]; then
  echo "[ERROR] Python venv not found at $ROOT_DIR/venv"
  echo "        Run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

NODES=${1:-3}
CONNECT_URL=${2:-"ws://127.0.0.1:8000/connect"}

echo "[FLEET] Launching $NODES local limbs -> $CONNECT_URL"

source "$ROOT_DIR/venv/bin/activate"

LOG_DIR="$HOME/TitanNetwork/limb/logs"
mkdir -p "$LOG_DIR"

for i in $(seq 1 "$NODES"); do
  WALLET_ID="FLEET_NODE_${i}"
  LOG_FILE="$LOG_DIR/fleet_node_${i}.log"

  echo "[FLEET] Starting node #$i (wallet=$WALLET_ID, log=$LOG_FILE)"

  OVERRIDE_WALLET_ADDRESS="$WALLET_ID" nohup python3 core/limb/worker_node.py \
    --connect "$CONNECT_URL" \
    > "$LOG_FILE" 2>&1 &
done

echo "[FLEET] Launch complete. Use 'ps aux | grep worker_node.py' to inspect processes."
