"""
TITAN PROTOCOL | GLOBAL CONFIGURATION MANIFEST (v3.0)
=====================================================
"""
import os

# --- IDENTITY ---
NODE_ID = os.getenv("TITAN_NODE_ID", "ORIN_GENESIS_01")
DEPLOYMENT_ENV = os.getenv("TITAN_ENV", "DEV")

# --- SECURITY ---
GENESIS_KEY = os.getenv("TITAN_GENESIS_KEY", "TITAN_GENESIS_KEY_V1_SECURE")

# --- NETWORK ---
DISPATCHER_IP   = os.getenv("TITAN_DISPATCHER_IP", "127.0.0.1")
DISPATCHER_HOST = "0.0.0.0"
DISPATCHER_PORT = int(os.getenv("TITAN_PORT", 8000))
WEBSOCKET_URL   = f"ws://{DISPATCHER_IP}:{DISPATCHER_PORT}/connect"

# --- FILESYSTEM ---
SCRIPTS_DIR = os.getenv("TITAN_SCRIPTS_DIR", "./scripts")
WAREHOUSE_PATH = os.getenv("TITAN_WAREHOUSE", "/mnt/warehouse")

# --- HARDWARE SAFETY ---
MAX_SAFE_TEMP_C = 85
HEARTBEAT_INTERVAL = 1.0
RECONNECT_DELAY = 5

# --- FINANCIAL ECONOMICS ---
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"
BOUNTY_PER_JOB = 0.001
WORKER_FEE_PERCENT  = 0.95
FOUNDER_FEE_PERCENT = 0.05
BANK_WALLET_PATH = os.path.join(os.path.dirname(__file__), "titan_bank.json")

# --- EXTERNAL AI SERVICES ---
TITAN_OLLAMA_HOST = os.getenv("TITAN_OLLAMA_HOST", "http://localhost:11434")
TITAN_COMFY_HOST  = os.getenv("TITAN_COMFY_HOST", "http://127.0.0.1:8188")
JOB_TIMEOUT_SEC = 600
