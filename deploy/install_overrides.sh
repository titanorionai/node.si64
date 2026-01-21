#!/usr/bin/env bash
set -euo pipefail

DEST_DIR_BRAIN=/etc/systemd/system/titan-brain.service.d
DEST_DIR_DISPATCHER=/etc/systemd/system/titan-dispatcher.service.d

echo "Installing systemd drop-ins for titan-brain and titan-dispatcher..."
sudo mkdir -p "$DEST_DIR_BRAIN" "$DEST_DIR_DISPATCHER"
sudo cp -v "$(dirname "$0")/titan-brain.override.conf" "$DEST_DIR_BRAIN/override.conf"
sudo cp -v "$(dirname "$0")/titan-dispatcher.override.conf" "$DEST_DIR_DISPATCHER/override.conf"
echo "Reloading systemd and restarting services..."
sudo systemctl daemon-reload
if sudo systemctl restart titan-brain.service 2>/dev/null; then
  echo "Restarted titan-brain.service"
else
  sudo systemctl restart titan-dispatcher.service || true
  echo "Restarted titan-dispatcher.service (if present)"
fi

echo "Showing Environment for services (if present):"
sudo systemctl show titan-brain.service -p Environment || true
sudo systemctl show titan-dispatcher.service -p Environment || true

echo "Done. Check logs with: sudo journalctl -u titan-brain.service -n 200 --no-pager | grep -E 'yellowstone|solana-mainnet.core.chainstack.com|HTTP Request: POST'"
