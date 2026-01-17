import sys
import os
import json
import logging
import sqlite3
import asyncio
import aiohttp
import redis.asyncio as redis
import re
import html
from datetime import datetime, timedelta
from uuid import uuid4
from typing import Optional, Dict
from collections import defaultdict
from time import time

from fastapi import FastAPI, WebSocket, HTTPException, Security, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security.api_key import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from pydantic import BaseModel, Field, validator

try:
    from solders.keypair import Keypair
    from solders.pubkey import Pubkey
    from solders.transaction import Transaction
    from solders.message import Message
    from solders.system_program import TransferParams, transfer
    from solana.rpc.async_api import AsyncClient
except Exception:
    # Optional dependencies may be missing in the test environment
    Keypair = None
    Pubkey = None
    Transaction = None
    Message = None
    TransferParams = None
    transfer = None
    AsyncClient = None

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from titan_config import *
except ImportError:
    GENESIS_KEY = "TITAN_GENESIS_KEY_V1_SECURE"
    SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"
    BOUNTY_PER_JOB = 0.001
    WORKER_FEE_PERCENT = 0.95
    DISPATCHER_HOST = "0.0.0.0"
    DISPATCHER_PORT = 8000

POINTS_CONNECT = 10
POINTS_JOB = 100
POINTS_UPTIME = 1

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | [%(name)s] | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("TITAN_OVERLORD")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "titan_ledger.db")
BANK_WALLET_PATH = os.path.join(BASE_DIR, "titan_bank.json")
STATIC_DIR = os.path.join(BASE_DIR, "www/static")
TEMPLATE_DIR = os.path.join(BASE_DIR, "www/templates")

app = FastAPI(title="Titan Cortex", version="7.0.0")
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATE_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
api_key_header = APIKeyHeader(name="x-genesis-key", auto_error=False)

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, calls: int = 10, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.clients: Dict[str, list] = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        now = time()
        
        # Clean old requests
        self.clients[client_ip] = [req_time for req_time in self.clients[client_ip] if now - req_time < self.period]
        
        # Check rate limit
        if len(self.clients[client_ip]) >= self.calls:
            raise HTTPException(status_code=429, detail="Too Many Requests")
        
        self.clients[client_ip].append(now)
        return await call_next(request)

class JobRequest(BaseModel):
    type: str = Field(..., description="Inference Type (LLAMA, SDXL)")
    prompt: str = Field(..., description="Input Payload")
    bounty: float = Field(default=BOUNTY_PER_JOB)
    
    @validator('type')
    def validate_type(cls, v):
        if not re.match(r'^[A-Z0-9_]+$', v) or len(v) > 50:
            raise ValueError('Invalid type format')
        return v
    
    @validator('prompt')
    def validate_prompt(cls, v):
        if len(v) > 10000:
            raise ValueError('Prompt too long')
        # Sanitize HTML/JS
        v = html.escape(v)
        return v
    
    @validator('bounty')
    def validate_bounty(cls, v):
        if v < 0 or v > 10:
            raise ValueError('Invalid bounty amount')
        return v

class RentalRequest(BaseModel):
    wallet: str
    tier: str
    duration_hours: int
    tx_signature: str

from concurrent.futures import ThreadPoolExecutor

# Add rate limiting middleware (increased to 50 req/60s for better legitimate traffic handling)
app.add_middleware(RateLimitMiddleware, calls=50, period=60)

class TitanVault:
    def __init__(self, db_path):
        self.db_path = db_path
        self.executor = ThreadPoolExecutor(max_workers=1)
        self._init_tables()

    def _init_tables(self):
        with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
            conn.execute('PRAGMA journal_mode=WAL;')
            conn.execute('''CREATE TABLE IF NOT EXISTS transactions (
                job_id TEXT PRIMARY KEY, worker_wallet TEXT, amount_sol REAL,
                tx_signature TEXT, timestamp DATETIME, status TEXT)''')
            conn.execute('''CREATE TABLE IF NOT EXISTS rentals (
                contract_id TEXT PRIMARY KEY, renter_wallet TEXT, hardware_tier TEXT,
                duration_hours INTEGER, cost_sol REAL, start_time DATETIME,
                status TEXT, tx_proof TEXT)''')
            conn.commit()

    def record_job(self, job_id, wallet, amount, tx_sig, status="CONFIRMED"):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO transactions (job_id, worker_wallet, amount_sol, tx_signature, timestamp, status) VALUES (?, ?, ?, ?, ?, ?)",
                    (job_id, wallet, amount, tx_sig, datetime.now(), status),
                )
                logger.info(f"LEDGER: Job {job_id} settled/updated for {amount:.5f} SOL ({status})")
        except Exception as e:
            logger.error(f"VAULT WRITE ERROR: {e}")

    def create_rental(self, wallet, tier, hours, tx_proof):
        contract_id = f"CTR-{str(uuid4())[:8].upper()}"
        rates = {"M2": 0.002, "ORIN": 0.005, "M3_ULTRA": 0.015}
        rate = rates.get(tier, 0.002)
        total_cost = rate * hours
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("INSERT INTO rentals VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                             (contract_id, wallet, tier, hours, total_cost, datetime.now(), "ACTIVE", tx_proof))
            logger.info(f"CONTRACT: {contract_id} deployed by {wallet[:6]}...")
            return {"contract_id": contract_id, "status": "ACTIVE", "cost": total_cost}
        except Exception as e:
            logger.error(f"CONTRACT FAILURE: {e}")
            return None

    def get_financials(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                job_rev = conn.execute("SELECT SUM(amount_sol) FROM transactions WHERE status='CONFIRMED'").fetchone()[0] or 0.0
                rent_rev = conn.execute("SELECT SUM(cost_sol) FROM rentals WHERE status='ACTIVE'").fetchone()[0] or 0.0
                return job_rev + rent_rev
        except:
            return 0.0

    def get_recent_activity(self, limit=10):
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = '''
                    SELECT job_id as id, worker_wallet as entity, amount_sol as val, timestamp, 'JOB' as type, tx_signature as tx 
                    FROM transactions 
                    UNION ALL
                    SELECT contract_id as id, renter_wallet as entity, cost_sol as val, start_time as timestamp, 'RENTAL' as type, tx_proof as tx
                    FROM rentals 
                    ORDER BY timestamp DESC LIMIT ?
                '''
                res = conn.execute(query, (limit,)).fetchall()
                return [{"job_id": r[0], "worker": f"{r[1][:4]}...{r[1][-4:]}", "amount": r[2], "time": str(r[3]), "type": r[4], "tx": r[5]} for r in res]
        except Exception as e:
            logger.error(f"VAULT READ ERROR: {e}")
            return []

class TitanBank:
    def __init__(self, keypair_path, rpc_url):
        self.client = None
        self._session = None
        if AsyncClient:
            try:
                if globals().get('SOLANA_RPC_TOKEN'):
                    self._session = aiohttp.ClientSession(headers={"x-token": SOLANA_RPC_TOKEN})
                    self.client = AsyncClient(rpc_url, session=self._session)
                else:
                    self.client = AsyncClient(rpc_url)
            except Exception:
                self.client = AsyncClient(rpc_url)
        self.keypair = None
        self.enabled = False
        if os.path.exists(keypair_path):
            try:
                with open(keypair_path, "r") as f:
                    self.keypair = Keypair.from_bytes(bytes(json.load(f))) if Keypair else None
                self.enabled = bool(self.keypair)
                logger.info(f"TITAN BANK: ONLINE. Treasury: {getattr(self.keypair, 'pubkey', lambda: 'UNKNOWN')()}")
            except Exception:
                logger.critical("TITAN BANK: KEYFILE CORRUPT.")
        else:
            logger.warning("TITAN BANK: NO WALLET FOUND. RUNNING IN SIMULATION MODE.")

    async def process_payout(self, worker_wallet, total_bounty):
        if not self.enabled:
            return "SIMULATED_TX_SIG_0000"
        payout = total_bounty * WORKER_FEE_PERCENT
        if payout < 0.000001:
            return "SKIPPED_DUST"
        lamports = int(payout * 1_000_000_000)
        dest = Pubkey.from_string(worker_wallet) if Pubkey else None
        attempts = 3
        delay = 1
        last_exc = None
        for attempt in range(1, attempts + 1):
            try:
                blockhash = await self.client.get_latest_blockhash()
                ix = transfer(TransferParams(from_pubkey=self.keypair.pubkey(), to_pubkey=dest, lamports=lamports))
                msg = Message.new_with_blockhash([ix], self.keypair.pubkey(), blockhash.value.blockhash)
                txn = Transaction([self.keypair], msg, blockhash.value.blockhash)
                sig = await self.client.send_transaction(txn)
                logger.info(f"PAYOUT: {payout:.6f} SOL -> {worker_wallet[:4]}...")
                return str(sig.value)
            except Exception as e:
                last_exc = e
                err_s = str(e)
                logger.warning(f"PAYOUT ATTEMPT {attempt} FAILED: {e}")
                if 'InsufficientFundsForRent' in err_s or 'InsufficientFundsForRent' in repr(e):
                    logger.error(f"PAYOUT FAILED (insufficient rent): {e}")
                    return "FAILED_RENT"
                if attempt < attempts:
                    await asyncio.sleep(delay)
                    delay *= 2
        logger.error(f"PAYOUT FAILED: {last_exc}")
        return "FAILED_TX"

    async def close(self):
        if self.client:
            await self.client.close()
        if getattr(self, '_session', None):
            await self._session.close()

class TitanLoyalty:
    def __init__(self, r):
        self.r = r

    async def award(self, node_id, points, reason):
        key = f"reputation:{node_id}"
        score = await self.r.incrby(key, points)
        if points > 5:
            logger.info(f"LOYALTY: {node_id} +{points} ({reason}). Total: {score}")
        return score

vault = TitanVault(DB_PATH)
bank = TitanBank(BANK_WALLET_PATH, SOLANA_RPC_URL)
loyalty = TitanLoyalty(redis_client)

app.on_event("shutdown")(lambda: asyncio.create_task(bank.close()))

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/stats")
async def stats(key: str = Security(api_key_header), id: Optional[str] = None):
    # Require authentication
    if key != GENESIS_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing API key")
    
    # Validate query parameters to prevent injection attacks
    if id is not None:
        if not re.match(r'^[a-zA-Z0-9_-]+$', id) or len(id) > 100:
            raise HTTPException(status_code=400, detail="Invalid id parameter format")
    
    fleet = await redis_client.scard("active_nodes")
    queue = await redis_client.llen("titan_job_queue")
    revenue = vault.get_financials()
    ledger = vault.get_recent_activity(10)
    return {"status": "OPERATIONAL", "fleet_size": fleet, "queue_depth": queue, "total_revenue": revenue, "transactions": ledger, "timestamp": str(datetime.now())}

@app.post("/api/rent")
async def rent_hardware(req: RentalRequest):
    contract = vault.create_rental(req.wallet, req.tier, req.duration_hours, req.tx_signature)
    if contract:
        return contract
    raise HTTPException(status_code=500, detail="Contract Generation Failed")

@app.post("/submit_job")
async def submit(job: JobRequest, key: str = Security(api_key_header)):
    if key != GENESIS_KEY:
        raise HTTPException(403, "Invalid Key")
    
    # Input validation already applied via JobRequest validators
    # Additional sanitization
    safe_type = html.escape(job.type)[:50]
    safe_prompt = html.escape(job.prompt)[:10000]
    safe_bounty = max(0, min(10, job.bounty))
    
    jid = str(uuid4())[:8]
    payload = {"job_id": jid, "type": safe_type, "prompt": safe_prompt, "bounty": safe_bounty}
    await redis_client.lpush("titan_job_queue", json.dumps(payload))
    logger.info(f"JOB INGESTED: {jid}")
    return {"status": "QUEUED", "job_id": jid}

@app.websocket("/connect")
async def ws_endpoint(ws: WebSocket):
    if ws.headers.get("x-genesis-key") != GENESIS_KEY:
        await ws.close()
        return
    await ws.accept()
    node_id = "UNKNOWN"
    try:
        data_init = json.loads(await ws.receive_text())
        node_id = data_init.get("node_id", "UNKNOWN")
        await redis_client.sadd("active_nodes", node_id)
        await loyalty.award(node_id, POINTS_CONNECT, "LINK_ESTABLISHED")
        while True:
            data = json.loads(await ws.receive_text())
            if data.get("last_event") == "JOB_COMPLETE":
                jid = data.get("job_id")
                wallet = data.get("wallet_address")
                if wallet:
                    payout_payload = {"job_id": jid, "wallet": wallet, "total_bounty": BOUNTY_PER_JOB, "node_id": node_id}
                    await redis_client.lpush("titan_payout_queue", json.dumps(payout_payload))
                    vault.record_job(jid, wallet, BOUNTY_PER_JOB * WORKER_FEE_PERCENT, "", "PENDING")
                    await loyalty.award(node_id, POINTS_JOB, "JOB_DONE")
                    await ws.send_text(json.dumps({"type": "ACK_JOB", "status": "QUEUED_FOR_PAYOUT"}))
            if data.get("status") == "IDLE":
                job = await redis_client.rpop("titan_job_queue")
                if job:
                    await ws.send_text(job)
    except Exception as e:
        logger.error(f"NODE LOST {node_id}: {e}")
        await redis_client.srem("active_nodes", node_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=DISPATCHER_HOST, port=DISPATCHER_PORT)
import sys
import os
import json
import logging
import sqlite3
import asyncio
import redis.asyncio as redis
from datetime import datetime, timedelta
from uuid import uuid4
from typing import Optional, List, Dict, Union

# --- ENTERPRISE HTTP STACK ---
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Security
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security.api_key import APIKeyHeader
from starlette.requests import Request
from pydantic import BaseModel, Field

# --- SOLANA FINANCIAL LAYER ---
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import Transaction
from solders.message import Message
from solders.system_program import TransferParams, transfer 
from solana.rpc.async_api import AsyncClient

# --- CONFIGURATION & ENV ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try: 
    from titan_config import *
except ImportError:
    # Fallback / Default Configuration
    GENESIS_KEY = "TITAN_GENESIS_KEY_V1_SECURE"
    SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"
    BOUNTY_PER_JOB = 0.001
    WORKER_FEE_PERCENT = 0.95
    DISPATCHER_HOST = "0.0.0.0"
    DISPATCHER_PORT = 8000

# --- POINTS SYSTEM (GAMIFICATION) ---
POINTS_CONNECT = 10
POINTS_JOB = 100
POINTS_UPTIME = 1

# --- MILITARY-GRADE LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | [%(name)s] | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("TITAN_OVERLORD")

# --- FILESYSTEM ARCHITECTURE ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "titan_ledger.db")
BANK_WALLET_PATH = os.path.join(BASE_DIR, "titan_bank.json")
STATIC_DIR = os.path.join(BASE_DIR, "www/static")
TEMPLATE_DIR = os.path.join(BASE_DIR, "www/templates")

# --- APP INITIALIZATION ---
app = FastAPI(title="Titan Cortex", version="7.0.0")
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATE_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

# --- DATA STORES ---
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
api_key_header = APIKeyHeader(name="x-genesis-key", auto_error=False)

# --- DATA MODELS ---
class JobRequest(BaseModel):
    type: str = Field(..., description="Inference Type (LLAMA, SDXL)")
    prompt: str = Field(..., description="Input Payload")
    bounty: float = Field(default=BOUNTY_PER_JOB)

class RentalRequest(BaseModel):
    wallet: str
    tier: str  # M2, ORIN, M3_ULTRA
    duration_hours: int
    tx_signature: str # Proof of payment

# --- COMPONENT 1: TITAN VAULT (UNIFIED LEDGER) ---
class TitanVault:
    """
    Manages the immutable record of all economic activity:
    1. Job Micropayments
    2. Rental Smart Contracts
    """
    def __init__(self, db_path):
        self.db_path = db_path
        self.executor = ThreadPoolExecutor(max_workers=1) # Serialized writes
        self._init_tables()

    def _init_tables(self):
        with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
            conn.execute('PRAGMA journal_mode=WAL;')
            
            # 1. Inference Jobs
            conn.execute('''CREATE TABLE IF NOT EXISTS transactions (
                job_id TEXT PRIMARY KEY, worker_wallet TEXT, amount_sol REAL, 
                tx_signature TEXT, timestamp DATETIME, status TEXT)''')
            
            # 2. Hardware Rentals
            conn.execute('''CREATE TABLE IF NOT EXISTS rentals (
                contract_id TEXT PRIMARY KEY, renter_wallet TEXT, hardware_tier TEXT,
                duration_hours INTEGER, cost_sol REAL, start_time DATETIME, 
                status TEXT, tx_proof TEXT)''')
            conn.commit()

    # --- WRITES ---
    def record_job(self, job_id, wallet, amount, tx_sig, status="CONFIRMED"):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?)",
                             (job_id, wallet, amount, tx_sig, datetime.now(), status))
                logger.info(f"LEDGER: Job {job_id} settled for {amount:.5f} SOL")
        except sqlite3.IntegrityError:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("UPDATE transactions SET worker_wallet=?, amount_sol=?, tx_signature=?, timestamp=?, status=? WHERE job_id=?",
                                 (wallet, amount, tx_sig, datetime.now(), status, job_id))
                    logger.info(f"LEDGER: Job {job_id} updated to {status}")
            except Exception as e:
                logger.error(f"VAULT WRITE ERROR (update): {e}")
        except Exception as e:
            logger.error(f"VAULT WRITE ERROR: {e}")

    def create_rental(self, wallet, tier, hours, tx_proof):
        contract_id = f"CTR-{str(uuid4())[:8].upper()}"
        # Hardware Pricing Oracle
        rates = {"M2": 0.002, "ORIN": 0.005, "M3_ULTRA": 0.015}
        rate = rates.get(tier, 0.002)
        total_cost = rate * hours
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("INSERT INTO rentals VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                             (contract_id, wallet, tier, hours, total_cost, datetime.now(), "ACTIVE", tx_proof))
            logger.info(f"CONTRACT: {contract_id} deployed by {wallet[:6]}...")
            return {"contract_id": contract_id, "status": "ACTIVE", "cost": total_cost}
        except Exception as e:
            logger.error(f"CONTRACT FAILURE: {e}")
            return None

    # --- READS (ANALYTICS) ---
    def get_financials(self):
        """Calculates Total Protocol Revenue (TVL)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                job_rev = conn.execute("SELECT SUM(amount_sol) FROM transactions WHERE status='CONFIRMED'").fetchone()[0] or 0.0
                rent_rev = conn.execute("SELECT SUM(cost_sol) FROM rentals WHERE status='ACTIVE'").fetchone()[0] or 0.0
                return job_rev + rent_rev
        except: return 0.0
        
    def get_recent_activity(self, limit=10):
        """Unified Stream of Jobs and Contracts for the Terminal"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = '''
                    SELECT job_id as id, worker_wallet as entity, amount_sol as val, timestamp, 'JOB' as type, tx_signature as tx 
                    FROM transactions 
                    UNION ALL
                    SELECT contract_id as id, renter_wallet as entity, cost_sol as val, start_time as timestamp, 'RENTAL' as type, tx_proof as tx
                    FROM rentals 
                    ORDER BY timestamp DESC LIMIT ?
                '''
                res = conn.execute(query, (limit,)).fetchall()
                return [{
                    "job_id": r[0], 
                    "worker": f"{r[1][:4]}...{r[1][-4:]}", 
                    "amount": r[2], 
                    "time": str(r[3]), 
                    "type": r[4], 
                    "tx": r[5]
                } for r in res]
        except Exception as e: 
            logger.error(f"VAULT READ ERROR: {e}")
            return []

# --- COMPONENT 2: TITAN BANK (SOLANA SETTLEMENT) ---
class TitanBank:
    def __init__(self, keypair_path, rpc_url):
        self.client = None
        self._session = None
        if AsyncClient:
            try:
                if globals().get('SOLANA_RPC_TOKEN'):
                    self._session = aiohttp.ClientSession(headers={"x-token": SOLANA_RPC_TOKEN})
                    self.client = AsyncClient(rpc_url, session=self._session)
                else:
                    self.client = AsyncClient(rpc_url)
            except Exception:
                self.client = AsyncClient(rpc_url)
        self.keypair = None
        self.enabled = False
        if os.path.exists(keypair_path):
            try:
                with open(keypair_path, "r") as f:
                    self.keypair = Keypair.from_bytes(bytes(json.load(f)))
                self.enabled = True
                logger.info(f"TITAN BANK: ONLINE. Treasury: {self.keypair.pubkey()}")
            except: logger.critical("TITAN BANK: KEYFILE CORRUPT.")
        else:
            logger.warning("TITAN BANK: NO WALLET FOUND. RUNNING IN SIMULATION MODE.")

    async def process_payout(self, worker_wallet, total_bounty):
        if not self.enabled:
            return "SIMULATED_TX_SIG_0000"

        # Economic Safety
        payout = total_bounty * WORKER_FEE_PERCENT
        if payout < 0.000001:
            return "SKIPPED_DUST"

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
            err_s = str(e)
            if 'InsufficientFundsForRent' in err_s or 'InsufficientFundsForRent' in repr(e):
                logger.error(f"PAYOUT FAILED (insufficient rent): {e}")
                return "FAILED_RENT"
            logger.error(f"PAYOUT FAILED: {e}")
            return "FAILED_TX"

    async def close(self):
        if self.client:
            await self.client.close()
        if getattr(self, '_session', None):
            await self._session.close()

# --- COMPONENT 3: TITAN LOYALTY (REPUTATION ENGINE) ---
class TitanLoyalty:
    """Tracks off-chain Points for future governance/airdrops."""
    def __init__(self, r): self.r = r
    
    async def award(self, node_id, points, reason):
        key = f"reputation:{node_id}"
        score = await self.r.incrby(key, points)
        if points > 5: logger.info(f"LOYALTY: {node_id} +{points} ({reason}). Total: {score}")
        return score

# --- INSTANTIATE SYSTEMS ---
from concurrent.futures import ThreadPoolExecutor
vault = TitanVault(DB_PATH)
bank = TitanBank(BANK_WALLET_PATH, SOLANA_RPC_URL)
loyalty = TitanLoyalty(redis_client)

# --- API ENDPOINTS ---

@app.on_event("shutdown")
async def shutdown(): await bank.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=DISPATCHER_HOST, port=DISPATCHER_PORT)
BANK_WALLET_PATH = os.path.join(BASE_DIR, "titan_bank.json")
STATIC_DIR = os.path.join(BASE_DIR, "www/static")
TEMPLATE_DIR = os.path.join(BASE_DIR, "www/templates")

# --- APP INITIALIZATION ---
app = FastAPI(title="Titan Cortex", version="7.0.0")
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATE_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

# --- DATA STORES ---
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
api_key_header = APIKeyHeader(name="x-genesis-key", auto_error=False)

# --- DATA MODELS ---
class JobRequest(BaseModel):
    type: str = Field(..., description="Inference Type (LLAMA, SDXL)")
    prompt: str = Field(..., description="Input Payload")
    bounty: float = Field(default=BOUNTY_PER_JOB)

class RentalRequest(BaseModel):
    wallet: str
    tier: str  # M2, ORIN, M3_ULTRA
    duration_hours: int
    tx_signature: str # Proof of payment

# --- COMPONENT 1: TITAN VAULT (UNIFIED LEDGER) ---
class TitanVault:
    """
    Manages the immutable record of all economic activity:
    1. Job Micropayments
    2. Rental Smart Contracts
    """
    def __init__(self, db_path):
        self.db_path = db_path
        self.executor = ThreadPoolExecutor(max_workers=1) # Serialized writes
        self._init_tables()

    def _init_tables(self):
        with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
            conn.execute('PRAGMA journal_mode=WAL;')
            
            # 1. Inference Jobs
            conn.execute('''CREATE TABLE IF NOT EXISTS transactions (
                job_id TEXT PRIMARY KEY, worker_wallet TEXT, amount_sol REAL, 
                tx_signature TEXT, timestamp DATETIME, status TEXT)''')
            
            # 2. Hardware Rentals
            conn.execute('''CREATE TABLE IF NOT EXISTS rentals (
                contract_id TEXT PRIMARY KEY, renter_wallet TEXT, hardware_tier TEXT,
                duration_hours INTEGER, cost_sol REAL, start_time DATETIME, 
                status TEXT, tx_proof TEXT)''')
            conn.commit()

    # --- WRITES ---
    def record_job(self, job_id, wallet, amount, tx_sig, status="CONFIRMED"):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?)",
                             (job_id, wallet, amount, tx_sig, datetime.now(), status))
                logger.info(f"LEDGER: Job {job_id} settled for {amount:.5f} SOL")
        except sqlite3.IntegrityError:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("UPDATE transactions SET worker_wallet=?, amount_sol=?, tx_signature=?, timestamp=?, status=? WHERE job_id=?",
                                 (wallet, amount, tx_sig, datetime.now(), status, job_id))
                    logger.info(f"LEDGER: Job {job_id} updated to {status}")
            except Exception as e:
                logger.error(f"VAULT WRITE ERROR (update): {e}")
        except Exception as e:
            logger.error(f"VAULT WRITE ERROR: {e}")

    def create_rental(self, wallet, tier, hours, tx_proof):
        contract_id = f"CTR-{str(uuid4())[:8].upper()}"
        # Hardware Pricing Oracle
        rates = {"M2": 0.002, "ORIN": 0.005, "M3_ULTRA": 0.015}
        rate = rates.get(tier, 0.002)
        total_cost = rate * hours
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("INSERT INTO rentals VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                             (contract_id, wallet, tier, hours, total_cost, datetime.now(), "ACTIVE", tx_proof))
            logger.info(f"CONTRACT: {contract_id} deployed by {wallet[:6]}...")
            return {"contract_id": contract_id, "status": "ACTIVE", "cost": total_cost}
        except Exception as e:
            logger.error(f"CONTRACT FAILURE: {e}")
            return None

    # --- READS (ANALYTICS) ---
    def get_financials(self):
        """Calculates Total Protocol Revenue (TVL)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                job_rev = conn.execute("SELECT SUM(amount_sol) FROM transactions WHERE status='CONFIRMED'").fetchone()[0] or 0.0
                rent_rev = conn.execute("SELECT SUM(cost_sol) FROM rentals WHERE status='ACTIVE'").fetchone()[0] or 0.0
                return job_rev + rent_rev
        except: return 0.0
        
    def get_recent_activity(self, limit=10):
        """Unified Stream of Jobs and Contracts for the Terminal"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = '''
                    SELECT job_id as id, worker_wallet as entity, amount_sol as val, timestamp, 'JOB' as type, tx_signature as tx 
                    FROM transactions 
                    UNION ALL
                    SELECT contract_id as id, renter_wallet as entity, cost_sol as val, start_time as timestamp, 'RENTAL' as type, tx_proof as tx
                    FROM rentals 
                    ORDER BY timestamp DESC LIMIT ?
                '''
                res = conn.execute(query, (limit,)).fetchall()
                return [{
                    "job_id": r[0], 
                    "worker": f"{r[1][:4]}...{r[1][-4:]}", 
                    "amount": r[2], 
                    "time": str(r[3]), 
                    "type": r[4], 
                    "tx": r[5]
                } for r in res]
        except Exception as e: 
            logger.error(f"VAULT READ ERROR: {e}")
            return []

# --- COMPONENT 2: TITAN BANK (SOLANA SETTLEMENT) ---
class TitanBank:
    def __init__(self, keypair_path, rpc_url):
        self.client = None
        self._session = None
        if AsyncClient:
            try:
                if globals().get('SOLANA_RPC_TOKEN'):
                    self._session = aiohttp.ClientSession(headers={"x-token": SOLANA_RPC_TOKEN})
                    self.client = AsyncClient(rpc_url, session=self._session)
                else:
                    self.client = AsyncClient(rpc_url)
            except Exception:
                self.client = AsyncClient(rpc_url)
        self.keypair = None
        self.enabled = False
        if os.path.exists(keypair_path):
            try:
                with open(keypair_path, "r") as f:
                    self.keypair = Keypair.from_bytes(bytes(json.load(f)))
                self.enabled = True
                logger.info(f"TITAN BANK: ONLINE. Treasury: {self.keypair.pubkey()}")
            except: logger.critical("TITAN BANK: KEYFILE CORRUPT.")
        else:
            logger.warning("TITAN BANK: NO WALLET FOUND. RUNNING IN SIMULATION MODE.")

    async def process_payout(self, worker_wallet, total_bounty):
        if not self.enabled:
            return "SIMULATED_TX_SIG_0000"

        # Economic Safety
        payout = total_bounty * WORKER_FEE_PERCENT
        if payout < 0.000001:
            return "SKIPPED_DUST"

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
            err_s = str(e)
            if 'InsufficientFundsForRent' in err_s or 'InsufficientFundsForRent' in repr(e):
                logger.error(f"PAYOUT FAILED (insufficient rent): {e}")
                return "FAILED_RENT"
            logger.error(f"PAYOUT FAILED: {e}")
            return "FAILED_TX"

    async def close(self): await self.client.close()

# --- COMPONENT 3: TITAN LOYALTY (REPUTATION ENGINE) ---
class TitanLoyalty:
    """Tracks off-chain Points for future governance/airdrops."""
    def __init__(self, r): self.r = r
    
    async def award(self, node_id, points, reason):
        key = f"reputation:{node_id}"
        score = await self.r.incrby(key, points)
        if points > 5: logger.info(f"LOYALTY: {node_id} +{points} ({reason}). Total: {score}")
        return score

# --- INSTANTIATE SYSTEMS ---
from concurrent.futures import ThreadPoolExecutor
vault = TitanVault(DB_PATH)
bank = TitanBank(BANK_WALLET_PATH, SOLANA_RPC_URL)
loyalty = TitanLoyalty(redis_client)

# --- API ENDPOINTS ---

@app.on_event("shutdown")
async def shutdown(): await bank.close()

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request): return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/stats")
async def stats():
    """Feeds the V7.1 Dashboard"""
    fleet = await redis_client.scard("active_nodes")
    queue = await redis_client.llen("titan_job_queue")
    revenue = vault.get_financials() # Aggregated Revenue
    ledger = vault.get_recent_activity(10) # Unified Stream
    
    return {
        "status": "OPERATIONAL",
        "fleet_size": fleet,
        "queue_depth": queue,
        "total_revenue": revenue,
        "transactions": ledger,
        "timestamp": str(datetime.now())
    }

@app.post("/api/rent")
async def rent_hardware(req: RentalRequest):
    """Handles Hardware Rental Contracts"""
    # In prod, verify on-chain signature here before provisioning
    contract = vault.create_rental(req.wallet, req.tier, req.duration_hours, req.tx_signature)
    if contract:
        return contract
    raise HTTPException(status_code=500, detail="Contract Generation Failed")

@app.post("/submit_job")
async def submit(job: JobRequest, key: str = Security(api_key_header)):
    """Ingests AI Inference Tasks"""
    if key != GENESIS_KEY: raise HTTPException(403, "Invalid Key")
    jid = str(uuid4())[:8]
    payload = {"job_id": jid, "type": job.type, "prompt": job.prompt, "bounty": job.bounty}
    await redis_client.lpush("titan_job_queue", json.dumps(payload))
    logger.info(f"JOB INGESTED: {jid}")
    return {"status": "QUEUED", "job_id": jid}

# --- THE NERVOUS SYSTEM (WEBSOCKET) ---
@app.websocket("/connect")
async def ws_endpoint(ws: WebSocket):
    if ws.headers.get("x-genesis-key") != GENESIS_KEY: await ws.close(); return
    await ws.accept()
    node_id = "UNKNOWN"
    try:
        # 1. Handshake
        data_init = json.loads(await ws.receive_text())
        node_id = data_init.get("node_id", "UNKNOWN")
        await redis_client.sadd("active_nodes", node_id)
        
        # Award 'Welcome' Points
        score = await loyalty.award(node_id, POINTS_CONNECT, "LINK_ESTABLISHED")
        
        while True:
            # 2. Main Loop
            data = json.loads(await ws.receive_text())
            
            # A. Job Completion
            if data.get("last_event") == "JOB_COMPLETE":
                jid = data.get("job_id")
                wallet = data.get("wallet_address")
                if wallet:
                    # Enqueue payout for rate-limited settlement
                    payout_payload = {"job_id": jid, "wallet": wallet, "total_bounty": BOUNTY_PER_JOB, "node_id": node_id}
                    await redis_client.lpush("titan_payout_queue", json.dumps(payout_payload))
                    vault.record_job(jid, wallet, BOUNTY_PER_JOB * WORKER_FEE_PERCENT, "", "PENDING")

                    # Award Points immediately
                    new_score = await loyalty.award(node_id, POINTS_JOB, "JOB_DONE")

                    # Feedback
                    await ws.send_text(json.dumps({
                        "type": "ACK_JOB", "status": "QUEUED_FOR_PAYOUT", "reputation": new_score
                    }))

            # B. Job Dispatch
            if data.get("status") == "IDLE":
                job = await redis_client.rpop("titan_job_queue")
                if job: await ws.send_text(job)
                
    except Exception as e:
        logger.error(f"NODE LOST {node_id}: {e}")
        await redis_client.srem("active_nodes", node_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=DISPATCHER_HOST, port=DISPATCHER_PORT)
