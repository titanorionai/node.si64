#!/usr/bin/env bash
set -euo pipefail

# Scan the repository for files that must never be published to the public repo.
# Exits with non-zero if any forbidden files are found.

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

FORBIDDEN_PATTERNS=(
  "dispatcher.py"
  "control_deck.py"
  "*.db"
  "*.sqlite"
  "genesis*"
  "*secret*"
  "*key*"
  "*.pem"
  "*.env"
  "__pycache__"
  "*.pyc"
  "worker-node-local.tar"
)

FOUND=()
for pat in "${FORBIDDEN_PATTERNS[@]}"; do
  # use git ls-files to respect repo state
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    FOUND+=("$f")
  done < <(git ls-files -- "${pat}")
done

if [ ${#FOUND[@]} -gt 0 ]; then
  echo "[ERROR] Forbidden files detected that must not be pushed to the public repo:" >&2
  for x in "${FOUND[@]}"; do
    echo "  - $x" >&2
  done
  echo "Aborting push. Use ./scripts/sync_to_public.sh to publish only whitelisted worker files." >&2
  exit 2
fi

echo "[OK] No forbidden files found in repository index."
