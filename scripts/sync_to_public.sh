#!/usr/bin/env bash
set -euo pipefail

# Wrapper that calls export_si64_public.sh then verifies and pushes.
# Usage: PUBLIC_REPO=owner/si64-node PUBLIC_BRANCH=main ./scripts/sync_to_public.sh

PUBLIC_REPO=${PUBLIC_REPO:?Need PUBLIC_REPO like 'owner/si64-node'}
PUBLIC_BRANCH=${PUBLIC_BRANCH:=main}

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT="$ROOT_DIR/scripts/export_si64_public.sh"

if [ ! -x "$SCRIPT" ]; then
  echo "[ERROR] Missing export script: $SCRIPT" >&2
  exit 1
fi

echo "[INFO] Running export script to prepare public payload..."
PUBLIC_REPO_PAT=${PUBLIC_REPO_PAT:-}
PUBLIC_REPO="$PUBLIC_REPO" PUBLIC_BRANCH="$PUBLIC_BRANCH" PUBLIC_REPO_PAT="$PUBLIC_REPO_PAT" "$SCRIPT"

echo "[INFO] Export complete. Verifying public repo connectivity..."

# Quick sanity check: ensure we can reach the remote
if ! git ls-remote "https://github.com/${PUBLIC_REPO}.git" &> /dev/null; then
  echo "[WARN] Unable to reach https://github.com/${PUBLIC_REPO}.git - push may fail due to auth or permissions." >&2
  exit 0
fi

echo "[INFO] Public sync finished. The public repo was updated by the export script."
