#!/usr/bin/env bash
set -euo pipefail
OUT=${1:-brain/genesis.key}
mkdir -p $(dirname "$OUT")
# Generate 32-byte hex key
KEY=$(openssl rand -hex 32)
printf "%s" "$KEY" > "$OUT"
chmod 600 "$OUT"
echo "Wrote genesis key to $OUT (chmod 600)"
