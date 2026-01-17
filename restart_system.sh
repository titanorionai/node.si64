#!/bin/bash
# TITAN PROTOCOL | SYSTEM RESET SEQUENCE
# ======================================

echo -e "\033[0;32m>>> INITIATING TITAN PROTOCOL RESTART SEQUENCE...\033[0m"

# 1. Restart the Brain (Service)
echo "[1/3] Restarting Titan Cortex (Brain)..."
sudo systemctl restart titan-brain

# 2. Kill any stale Workers
echo "[2/3] Neutralizing old Worker Nodes..."
pkill -f worker_node.py || echo "   >> No active workers found to kill."

# 3. Wait for Brain to boot
echo "   >> Waiting for Cortex to stabilize..."
sleep 3

# 4. Health Check (The "Ping")
if curl -s http://127.0.0.1:8000/api/stats > /dev/null; then
    echo -e "\033[0;32m   >> CORTEX STATUS: NOMINAL (ONLINE)\033[0m"
else
    echo -e "\033[0;31m   >> CRITICAL: CORTEX FAILED TO START.\033[0m"
    echo "   >> DUMPING ERROR LOGS:"
    sudo journalctl -u titan-brain -n 10 --no-pager
    exit 1
fi

# 5. Launch Worker
echo "[3/3] Deploying Titan Limb (Worker)..."
echo -e "\033[0;36m>>> WORKER OUTPUT FOLLOWS (Press Ctrl+C to stop worker) <<<\033[0m"
echo "-------------------------------------------------------------"

# Run the worker and attach output to this terminal
python3 ~/TitanNetwork/core/limb/worker_node.py
