#!/bin/bash
# TITAN PROTOCOL | BRAIN-ONLY RESTART
# ====================================

echo -e "\033[0;32m>>> RESTARTING TITAN CORTEX (BRAIN ONLY)...\033[0m"

# 1. Restart the Brain service
echo "[1/2] Restarting Titan Cortex (Brain)..."
sudo systemctl restart titan-brain

# 2. Wait briefly for Brain to boot
echo "   >> Waiting for Cortex to stabilize..."
sleep 3

# 3. Health Check
if curl -s http://127.0.0.1:8000/api/stats > /dev/null; then
    echo -e "\033[0;32m   >> CORTEX STATUS: NOMINAL (ONLINE)\033[0m"
else
    echo -e "\033[0;31m   >> CRITICAL: CORTEX FAILED TO START.\033[0m"
    echo "   >> DUMPING ERROR LOGS:"
    sudo journalctl -u titan-brain -n 10 --no-pager
    exit 1
fi

echo -e "\033[0;32m>>> BRAIN RESTART COMPLETE (NO WORKERS LAUNCHED).\033[0m"
