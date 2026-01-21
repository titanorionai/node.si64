#!/usr/bin/env bash
set -euo pipefail

REPO=${1:-titanorion/worker-node:latest}
PLATFORM=${2:-linux/arm64}

echo "[BUILD] Ensuring buildx builder exists..."
docker buildx create --name titan-builder --use 2>/dev/null || true
docker buildx inspect --bootstrap

echo "[BUILD] Building for platform ${PLATFORM} and pushing to ${REPO}"
echo "Note: ensure you're logged in (docker login) before pushing."

docker buildx build --platform ${PLATFORM} \
  -t ${REPO} \
  -t ${REPO%:*}:v1.0.0-arm64 \
  --push .

echo "[BUILD] Build+push complete."
