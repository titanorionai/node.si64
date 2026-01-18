#!/bin/bash
# TITAN PROTOCOL | FULL SYSTEM AUDIT (BRAIN + STRESS/THREAT HARNESS)
# ==================================================================

set -e

echo -e "\033[0;32m>>> STARTING FULL TITAN AUDIT (BRAIN RESTART + STRESS/THREAT TESTS)...\033[0m"

# Ensure we have a genesis key in the environment
if [ -z "$TITAN_GENESIS_KEY" ]; then
  echo -e "\033[0;31mERROR: TITAN_GENESIS_KEY is not set in this shell.\033[0m"
  echo "Please export TITAN_GENESIS_KEY to match your production genesis key and re-run."
  exit 1
fi

# Target URL for the dispatcher (can override via TITAN_BASE_URL)
export TITAN_BASE_URL="${TITAN_BASE_URL:-http://127.0.0.1:8000}"

echo "[1/2] Restarting brain only via restart_brain_only.sh..."
"$(dirname "$0")/restart_brain_only.sh"

echo "[2/2] Running comprehensive stress + cyber threat harness..."
cd "$(dirname "$0")"
python3 stress_test_threats.py

echo -e "\033[0;32m>>> FULL AUDIT COMPLETE. See STRESS_TEST_REPORT.json for details.\033[0m"
