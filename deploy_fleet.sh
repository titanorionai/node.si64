#!/bin/bash
# TITAN PROTOCOL | FLEET DEPLOYMENT SCRIPT
# ========================================
# Safely (re)deploys a fleet of worker containers without
# interrupting unrelated Docker workloads.

set -e

# --- [ TACTICAL CONFIGURATION ] ---
# CHANGE 1: Use ws:// protocol and explicit /connect path
BRAIN_UPLINK="ws://127.0.0.1:8000/connect"

# Docker image that contains the worker container runtime
IMAGE_NAME="titan-worker:latest"

# Container name prefix for this script's managed fleet
FLEET_PREFIX="titan-worker-"

# Default fleet size if not provided as argument
DEFAULT_FLEET_SIZE=1

# --- [ ARGUMENT PARSING ] ---
FLEET_SIZE=${1:-$DEFAULT_FLEET_SIZE}

if ! [[ "$FLEET_SIZE" =~ ^[0-9]+$ ]] || [ "$FLEET_SIZE" -le 0 ]; then
  echo "[ERROR] Invalid fleet size: $FLEET_SIZE" >&2
  echo "Usage: $0 [fleet_size]" >&2
  exit 1
fi

TITAN_ROOT="/home/titan/TitanNetwork"
WORKER_PATH_HOST="$TITAN_ROOT/core/limb/worker_node.py"

if [ ! -f "$WORKER_PATH_HOST" ]; then
  echo "[ERROR] worker_node.py not found at $WORKER_PATH_HOST" >&2
  exit 1
fi

# Optional wallet config: if worker_wallets.env exists, source it to load
# WORKER_WALLET_1, WORKER_WALLET_2, ... without manual exports.
WALLET_ENV_FILE="$TITAN_ROOT/worker_wallets.env"
if [ -f "$WALLET_ENV_FILE" ]; then
  # shellcheck disable=SC1090
  . "$WALLET_ENV_FILE"
  echo "[TITAN] Loaded wallet config from $WALLET_ENV_FILE"
fi

# Ensure worker image exists; build once if missing (no rebuilds needed for code changes
# because worker_node.py is bind-mounted from the host).
if ! docker images -q "$IMAGE_NAME" >/dev/null 2>&1 || [ -z "$(docker images -q "$IMAGE_NAME" 2>/dev/null)" ]; then
  echo "[TITAN] Worker image $IMAGE_NAME not found. Building from Dockerfile.worker..."
  if [ -f "$TITAN_ROOT/Dockerfile.worker" ]; then
    (cd "$TITAN_ROOT" && docker build -f Dockerfile.worker -t "$IMAGE_NAME" .) || {
      echo "[ERROR] Failed to build image $IMAGE_NAME" >&2
      exit 1
    }
  else
    echo "[ERROR] Dockerfile.worker not found at $TITAN_ROOT" >&2
    exit 1
  fi
fi

echo "[TITAN] Deploying fleet of $FLEET_SIZE worker container(s)"

echo "[TITAN] Using Brain uplink: $BRAIN_UPLINK"

echo "[TITAN] Using image: $IMAGE_NAME"

# --- [ FLEET DEPLOYMENT ] ---
for i in $(seq 1 "$FLEET_SIZE"); do
  CONTAINER_NAME="${FLEET_PREFIX}${i}"

  echo "" 
  echo "[TITAN] Deploying unit: $CONTAINER_NAME"

  # Stop only our managed container if it exists
  if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "  >> Existing container detected. Stopping..."
    docker stop "$CONTAINER_NAME" > /dev/null 2>&1 || true
    echo "  >> Removing old container..."
    docker rm "$CONTAINER_NAME" > /dev/null 2>&1 || true
  fi

  # Optional per-worker wallet: set WORKER_WALLET_1, WORKER_WALLET_2, ... in env
  wallet_env_name="WORKER_WALLET_${i}"
  # Use bash indirect expansion so values sourced from worker_wallets.env are seen
  wallet_value="${!wallet_env_name:-}"
  wallet_args=()
  if [ -n "$wallet_value" ]; then
    wallet_args=( -e OVERRIDE_WALLET_ADDRESS="$wallet_value" )
    echo "  >> Assigning wallet to $CONTAINER_NAME: ${wallet_value:0:6}..."
  fi

  # Launch new container with live code mount
  docker run -d \
    --name "$CONTAINER_NAME" \
    --network host \
    --runtime nvidia \
    --restart unless-stopped \
    -e BRAIN_URL="$BRAIN_UPLINK" \
    -e WORKER_NAME="$CONTAINER_NAME" \
    -e TITAN_CONTAINER_MODE="true" \
    "${wallet_args[@]}" \
    -v "$TITAN_ROOT":/app/workspace \
    "$IMAGE_NAME" > /dev/null 2>&1

  if [ $? -eq 0 ]; then
    echo "  >> Unit online: $CONTAINER_NAME"
  else
    echo "  >> FAILED to start: $CONTAINER_NAME" >&2
  fi

  # Small delay for rolling behavior (avoid brain shock)
  sleep 1

done

echo "" 
echo "[TITAN] Fleet deployment complete. Managed units: $FLEET_SIZE"

echo "[TITAN] To restart a single unit with updated code:"
echo "  docker restart ${FLEET_PREFIX}1"