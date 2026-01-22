#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALLER="$SCRIPT_DIR/scripts/si64_node_installer.sh"

if [ ! -x "$INSTALLER" ]; then
  echo "[si64] Error: $INSTALLER not found or not executable." >&2
  echo "[si64] Make sure you are in the root of the si64-core repo." >&2
  exit 1
fi

exec "$INSTALLER" "$@"
