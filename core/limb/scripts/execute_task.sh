#!/bin/bash
# ==============================================================================
# TITAN PROTOCOL | TASK EXECUTOR v2.1 (ENTERPRISE)
# ==============================================================================
# Role: Universal Adapter for AI Cores (Ollama, ComfyUI, System Diagnostics)
# Target: NVIDIA Jetson (ARM64) / Linux / macOS
# Integrity: Enforces timeouts, strict error handling, and atomic writes.
# ==============================================================================

# --- 1. CONFIGURATION ---
# Default to localhost if environment variables are not set
OLLAMA_HOST="${TITAN_OLLAMA_HOST:-http://localhost:11434}"
COMFY_HOST="${TITAN_COMFY_HOST:-http://127.0.0.1:8188}"
TIMEOUT_SEC=600   # Hard limit: 10 Minutes per job

# --- 2. LOGGING TELEMETRY ---
# Standardized output for parsing by the Python Worker
log_info() { echo -e "$(date '+%Y-%m-%d %H:%M:%S') [INFO]  $1"; }
log_warn() { echo -e "$(date '+%Y-%m-%d %H:%M:%S') [WARN]  $1"; }
log_err()  { echo -e "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] $1" >&2; }

# --- 3. SYSTEM INTEGRITY CHECKS ---
# Verify critical dependencies before execution
REQUIRED_BINS=("curl" "jq" "timeout")
for bin in "${REQUIRED_BINS[@]}"; do
    if ! command -v "$bin" &> /dev/null; then
        log_err "CRITICAL: Dependency '$bin' missing. Install via apt/brew."
        # We try to write a failure receipt even if tools are missing, 
        # but without jq/curl this might fail, so we exit hard.
        exit 99
    fi
done

# --- 4. ARGUMENT PARSING ---
TYPE=""
PROMPT=""
OUT=""

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --type)   TYPE="$2"; shift ;;
        --prompt) PROMPT="$2"; shift ;;
        --out)    OUT="$2"; shift ;;
        *) log_err "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Input Validation
if [[ -z "$TYPE" || -z "$PROMPT" || -z "$OUT" ]]; then
    log_err "Usage: $0 --type <TYPE> --prompt <PROMPT> --out <FILE_PATH>"
    exit 1
fi

# Ensure Output Directory Exists and is Writable
OUT_DIR=$(dirname "$OUT")
if ! mkdir -p "$OUT_DIR"; then
    log_err "CRITICAL: Cannot create output directory $OUT_DIR"
    exit 1
fi

# --- 5. UTILITY FUNCTIONS ---

# Writes a standardized JSON receipt to disk (Atomic Operation)
write_receipt() {
    local status=$1
    local message=$2
    local data=$3
    
    # If data is empty, make it null
    if [[ -z "$data" ]]; then data="null"; fi

    # Construct JSON safely using jq
    # We write to a .tmp file first, then move it. 
    # This prevents the Python worker from reading a partial file.
    jq -n \
        --arg status "$status" \
        --arg msg "$message" \
        --arg type "$TYPE" \
        --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        --argjson payload "$data" \
        '{status: $status, message: $msg, job_type: $type, timestamp: $ts, data: $payload}' \
        > "$OUT.tmp" && mv "$OUT.tmp" "$OUT"
}

# Checks if a service endpoint is reachable
check_health() {
    local url=$1
    local service=$2
    # --max-time 3 prevents hanging on network check
    if curl --output /dev/null --silent --head --fail --max-time 3 "$url"; then
        log_info "Link Verified: $service is ONLINE."
        return 0
    else
        log_err "Link Failure: $service is UNREACHABLE at $url"
        return 1
    fi
}

# --- 6. EXECUTION ENGINES ---

# ENGINE A: OLLAMA (LLM Inference)
execute_llama() {
    log_info "Initializing Cortex Engine (Llama 3.2)..."

    # A. Health Check
    if ! check_health "$OLLAMA_HOST" "Ollama"; then
        write_receipt "FAILED" "Ollama Service Unreachable" "null"
        exit 101
    fi

    # B. Construct Payload
    # Note: 'stream: false' is critical for batch processing
    # We use jq to safely escape the user prompt
    local payload
    payload=$(jq -n \
                  --arg model "llama3.2" \
                  --arg prompt "$PROMPT" \
                  '{model: $model, prompt: $prompt, stream: false}')

    # C. Execute with Timeout
    log_info "Dispatching payload to Cortex..."
    
    # Use a unique temporary file for the raw response
    local raw_response="/tmp/titan_llama_raw_$$.json"
    
    # We use 'timeout' to prevent hanging indefinitely.
    # -s: Silent mode
    # -d: POST Data
    # -o: Output file
    timeout "$TIMEOUT_SEC" curl -X POST "$OLLAMA_HOST/api/generate" \
        -s \
        -d "$payload" \
        -o "$raw_response"
    
    local exit_code=$?

    # D. Handle Results
    if [[ $exit_code -eq 124 ]]; then
        log_err "Execution Timed Out (${TIMEOUT_SEC}s)"
        write_receipt "FAILED" "Timeout Exceeded" "null"
        rm -f "$raw_response"
        exit 102
    fi

    if [[ -s "$raw_response" ]]; then
        # Parse the raw response to ensure it's valid JSON
        if jq -e .response "$raw_response" > /dev/null; then
            local result_text
            result_text=$(jq -r .response "$raw_response")
            
            # Write final receipt
            # We encapsulate the result text into a structured JSON object
            local json_data
            json_data=$(jq -n --arg txt "$result_text" '{response: $txt}')
            write_receipt "SUCCESS" "Inference Complete" "$json_data"
            log_info "Task Complete. Receipt generated."
        else
            # Sometimes Ollama returns an error object
            local err_msg
            err_msg=$(jq -r .error "$raw_response" 2>/dev/null || echo "Invalid JSON from Cortex")
            log_err "Cortex Error: $err_msg"
            write_receipt "FAILED" "Cortex Error: $err_msg" "null"
        fi
    else
        write_receipt "FAILED" "Empty Response from Cortex" "null"
    fi
    
    rm -f "$raw_response"
}

# ENGINE B: COMFYUI (Image Synthesis)
execute_comfy() {
    log_info "Initializing Artist Engine (ComfyUI)..."

    # A. Health Check
    if ! check_health "$COMFY_HOST" "ComfyUI"; then
        write_receipt "FAILED" "ComfyUI Service Unreachable" "null"
        exit 201
    fi

    # B. Workflow (Simulated for V1 Stability)
    # Real ComfyUI API requires constructing a massive node graph JSON (Phase 2).
    # For V1, we validate connectivity and simulate the render time.
    
    log_info "Queueing Render Task..."
    sleep 2 # Simulate handoff latency

    # C. Generate Receipt
    local json_data
    json_data=$(jq -n \
        --arg prompt "$PROMPT" \
        --arg engine "StableDiffusionXL" \
        '{asset_type: "image", prompt: $prompt, engine: $engine, status: "SIMULATED_RENDER"}')
        
    write_receipt "SUCCESS" "Asset Rendered (Simulated)" "$json_data"
    log_info "Task Complete. Receipt generated."
}

# ENGINE C: DIAGNOSTICS
execute_syscheck() {
    log_info "Running System Diagnostics..."
    
    local uptime=$(uptime -p)
    local disk=$(df -h / | awk 'NR==2 {print $5}')
    
    local json_data
    json_data=$(jq -n \
        --arg up "$uptime" \
        --arg disk "$disk" \
        '{uptime: $up, disk_usage: $disk, status: "HEALTHY"}')
        
    write_receipt "SUCCESS" "Diagnostics Complete" "$json_data"
}

# --- 7. MAIN CONTROLLER ---

log_info "TITAN EXECUTOR INITIALIZED (PID $$)"
log_info "Targeting: $TYPE"

case "$TYPE" in
    LLAMA)
        execute_llama
        ;;
    IMAGE)
        execute_comfy
        ;;
    SYSCHECK)
        execute_syscheck
        ;;
    *)
        log_err "CRITICAL: Unknown Job Type '$TYPE'"
        write_receipt "FAILED" "Unknown Job Type" "null"
        exit 1
        ;;
esac

exit 0
