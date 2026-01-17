#!/bin/bash
# TITAN TASK EXECUTOR v0.1 (Connectivity Test)
# Usage: ./execute_task.sh --type TYPE --prompt PROMPT --out OUT

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --type) TYPE="$2"; shift ;;
        --prompt) PROMPT="$2"; shift ;;
        --out) OUT="$2"; shift ;;
        *) echo "Unknown: $1"; exit 1 ;;
    esac
    shift
done

# SAFETY FIX: Create the directory if it doesn't exist
DIR=$(dirname "$OUT")
mkdir -p "$DIR"

# Simulate AI Processing
sleep 2

# Write Success Receipt
echo "{\"status\": \"success\", \"data\": \"Titan Node Active. Received: $PROMPT\", \"timestamp\": \"$(date)\"}" > "$OUT"
