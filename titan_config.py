"""TITAN PROTOCOL | GLOBAL CONFIGURATION MANIFEST (v4.0)

Minimal, importable Python config used by the dispatcher and workers.
"""
import os

# --- IDENTITY ---
NODE_ID = os.getenv("TITAN_NODE_ID", "ORIN_GENESIS_01")
DEPLOYMENT_ENV = os.getenv("TITAN_ENV", "PRODUCTION")

# --- SECURITY ---
GENESIS_KEY = os.getenv("TITAN_GENESIS_KEY", "TITAN_GENESIS_KEY_V1_SECURE")

# --- NETWORK ---
DISPATCHER_IP = os.getenv("TITAN_DISPATCHER_IP", "127.0.0.1")
DISPATCHER_HOST = "0.0.0.0"
DISPATCHER_PORT = int(os.getenv("TITAN_PORT", 8000))
WEBSOCKET_URL = f"ws://{DISPATCHER_IP}:{DISPATCHER_PORT}/connect"

# --- FILESYSTEM ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
WAREHOUSE_PATH = os.path.join(BASE_DIR, "warehouse")

# --- HARDWARE SAFETY ---
MAX_SAFE_TEMP_C = 85
HEARTBEAT_INTERVAL = 1.0
RECONNECT_DELAY = 5

# --- FINANCIAL ECONOMICS (SOLANA MAINNET OR CUSTOM RPC) ---
# Override by setting environment variables `SOLANA_RPC_URL` and `SOLANA_RPC_TOKEN`.
SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
# Optional per-request header token for RPC providers (e.g. Chainstack)
SOLANA_RPC_TOKEN = os.getenv("SOLANA_RPC_TOKEN", "")

BOUNTY_PER_JOB = float(os.getenv("BOUNTY_PER_JOB", "0.001"))
WORKER_FEE_PERCENT = float(os.getenv("WORKER_FEE_PERCENT", "0.90"))
FOUNDER_FEE_PERCENT = float(os.getenv("FOUNDER_FEE_PERCENT", "0.10"))
BANK_WALLET_PATH = os.path.join(BASE_DIR, "titan_bank.json")

# --- EXTERNAL AI SERVICES ---
TITAN_OLLAMA_HOST = os.getenv("TITAN_OLLAMA_HOST", "http://localhost:11434")
TITAN_COMFY_HOST = os.getenv("TITAN_COMFY_HOST", "http://127.0.0.1:8188")
JOB_TIMEOUT_SEC = int(os.getenv("JOB_TIMEOUT_SEC", "600"))
