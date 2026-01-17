import sys
import os
import json
import logging
import sqlite3
import asyncio
import redis.asyncio as redis
from datetime import datetime
from uuid import uuid4
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor

# Third-Party Enterprise Libraries
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Security
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security.api_key import APIKeyHeader
from starlette.requests import Request
from pydantic import BaseModel, Field

# --- CONFIGURATION IMPORT ---
# Dynamically add the parent directory to path to locate titan_config.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from titan_config import *
except ImportError:
    # Emergency Fallback Defaults
    print("CRITICAL: Config module missing. Loading Emergency Defaults.")
    GENESIS_KEY = "TITAN_DEBUG_KEY"
    DISPATCHER_HOST = "0.0.0.0"
    DISPATCHER_PORT = 8000
    WORKER_FEE_PERCENT = 0.95
    FOUNDER_FEE_PERCENT = 0.05

# --- SYSTEM ARCHITECTURE SETTINGS ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "titan_ledger.db")
STATIC_DIR = os.path.join(BASE_DIR, "www/static")
TEMPLATE_DIR = os.path.join(BASE_DIR, "www/templates")

# --- LOGGING CONFIGURATION (MILITARY STANDARD) ---
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
    """Schema for external job submission."""
    type: str = Field(..., description="Job Type: 'LLAMA', 'IMAGE', 'TRAIN'")
    prompt: str = Field(..., description="The raw input data or prompt")
    bounty: float = Field(..., gt=0, description="Payment offered (USD/Credits)")

class JobResponse(BaseModel):
    status: str
    job_id: str
    tax_deducted: float
    timestamp: datetime

# --- COMPONENT 1: THE VAULT (Long-Term Memory / SQLite) ---
class TitanVault:
    """
    The Immutable Ledger.
    Handles all financial transactions and historical records.
    Uses a ThreadPool to prevent disk I/O from blocking the Async Event Loop.
    """
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
        # ThreadPoolExecutor ensures that slow disk writes don't freeze the API
        self.executor = ThreadPoolExecutor(max_workers=1)

    def _init_db(self):
        """Synchronous DB Initialization."""
        try:
            with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
                conn.execute('PRAGMA journal_mode=WAL;') # High-concurrency mode
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS transactions (
                        job_id TEXT PRIMARY KEY, 
                        wallet_address TEXT, 
                        total_amount REAL, 
                        protocol_fee REAL, 
                        worker_share REAL, 
                        timestamp DATETIME
                    )
                ''')
                conn.commit()
            logger.info("Titan Vault: Integrity Verified.")
        except Exception as e:
            logger.critical(f"Vault Initialization Failed: {e}")
            sys.exit(1)

    def _record_transaction_sync(self, job_id, wallet, amount):
        """Internal Synchronous Write."""
        try:
            # Calculate Splits
            fee = round(amount * FOUNDER_FEE_PERCENT, 4)
            share = round(amount * WORKER_FEE_PERCENT, 4)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?)",
                    (job_id, wallet, amount, fee, share, datetime.now())
                )
            logger.info(f"SETTLEMENT: {job_id} | Paid ${share} to {wallet}")
            return True
        except Exception as e:
            logger.error(f"Ledger Write Error: {e}")
            return False

    def _get_revenue_sync(self):
        """Internal Synchronous Read."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT SUM(protocol_fee) FROM transactions")
                result = cursor.fetchone()[0]
                return result if result else 0.0
        except Exception:
            return 0.0

    async def record_transaction(self, job_id, wallet, amount):
        """Async Wrapper for Transaction Recording."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self.executor, self._record_transaction_sync, job_id, wallet, amount
        )

    async def get_total_revenue(self):
        """Async Wrapper for Revenue Reporting."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self.executor, self._get_revenue_sync
        )

# --- INITIALIZATION ---
app = FastAPI(
    title="Titan Protocol Cortex",
    version="2.0.0",
    description="Enterprise Orchestrator for Decentralized Edge Compute"
)

# Mount Static Assets (CSS/Images)
# Ensure directories exist to prevent startup crash
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATE_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

# Initialize Memory Systems
vault = TitanVault(DB_PATH)
# Redis: The High-Speed Reflex Layer
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Security Headers
api_key_header = APIKeyHeader(name="x-genesis-key", auto_error=False)

# --- DEPENDENCIES ---
async def verify_key(key: str = Security(api_key_header)):
    if key != GENESIS_KEY:
        raise HTTPException(status_code=403, detail="Access Denied: Invalid Genesis Key")
    return key

# --- LIFECYCLE HOOKS ---
@app.on_event("startup")
async def startup_event():
    """System Boot Sequence."""
    logger.info("TITAN CORTEX: BOOT SEQUENCE INITIATED...")
    try:
        await redis_client.ping()
        logger.info("Layer 2 Memory (Redis): ONLINE")
        # Clear stale active node set on restart
        await redis_client.delete("active_nodes")
    except Exception as e:
        logger.critical(f"Layer 2 Memory (Redis) FAILED: {e}")
        logger.critical("System cannot operate without Short-Term Memory. Aborting.")
        sys.exit(1)

@app.on_event("shutdown")
async def shutdown_event():
    """System Shutdown Sequence."""
    logger.info("TITAN CORTEX: SHUTDOWN SEQUENCE...")
    await redis_client.close()
    vault.executor.shutdown()
    logger.info("Memory Systems Offline.")

# --- API ENDPOINTS ---

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serves the Command Center Dashboard."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/stats")
async def get_system_stats():
    """
    Hybrid Telemetry Endpoint.
    Combines Redis (Speed) and SQLite (Truth) for the Dashboard.
    """
    # 1. Real-time Fleet Metrics (Redis)
    fleet_size = await redis_client.scard("active_nodes")
    queue_depth = await redis_client.llen("titan_job_queue")
    
    # 2. Financial Metrics (SQLite - Async)
    revenue = await vault.get_total_revenue()
    
    return {
        "status": "OPERATIONAL",
        "fleet_size": fleet_size,
        "queue_depth": queue_depth,
        "total_revenue": revenue,
        "timestamp": str(datetime.now())
    }

@app.post("/submit_job", response_model=JobResponse, dependencies=[Depends(verify_key)])
async def submit_job(job: JobRequest):
    """
    Ingests a new job into the High-Speed Queue.
    """
    job_id = str(uuid4())[:8]
    
    # Construct Payload
    payload = {
        "job_id": job_id,
        "type": job.type,
        "prompt": job.prompt,
        "bounty": job.bounty, # Passed to worker for verification
        "timestamp": str(datetime.now())
    }
    
    # Push to Redis (Microsecond latency)
    try:
        await redis_client.lpush("titan_job_queue", json.dumps(payload))
        logger.info(f"JOB INGESTED: {job_id} [{job.type}] | Bounty: ${job.bounty}")
    except Exception as e:
        logger.error(f"Ingestion Failed: {e}")
        raise HTTPException(status_code=500, detail="Queue Error")

    return JobResponse(
        status="QUEUED",
        job_id=job_id,
        tax_deducted=job.bounty * FOUNDER_FEE_PERCENT,
        timestamp=datetime.now()
    )

@app.websocket("/connect")
async def websocket_endpoint(websocket: WebSocket):
    """
    The Nervous System.
    Manages the swarm of Worker Nodes via persistent WebSocket.
    """
    # 1. Security Handshake
    key = websocket.headers.get("x-genesis-key")
    if key != GENESIS_KEY:
        logger.warning(f"Intrusion Attempt: {websocket.client}")
        await websocket.close(code=1008)
        return

    await websocket.accept()
    node_id = "UNKNOWN"

    try:
        # 2. Identification
        # Wait for initial telemetry packet
        data = await websocket.receive_text()
        telemetry = json.loads(data)
        node_id = telemetry.get("node_id", f"NODE_{str(uuid4())[:4]}")
        
        # Mark Online in Redis Set
        await redis_client.sadd("active_nodes", node_id)
        logger.info(f"SWARM UPDATE: Node {node_id} Linked.")

        # 3. Command Loop
        while True:
            # A. Process Incoming Telemetry
            data = await websocket.receive_text()
            telemetry = json.loads(data)
            
            # Store Live State in Redis (Expires in 5s for auto-cleanup of dead nodes)
            await redis_client.setex(f"node_state:{node_id}", 5, json.dumps(telemetry))
            
            # B. Handle Job Completion / Settlement
            if telemetry.get("last_event") == "JOB_COMPLETE":
                # Trigger Financial Settlement
                # In a real system, we would look up the job's bounty from a "pending_jobs" map.
                # Here we assume a standard rate or data passed back for V1 simplicity.
                # Ideally, the Job ID is cross-referenced.
                job_id = telemetry.get("job_id", "UNKNOWN")
                wallet = telemetry.get("wallet_address", "UNKNOWN")
                
                # Asynchronously record the payment
                # Hardcoded bounty for V1 demo; in V2 fetch from Redis 'job_manifest'
                await vault.record_transaction(job_id, wallet, 0.50)

            # C. Dispatch Logic
            # If Node is IDLE, check the Queue
            if telemetry.get("status") == "IDLE":
                # Atomic Pop from Redis Queue
                job_bytes = await redis_client.rpop("titan_job_queue")
                
                if job_bytes:
                    job_data = json.loads(job_bytes)
                    logger.info(f"DISPATCH: Job {job_data['job_id']} -> {node_id}")
                    await websocket.send_text(json.dumps(job_data))

    except WebSocketDisconnect:
        logger.info(f"NODE LOST: {node_id}")
        # Remove from Active Set
        await redis_client.srem("active_nodes", node_id)
        # Note: We rely on Redis TTL to expire the 'node_state' key automatically

    except Exception as e:
        logger.error(f"Connection Error ({node_id}): {e}")
        await redis_client.srem("active_nodes", node_id)

# --- ENTRY POINT ---
if __name__ == "__main__":
    import uvicorn
    logger.info("TITAN CORTEX ENGINE: STARTING...")
    uvicorn.run(app, host=DISPATCHER_HOST, port=DISPATCHER_PORT)
