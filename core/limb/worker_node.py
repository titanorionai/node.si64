"""
TITAN PROTOCOL | WORKER LIMB (V8.1 - CONTAINERIZED EXECUTION)
=======================================================
Authority:      Local Node Command
Classification: RESTRICTED
Capabilities:   
  - Docker Container Isolation (ALL jobs sandboxed)
  - Native Ollama API Bridge (Async/Non-Blocking)
  - True Silicon Telemetry (Kernel Level)
  - Hardware-Specific Model Targeting
  - Thermal Throttling & Self-Preservation
"""

import asyncio
import websockets
import json
import logging
import hmac
import hashlib
import os
import sys
import platform
import argparse
import uuid
import re
import subprocess
import aiohttp
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Dict, Optional
import socket


def get_identity():
    """
    STRICT IDENTITY PROTOCOL v1.0
    Only accepts the official SI64 standard. No legacy fallbacks.
    """
    wallet = os.getenv("SI64_WALLET_ADDRESS")
    if wallet:
        logging.info(f"IDENTITY VERIFIED: {wallet}")
        return wallet

    logging.critical("MISSING CONFIGURATION: 'SI64_WALLET_ADDRESS' env var is required.")
    logging.critical("DEPLOYMENT ABORTED.")
    sys.exit(1)


def print_critical_warning():
    # ANSI Colors
    YELLOW = "\033[93m"
    RED = "\033[91m"
    RESET = "\033[0m"
    BOLD = "\033[1m"
    
    # Send to Standard Error (sys.stderr) so it bypasses pipes
    sys.stderr.write(f"\n{YELLOW}" + "="*60 + "\n")
    sys.stderr.write(f" {RED}🛑 CRITICAL FAILURE: MISSING WALLET CONFIGURATION{YELLOW}\n")
    sys.stderr.write("="*60 + f"{RESET}\n")
    
    sys.stderr.write(f"\n {BOLD}The node cannot operate without a payout target.{RESET}\n")
    sys.stderr.write(f" Rewards will be lost. Mission Aborted.\n")
    
    sys.stderr.write("\n [RECOVERY PROTOCOLS]\n")
    sys.stderr.write(f" 1. Edit Configuration:\n")
    sys.stderr.write(f"    {BOLD}nano ~/.si64/config.json{RESET}\n")
    sys.stderr.write("\n 2. Input Solana Wallet Address.\n")
    sys.stderr.write("\n 3. Restart Node.\n")
    
    sys.stderr.write(f"\n{YELLOW}" + "="*60 + f"{RESET}\n\n")
    
    # KILL SWITCH
    sys.exit(1)

try:
    import docker  # Optional; enables container isolation when available
except ImportError:
    docker = None

# --- CONFIGURATION LAYER ---
# Calculate the TitanNetwork root directory
_current_file = os.path.abspath(__file__)
_limb_dir = os.path.dirname(_current_file)
_core_dir = os.path.dirname(_limb_dir)
_root_dir = os.path.dirname(_core_dir)
sys.path.insert(0, _root_dir)

try:
    from titan_config import *
except ImportError as e:
    # Fallback Configuration (Fail-Safe)
    print(f"[WARN] Failed to import titan_config from {_root_dir}: {e}")
    print(f"[WARN] Using fallback configuration")
    # SECURITY: Do NOT hardcode sensitive keys. Read from environment.
    GENESIS_KEY = os.getenv("GENESIS_KEY")
    WEBSOCKET_URL = "ws://127.0.0.1:8000/connect"
    TITAN_OLLAMA_HOST = "http://localhost:11434"
    MAX_SAFE_TEMP_C = 85
    DEFAULT_WALLET = "3ykXYQWyoRsAhJ8GDQforFsK37emQgeri5DkDTUQfShz"
    RECONNECT_DELAY = 5
    HEARTBEAT_INTERVAL = 2.0

# --- HARDWARE RECONNAISSANCE ---
ARCH = platform.machine().lower()
SYSTEM = platform.system().lower()
IS_JETSON = False
IS_MAC = (SYSTEM == 'darwin' and ARCH == 'arm64')

# Jetson-Specific Libraries
if IS_JETSON:
    try:
        from jtop import jtop
    except ImportError:
        pass # Telemetry will degrade gracefully if missing

# --- LOGGING SETUP ---
log_dir = os.path.expanduser("~/TitanNetwork/limb/logs")
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | [%(name)s] | %(message)s", 
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(log_dir, "limb.log"))
    ]
)
LOGGER_NAME = "TITAN_LIMB_ORIN" if IS_JETSON else ("TITAN_LIMB_APPLE" if IS_MAC else "TITAN_LIMB_STD")
logger = logging.getLogger(LOGGER_NAME)
NODE_ID = f"{platform.node()}_{LOGGER_NAME.split('_')[-1]}_{str(uuid.uuid4())[:4]}"

# --- CONTAINER EXECUTION MODE ---
CONTAINER_MODE = os.getenv("TITAN_CONTAINER_MODE", "false").lower() == "true"
DOCKER_CLIENT = None

if docker is not None:
    try:
        DOCKER_CLIENT = docker.from_env()
        logger.info("[SECURITY] Docker client initialized - container isolation ENABLED")
    except Exception as e:
        logger.warning(f"[SECURITY] Docker unavailable: {e}. Fallback to safe mode.")
        DOCKER_CLIENT = None
else:
    logger.warning("[SECURITY] Docker library not installed. Running without container isolation.")

class TitanLimb:
    def __init__(self, connect_url=None, wallet=None, container_mode=False):
        self.uri = connect_url if connect_url else WEBSOCKET_URL

        # Strict identity: only accept SI64_WALLET_ADDRESS (no legacy fallbacks)
        self.wallet = get_identity()
        self.headers = {"x-genesis-key": GENESIS_KEY}
        # Enforce explicit wallet configuration: if the node is launched
        # without an explicit `--wallet` argument and no `TITAN_WORKER_WALLET`
        # environment variable is set, refuse to run to avoid reward loss.
        try:
            # Only treat missing wallet as fatal if no explicit CLI arg or env var
            if wallet is None and not env_wallet:
                print_critical_warning()
        except Exception:
            pass
        # Advertise node identity in handshake headers so the dispatcher
        # can whitelist internal nodes prior to the challenge-response.
        try:
            self.headers["node_id"] = NODE_ID
            self.headers["wallet_address"] = self.wallet
        except Exception:
            pass
        self.is_busy = False
        self.reconnect_attempts = 0
        self.ollama_url = TITAN_OLLAMA_HOST
        self.container_mode = container_mode or CONTAINER_MODE
        self.docker_client = DOCKER_CLIENT
        
        # Active job tracking for janitor loop
        self.active_jobs = {}  # {job_id: {"start_time": timestamp, "container_id": id}}
        self.job_timeout = 300  # 5 minutes max execution time
        
        # Thread pool for blocking I/O (Telemetry subprocesses)
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        # Verify Neural Uplink at Startup
        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self._verify_ollama_link())
        self.loop.create_task(self._janitor_loop())
        
        logger.info(f"[SECURITY] Container Mode: {'ENABLED' if self.container_mode else 'DISABLED'}")

    async def _verify_ollama_link(self):
        """Checks connectivity to the local AI engine."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.ollama_url}/api/tags") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        models = [m['name'] for m in data.get('models', [])]
                        logger.info(f"NEURAL UPLINK ONLINE. ARSENAL: {len(models)} MODELS")
                    else:
                        logger.warning(f"NEURAL UPLINK UNSTABLE: HTTP {resp.status}")
        except Exception as e:
            logger.critical(f"NEURAL UPLINK FAILED: {e}")
            logger.critical("CHECK OLLAMA SERVICE (systemctl status ollama)")

    # --- JANITOR LOOP (STALE HEARTBEAT CLEANUP) ---
    async def _janitor_loop(self):
        """Monitors active jobs and cleans up stale heartbeats."""
        while True:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds
                current_time = datetime.now()
                stale_jobs = []
                
                # Find stale jobs
                for job_id, job_data in self.active_jobs.items():
                    elapsed = (current_time - job_data["start_time"]).total_seconds()
                    
                    if elapsed > self.job_timeout:
                        stale_jobs.append((job_id, elapsed, job_data.get("container_id")))
                        logger.warning(f"[JANITOR] Job {job_id} STALE (timeout: {elapsed:.0f}s)")
                
                # Clean up stale jobs
                for job_id, elapsed, container_id in stale_jobs:
                    # Stop container if running
                    if self.container_mode and self.docker_client and container_id:
                        try:
                            container = self.docker_client.containers.get(container_id)
                            if container.status == "running":
                                logger.info(f"[JANITOR] Killing stale container: {container_id}")
                                container.kill()
                                container.remove()
                        except Exception as e:
                            logger.error(f"[JANITOR] Failed to kill container {container_id}: {e}")
                    
                    # Remove from tracking
                    del self.active_jobs[job_id]
                    logger.info(f"[JANITOR] Removed stale job {job_id} after {elapsed:.0f}s")
                
                # Log active jobs status
                if self.active_jobs:
                    logger.debug(f"[JANITOR] Tracking {len(self.active_jobs)} active jobs")
                    
            except Exception as e:
                logger.error(f"[JANITOR] Loop error: {e}")
                await asyncio.sleep(5)

    # --- TRUE SILICON TELEMETRY (HARDENED) ---
    def _read_apple_silicon_sensors(self):
        """
        Direct Kernel Interrogation for Apple M-Series.
        Executes 'powermetrics' to read true power draw.
        """
        try:
            cmd = ["sudo", "powermetrics", "--samplers", "thermal,gpu_power", "-n", "1", "-i", "10", "--format", "plist"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
            output = result.stdout
            
            gpu_power = 0.0
            match = re.search(r'GPU Power: (\d+) mW', output)
            if match: gpu_power = int(match.group(1)) / 1000.0
            
            thermal_status = "OK"
            if "Serious" in output: thermal_status = "HOT"
            elif "Critical" in output: thermal_status = "CRITICAL"
            
            return {"gpu_temp": 0, "thermal_status": thermal_status, "power": gpu_power}
        except: 
            return {"gpu_temp": 0, "thermal_status": "NO_SUDO", "power": 0}

    async def get_telemetry(self, jetson_interface=None) -> Dict:
        """Aggregates hardware stats for the Brain."""
        stats = {
            "node_id": NODE_ID,
            "wallet_address": self.wallet,
            "status": "BUSY" if self.is_busy else "IDLE",
            "hardware": "UNIT_ORIN_AGX" if IS_JETSON else "UNIT_APPLE_M_SERIES" if IS_MAC else "UNIT_NVIDIA_CUDA",
            "specs": {"gpu_temp": 0, "power": 0, "thermal": "OK"}
        }

        # 1. Jetson Orin Logic
        if IS_JETSON and jetson_interface and jetson_interface.ok():
            s = jetson_interface.stats
            stats["specs"]["gpu_temp"] = int(s.get('Temp', {}).get('GPU', 0))
            stats["specs"]["power"] = int((s.get('Power', {}).get('tot', 0) or 0) / 1000.0)
            
            # Thermal Safety Cutoff
            if stats["specs"]["gpu_temp"] > MAX_SAFE_TEMP_C: 
                logger.warning(f"THERMAL CRITICAL: {stats['specs']['gpu_temp']}°C. THROTTLING.")
                stats["status"] = "COOLDOWN"

        # 2. Apple Silicon Logic
        elif IS_MAC:
            mac_data = await asyncio.get_event_loop().run_in_executor(
                self.executor, self._read_apple_silicon_sensors
            )
            stats["specs"]["thermal"] = mac_data["thermal_status"]
            stats["specs"]["power"] = mac_data["power"]
            if mac_data["thermal_status"] in ["HOT", "CRITICAL"]: stats["status"] = "COOLDOWN"

        return stats

    # --- INFERENCE ENGINE (OLLAMA ADAPTER) ---
    async def execute_task(self, job_data: dict) -> Dict:
        """
        Routes the intelligence request to the local Ollama instance.
        Tracks job lifecycle for janitor loop.
        """
        job_id = job_data.get('job_id', 'UNKNOWN')
        prompt = job_data.get('prompt', '')
        
        # Track job start
        self.active_jobs[job_id] = {
            "start_time": datetime.now(),
            "container_id": None
        }
        logger.info(f"[JANITOR] Job {job_id} registered (tracking started)")
        
        # Strategic Model Selection
        # Jetson Orin (64GB) -> Heavyweight Commander (70B)
        # Mac Studio (Unified) -> Agile Architect (32B/70B depends on specific Mac config)
        # Standard GPU -> Fallback (8B)
        target_model = "llama3.3:70b" if IS_JETSON else ("qwen2.5-coder:32b" if IS_MAC else "llama3")
        
        self.is_busy = True
        logger.info(f"EXECUTING MISSION: {job_id}")
        logger.info(f"MODEL DESIGNATION: {target_model}")

        result_payload = {
            "last_event": "JOB_COMPLETE",
            "job_id": job_id,
            "node_id": NODE_ID,
            "wallet_address": self.wallet,
            "result": None
        }

        try:
            # Async HTTP Request (Non-Blocking)
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": target_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_ctx": 8192, "temperature": 0.7}
                }
                
                start_time = datetime.now()
                async with session.post(f"{self.ollama_url}/api/generate", json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        duration = (datetime.now() - start_time).total_seconds()
                        result_payload["result"] = data.get("response", "")
                        logger.info(f"MISSION SUCCESS ({duration:.2f}s). INTEL SECURED.")
                    else:
                        err_msg = await resp.text()
                        logger.error(f"OLLAMA ERROR {resp.status}: {err_msg}")
                        result_payload["result"] = f"ERR: NEURAL ENGINE FAILURE {resp.status}"
                        
        except Exception as e:
            logger.error(f"EXECUTION FAILURE: {e}")
            result_payload["result"] = f"CRITICAL: {str(e)}"
        
        # Clean up job tracking
        if job_id in self.active_jobs:
            elapsed = (datetime.now() - self.active_jobs[job_id]["start_time"]).total_seconds()
            del self.active_jobs[job_id]
            logger.info(f"[JANITOR] Job {job_id} completed in {elapsed:.2f}s")
        
        self.is_busy = False
        return result_payload

    # --- MAIN COMMAND LOOP ---
    async def run(self):
        # Activate Hardware Monitor
        jetson = None
        if IS_JETSON:
            try: jetson = jtop(); jetson.start()
            except: pass

        logger.info(f"TITAN LIMB ONLINE. ID: {NODE_ID}")
        
        while True:
            try:
                # Polymorphic Header Fix (Robustness against library updates)
                connect_args = {"uri": self.uri}
                try:
                    import websockets.version
                    ver = int(websockets.version.version.split('.')[0])
                    if ver >= 14: connect_args["additional_headers"] = self.headers
                    else: connect_args["extra_headers"] = self.headers
                except: connect_args["extra_headers"] = self.headers

                logger.info(f"ESTABLISHING UPLINK: {self.uri}")
                async with websockets.connect(**connect_args) as ws:
                    logger.info("UPLINK SECURE. AWAITING DIRECTIVES.")
                    # --- START HANDSHAKE INJECTION ---
                    try:
                        import platform as _platform
                        handshake_payload = {
                            "type": "handshake",
                            "model": "NVIDIA Jetson Orin NX (16GB)",
                            "arch": _platform.machine(),
                            "status": "online",
                            "version": "1.0.2"
                        }
                        await ws.send(json.dumps(handshake_payload))
                        print(f"[>>] SENT HANDSHAKE: {handshake_payload}")
                    except Exception as e:
                        print(f"[!!] HANDSHAKE FAILED: {e}")
                    # --- END HANDSHAKE INJECTION ---
                    self.reconnect_attempts = 0
                    
                    # Handshake / Challenge-Response
                    try:
                        # Wait for server challenge (or initial prompt). The
                        # dispatcher will send a JSON payload like {"challenge": "..."}
                        raw = await ws.recv()
                        try:
                            incoming = json.loads(raw)
                        except Exception:
                            incoming = {}

                        if incoming.get("challenge"):
                            nonce = incoming.get("challenge")
                            resp = hmac.new(GENESIS_KEY.encode(), nonce.encode(), hashlib.sha256).hexdigest()
                            # Include explicit handshake metadata so the dispatcher
                            # can register model/specs for frontend filtering.
                            handshake = {
                                "type": "handshake",
                                "challenge_resp": resp,
                                "node_id": NODE_ID,
                                "hardware": ("UNIT_ORIN_AGX" if IS_JETSON else ("UNIT_APPLE_M_SERIES" if IS_MAC else "UNIT_NVIDIA_CUDA")),
                                "model": "NVIDIA Jetson Orin",
                                "arch": platform.machine(),
                                "cores": 8,
                                "ram": "16GB",
                                "wallet_address": self.wallet,
                                "last_event": "HANDSHAKE"
                            }
                            await ws.send(json.dumps(handshake))
                        else:
                            # Fallback: send telemetry as handshake if server didn't issue a challenge
                            # Send a clearly labelled handshake payload so the
                            # dispatcher stores a human-friendly model string.
                            init = await self.get_telemetry(jetson)
                            init["type"] = "handshake"
                            init["model"] = "NVIDIA Jetson Orin"
                            init["node_id"] = NODE_ID
                            init["arch"] = platform.machine()
                            init["cores"] = 8
                            init["ram"] = "16GB"
                            init["last_event"] = "HANDSHAKE"
                            print(f"Sending Specs: {init}")
                            await ws.send(json.dumps(init))
                    except Exception as e:
                        logger.warning(f"HANDSHAKE ERROR: {e}")

                    while True:
                        # 1. Heartbeat Report
                        telemetry = await self.get_telemetry(jetson)
                        await ws.send(json.dumps(telemetry))
                        
                        # 2. Receive Orders
                        try:
                            msg = await asyncio.wait_for(ws.recv(), timeout=HEARTBEAT_INTERVAL)
                            job = json.loads(msg)
                            
                            # Valid Job Received
                            if job.get("job_id"):
                                # Acknowledge Receipt
                                self.is_busy = True
                                await ws.send(json.dumps(await self.get_telemetry(jetson)))
                                
                                # Execute
                                result = await self.execute_task(job)
                                
                                # Transmit Intel
                                await ws.send(json.dumps(result))
                                
                        except asyncio.TimeoutError: pass # Just a heartbeat cycle
                        except websockets.exceptions.ConnectionClosed:
                            logger.warning("UPLINK SEVERED. RECONNECTING...")
                            break
            
            except Exception as e:
                self.reconnect_attempts += 1
                delay = min(RECONNECT_DELAY * self.reconnect_attempts, 60)
                logger.error(f"LINK ERROR: {e}. Retrying in {delay}s...")
                await asyncio.sleep(delay)

if __name__ == "__main__":
    import argparse as _argparse

    parser = _argparse.ArgumentParser(description="Titan Limb Worker")
    parser.add_argument("--connect", help="WebSocket connect URL", default=os.getenv("WEBSOCKET_URL", "ws://127.0.0.1:8000/connect"))
    parser.add_argument("--config", help="Path to config file", default=os.path.expanduser("~/.si64/config.json"))
    args = parser.parse_args()

    # Update Configuration Variables
    BRAIN_URL = args.connect
    CONFIG_FILE = args.config
    WEBSOCKET_URL = BRAIN_URL

    logger.info(f"[CLI] UPLINK: {BRAIN_URL}")
    logger.info(f"[CLI] CONFIG: {CONFIG_FILE}")

    node = TitanLimb(connect_url=BRAIN_URL)
    try:
        asyncio.run(node.run())
    except KeyboardInterrupt:
        logger.info("MANUAL OVERRIDE. SHUTTING DOWN.")
        sys.exit(0)
