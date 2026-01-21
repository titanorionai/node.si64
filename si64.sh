#!/usr/bin/env bash
# SI64 convenience shell helpers

# --- Base paths ---
export SI64_ROOT="$HOME/TitanNetwork"
export SI64_CORE="$HOME/.si64-core"

# --- Quick cd helpers ---
alias si-core='cd "$SI64_ROOT"'
alias si-node-core='cd "$SI64_CORE"'

# --- Installer / onboarding ---
alias si-install='curl -sL https://si64.net/install | bash'
alias si-node-run='cd "$SI64_CORE" && source venv/bin/activate && python3 limb/worker_node.py --connect wss://si64.net/connect'

# --- Ghost Fleet / Docker workers ---
alias si-fleet-remote='cd "$SI64_ROOT" && TARGET_MODE=remote ./deploy_fleet.sh 5'
alias si-fleet-local='cd "$SI64_ROOT" && TARGET_MODE=local ./deploy_fleet.sh 5'

# --- Tunnel monitor ---
alias si-tunnel-check='cd "$SI64_ROOT" && ./scripts/monitor_tunnel.py'

# --- Load / stress testing ---
alias si-stress-remote='cd "$SI64_ROOT" && ./scripts/titan_stress_test.py'
alias si-stress-local='cd "$SI64_ROOT" && TITAN_STRESS_TARGET=http://127.0.0.1:8000/submit_job ./scripts/titan_stress_test.py'

# --- Security / Sentinel ---
alias si-sentinel='cd "$SI64_ROOT/scripts" && sudo ./titan_sentinel.py'
alias si-verify='cd "$SI64_ROOT" && ./verify_security.sh'

# --- Tests ---
alias si-test-api='cd "$SI64_ROOT" && pytest src/tests/test_api_endpoints.py -q'

# Small confirmation when sourced directly
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  echo "Loaded SI64 helpers. In future, use: source $SI64_ROOT/si64.sh"
fi
