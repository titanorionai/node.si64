#!/bin/bash
# TITAN PROTOCOL | TASK EXECUTOR v4.0
# Integrity: Atomic Writes

OLLAMA_HOST="${TITAN_OLLAMA_HOST:-http://localhost:11434}"
TIMEOUT_SEC=600

log_info() { echo -e "$(date '+%Y-%m-%d %H:%M:%S') [INFO]  $1"; }
log_err()  { echo -e "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] $1" >&2; }

# Args
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --type)   TYPE="$2"; shift ;;
        --prompt) PROMPT="$2"; shift ;;
        --out)    OUT="$2"; shift ;;
        *) shift ;;
    esac
    shift
done

if [[ -z "$TYPE" || -z "$OUT" ]]; then exit 1; fi
mkdir -p "$(dirname "$OUT")"

write_receipt() {
    jq -n --arg s "$1" --arg m "$2" --arg t "$TYPE" --arg d "$(date -u)" --argjson p "$3" \
        '{status: $s, message: $m, type: $t, timestamp: $d, data: $p}' > "$OUT.tmp" && mv "$OUT.tmp" "$OUT"
}

execute_llama() {
    local payload=$(jq -n --arg m "llama3.2" --arg p "$PROMPT" '{model: $m, prompt: $p, stream: false}')
    local raw="/tmp/titan_$$.json"
    timeout "$TIMEOUT_SEC" curl -X POST "$OLLAMA_HOST/api/generate" -s -d "$payload" -o "$raw"
    if [[ $? -eq 0 && -s "$raw" ]]; then
        local txt=$(jq -r .response "$raw")
        write_receipt "SUCCESS" "Inference Done" "$(jq -n --arg t "$txt" '{response: $t}')"
    else
        write_receipt "FAILED" "Inference Error" "null"
    fi
    rm -f "$raw"
}

case "$TYPE" in
    LLAMA) execute_llama ;;
    *)     write_receipt "FAILED" "Unknown Type" "null" ;;
esac
exit 0
#!/bin/bash
# TITAN PROTOCOL | TASK EXECUTOR v4.0
# Integrity: Atomic Writes

OLLAMA_HOST="${TITAN_OLLAMA_HOST:-http://localhost:11434}"
TIMEOUT_SEC=600

log_info() { echo -e "$(date '+%Y-%m-%d %H:%M:%S') [INFO]  $1"; }
log_err()  { echo -e "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] $1" >&2; }

# Args
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --type)   TYPE="$2"; shift ;;
        --prompt) PROMPT="$2"; shift ;;
        --out)    OUT="$2"; shift ;;
        *) shift ;;
    esac
    shift
done

if [[ -z "$TYPE" || -z "$OUT" ]]; then exit 1; fi
mkdir -p "$(dirname "$OUT")"

write_receipt() {
    jq -n --arg s "$1" --arg m "$2" --arg t "$TYPE" --arg d "$(date -u)" --argjson p "$3" \
        '{status: $s, message: $m, type: $t, timestamp: $d, data: $p}' > "$OUT.tmp" && mv "$OUT.tmp" "$OUT"
}

execute_llama() {
    local payload=$(jq -n --arg m "llama3.2" --arg p "$PROMPT" '{model: $m, prompt: $p, stream: false}')
    local raw="/tmp/titan_$$.json"
    timeout "$TIMEOUT_SEC" curl -X POST "$OLLAMA_HOST/api/generate" -s -d "$payload" -o "$raw"
    if [[ $? -eq 0 && -s "$raw" ]]; then
        local txt=$(jq -r .response "$raw")
        write_receipt "SUCCESS" "Inference Done" "$(jq -n --arg t "$txt" '{response: $t}')"
    else
        write_receipt "FAILED" "Inference Error" "null"
    fi
    rm -f "$raw"
}

case "$TYPE" in
    LLAMA) execute_llama ;;
    *)     write_receipt "FAILED" "Unknown Type" "null" ;;
esac
exit 0
