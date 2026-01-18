#!/usr/bin/env bash
set -euo pipefail

cd /home/titan/TitanNetwork

echo "[Ollama] Starting titan-ollama-engine container via docker compose..."
docker compose up -d ollama

echo "[Ollama] Service requested. Current containers:"
docker ps --filter "name=titan-ollama-engine"
