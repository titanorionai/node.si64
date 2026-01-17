import asyncio
import websockets
import json
import logging
import os
import sys
import platform
import subprocess
import random
from datetime import datetime
from typing import Dict, Optional, Union

# --- CONFIGURATION IMPORT ---
# Dynamically add the parent directory to path to locate titan_config.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from titan_config import *
except ImportError:
    # Emergency Defaults for Standalone Deployment
    print("WARNING: Config module missing. Loading Emergency Protocol Defaults.")
    GENESIS_KEY = "TITAN_DEBUG_KEY"
    DISPATCHER_IP = "127.0.0.1"
    DISPATCHER_PORT = 8000
    WEBSOCKET_URL = f"ws://{DISPATCHER_IP}:{DISPATCHER_PORT}/connect"
    MAX_SAFE_TEMP_C = 85
    SCRIPTS_DIR = "./scripts"
    WAREHOUSE_PATH = "/mnt/warehouse"
    HEARTBEAT_INTERVAL = 1.0
    RECONNECT_DELAY = 5

# --- WALLET IDENTITY ---
# Critical for Settlement Layer. Ensure this is set in your environment.
WALLET_ADDRESS = "FpFtUESU6Rvy7uS85sLDg7iayjczrsFNJa4Q2dFV8z6q"

# --- ARCHITECTURE GATING (THE BOUNCER) ---
# Titan Protocol is optimized for Unified Memory. Legacy x86 hardware is rejected.
ARCH = platform.machine().lower()
SYSTEM = platform.system().lower()

VALID_ARCHS = ['aarch64', 'arm64']

if ARCH not in VALID_ARCHS:
    print(f"CRITICAL SYSTEM ERROR: Unsupported Architecture Detected: {ARCH}")
    print("PROTOCOL MANDATE: Titan Network is exclusively for ARM64 Unified Memory devices.")
    print("x86_64/AMD64 nodes are not permitted on this layer.")
    sys.exit(1)

# --- HARDWARE ABSTRACTION LAYER ---
IS_JETSON = False
IS_MAC = False
IS_GENERIC_ARM = False

# 1. Check for NVIDIA Jetson
try:
    from jtop import jtop
    IS_JETSON = True
except ImportError:
    # 2. Check for Apple Silicon
    if SYSTEM == 'darwin' and ARCH == 'arm64':
        IS_MAC = True
    else:
        # 3. Fallback to Generic ARM (e.g. RPi 5, RockChip)
        IS_GENERIC_ARM = True

# --- LOGGING CONFIGURATION ---
LOG_FORMAT = "%(asctime)s | %(levelname)s | [%(name)s] | %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("titan_limb.log")
    ]
)

# Set Logger Identity based on Hardware
if IS_JETSON:
    LOGGER_NAME = "TITAN_LIMB_ORIN"
elif IS_MAC:
    LOGGER_NAME = "TITAN_LIMB_APPLE"
else:
    LOGGER_NAME = "TITAN_LIMB_ARM"

logger = logging.getLogger(LOGGER_NAME)

# --- NODE IDENTITY ---
HOSTNAME = platform.node()
NODE_ID = os.getenv("NODE_ID", f"{HOSTNAME}_{LOGGER_NAME.split('_')[-1]}")

class TitanLimb:
    """
    The ARM64 Universal Worker Unit.
    Polymorphic agent capable of interfacing with NVIDIA Jetson, Apple Silicon, 
    and Generic ARM compute units.
    """
    def __init__(self):
        self.uri = WEBSOCKET_URL
        self.headers = {"x-genesis-key": GENESIS_KEY}
        self.is_busy = False
        self.current_job_id: Optional[str] = None
        self.reconnect_attempts = 0
        self.status = "BOOTING"

        # Environment Integrity Check
        if not os.path.exists(SCRIPTS_DIR):
            logger.warning(f"SCRIPTS MISSING at {SCRIPTS_DIR}. Attempting auto-creation...")
            try:
                os.makedirs(SCRIPTS_DIR, exist_ok=True)
            except OSError as e:
                logger.critical(f"FILESYSTEM ERROR: {e}")

    async def get_telemetry(self, jetson_interface=None) -> Dict:
        """
        Polymorphic Telemetry Reader.
        Adaptively reads sensors based on the underlying silicon.
        """
        stats = {
            "node_id": NODE_ID,
            "wallet_address": WALLET_ADDRESS,
            "arch": "ARM64",
            "platform": SYSTEM,
            "status": "BUSY" if self.is_busy else "IDLE",
            "timestamp": str(datetime.now()),
            "specs": {
                "vram_percent": 0,
                "gpu_temp_c": 0,
                "power_watts": 0,
                "uptime": str(datetime.now())
            }
        }

        # --- MODE 1: NVIDIA JETSON (ORIN/XAVIER) ---
        if IS_JETSON and jetson_interface and jetson_interface.ok():
            try:
                s = jetson_interface.stats
                stats["specs"]["vram_percent"] = int(s.get('RAM', 0))
                # Grab GPU temp specifically
                stats["specs"]["gpu_temp_c"] = int(s.get('Temp', {}).get('GPU', 0))
                # Convert mW to W
                stats["specs"]["power_watts"] = int((s.get('Power', {}).get('tot', 0) or 0) / 1000.0)
            except Exception as e:
                logger.warning(f"Telemetry Read Error (Jetson): {e}")

        # --- MODE 2: APPLE SILICON (M1/M2/M3) ---
        elif IS_MAC:
            try:
                # We use psutil for memory. 
                # Note: Reading Power/Temp on Mac requires 'powermetrics' (sudo) or Objective-C bridges.
                # For v1.0 reliability, we use safe heuristics or psutil data where possible.
                import psutil
                mem = psutil.virtual_memory()
                stats["specs"]["vram_percent"] = int(mem.percent) # Unified Memory = System RAM
                
                # Heuristics for safe operation without sudo
                stats["specs"]["gpu_temp_c"] = 45 # Nominal Baseline
                stats["specs"]["power_watts"] = 15 # Idle Estimate M-Series
            except ImportError:
                logger.error("Dependency Missing: 'psutil'. Install via pip.")

        # --- MODE 3: GENERIC ARM (RPi 5 / RockChip) ---
        else:
            try:
                import psutil
                stats["specs"]["vram_percent"] = int(psutil.virtual_memory().percent)
                
                # Try standard Linux thermal zone reading
                if os.path.exists("/sys/class/thermal/thermal_zone0/temp"):
                    with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                        # Value is usually in millidegrees
                        stats["specs"]["gpu_temp_c"] = int(int(f.read().strip()) / 1000)
                else:
                    stats["specs"]["gpu_temp_c"] = 50 # Safe Fallback
                    
                stats["specs"]["power_watts"] = 5 # Passive RPi estimate
            except Exception:
                pass

        # --- THERMAL SAFETY PROTOCOL ---
        if stats["specs"]["gpu_temp_c"] > MAX_SAFE_TEMP_C:
            logger.warning(f"THERMAL CRITICAL: GPU @ {stats['specs']['gpu_temp_c']}C. Engaging COOLDOWN.")
            self.status = "COOLDOWN"
            stats["status"] = "COOLDOWN"
        else:
            self.status = stats["status"]

        return stats

    async def execute_task(self, job_data: dict) -> bool:
        """
        Executes the AI Payload via Shell Wrapper.
        Supports ZSH (Mac) and BASH (Linux).
        """
        job_id = job_data.get('job_id', 'UNKNOWN')
        job_type = job_data.get('type', 'UNKNOWN')
        prompt = job_data.get('prompt', '')

        self.is_busy = True
        self.current_job_id = job_id
        
        logger.info(f"MISSION ACCEPTED: Job {job_id} [{job_type}]")
        logger.info(f"PAYLOAD: {prompt[:50]}...")

        executor_script = os.path.join(SCRIPTS_DIR, "execute_task.sh")
        output_file = os.path.join(WAREHOUSE_PATH, f"{job_id}.json")

        # Select Shell based on OS
        shell_cmd = "zsh" if IS_MAC else "bash"

        if not os.path.exists(executor_script):
            logger.error(f"CRITICAL: Executor script missing at {executor_script}")
            self.is_busy = False
            return False

        # Build Command
        cmd = [
            shell_cmd, executor_script, 
            "--type", job_type, 
            "--prompt", prompt, 
            "--out", output_file
        ]

        start_time = datetime.now()

        try:
            # Atomic Subprocess Execution
            process = await asyncio.create_subprocess_exec(
                *cmd, 
                stdout=asyncio.subprocess.PIPE, 
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            duration = (datetime.now() - start_time).total_seconds()

            if process.returncode == 0:
                logger.info(f"MISSION SUCCESS: Job {job_id} finished in {duration:.2f}s")
                self.is_busy = False
                # Note: current_job_id is cleared after the final telemetry report
                return True
            else:
                logger.error(f"MISSION FAILED: Job {job_id} (Exit {process.returncode})")
                logger.error(f"STDERR: {stderr.decode().strip()}")
                self.is_busy = False
                return False

        except Exception as e:
            logger.critical(f"EXECUTION ENGINE FAILURE: {e}")
            self.is_busy = False
            return False

    async def run(self):
        """
        Main Event Loop.
        Manages Lifecycle: Connection -> Handshake -> Heartbeat -> Execution -> Reporting.
        """
        # --- CONTEXT INITIALIZATION ---
        jetson_context = None
        if IS_JETSON:
            try:
                from jtop import jtop
                jetson_context = jtop()
                jetson_context.start()
                if not jetson_context.ok():
                    logger.warning("Jetson Service (jtop) not fully responsive.")
            except Exception as e:
                logger.error(f"Jetson Context Init Failed: {e}")

        logger.info(f"TITAN LIMB ONLINE. ID: {NODE_ID} | Arch: {ARCH} | OS: {SYSTEM}")
        
        # --- RECONNECTION LOOP ---
        while True:
            try:
                logger.info(f"Establishing Uplink to Cortex: {self.uri}")
                
                async with websockets.connect(self.uri, extra_headers=self.headers) as ws:
                    logger.info("UPLINK ESTABLISHED. Awaiting Orders.")
                    self.reconnect_attempts = 0 # Reset on success

                    # 1. Handshake (Identify Hardware to Brain)
                    handshake_data = await self.get_telemetry(jetson_context)
                    await ws.send(json.dumps(handshake_data))

                    # 2. Command Loop
                    while True:
                        # A. Gather Telemetry
                        telemetry = await self.get_telemetry(jetson_context)
                        
                        # B. Check for Job Completion Signal
                        if not self.is_busy and self.current_job_id:
                            telemetry["last_event"] = "JOB_COMPLETE"
                            telemetry["job_id"] = self.current_job_id
                            # Clear ID only after queuing the report
                            self.current_job_id = None

                        # C. Send Heartbeat
                        await ws.send(json.dumps(telemetry))

                        # D. Listen (Blocking wait for 'HEARTBEAT_INTERVAL')
                        try:
                            msg = await asyncio.wait_for(ws.recv(), timeout=HEARTBEAT_INTERVAL)
                            job_data = json.loads(msg)
                            
                            # E. Immediate Acknowledgement
                            self.is_busy = True
                            telemetry["status"] = "BUSY"
                            await ws.send(json.dumps(telemetry))
                            
                            # F. Execution
                            await self.execute_task(job_data)
                            
                        except asyncio.TimeoutError:
                            # Normal operation: No jobs received this tick.
                            pass
                        except websockets.exceptions.ConnectionClosed:
                            logger.warning("Uplink severed by Cortex.")
                            break

            except Exception as e:
                self.reconnect_attempts += 1
                # Smart Backoff: 5s, 10s, 15s... max 60s
                delay = min(RECONNECT_DELAY * self.reconnect_attempts, 60)
                
                logger.error(f"Connection Failure: {e}")
                logger.info(f"Survival Mode: Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
            
            finally:
                # Cleanup logic if loop breaks cleanly
                pass

if __name__ == "__main__":
    try:
        asyncio.run(TitanLimb().run())
    except KeyboardInterrupt:
        logger.info("MANUAL OVERRIDE: Shutting down Titan Limb.")
        # Cleanup Jetson Context if exists
        if IS_JETSON and 'jetson_context' in locals() and jetson_context:
            jetson_context.close()
        sys.exit(0)
