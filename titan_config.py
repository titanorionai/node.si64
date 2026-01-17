"""
TITAN PROTOCOL | GLOBAL CONFIGURATION MANIFEST (V16.0 - SOVEREIGN CLASS)
========================================================================
AUTHORITY:       CENTRAL COMMAND (C2)
CLASSIFICATION:  RESTRICTED // INTERNAL USE ONLY
STATUS:          ACTIVE (MAINNET INTEGRATED)

WARNING:
  - REAL FUNDS AT RISK (SOLANA MAINNET).
  - HARDWARE THERMAL LIMITS ACTIVE.
  - UNAUTHORIZED ACCESS ATTEMPTS WILL BE LOGGED.
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# --- 1. SECURE VAULT INITIALIZATION ---
# Locates and loads the encrypted environment variables.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")

if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH, override=True)
else:
    # Non-blocking warning for Docker/CI environments where vars are injected
    print(f"[WARN] VAULT MISSING AT {ENV_PATH}. RELYING ON SYSTEM ENVIRONMENT.")

# --- 2. IDENTITY & AUTHENTICATION ---
NODE_ID = os.getenv("TITAN_NODE_ID", "UNIT_UNKNOWN")
DEPLOYMENT_ENV = os.getenv("TITAN_ENV", "PRODUCTION")
GENESIS_KEY = os.getenv("TITAN_GENESIS_KEY")

# [SECURITY INTERLOCK]
# Immediate system halt if the cryptographic keystone is missing.
if not GENESIS_KEY:
    print("\n[CRITICAL] SECURITY BREACH: GENESIS_KEY NOT FOUND.")
    print(">> INITIATING EMERGENCY SHUTDOWN SEQUENCE.")
    sys.exit(1)

# --- 3. NETWORK TOPOLOGY (C2 UPLINK) ---
# The IP/Domain that Limbs connect to.
DISPATCHER_IP = os.getenv("TITAN_DISPATCHER_IP", "127.0.0.1")
DISPATCHER_HOST = os.getenv("TITAN_DISPATCHER_HOST", "0.0.0.0")
DISPATCHER_PORT = int(os.getenv("TITAN_PORT", 8000))

# Public Uplink Construction (Auto-Detects SSL requirement based on domain)
TITAN_DOMAIN = "si64.net" # Primary Target
if "localhost" in DISPATCHER_IP or "127.0.0.1" in DISPATCHER_IP:
    WEBSOCKET_URL = f"ws://{DISPATCHER_IP}:{DISPATCHER_PORT}/connect"
else:
    # Assume SSL for remote domains (Cloudflare Tunnel)
    WEBSOCKET_URL = f"wss://{TITAN_DOMAIN}/connect"

# --- 4. FINANCIAL ECONOMICS (CHAINSTACK / MAINNET) ---
# RPC Endpoint for Solana Settlement
SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
# Optional Auth Token for Premium RPCs
SOLANA_RPC_TOKEN = os.getenv("SOLANA_RPC_TOKEN", "")

# Economic Policy (Immutable Constants)
BOUNTY_PER_JOB = float(os.getenv("BOUNTY_PER_JOB", "0.0001"))
WORKER_FEE_PERCENT = float(os.getenv("WORKER_FEE_PERCENT", "0.90")) # 90% to Compute Provider
PROTOCOL_TAX = float(os.getenv("PROTOCOL_TAX", "0.10"))              # 10% to DAO Treasury

# --- 5. HARDWARE SAFETY PROTOCOLS ---
# Thermal Shutdown Limit (Celsius) - Protects Silicon.
MAX_SAFE_TEMP_C = int(os.getenv("TITAN_MAX_TEMP", 85))
# Network Heartbeat (Seconds) - High frequency for low latency.
HEARTBEAT_INTERVAL = 2.0
RECONNECT_DELAY = 5

# --- 6. NEURAL INTERFACES ---
# Pointers to local inference engines (Ollama / Llama.cpp)
TITAN_OLLAMA_HOST = os.getenv("TITAN_OLLAMA_HOST", "http://localhost:11434")
TITAN_COMFY_HOST = os.getenv("TITAN_COMFY_HOST", "http://127.0.0.1:8188")
JOB_TIMEOUT_SEC = int(os.getenv("JOB_TIMEOUT_SEC", "600"))
DEFAULT_WALLET = os.getenv("TITAN_DEFAULT_WALLET", "5mEvgLUE2MvNTSr9mGRo6zvL2M2Jng132sDCP4411FHZ")

# --- 7. FILESYSTEM ARCHITECTURE ---
# Standardized paths for all modules.
BANK_WALLET_PATH = os.path.join(BASE_DIR, "titan_bank.json")
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
WAREHOUSE_PATH = os.path.join(BASE_DIR, "warehouse")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

# Automatic Provisioning: Repair directory structure on boot.
for _path in [SCRIPTS_DIR, WAREHOUSE_PATH, LOGS_DIR]:
    os.makedirs(_path, exist_ok=True)

# --- 8. CENTRALIZED LOGGING SYSTEM ---
# Configures a unified logging format for all importing modules.
LOG_FILE_PATH = os.path.join(LOGS_DIR, "titan_network.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | [%(name)s] | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE_PATH)
    ]
)

# --- 9. SYSTEM DIAGNOSTIC (PRE-FLIGHT CHECK) ---
def run_diagnostics():
    """Prints a tactical summary of the active configuration."""
    print(f"\n>> TITAN PROTOCOL MANIFEST V16.0 [INITIALIZED]")
    print(f"   -------------------------------------------")
    print(f"   [MODE]       {DEPLOYMENT_ENV}")
    print(f"   [IDENTITY]   {NODE_ID}")
    print(f"   [UPLINK]     {WEBSOCKET_URL}")
    print(f"   [RPC]        {SOLANA_RPC_URL[:40]}...")
    print(f"   [BANKING]    {'ACTIVE' if os.path.exists(BANK_WALLET_PATH) else 'MISSING (SIMULATION)'}")
    print(f"   [ECONOMY]    {BOUNTY_PER_JOB} SOL/OP | SPLIT: {int(WORKER_FEE_PERCENT*100)}/{int(PROTOCOL_TAX*100)}")
    print(f"   -------------------------------------------\n")

if __name__ == "__main__":
    run_diagnostics()
