import sys
import os
import json
import logging
import sqlite3
import asyncio
import hashlib
import redis.asyncio as redis
import html
import re
from datetime import datetime
from uuid import uuid4
from typing import Dict, Optional, List, Union
from collections import defaultdict
from time import time
from concurrent.futures import ThreadPoolExecutor

# --- ENTERPRISE HTTP STACK ---
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Security, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security.api_key import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, Field, validator

# --- IMPORT PATH CONFIGURATION ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- SWARM INTELLIGENCE IMPORT ---
try:
    from brain.swarm_commander import SwarmCommander, HardwareClass, JobDirective, MissionTier
except ImportError:
    print("CRITICAL: SWARM MODULE MISSING. System Halted.")
    sys.exit(1)

# --- SOLANA LAYER (DEFI MECHANICS) ---
try:
    from solders.keypair import Keypair
    from solders.pubkey import Pubkey
    from solders.signature import Signature
    from solders.system_program import TransferParams, transfer
    from solders.message import Message
    from solders.transaction import Transaction
    from solders.instruction import Instruction
    from solana.rpc.async_api import AsyncClient
except ImportError:
    Keypair = None; AsyncClient = None
    print("WARNING: Solana libraries missing. Banking will run in SIMULATION mode.")

# --- CONFIGURATION ---
try:
    from titan_config import *
except ImportError:
    # Fallback Defaults
    SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"
    BOUNTY_PER_JOB = 0.0001
    WORKER_FEE_PERCENT = 0.90
    PROTOCOL_TAX = 0.10
    GENESIS_KEY = "TITAN_GENESIS_KEY_V1_SECURE"
    DISPATCHER_HOST = "0.0.0.0"
    DISPATCHER_PORT = 8000

# --- GAMIFICATION ---
POINTS_CONNECT = 10
POINTS_JOB = 100

# --- ECONOMIC FIREWALL / SENTINEL CONFIG ---
# Minimum external worker stake required to receive payouts (in SOL).
STAKE_MIN_SOL = float(os.getenv("TITAN_MIN_STAKE_SOL", "0.1"))

# IPs considered "sovereign" / internal and exempt from stake + TTS bans.
INTERNAL_IP_WHITELIST = {
    ip.strip()
    for ip in os.getenv(
        "TITAN_INTERNAL_IPS",
        "127.0.0.1,localhost,::1",
    ).split(",")
}

# --- LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | [%(name)s] | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(BASE_DIR, "brain/logs/overlord.log"))
    ]
)
logger = logging.getLogger("TITAN_PROTOCOL")

# --- FILESYSTEM ---
DB_PATH = os.path.join(BASE_DIR, "titan_ledger.db")
BANK_WALLET_PATH = os.path.join(BASE_DIR, "titan_bank.json")
STATIC_DIR = os.path.join(BASE_DIR, "www/static")
TEMPLATE_DIR = os.path.join(BASE_DIR, "www/templates")

app = FastAPI(title="Titan Protocol", version="14.0.0")
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATE_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

# --- SYSTEM HEALTH CHECK ---
def preflight_system_check():
    """Ensures all vital organs are functioning before boot."""
    print("\n[TITAN OVERLORD] INITIATING PRE-FLIGHT SEQUENCE...")
    
    # 1. REDIS CHECK
    try:
        import redis
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = int(os.getenv('REDIS_PORT', '6379'))
        redis_password = os.getenv('REDIS_PASSWORD')
        r_check = redis.Redis(host=redis_host, port=redis_port, password=redis_password, socket_connect_timeout=1)
        if not r_check.ping(): raise ConnectionError
        print("   [✓] NEURAL LINK (REDIS): ONLINE")
    except:
        print("   [!] NEURAL LINK (REDIS): OFFLINE - ATTEMPTING RESTART...")
        os.system("sudo systemctl start redis-server")

    # 2. BANK CHECK
    if os.path.exists(BANK_WALLET_PATH):
        print("   [✓] TREASURY VAULT: DETECTED")
    else:
        print("   [!] TREASURY VAULT: MISSING (Simulation Mode Active)")
    
    print("[TITAN OVERLORD] SYSTEM GREEN. ENGAGING MAIN LOOP.\n")

preflight_system_check()

# Redis connection - use environment variables if running in Docker
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD, db=0, decode_responses=True)
api_key_header = APIKeyHeader(name="x-genesis-key", auto_error=False)

# --- SECURITY: RATE LIMITING MIDDLEWARE ---
class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, calls: int = 150, period: int = 10):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.clients: Dict[str, list] = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next):
        # Allow WebSocket handshakes to bypass limiter
        if request.url.path == "/connect": return await call_next(request)
        
        client_ip = request.client.host
        now = time()
        self.clients[client_ip] = [t for t in self.clients[client_ip] if now - t < self.period]
        
        if len(self.clients[client_ip]) >= self.calls:
            return JSONResponse(status_code=429, content={"detail": "Rate Limit Exceeded"})
            
        self.clients[client_ip].append(now)
        return await call_next(request)

# Global rate limiting: tuned for stronger DoS protection while
# allowing normal interactive usage from dashboards and tools.
# At 10-second windows, this allows up to ~4.5 RPS per client IP.
app.add_middleware(RateLimitMiddleware, calls=45, period=10)

@app.get("/install")
async def installer_script():
    """Serve the SI64 node installer shell script at /install.

    This allows curl/bash style installs: curl -sSL https://si64.net/install | bash
    """
    script_path = os.path.join(BASE_DIR, "scripts", "si64_node_installer.sh")
    if not os.path.exists(script_path):
        raise HTTPException(status_code=404, detail="Installer not available")
    return FileResponse(script_path, media_type="text/x-shellscript", filename="si64_node_installer.sh")

# --- DATA MODELS ---
class JobRequest(BaseModel):
    type: str = Field(..., description="Job Classification")
    prompt: str = Field(..., description="Intelligence Payload")
    # Default to standard GPU pool; legacy tests used ORIN-specific queue
    hardware: str = Field(default="UNIT_NVIDIA_CUDA")
    # Optional per-job bounty override (SOL). If omitted, ValuationEngine is used.
    bounty: Optional[float] = Field(default=None, description="Per-job bounty in SOL")

    @validator('prompt')
    def sanitize(cls, v): return html.escape(v)

class RentalRequest(BaseModel):
    wallet: str
    tier: str
    duration_hours: int
    tx_signature: str

# --- TITAN VALUATION ENGINE (THE ORACLE) ---
class ValuationEngine:
    """
    Determines the Fair Market Value (FMV) of a compute task 
    based on complexity, urgency, and token output.
    """
    @staticmethod
    def appraise(job_type: str) -> float:
        base_rates = {
            "DEFI_INTEL": 0.0002,          # Standard Analysis
            "SMART_CONTRACT_AUDIT": 0.001, # High Value / High Risk
            "MEV_OPPORTUNITY_ANALYSIS": 0.0005,
            "IMPERMANENT_LOSS_MODEL": 0.0003,
            "DEFAULT": BOUNTY_PER_JOB
        }
        return base_rates.get(job_type, base_rates["DEFAULT"])

# --- TITAN VAULT (LEDGER) ---
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
                status TEXT, tx_proof TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')
            conn.execute('''CREATE TABLE IF NOT EXISTS settlements (
                contract_id TEXT PRIMARY KEY, renter_wallet TEXT, prepaid_sol REAL,
                used_sol REAL, refund_sol REAL, settlement_tx TEXT, settled_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')
            conn.execute('''CREATE TABLE IF NOT EXISTS devices (
                device_id TEXT PRIMARY KEY, device_name TEXT, hardware_tier TEXT,
                region TEXT, uri TEXT, address TEXT, ram TEXT, audited INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')
            conn.execute('''CREATE TABLE IF NOT EXISTS billing_events (
                event_id TEXT PRIMARY KEY, contract_id TEXT, event_type TEXT,
                amount_sol REAL, cpu_percent REAL, memory_mb REAL, timestamp DATETIME)''')
            conn.commit()
        try:
            os.chmod(self.db_path, 0o600)
        except Exception:
            logger.warning("VAULT: Unable to harden ledger file permissions")

    def record_job(self, job_id, wallet, amount, tx_sig, status="CONFIRMED"):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("INSERT OR REPLACE INTO transactions VALUES (?, ?, ?, ?, ?, ?)",
                             (job_id, wallet, amount, tx_sig, datetime.now(), status))
                logger.info(f"LEDGER: Job {job_id} settled for {amount:.6f} SOL")
        except Exception as e:
            logger.error(f"VAULT ERROR: {e}")

    def create_rental(self, wallet, tier, hours, tx_proof):
        contract_id = f"CTR-{str(uuid4())[:8].upper()}"
        rates = {
            "M2": 0.001,
            "ORIN": 0.004,
            "M3_ULTRA": 0.025,
            "THOR": 0.035
        }
        cost = rates.get(tier, 0.001) * hours
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("INSERT INTO rentals (contract_id, renter_wallet, hardware_tier, duration_hours, cost_sol, start_time, status, tx_proof) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                             (contract_id, wallet, tier, hours, cost, datetime.now(), "ACTIVE", tx_proof))
                conn.commit()
            logger.info(f"VAULT: Rental {contract_id} created for {wallet} | {tier} | {hours}h | {cost} SOL")
            return {"contract_id": contract_id, "status": "ACTIVE"}
        except Exception as e:
            logger.error(f"Rental creation failed: {e}")
            return None

    def get_financials(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                job_rev = conn.execute("SELECT SUM(amount_sol) FROM transactions").fetchone()[0] or 0.0
                rent_rev = conn.execute("SELECT SUM(cost_sol) FROM rentals").fetchone()[0] or 0.0
                return job_rev + rent_rev
        except: return 0.0

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
                return [{"job_id": r[0], "worker": r[1], "amount": r[2], "time": str(r[3]), "type": r[4], "tx": r[5]} for r in res]
        except: return []

# --- TITAN BANK (ON-CHAIN SETTLEMENT) ---
class TitanBank:
    def __init__(self, keypair_path, rpc_url):
        # Preserve the RPC URL for diagnostics and mode selection
        self.rpc_url = rpc_url
        self.client = AsyncClient(rpc_url) if AsyncClient else None
        self.keypair = None
        self.enabled = False
        # Simple Mode: Native SOL transfers only (no custom programs)
        # Can be toggled via env to avoid program-id issues on different clusters.
        self.simple_mode = os.getenv("TITAN_BANK_SIMPLE_MODE", "true").lower() == "true"
        
        # Load Treasury Key
        if os.path.exists(keypair_path) and Keypair:
            try:
                with open(keypair_path, "r") as f:
                    self.keypair = Keypair.from_bytes(bytes(json.load(f)))
                self.enabled = True
                logger.info(f"TREASURY: ONLINE | {self.keypair.pubkey()}")
            except: logger.warning("TREASURY: KEY INVALID")
        else: logger.warning("TREASURY: OFFLINE (SIMULATION)")

        # Memo Program ID (optional; disabled in simple_mode)
        if not self.simple_mode and Pubkey:
            self.memo_program_id = Pubkey.from_string("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcQb")
        else:
            self.memo_program_id = None

    async def verify_transaction(self, signature: str, required_amount: float) -> bool:
        """Audits inbound rental payments on-chain."""
        if not self.enabled: return True # Sim mode allows all
        try:
            sig = Signature.from_string(signature)
            tx = await self.client.get_transaction(sig, max_supported_transaction_version=0)
            if not tx.value or tx.value.transaction.meta.err: return False
            return True
        except Exception: return False

    async def settle_contract(self, wallet_address: str, amount_sol: float, job_id: str, result_hash: str):
        """
        Executes DeFi Settlement.
        - Simple Mode: Native SOL transfer only (default for robustness).
        - Full Mode: Adds Memo instruction for on-chain proof.
        """
        if not self.enabled: return "SIMULATION_TX_SIG"

        try:
            worker_share = int(amount_sol * WORKER_FEE_PERCENT * 1e9) # Lamports

            # Base transfer instruction (native SOL transfer)
            transfer_ix = transfer(
                TransferParams(
                    from_pubkey=self.keypair.pubkey(),
                    to_pubkey=Pubkey.from_string(wallet_address),
                    lamports=worker_share
                )
            )

            instructions = [transfer_ix]

            # Optional Memo for full mode
            if not self.simple_mode and self.memo_program_id is not None:
                memo_content = f"TITAN-V1:{job_id}:{result_hash}".encode("utf-8")
                memo_ix = Instruction(
                    program_id=self.memo_program_id,
                    accounts=[],
                    data=memo_content
                )
                instructions.insert(0, memo_ix)

            # Transaction Assembly
            blockhash = (await self.client.get_latest_blockhash()).value.blockhash
            msg = Message.new_with_blockhash(
                instructions,
                self.keypair.pubkey(), 
                blockhash
            )
            
            # Sign & Fire
            txn = Transaction([self.keypair], msg, blockhash)
            sig = await self.client.send_transaction(txn)
            
            logger.info(f"SETTLEMENT: {amount_sol} SOL -> {wallet_address} | SIG: {sig.value}")
            return str(sig.value)

        except Exception as e:
            logger.error(f"SETTLEMENT FAILED: {type(e).__name__}: {str(e)}")
            logger.error(f"  Amount: {amount_sol} SOL | Wallet: {wallet_address}")
            # Self.rpc_url is always defined in __init__
            logger.error(f"  RPC: {self.rpc_url} | Client Status: {'OK' if self.client else 'OFFLINE'} | SimpleMode: {self.simple_mode}")
            return "FAILED"
    
    async def get_balance(self) -> float:
        """Returns balance of TITAN bank wallet in SOL"""
        if not self.enabled or not self.client or not self.keypair:
            return 0.0
        
        try:
            balance_response = await self.client.get_balance(self.keypair.pubkey())
            balance_lamports = balance_response.value
            balance_sol = balance_lamports / 1_000_000_000
            return balance_sol
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            return 0.0
    
    async def close(self):
        if self.client: await self.client.close()

# --- TITAN LOYALTY (GAMIFICATION) ---
class TitanLoyalty:
    def __init__(self, r): self.r = r
    async def award(self, nid, pts, reason):
        try: return await self.r.incrby(f"reputation:{nid}", pts)
        except: return 0

# --- SYSTEM INSTANTIATION ---
vault = TitanVault(DB_PATH)
bank = TitanBank(BANK_WALLET_PATH, SOLANA_RPC_URL)
loyalty = TitanLoyalty(redis_client)
commander = SwarmCommander(redis_client)

# --- HARDWARE TTS BUDGETS (SECONDS) ---
HARDWARE_TTS_BUDGET = {
    HardwareClass.STD_GPU: float(os.getenv("TITAN_TTS_STD_GPU", "10.0")),
    HardwareClass.JETSON_ORIN: float(os.getenv("TITAN_TTS_ORIN", "20.0")),
    HardwareClass.APPLE_SILICON: float(os.getenv("TITAN_TTS_APPLE", "15.0")),
}


async def has_sufficient_stake(wallet_address: str, is_internal: bool) -> bool:
    """Stake-to-Work guard.

    Internal (sovereign) nodes bypass this check. External nodes must hold at
    least STAKE_MIN_SOL on Solana to be eligible for payouts.
    """

    if is_internal:
        return True

    if not wallet_address:
        logger.warning("STAKE FIREWALL: missing wallet address on settlement")
        return False

    # If Solana client or bank is unavailable, treat as a hard deny for
    # external workers to avoid draining the treasury in degraded mode.
    if AsyncClient is None or bank is None or getattr(bank, "client", None) is None:
        logger.warning("STAKE FIREWALL: Solana client unavailable; denying external payout")
        return False

    try:
        resp = await bank.client.get_balance(Pubkey.from_string(wallet_address))
        balance_lamports = resp.value
        balance_sol = balance_lamports / 1_000_000_000
        logger.info(
            f"STAKE CHECK: {wallet_address[:6]}… balance={balance_sol:.6f} SOL (threshold={STAKE_MIN_SOL:.3f})"
        )
        return balance_sol >= STAKE_MIN_SOL
    except Exception as e:  # noqa: BLE001
        logger.warning(
            f"STAKE FIREWALL: error checking stake for {wallet_address[:6]}…: {e}"
        )
        return False

# --- API ENDPOINTS ---

@app.on_event("shutdown")
async def shutdown(): 
    await bank.close()
    await redis_client.close()

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request): return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/stats")
async def stats(request: Request):
    """Public telemetry endpoint for dashboard.

    Exposes aggregate fleet stats without authentication so the
    public web UI at https://si64.net can poll it directly.
    No sensitive per-node data is returned here.
    """
    # Aggregated Swarm Telemetry
    fleet = await redis_client.scard("pool:UNIT_ORIN_AGX:active") + \
        await redis_client.scard("pool:UNIT_APPLE_M_SERIES:active") + \
        await redis_client.scard("pool:UNIT_NVIDIA_CUDA:active")

    # Primary production queue is STD GPU; legacy ORIN queues may contain
    # historical test jobs that are no longer routed to active workers.
    queue_depth = await redis_client.llen("queue:UNIT_NVIDIA_CUDA")

    return {
        "status": "OPERATIONAL",
        "treasury_mode": "MAINNET" if bank.enabled else "SIMULATION",
        "fleet_size": fleet,
        "queue_depth": queue_depth,
        "total_revenue": vault.get_financials(),
        "transactions": vault.get_recent_activity(10)
    }

@app.get("/api/admin/stats")
async def admin_stats(request: Request, key: str = Security(api_key_header), id: Optional[str] = None):
    """Admin-only stats endpoint with stricter validation and auth.

    Used by internal threat/stress harnesses. Requires the genesis API key
    and rejects obviously malicious query payloads.
    """
    if key != GENESIS_KEY:
        raise HTTPException(401)

    # Simple SQLi/XSS-style payload detection on the optional id parameter
    if id is not None:
        suspicious_tokens = ("'", '"', ";", "--", "/*", "*/")
        if any(tok in id for tok in suspicious_tokens):
            raise HTTPException(400, "Invalid id parameter")

    fleet = await redis_client.scard("pool:UNIT_ORIN_AGX:active") + \
            await redis_client.scard("pool:UNIT_APPLE_M_SERIES:active") + \
            await redis_client.scard("pool:UNIT_NVIDIA_CUDA:active")

    queue_depth = await redis_client.llen("queue:UNIT_NVIDIA_CUDA")

    return {
        "status": "OPERATIONAL",
        "treasury_mode": "MAINNET" if bank.enabled else "SIMULATION",
        "fleet_size": fleet,
        "queue_depth": queue_depth,
        "total_revenue": vault.get_financials(),
        "transactions": vault.get_recent_activity(10)
    }

@app.get("/api/fleet")
async def fleet_overview():
    """Public view of live fleet topology.

    Returns a breakdown of active nodes per hardware pool along with
    lightweight, non-sensitive per-node metadata (node id + reputation).
    This powers the "live swarm" view on the public dashboard.
    """

    # Known hardware pools managed by SwarmCommander
    pools = {
        "UNIT_ORIN_AGX": "pool:UNIT_ORIN_AGX:active",
        "UNIT_APPLE_M_SERIES": "pool:UNIT_APPLE_M_SERIES:active",
        "UNIT_NVIDIA_CUDA": "pool:UNIT_NVIDIA_CUDA:active",
    }

    topology = {"pools": {}, "fleet_size": 0}
    seen_nodes = set()

    for hardware, pool_key in pools.items():
        try:
            members = await redis_client.smembers(pool_key)
        except Exception:
            members = []

        nodes = []
        for nid in members:
            seen_nodes.add(nid)
            # Reputation is optional gamification metadata; absence is treated as 0.
            rep = 0
            try:
                rep_str = await redis_client.get(f"reputation:{nid}")
                if rep_str is not None:
                    rep = int(rep_str)
            except Exception:
                rep = 0

            nodes.append({
                "id": nid,
                "reputation": rep,
            })

        topology["pools"][hardware] = {
            "count": len(members),
            "nodes": nodes,
        }

    topology["fleet_size"] = len(seen_nodes)
    return topology

@app.get("/api/admin/bounties")
async def admin_bounties(request: Request, key: str = Security(api_key_header), limit: int = 10):
    """Admin-only view: recent job payouts with their original bounty.

    Requires the genesis API key. Uses the ledger for settled amounts and Redis
    metadata (`job:{id}:bounty`) for the requested bounty. Intended for quick
    verification that random/configured bounties are being respected.
    """
    if key != GENESIS_KEY:
        raise HTTPException(401)

    if limit <= 0 or limit > 100:
        limit = 10

    # Recent financial activity already ordered by timestamp desc
    recent = vault.get_recent_activity(limit)
    jobs_only = [r for r in recent if r.get("type") == "JOB"]

    out = []
    for rec in jobs_only:
        jid = rec.get("job_id")
        bounty_val = None
        try:
            stored = await redis_client.get(f"job:{jid}:bounty")
            if stored is not None:
                bounty_val = float(stored)
        except Exception as e:
            logger.warning(f"Bounty introspection failed for job {jid}: {e}")

        out.append({
            "job_id": jid,
            "worker": rec.get("worker"),
            "settled_amount": rec.get("amount"),
            "bounty": bounty_val,
            "time": rec.get("time"),
            "tx": rec.get("tx")
        })

    return {"results": out}

@app.post("/api/admin/reap_ghosts")
async def admin_reap_ghosts(request: Request, key: str = Security(api_key_header)):
    """Admin-only: remove ghost nodes from Redis active sets.

    A "ghost" is any node ID present in Redis (active_nodes / pools) that does
    not have a live uplink in SwarmCommander.active_uplinks. This can happen
    if a worker process is killed ungracefully. Reaping ghosts keeps
    fleet_size and pool membership aligned with reality.
    """
    if key != GENESIS_KEY:
        raise HTTPException(401)

    try:
        # Snapshot current registry and live uplinks
        active = await redis_client.smembers("active_nodes")
        live = set(commander.active_uplinks.keys())

        ghosts = [nid for nid in active if nid not in live]

        removed = []
        for nid in ghosts:
            # Remove from global active set
            await redis_client.srem("active_nodes", nid)
            # Attempt to remove from all known hardware pools (cheap, idempotent)
            for pool in [
                "pool:UNIT_ORIN_AGX:active",
                "pool:UNIT_APPLE_M_SERIES:active",
                "pool:UNIT_NVIDIA_CUDA:active",
            ]:
                await redis_client.srem(pool, nid)
            removed.append(nid)

        # Recompute fleet after cleanup
        fleet = await redis_client.scard("pool:UNIT_ORIN_AGX:active") + \
                await redis_client.scard("pool:UNIT_APPLE_M_SERIES:active") + \
                await redis_client.scard("pool:UNIT_NVIDIA_CUDA:active")

        return {"removed": removed, "fleet_size": fleet}
    except Exception as e:
        logger.error(f"Ghost reap failed: {e}")
        raise HTTPException(500, "Ghost reap failed")

@app.get("/api/wallet")
async def get_wallet_info():
    """Returns TITAN bank wallet info (no auth required - public data)"""
    try:
        if bank and bank.keypair:
            balance = await bank.get_balance()
            return {
                "connected": True,
                "address": str(bank.keypair.pubkey()),
                "balance": balance,
                "mode": "MAINNET" if bank.enabled else "SIMULATION"
            }
        else:
            return {
                "connected": False,
                "address": None,
                "balance": 0,
                "mode": "UNKNOWN"
            }
    except Exception as e:
        logger.error(f"Error fetching wallet info: {e}")
        return {
            "connected": False,
            "address": None,
            "balance": 0,
            "mode": "ERROR"
        }

@app.get("/health", status_code=200)
async def health():
        """Lightweight health endpoint for container checks."""
        try:
            # Minimal checks: Redis ping and ledger accessible
            ok = True
            try:
                await redis_client.ping()
            except Exception:
                ok = False
            return {"status": "ok" if ok else "degraded"}
        except Exception:
            # Always return a 200 with degraded to avoid false negatives
            return {"status": "degraded"}
        # Failsafe: unreachable

@app.get("/api/devices/{tier}")
async def get_devices(tier: str):
    """Return device inventory for a tier based on live pools.

    Primary source of truth is Redis pool membership. Each active node in the
    relevant pool becomes a device record, enriched with optional metrics if
    available. If Redis is unavailable or a pool is empty, falls back to the
    legacy static templates so that marketing data still renders.
    """
    tier_upper = tier.upper()

    # Validate tier
    valid_tiers = ["M2", "ORIN", "M3_ULTRA", "THOR"]
    if tier_upper not in valid_tiers:
        raise HTTPException(status_code=400, detail=f"Invalid tier: {tier}")

    # Map UI tiers to internal hardware pools
    tier_to_pool = {
        "M2": "UNIT_APPLE_M_SERIES",
        "ORIN": "UNIT_ORIN_AGX",
        "M3_ULTRA": "UNIT_NVIDIA_CUDA",
        "THOR": "UNIT_NVIDIA_CUDA",
    }

    pool_key = f"pool:{tier_to_pool[tier_upper]}:active"

    live_devices = []
    try:
        node_ids = await redis_client.smembers(pool_key)
    except Exception:
        node_ids = []

    for nid in node_ids:
        # Optional per-node metrics (if ever populated elsewhere)
        try:
            leases_str = await redis_client.get(f"node:{nid}:active_jobs") or "0"
            leases = int(leases_str)
        except Exception:
            leases = 0

        try:
            uptime_str = await redis_client.get(f"node:{nid}:uptime") or "99.9"
            uptime = uptime_str
        except Exception:
            uptime = "99.9"

        try:
            audited_str = await redis_client.get(f"node:{nid}:audited") or "true"
            audited = audited_str.lower() == "true"
        except Exception:
            audited = True

        live_devices.append({
            "id": nid,
            "name": nid,
            "uri": None,
            "address": None,
            "region": "GLOBAL GRID",
            "ram": "N/A",
            "leases": leases,
            "uptime": f"{uptime}%" if not uptime.endswith("%") else uptime,
            "audited": audited,
        })

    # If we have live devices, return them; otherwise fall back to static set
    if live_devices:
        return live_devices

    device_templates = {
        "M2": [
            {"id": "device-m2-001", "name": "M2-DEV-01", "uri": "node001.si64.network", "address": "192.168.1.101", "region": "West Coast", "ram": "8GB"},
            {"id": "device-m2-002", "name": "M2-DEV-02", "uri": "node002.si64.network", "address": "192.168.1.102", "region": "Central", "ram": "8GB"},
            {"id": "device-m2-003", "name": "M2-DEV-03", "uri": "node003.si64.network", "address": "192.168.1.103", "region": "East Coast", "ram": "16GB"},
        ],
        "ORIN": [
            {"id": "device-orin-001", "name": "ORIN-CV-01", "uri": "node004.si64.network", "address": "192.168.1.201", "region": "Pacific NW", "ram": "12GB"},
            {"id": "device-orin-002", "name": "ORIN-CV-02", "uri": "node005.si64.network", "address": "192.168.1.202", "region": "Northeast", "ram": "12GB"},
            {"id": "device-orin-003", "name": "ORIN-CV-03", "uri": "node006.si64.network", "address": "192.168.1.203", "region": "Mountain", "ram": "12GB"},
            {"id": "device-orin-004", "name": "ORIN-CV-04", "uri": "node007.si64.network", "address": "192.168.1.204", "region": "Pacific NW", "ram": "12GB"},
        ],
        "M3_ULTRA": [
            {"id": "device-m3u-001", "name": "M3U-ULTRA-01", "uri": "node008.si64.network", "address": "192.168.1.301", "region": "West Coast", "ram": "128GB"},
            {"id": "device-m3u-002", "name": "M3U-ULTRA-02", "uri": "node009.si64.network", "address": "192.168.1.302", "region": "Southeast", "ram": "128GB"},
        ],
        "THOR": [
            {"id": "device-thor-001", "name": "THOR-HPC-01", "uri": "node010.si64.network", "address": "192.168.1.401", "region": "Southwest", "ram": "144GB"},
            {"id": "device-thor-002", "name": "THOR-HPC-02", "uri": "node011.si64.network", "address": "192.168.1.402", "region": "Midwest", "ram": "144GB"},
            {"id": "device-thor-003", "name": "THOR-HPC-03", "uri": "node012.si64.network", "address": "192.168.1.403", "region": "Southeast", "ram": "144GB"},
        ],
    }

    fallback = []
    for device in device_templates.get(tier_upper, []):
        fallback.append({
            **device,
            "leases": 0,
            "uptime": "99.8%",
            "audited": True,
        })

    return fallback

@app.post("/api/rent")
async def rent(req: RentalRequest):
    """Executes Hardware Rental with On-Chain Verification"""
    rates = {
        "M2": 0.001,
        "ORIN": 0.004,
        "M3_ULTRA": 0.025,
        "THOR": 0.035
    }
    
    # Calculate total cost
    cost = rates.get(req.tier, 0.001) * req.duration_hours
    
    # Verify transaction on Solana (in simulation mode, always passes)
    if not await bank.verify_transaction(req.tx_signature, cost):
        raise HTTPException(status_code=402, detail="Payment Verification Failed")

    # Create rental contract
    contract = vault.create_rental(req.wallet, req.tier, req.duration_hours, req.tx_signature)
    if not contract:
        raise HTTPException(status_code=500, detail="Contract Creation Failed")
    
    # Initialize contract state in Redis
    contract_id = contract["contract_id"]
    await redis_client.set(f"contract:{contract_id}:wallet", req.wallet)
    await redis_client.set(f"contract:{contract_id}:tier", req.tier)
    await redis_client.set(f"contract:{contract_id}:duration_hours", req.duration_hours)
    await redis_client.set(f"contract:{contract_id}:cost_sol", cost)
    await redis_client.set(f"contract:{contract_id}:start_time", int(time()))
    await redis_client.set(f"contract:{contract_id}:status", "ACTIVE")
    await redis_client.set(f"contract:{contract_id}:usage_cost", 0)
    await redis_client.set(f"contract:{contract_id}:expiration", int(time()) + (req.duration_hours * 3600))
    
    # Add to active contracts list
    await redis_client.sadd("contracts:active", contract_id)
    
    logger.info(f"RENTAL: Contract {contract_id} created for {req.wallet} | {req.tier} | {req.duration_hours}h | {cost} SOL")
    
    return {
        **contract,
        "cost_sol": cost,
        "tier": req.tier,
        "duration_hours": req.duration_hours
    }

@app.get("/api/contracts/{contract_id}")
async def get_contract(contract_id: str):
    """Retrieves live contract status and billing information"""
    contract_status = await redis_client.get(f"contract:{contract_id}:status")
    if not contract_status:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    wallet = await redis_client.get(f"contract:{contract_id}:wallet")
    tier = await redis_client.get(f"contract:{contract_id}:tier")
    duration_hours = float(await redis_client.get(f"contract:{contract_id}:duration_hours") or 0)
    cost_sol = float(await redis_client.get(f"contract:{contract_id}:cost_sol") or 0)
    start_time = int(await redis_client.get(f"contract:{contract_id}:start_time") or 0)
    usage_cost = float(await redis_client.get(f"contract:{contract_id}:usage_cost") or 0)
    expiration = int(await redis_client.get(f"contract:{contract_id}:expiration") or 0)
    
    # Calculate elapsed time
    elapsed_seconds = int(time()) - start_time
    elapsed_hours = elapsed_seconds / 3600.0
    remaining_seconds = max(0, expiration - int(time()))
    
    # Calculate refund amount
    refund_amount = max(0, cost_sol - usage_cost)
    
    return {
        "contract_id": contract_id,
        "wallet": wallet,
        "tier": tier,
        "status": contract_status,
        "prepaid_sol": cost_sol,
        "used_sol": usage_cost,
        "refund_available": refund_amount,
        "duration_hours": duration_hours,
        "elapsed_hours": round(elapsed_hours, 2),
        "remaining_seconds": remaining_seconds,
        "created_at": start_time,
        "expires_at": expiration
    }

@app.post("/api/contracts/{contract_id}/extend")
async def extend_contract(contract_id: str, additional_hours: int):
    """Extends an active contract and processes additional payment"""
    contract_status = await redis_client.get(f"contract:{contract_id}:status")
    if contract_status != "ACTIVE":
        raise HTTPException(status_code=400, detail="Contract not active")
    
    tier = await redis_client.get(f"contract:{contract_id}:tier")
    rates = {
        "M2": 0.001,
        "ORIN": 0.004,
        "M3_ULTRA": 0.025,
        "THOR": 0.035
    }
    
    additional_cost = rates.get(tier, 0.001) * additional_hours
    
    # Update contract
    duration_hours = float(await redis_client.get(f"contract:{contract_id}:duration_hours") or 0)
    current_cost = float(await redis_client.get(f"contract:{contract_id}:cost_sol") or 0)
    
    new_duration = duration_hours + additional_hours
    new_cost = current_cost + additional_cost
    
    await redis_client.set(f"contract:{contract_id}:duration_hours", new_duration)
    await redis_client.set(f"contract:{contract_id}:cost_sol", new_cost)
    await redis_client.set(f"contract:{contract_id}:expiration", 
                          int(time()) + int(new_duration * 3600))
    
    logger.info(f"EXTEND: Contract {contract_id} extended by {additional_hours}h | +{additional_cost} SOL")
    
    return {
        "contract_id": contract_id,
        "extended_hours": additional_hours,
        "additional_cost_sol": additional_cost,
        "new_total_cost": new_cost,
        "new_expiration": int(time()) + int(new_duration * 3600)
    }

@app.post("/api/contracts/{contract_id}/settle")
async def settle_contract(contract_id: str):
    """
    Settles a contract: calculates actual usage, issues refund if applicable.
    Called when contract expires or customer terminates early.
    """
    contract_status = await redis_client.get(f"contract:{contract_id}:status")
    if not contract_status:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    wallet = await redis_client.get(f"contract:{contract_id}:wallet")
    cost_sol = float(await redis_client.get(f"contract:{contract_id}:cost_sol") or 0)
    usage_cost = float(await redis_client.get(f"contract:{contract_id}:usage_cost") or 0)
    start_time = int(await redis_client.get(f"contract:{contract_id}:start_time") or 0)
    
    # Calculate refund
    refund_amount = max(0, cost_sol - usage_cost)
    
    # Mark as settled
    await redis_client.set(f"contract:{contract_id}:status", "SETTLED")
    await redis_client.srem("contracts:active", contract_id)
    
    # Record settlement
    settlement_record = {
        "contract_id": contract_id,
        "wallet": wallet,
        "prepaid": cost_sol,
        "used": usage_cost,
        "refund": refund_amount,
        "settlement_time": int(time())
    }
    await redis_client.rpush("settlements:completed", json.dumps(settlement_record))
    
    # If refund > 0 and we have on-chain capability, process refund
    if refund_amount > 0 and bank.enabled:
        try:
            tx_sig = await bank.settle_contract(wallet, refund_amount, contract_id, f"REFUND-{contract_id}")
            logger.info(f"SETTLEMENT: Contract {contract_id} | Refund {refund_amount} SOL -> {wallet} | TX: {tx_sig}")
            return {
                "contract_id": contract_id,
                "status": "SETTLED",
                "prepaid_sol": cost_sol,
                "used_sol": usage_cost,
                "refund_sol": refund_amount,
                "tx_signature": tx_sig
            }
        except Exception as e:
            logger.error(f"Settlement failed for {contract_id}: {e}")
            return {
                "contract_id": contract_id,
                "status": "SETTLEMENT_ERROR",
                "error": str(e)
            }
    else:
        return {
            "contract_id": contract_id,
            "status": "SETTLED",
            "prepaid_sol": cost_sol,
            "used_sol": usage_cost,
            "refund_sol": refund_amount,
            "tx_signature": "SIMULATION_MODE"
        }

@app.post("/api/metrics/{contract_id}")
async def record_metrics(contract_id: str, metrics: dict):
    """
    Records real-time metrics from executing container.
    Called every 500ms by device worker nodes.
    Updates billing in real-time.
    """
    contract_status = await redis_client.get(f"contract:{contract_id}:status")
    if contract_status != "ACTIVE":
        raise HTTPException(status_code=400, detail="Contract not active")
    
    # Extract metrics
    cpu_percent = metrics.get("cpu_percent", 0)
    memory_mb = metrics.get("memory_mb", 0)
    disk_io_mbps = metrics.get("disk_io_mbps", 0)
    network_io_mbps = metrics.get("network_io_mbps", 0)
    
    # Get contract details
    tier = await redis_client.get(f"contract:{contract_id}:tier")
    start_time = int(await redis_client.get(f"contract:{contract_id}:start_time") or 0)
    cost_sol = float(await redis_client.get(f"contract:{contract_id}:cost_sol") or 0)
    
    # Calculate elapsed time
    elapsed_seconds = int(time()) - start_time
    elapsed_hours = elapsed_seconds / 3600.0
    
    # Calculate usage cost (linear billing based on elapsed time)
    rates = {
        "M2": 0.001,
        "ORIN": 0.004,
        "M3_ULTRA": 0.025,
        "THOR": 0.035
    }
    rate = rates.get(tier, 0.001)
    usage_cost = rate * elapsed_hours
    
    # Update Redis
    await redis_client.set(f"contract:{contract_id}:usage_cost", usage_cost)
    await redis_client.set(f"contract:{contract_id}:last_metric_time", int(time()))
    
    # Store metrics time-series
    metric_entry = {
        "cpu": cpu_percent,
        "memory_mb": memory_mb,
        "disk_io": disk_io_mbps,
        "network_io": network_io_mbps,
        "cost_so_far": usage_cost,
        "timestamp": int(time())
    }
    await redis_client.rpush(f"contract:{contract_id}:metrics", json.dumps(metric_entry))
    
    # Keep last 100 metrics
    await redis_client.ltrim(f"contract:{contract_id}:metrics", -100, -1)
    
    return {
        "contract_id": contract_id,
        "metrics_recorded": True,
        "elapsed_hours": round(elapsed_hours, 4),
        "cost_so_far": round(usage_cost, 6),
        "refund_available": round(cost_sol - usage_cost, 6)
    }

@app.get("/api/billing/ledger")
async def get_billing_ledger():
    """Returns complete billing ledger for all active contracts"""
    active_contracts = await redis_client.smembers("contracts:active")
    
    ledger = []
    for contract_id in active_contracts:
        wallet = await redis_client.get(f"contract:{contract_id}:wallet")
        tier = await redis_client.get(f"contract:{contract_id}:tier")
        cost_sol = float(await redis_client.get(f"contract:{contract_id}:cost_sol") or 0)
        usage_cost = float(await redis_client.get(f"contract:{contract_id}:usage_cost") or 0)
        status = await redis_client.get(f"contract:{contract_id}:status")
        
        ledger.append({
            "contract_id": contract_id,
            "wallet": wallet,
            "tier": tier,
            "prepaid": cost_sol,
            "used": usage_cost,
            "refund": cost_sol - usage_cost,
            "status": status
        })
    
    # Get completed settlements
    settlements_raw = await redis_client.lrange("settlements:completed", 0, -1)
    completed = [json.loads(s) for s in settlements_raw]
    
    return {
        "active_contracts": ledger,
        "completed_settlements": completed,
        "total_active_value": sum(c["prepaid"] for c in ledger),
        "total_used": sum(c["used"] for c in ledger),
        "total_pending_refunds": sum(c["refund"] for c in ledger)
    }

@app.post("/submit_job")
async def submit(job: JobRequest, key: str = Security(api_key_header)):
    if key != GENESIS_KEY:
        raise HTTPException(401)

    # 1. Valuation: prefer explicit bounty if provided, otherwise use oracle
    if job.bounty is not None:
        est_value = float(job.bounty)
    else:
        est_value = ValuationEngine.appraise(job.type)

    # 2. Hardware Routing (default to standard GPU pool)
    try:
        hw = HardwareClass(job.hardware)
    except Exception:
        hw = HardwareClass.STD_GPU

    # 3. Dispatch
    payload = job.dict()
    payload["contract_value"] = est_value

    directive = JobDirective(tier=MissionTier.BETA, hardware_req=hw, payload=payload)
    jid = await commander.dispatch_mission(directive)

    if jid:
        # Persist bounty so settlement can use the exact agreed value
        try:
            await redis_client.set(f"job:{jid}:bounty", est_value)
            # Safety: expire bounty metadata after 24h to avoid unbounded growth
            await redis_client.expire(f"job:{jid}:bounty", 86400)
        except Exception as e:
            logger.warning(f"Failed to persist bounty for job {jid}: {e}")
        return {"status": "CONTRACT_ISSUED", "job_id": jid, "value_sol": est_value}

    raise HTTPException(500, "Dispatch Failed")

@app.websocket("/connect")
async def ws_endpoint(ws: WebSocket):
    """Unified Nervous System Uplink"""
    # Debug: Log all headers
    logger.info(f"WebSocket connection attempt from {ws.client.host}")
    logger.info(f"Headers received: {dict(ws.headers)}")

    client_ip = ws.client.host or ""
    is_internal = client_ip in INTERNAL_IP_WHITELIST or client_ip.startswith("127.")
    if is_internal:
        logger.info(f"SOVEREIGN BYPASS: {client_ip} marked as internal node")
    
    # Check for GENESIS_KEY in headers (case-insensitive)
    provided_key = None
    for header_name, header_value in ws.headers.items():
        if header_name.lower() == "x-genesis-key":
            provided_key = header_value
            break
    
    logger.info(f"Genesis Key from headers: {provided_key}")
    
    if provided_key != GENESIS_KEY:
        logger.warning(f"WebSocket auth failed: expected '{GENESIS_KEY}', got '{provided_key}'")
        await ws.close(code=1008, reason="Unauthorized: Invalid GENESIS_KEY")
        return
    
    await ws.accept()

    nid = "UNKNOWN"
    hw = HardwareClass.STD_GPU
    
    try:
        # Handshake
        data = json.loads(await ws.receive_text())
        nid = data.get("node_id", str(uuid4())[:8])
        try:
            hw = HardwareClass(data.get("hardware", "UNIT_NVIDIA_CUDA"))
        except Exception:  # noqa: BLE001
            hw = HardwareClass.STD_GPU

        # Sentinel banlist check: block previously banned nodes
        try:
            if await redis_client.sismember("banned_nodes", nid):
                logger.warning(f"SENTINEL: Rejected banned node {nid} from {client_ip}")
                await ws.close(code=1008, reason="Node banned by Sentinel")
                return
        except Exception as e:  # noqa: BLE001
            logger.warning(f"SENTINEL: Banlist check failed for {nid}: {e}")

        await commander.commission_unit(ws, nid, hw)
        await loyalty.award(nid, 10, "INIT")
        
        while True:
            msg = json.loads(await ws.receive_text())
            
            # SETTLEMENT LOGIC
            if msg.get("last_event") == "JOB_COMPLETE":
                jid = msg.get("job_id")
                worker_wallet = msg.get("wallet_address")
                result_content = msg.get("result", "")

                # Time-to-Solution Sentinel: measure wall-clock from dispatch
                tts = None
                over_tts = False
                try:
                    start_ts = await redis_client.get(f"job:{jid}:start_ts")
                    if start_ts is not None:
                        tts = time() - float(start_ts)
                        budget = HARDWARE_TTS_BUDGET.get(
                            hw, HARDWARE_TTS_BUDGET.get(HardwareClass.STD_GPU)
                        )
                        if tts > budget:
                            over_tts = True
                            logger.warning(
                                f"SENTINEL: Node {nid} exceeded TTS budget "
                                f"({tts:.2f}s > {budget:.2f}s) [{hw.value}]"
                            )
                            try:
                                await redis_client.sadd("banned_nodes", nid)
                            except Exception as e:  # noqa: BLE001
                                logger.warning(
                                    f"SENTINEL: Failed to persist ban for {nid}: {e}"
                                )
                    else:
                        logger.debug(f"SENTINEL: No start_ts for job {jid}; skipping TTS check")
                except Exception as e:  # noqa: BLE001
                    logger.warning(f"SENTINEL: TTS evaluation failed for job {jid}: {e}")

                # If an EXTERNAL node blows the TTS budget, ban and stop.
                if over_tts and not is_internal:
                    vault.record_job(jid, worker_wallet, 0.0, "SENTINEL_BAN", status="SENTINEL_BAN")
                    await loyalty.award(nid, -250, "SENTINEL_BAN")
                    await ws.send_text(json.dumps({
                        "type": "ACK",
                        "status": "BANNED_SENTINEL",
                        "tx_signature": None,
                        "value": 0.0,
                    }))
                    await ws.close(code=1013, reason="Hardware mismatch; banned by Sentinel")
                    return

                # Proof of Intelligence (Simple Hash)
                result_hash = hashlib.sha256(str(result_content).encode()).hexdigest()[:16]

                # Valuation Lookup: prefer the original agreed bounty if available
                payout_value: float
                try:
                    stored = await redis_client.get(f"job:{jid}:bounty")
                    if stored is not None:
                        payout_value = float(stored)
                    else:
                        # Fallback heuristic: content-based or default oracle value
                        payout_value = 0.001 if "Rust" in str(result_content) else ValuationEngine.appraise("DEFAULT")
                except Exception as e:
                    logger.warning(f"Bounty lookup failed for job {jid}: {e}")
                    payout_value = ValuationEngine.appraise("DEFAULT")

                # Stake-to-Work Economic Firewall: external nodes must hold stake
                if not await has_sufficient_stake(worker_wallet, is_internal):
                    logger.warning(
                        f"STAKE FIREWALL: denying payout for job {jid} from "
                        f"wallet {worker_wallet[:6]}…"
                    )
                    vault.record_job(jid, worker_wallet, 0.0, "DENIED_STAKE", status="DENIED_STAKE")
                    await loyalty.award(nid, -50, "INSUFFICIENT_STAKE")
                    await ws.send_text(json.dumps({
                        "type": "ACK",
                        "status": "DENIED_STAKE",
                        "tx_signature": None,
                        "value": 0.0,
                    }))
                    continue

                # Execute Settlement
                tx_sig = await bank.settle_contract(worker_wallet, payout_value, jid, result_hash)
                vault.record_job(jid, worker_wallet, payout_value, tx_sig)

                await loyalty.award(nid, 100, "JOB_DONE")
                await ws.send_text(json.dumps({
                    "type": "ACK",
                    "status": "SETTLED",
                    "tx_signature": tx_sig,
                    "value": payout_value
                }))
            
            # DISPATCH LOGIC
            if msg.get("status") == "IDLE":
                target_queue = f"queue:{hw.value}"
                raw = await redis_client.rpop(target_queue)
                if raw:
                    job = json.loads(raw)
                    logger.info(f"DISPATCH {job['job_id']} -> {nid}")
                    # Record dispatch metadata for Sentinel (Time-to-Solution)
                    dispatch_ts = time()
                    try:
                        async with redis_client.pipeline() as pipe:
                            pipe.set(f"job:{job['job_id']}:start_ts", dispatch_ts, ex=3600)
                            pipe.set(f"job:{job['job_id']}:hardware", hw.value, ex=3600)
                            pipe.set(f"job:{job['job_id']}:node", nid, ex=3600)
                            await pipe.execute()
                    except Exception as e:  # noqa: BLE001
                        logger.warning(
                            f"SENTINEL: Failed to record dispatch metadata for job {job['job_id']}: {e}"
                        )
                    # Merge ID into payload for worker
                    final_payload = job['payload']
                    final_payload['job_id'] = job['job_id']
                    await ws.send_text(json.dumps(final_payload))
                    
    except Exception as e:
        logger.error(f"NODE LOST {nid}: {e}")
    finally:
        await commander.decommission_unit(nid, hw)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=DISPATCHER_HOST, port=DISPATCHER_PORT)
