#!/bin/bash
# TITAN PROTOCOL | QUICK FLEET LAUNCH (5 WORKERS)
# Uses worker_wallets.env (if present) to assign wallets,
# then deploys 5 containerized workers.

set -e

ROOT_DIR="$HOME/TitanNetwork"
cd "$ROOT_DIR"

if [ ! -f "$ROOT_DIR/worker_wallets.env" ]; then
  echo "[WARN] worker_wallets.env not found in $ROOT_DIR"
  echo "       Workers without WORKER_WALLET_N entries will use the default wallet."
fi

"$ROOT_DIR/deploy_fleet.sh" 5
