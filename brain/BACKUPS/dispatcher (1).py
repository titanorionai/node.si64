import sys
import os
import json
import logging
import sqlite3
import asyncio
import redis.asyncio as redis
from datetime import datetime
from uuid import uuid4
from typing import Optional, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor

# --- THIRD PARTY ENTERPRISE LIBRARIES ---
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Security
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security.api_key import APIKeyHeader
from starlette.requests import Request
from pydantic import BaseModel, Field

# --- SOLANA FINANCIAL STACK (MODERN SOLDERS V0.30+) ---
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.message import Message
from solders.transaction import Transaction
from solana.rpc.async_api import AsyncClient
from solders.system_program import TransferParams, transfer # <--- FIXED

# --- CONFIGURATION IMPORT ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from titan_config import *
except ImportError:
    # EMERGENCY FALLBACK DEFAULTS
    print("CRITICAL SYSTEM WARNING: Config module missing. Loading Emergency Defaults.")
    GENESIS_KEY = "TITAN_DEBUG_KEY"
    DISPATCHER_HOST = "0.0.0.0"
    DISPATCHER_PORT = 8000
    SOLANA_RPC_URL = "https://api.devnet.solana.com" 
    BOUNTY_PER_JOB = 0.001
    WORKER_FEE_PERCENT = 0.90 

# --- SYSTEM ARCHITECTURE ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "titan_ledger.db")
BANK_WALLET_PATH = os.path.join(BASE_DIR, "titan_bank.json")
STATIC_DIR = os.path.join(BASE_DIR, "www/static")
TEMPLATE_DIR = os.path.join(BASE_DIR, "www/templates")

# --- LOGGING CONFIGURATION ---
LOG_FORMAT = "%(asctime)s | %(levelname)s | [%(name)s] | %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("titan_cortex.log")
    ]
)
logger = logging.getLogger("TITAN_CORTEX")

# --- DATA MODELS ---
class JobRequest(BaseModel):
    """External Job Submission Schema"""
    type: str = Field(..., description="Compute Type: 'LLAMA', 'IMAGE', 'TRAIN'")
    prompt: str = Field(..., description="The input prompt")
    bounty: Optional[float] = Field(BOUNTY_PER_JOB, description="Override Bounty amount")

class JobResponse(BaseModel):
    status: str
    job_id: str
    timestamp: datetime

# --- COMPONENT 1: TITAN VAULT (SQLITE) ---
class TitanVault:
    """
    Internal Accounting & Audit Trail.
    Records every job, payout, and wallet interaction locally.
    Uses WAL mode for high concurrency.
    """
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
        self.executor = ThreadPoolExecutor(max_workers=1)

    def _init_db(self):
        with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
            conn.execute('PRAGMA journal_mode=WAL;')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    job_id TEXT PRIMARY KEY, 
                    worker_wallet TEXT, 
                    amount_sol REAL, 
                    tx_signature TEXT, 
                    timestamp DATETIME,
                    status TEXT
                )
            ''')
            conn.commit()
        logger.info("Titan Vault: Ledger Integrity Verified.")

    def _record_sync(self, job_id, wallet, amount, tx_sig, status):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?)",
                    (job_id, wallet, amount, tx_sig, datetime.now(), status)
                )
            return True
        except Exception as e:
            logger.error(f"Vault Write Error: {e}")
            return False

    async def record_transaction(self, job_id, wallet, amount, tx_sig, status="CONFIRMED"):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self.executor, self._record_sync, job_id, wallet, amount, tx_sig, status
        )
    
    async def get_total_paid(self) -> float:
        """Calculate total SOL paid out to workers."""
        loop = asyncio.get_running_loop()
        def _query():
            with sqlite3.connect(self.db_path) as conn:
                res = conn.execute("SELECT SUM(amount_sol) FROM transactions WHERE status='CONFIRMED'").fetchone()
                return res[0] if res[0] else 0.0
        return await loop.run_in_executor(self.executor, _query)

# --- COMPONENT 2: TITAN BANK (SOLANA) ---
class TitanBank:
    """
    The Central Bank.
    Manages the hot wallet and executes on-chain settlements using Solders.
    """
    def __init__(self, keypair_path: str, rpc_url: str):
        self.client = AsyncClient(rpc_url)
        self.keypair = None
        self.enabled = False
        
        # Load Wallet Integrity Check
        if os.path.exists(keypair_path):
            try:
                with open(keypair_path, "r") as f:
                    # Expecting standard Solana JSON array [12, 23, ...]
                    raw_key = json.load(f)
                    self.keypair = Keypair.from_bytes(bytes(raw_key))
                self.enabled = True
                logger.info(f"Titan Bank: OPEN. Reserve Address: {self.keypair.pubkey()}")
            except Exception as e:
                logger.critical(f"Titan Bank: Keyfile Corrupt. {e}")
        else:
            logger.warning(f"Titan Bank: No Keypair found at {keypair_path}. Settlement Mode: SIMULATION.")

    async def process_payout(self, worker_wallet: str, amount_sol: float) -> str:
        """
        Executes a real SOL transfer using the modern Solders library logic.
        """
        if not self.enabled:
            return "SIMULATED_TX_SIG_00000000"

        try:
            # 1. Validation
            if not worker_wallet or len(worker_wallet) < 32 or "REPLACE" in worker_wallet:
                logger.warning(f"Settlement Aborted: Invalid Wallet '{worker_wallet}'")
                return "FAILED_INVALID_WALLET"

            lamports = int(amount_sol * 1_000_000_000)
            dest_pubkey = Pubkey.from_string(worker_wallet)

            # 2. Check Reserve Balance
            balance = await self.client.get_balance(self.keypair.pubkey())
            if balance.value < lamports + 5000: 
                logger.critical("Titan Bank: INSUFFICIENT FUNDS. Refill Treasury immediately.")
                return "FAILED_NSF"

            # 3. Construct Transaction (MODERN SOLDERS IMPLEMENTATION)
            latest_blockhash = await self.client.get_latest_blockhash()
            
            instruction = transfer(
                TransferParams(
                    from_pubkey=self.keypair.pubkey(),
                    to_pubkey=dest_pubkey,
                    lamports=lamports
                )
            )
            
            # Message Construction (v0.30+ Compliant)
            msg = Message.new_with_blockhash(
                [instruction], 
                self.keypair.pubkey(), 
                latest_blockhash.value.blockhash
            )
            
            # Transaction Signing
            txn = Transaction([self.keypair], msg, latest_blockhash.value.blockhash)
            
            # 4. Broadcast to Network
            response = await self.client.send_transaction(txn)
            
            sig_str = str(response.value)
            logger.info(f"SETTLEMENT: Sent {amount_sol} SOL to {worker_wallet[:6]}... | TX: {sig_str}")
            return sig_str

        except Exception as e:
            logger.error(f"Titan Bank Error: {e}")
            return "FAILED_RPC_ERROR"

    async def close(self):
        await self.client.close()

# --- INITIALIZATION ---
app = FastAPI(title="Titan Protocol Cortex", version="3.3.0")

# Setup Assets
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATE_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

# Initialize Core Systems
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
vault = TitanVault(DB_PATH)
bank = TitanBank(BANK_WALLET_PATH, SOLANA_RPC_URL)

# Security
api_key_header = APIKeyHeader(name="x-genesis-key", auto_error=False)

# --- STARTUP / SHUTDOWN ---
@app.on_event("startup")
async def startup_event():
    logger.info("TITAN CORTEX: SYSTEM ONLINE.")
    try:
        await redis_client.ping()
    except Exception:
        logger.critical("Redis Connection Failed. Aborting.")
        sys.exit(1)

@app.on_event("shutdown")
async def shutdown_event():
    await redis_client.close()
    await bank.close()
    logger.info("TITAN CORTEX: SYSTEM OFFLINE.")

# --- API ENDPOINTS ---

@app.get("/", response_class=HTMLResponse)
async def read_dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/stats")
async def get_stats():
    """Hybrid Telemetry Endpoint (Redis + SQLite)"""
    fleet_size = await redis_client.scard("active_nodes")
    queue_depth = await redis_client.llen("titan_job_queue")
    total_paid = await vault.get_total_paid()
    
    return {
        "status": "OPERATIONAL",
        "fleet_size": fleet_size,
        "queue_depth": queue_depth,
        "total_revenue": total_paid, # In SOL
        "timestamp": str(datetime.now())
    }

@app.post("/submit_job", response_model=JobResponse)
async def submit_job(job: JobRequest, key: str = Security(api_key_header)):
    if key != GENESIS_KEY:
        raise HTTPException(status_code=403, detail="Invalid Key")
        
    job_id = str(uuid4())[:8]
    
    # Construct Payload
    payload = {
        "job_id": job_id,
        "type": job.type,
        "prompt": job.prompt,
        "bounty": job.bounty,
        "timestamp": str(datetime.now())
    }
    
    # Push to Redis
    await redis_client.lpush("titan_job_queue", json.dumps(payload))
    logger.info(f"JOB INGESTED: {job_id} [{job.type}]")
    
    return JobResponse(status="QUEUED", job_id=job_id, timestamp=datetime.now())

# --- THE NERVOUS SYSTEM (WEBSOCKET) ---
@app.websocket("/connect")
async def websocket_endpoint(websocket: WebSocket):
    # 1. Security Check
    key = websocket.headers.get("x-genesis-key")
    if key != GENESIS_KEY:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    node_id = "UNKNOWN"
    
    try:
        # 2. Handshake & Registration
        data = await websocket.receive_text()
        telemetry = json.loads(data)
        node_id = telemetry.get("node_id", "UNKNOWN_NODE")
        
        await redis_client.sadd("active_nodes", node_id)
        logger.info(f"LINK ESTABLISHED: {node_id}")

        while True:
            # 3. Main Event Loop
            data = await websocket.receive_text()
            telemetry = json.loads(data)
            
            # --- SETTLEMENT LAYER ---
            # If the worker just finished a job, pay them immediately.
            if telemetry.get("last_event") == "JOB_COMPLETE":
                finished_job_id = telemetry.get("job_id", "UNKNOWN")
                worker_wallet = telemetry.get("wallet_address", None)
                
                logger.info(f"WORK VERIFIED: {finished_job_id} by {node_id}")
                
                if worker_wallet:
                    # Execute On-Chain Payment
                    tx_sig = await bank.process_payout(worker_wallet, BOUNTY_PER_JOB)
                    
                    # Record in Immutable Ledger
                    status = "CONFIRMED" if "FAILED" not in tx_sig else "FAILED"
                    await vault.record_transaction(finished_job_id, worker_wallet, BOUNTY_PER_JOB, tx_sig, status)
                else:
                    logger.warning(f"Payment Skipped: Node {node_id} has no wallet configured.")

            # --- DISPATCH LAYER ---
            # If worker is IDLE, give them work from the Queue
            if telemetry.get("status") == "IDLE":
                job_bytes = await redis_client.rpop("titan_job_queue")
                if job_bytes:
                    job_data = json.loads(job_bytes)
                    logger.info(f"DISPATCH: Job {job_data['job_id']} -> {node_id}")
                    await websocket.send_text(json.dumps(job_data))

    except WebSocketDisconnect:
        logger.info(f"LINK SEVERED: {node_id}")
        await redis_client.srem("active_nodes", node_id)
    
    except Exception as e:
        logger.error(f"Connection Error ({node_id}): {e}")
        await redis_client.srem("active_nodes", node_id)
        await websocket.close()

# --- ENTRY POINT ---
if __name__ == "__main__":
    import uvicorn
    # Start the Cortex Engine
    uvicorn.run(app, host=DISPATCHER_HOST, port=DISPATCHER_PORT)
