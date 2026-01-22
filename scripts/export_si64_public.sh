#!/usr/bin/env bash
set -euo pipefail

# Export only the worker-essential files into a temporary git repo
# and push to a public repository. Intended to be run from the
# private/dev repository root.

: "${PUBLIC_REPO:?Need PUBLIC_REPO like 'owner/si64-node'}"
: "${PUBLIC_BRANCH:=main}"
: "${GIT_AUTHOR_NAME:=si64-bot}"
: "${GIT_AUTHOR_EMAIL:=si64-bot@example.com}"

TMPDIR=$(mktemp -d)
echo "Preparing export in $TMPDIR"

# Whitelist of files to include in the public distribution
INCLUDE=(
  "core/limb/worker_node.py"
  "requirements.txt"
  "Dockerfile"
  "install.sh"
  "scripts/si64_node_installer.sh"
)

# Copy only the whitelisted files. Fail if any required file is missing.
MISSING=()
for f in "${INCLUDE[@]}"; do
  if [ -e "$f" ]; then
    mkdir -p "$TMPDIR/$(dirname "$f")"
    cp -a "$f" "$TMPDIR/$f"
  else
    MISSING+=("$f")
  fi
done

if [ ${#MISSING[@]} -gt 0 ]; then
  echo "[ERROR] Missing required public files: ${MISSING[*]}" >&2
  echo "Aborting export. Ensure the private repo contains the worker artifacts." >&2
  rm -rf "$TMPDIR"
  exit 2
fi

# Create a minimal README to make the public repo self-contained
if [ ! -f "$TMPDIR/README.md" ]; then
  cat > "$TMPDIR/README.md" <<'EOF'
si64-node — public worker installer and runtime

This repository contains only the worker runtime, installer, and container
build files. It intentionally omits any brain/dispatcher, ledger files,
admin tooling, or private keys.

Use this repository only to build and run a worker node.
EOF
fi

cd "$TMPDIR"
git init -q
git config user.name "$GIT_AUTHOR_NAME"
git config user.email "$GIT_AUTHOR_EMAIL"
git add -A
git commit -m "chore: export worker-only public distribution" >/dev/null

if [ -n "${PUBLIC_REPO_PAT:-}" ]; then
  REMOTE_URL="https://x-access-token:${PUBLIC_REPO_PAT}@github.com/${PUBLIC_REPO}.git"
else
  REMOTE_URL="https://github.com/${PUBLIC_REPO}.git"
fi

git remote add public "$REMOTE_URL"
git push --force public HEAD:"${PUBLIC_BRANCH}"

echo "Pushed worker-only distribution to ${PUBLIC_REPO}:${PUBLIC_BRANCH}"

rm -rf "$TMPDIR"
