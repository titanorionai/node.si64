import sys
import os
import json
import logging
import sqlite3
import asyncio
import redis.asyncio as redis
from datetime import datetime
from uuid import uuid4
from typing import Optional, Dict, List, Any
from concurrent.futures import ThreadPoolExecutor

# --- ENTERPRISE HTTP STACK ---
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Security, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security.api_key import APIKeyHeader
from starlette.requests import Request
from pydantic import BaseModel, Field

# --- SOLANA FINANCIAL LAYER (SOLDERS v0.30+) ---
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import Transaction
from solders.message import Message
from solders.system_program import TransferParams, transfer
from solana.rpc.async_api import AsyncClient

# --- SYSTEM CONFIGURATION ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from titan_config import *
except ImportError:
    # Safety Net Defaults
    GENESIS_KEY = "TITAN_DEBUG_KEY"
    SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"
    BOUNTY_PER_JOB = 0.001
    WORKER_FEE_PERCENT = 0.90
    DISPATCHER_HOST = "0.0.0.0"
    DISPATCHER_PORT = 8000

# --- POINTS & REPUTATION CONFIG ---
POINTS_JOB_COMPLETE = 100
POINTS_HEARTBEAT = 1
POINTS_REFERRAL = 500

# --- LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | [%(name)s] | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("TITAN_CORTEX")

# --- FILESYSTEM ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "titan_ledger.db")
BANK_WALLET_PATH = os.path.join(BASE_DIR, "titan_bank.json")
STATIC_DIR = os.path.join(BASE_DIR, "www/static")
TEMPLATE_DIR = os.path.join(BASE_DIR, "www/templates")

# --- INIT ---
app = FastAPI(title="Titan Cortex", version="4.1.0")
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATE_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
api_key_header = APIKeyHeader(name="x-genesis-key", auto_error=False)

# --- MODELS ---
class JobRequest(BaseModel):
    type: str = Field(..., description="Compute Type")
    prompt: str = Field(..., description="Payload")
    bounty: float = Field(default=BOUNTY_PER_JOB, description="SOL Offer")

class JobResponse(BaseModel):
    status: str
    job_id: str
    timestamp: datetime

# --- COMPONENT 1: VAULT (LEDGER) ---
class TitanVault:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.executor = ThreadPoolExecutor(max_workers=1)
        self._init_schema()

    def _init_schema(self):
        with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
            conn.execute('PRAGMA journal_mode=WAL;')
            conn.execute('''CREATE TABLE IF NOT EXISTS transactions (
                job_id TEXT PRIMARY KEY, worker_wallet TEXT, amount_sol REAL, 
                tx_signature TEXT, timestamp DATETIME, status TEXT)''')
            conn.commit()

    def _record_sync(self, job_id, wallet, amount, tx_sig, status):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?)",
                             (job_id, wallet, amount, tx_sig, datetime.now(), status))
            return True
        except Exception as e:
            logger.error(f"VAULT WRITE FAILURE: {e}")
            return False

    async def record(self, job_id, wallet, amount, tx_sig, status="CONFIRMED"):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.executor, self._record_sync, job_id, wallet, amount, tx_sig, status)

    def _get_total_paid_sync(self) -> float:
        try:
            with sqlite3.connect(self.db_path) as conn:
                res = conn.execute("SELECT SUM(amount_sol) FROM transactions WHERE status='CONFIRMED'").fetchone()
                return res[0] if res[0] else 0.0
        except: return 0.0

    async def get_total_paid(self) -> float:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.executor, self._get_total_paid_sync)

    def _get_recent_txs_sync(self, limit) -> List[Dict]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                res = conn.execute("SELECT job_id, worker_wallet, amount_sol, timestamp, tx_signature FROM transactions ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
                return [{"job_id": r[0], "worker": f"{r[1][:4]}...", "amount": r[2], "time": str(r[3]), "tx": r[4]} for r in res]
        except: return []

    async def get_recent_txs(self, limit=10) -> List[Dict]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.executor, self._get_recent_txs_sync, limit)

# --- COMPONENT 2: BANK (SOLANA) ---
class TitanBank:
    def __init__(self, keypair_path: str, rpc_url: str):
        self.client = AsyncClient(rpc_url)
        self.keypair = None
        self.enabled = False
        self._load_keypair(keypair_path)

    def _load_keypair(self, path):
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    self.keypair = Keypair.from_bytes(bytes(json.load(f)))
                self.enabled = True
                logger.info(f"TITAN BANK: ONLINE. {self.keypair.pubkey()}")
            except: logger.critical("TITAN BANK: KEYFILE CORRUPT.")
        else: logger.warning("TITAN BANK: NO WALLET. SIMULATION MODE.")

    async def process_payout(self, worker_wallet: str, total_bounty: float) -> str:
        if not self.enabled: return "SIMULATED_TX"
        payout = total_bounty * WORKER_FEE_PERCENT
        if payout < 0.000001: return "SKIPPED_DUST"

        try:
            lamports = int(payout * 1_000_000_000)
            dest = Pubkey.from_string(worker_wallet)
            blockhash = await self.client.get_latest_blockhash()
            ix = transfer(TransferParams(from_pubkey=self.keypair.pubkey(), to_pubkey=dest, lamports=lamports))
            msg = Message.new_with_blockhash([ix], self.keypair.pubkey(), blockhash.value.blockhash)
            txn = Transaction([self.keypair], msg, blockhash.value.blockhash)
            sig = await self.client.send_transaction(txn)
            logger.info(f"PAYOUT: {payout:.6f} SOL -> {worker_wallet[:4]}...")
            return str(sig.value)
        except Exception as e:
            logger.error(f"PAYOUT FAILED: {e}")
            return "FAILED_TX"

    async def close(self): await self.client.close()

# --- COMPONENT 3: LOYALTY (SHADOW LEDGER) ---
class TitanLoyalty:
    """
    Tracks off-chain Reputation Points (Titan Points) for future governance/airdrops.
    """
    def __init__(self, redis):
        self.redis = redis
    
    async def award(self, node_id: str, points: int, reason: str):
        # Key: "reputation:NODE_ID"
        key = f"reputation:{node_id}"
        new_score = await self.redis.incrby(key, points)
        if points > 10: # Only log significant events to avoid spam
            logger.info(f"LOYALTY: {node_id} +{points} PTS ({reason}). Total: {new_score}")
        return new_score

    async def get_score(self, node_id: str) -> int:
        score = await self.redis.get(f"reputation:{node_id}")
        return int(score) if score else 0

# --- INSTANTIATE ---
vault = TitanVault(DB_PATH)
bank = TitanBank(BANK_WALLET_PATH, SOLANA_RPC_URL)
loyalty = TitanLoyalty(redis_client)

# --- API ---
@app.on_event("shutdown")
async def shutdown(): 
    await bank.close()

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request): return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/stats")
async def stats():
    fleet = await redis_client.scard("active_nodes")
    queue = await redis_client.llen("titan_job_queue")
    paid = await vault.get_total_paid()
    txs = await vault.get_recent_txs(10)
    
    return {
        "status": "OPERATIONAL",
        "fleet": fleet, "fleet_size": fleet,
        "queue": queue, "queue_depth": queue,
        "paid": paid, "total_revenue": paid,
        "transactions": txs,
        "timestamp": str(datetime.now())
    }

@app.post("/submit_job")
async def submit(job: JobRequest, key: str = Security(api_key_header)):
    if key != GENESIS_KEY: raise HTTPException(403, "Invalid Key")
    jid = str(uuid4())[:8]
    payload = {"job_id": jid, "type": job.type, "prompt": job.prompt, "bounty": job.bounty}
    await redis_client.lpush("titan_job_queue", json.dumps(payload))
    logger.info(f"JOB INGESTED: {jid}")
    return {"status": "QUEUED", "job_id": jid}

# --- GAMIFIED NERVOUS SYSTEM ---
@app.websocket("/connect")
async def ws_endpoint(ws: WebSocket):
    if ws.headers.get("x-genesis-key") != GENESIS_KEY: await ws.close(); return
    await ws.accept()
    node_id = "UNKNOWN"
    try:
        # 1. Initial Handshake
        data = json.loads(await ws.receive_text())
        node_id = data.get("node_id", "UNKNOWN")
        await redis_client.sadd("active_nodes", node_id)
        
        # Award initial connection points
        current_pts = await loyalty.award(node_id, 10, "LINK_ESTABLISHED")
        logger.info(f"LINKED: {node_id} | REP: {current_pts}")
        
        while True:
            # 2. Event Loop
            data = json.loads(await ws.receive_text())
            
            # A. Job Completion Logic
            if data.get("last_event") == "JOB_COMPLETE":
                jid = data.get("job_id")
                wallet = data.get("wallet_address")
                
                # 1. Pay SOL (Real Money)
                if wallet:
                    sig = await bank.process_payout(wallet, BOUNTY_PER_JOB)
                    status = "CONFIRMED" if "FAILED" not in sig else "FAILED"
                    await vault.record(jid, wallet, BOUNTY_PER_JOB * WORKER_FEE_PERCENT, sig, status)
                
                # 2. Award Points (Shadow Ledger)
                new_score = await loyalty.award(node_id, POINTS_JOB_COMPLETE, "JOB_FINISHED")
                
                # 3. Send feedback to worker
                await ws.send_text(json.dumps({
                    "type": "ACK_JOB",
                    "status": "PAID",
                    "new_reputation": new_score
                }))
            
            # B. Heartbeat Logic
            if data.get("status") == "IDLE":
                # Check for work
                job = await redis_client.rpop("titan_job_queue")
                if job: 
                    await ws.send_text(job)
                else:
                    # Drip small points for uptime (optional, kept small)
                    # await loyalty.award(node_id, POINTS_HEARTBEAT, "UPTIME") 
                    pass

    except WebSocketDisconnect:
        logger.info(f"LOST: {node_id}")
        await redis_client.srem("active_nodes", node_id)
    except Exception as e:
        logger.error(f"CRITICAL WS ERROR: {e}")
        await redis_client.srem("active_nodes", node_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=DISPATCHER_HOST, port=DISPATCHER_PORT)
