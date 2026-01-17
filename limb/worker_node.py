import asyncio
import websockets
import json
import logging
import os
import sys
import platform
import argparse
from datetime import datetime
from typing import Dict, Optional

# --- CONFIG LOADING ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from titan_config import *
except ImportError:
    GENESIS_KEY = "TITAN_GENESIS_KEY_V1_SECURE"
    WEBSOCKET_URL = "ws://127.0.0.1:8000/connect"
    MAX_SAFE_TEMP_C = 85
    SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
    WAREHOUSE_PATH = "/tmp/titan_warehouse"
    RECONNECT_DELAY = 5
    HEARTBEAT_INTERVAL = 1.0

# --- IDENTITY ---
WALLET_ADDRESS = "FpFtUESU6Rvy7uS85sLDg7iayjczrsFNJa4Q2dFV8z6q"

# --- HARDWARE ---
ARCH = platform.machine().lower()
SYSTEM = platform.system().lower()
IS_JETSON = False
IS_MAC = (SYSTEM == 'darwin' and ARCH == 'arm64')

try:
    from jtop import jtop
    IS_JETSON = True
except ImportError:
    pass

# --- LOGGING ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
LOGGER_NAME = "TITAN_LIMB_ORIN" if IS_JETSON else "TITAN_LIMB_GENERIC"
logger = logging.getLogger(LOGGER_NAME)
NODE_ID = f"{platform.node()}_{LOGGER_NAME.split('_')[-1]}"

class TitanLimb:
    def __init__(self, connect_url=None):
        self.uri = connect_url if connect_url else WEBSOCKET_URL
        self.headers = {"x-genesis-key": GENESIS_KEY}
        self.is_busy = False
        self.current_job_id: Optional[str] = None
        self.reconnect_attempts = 0
        os.makedirs(SCRIPTS_DIR, exist_ok=True)
        os.makedirs(WAREHOUSE_PATH, exist_ok=True)

    async def get_telemetry(self, jetson_interface=None) -> Dict:
        stats = {
            "node_id": NODE_ID, "wallet_address": WALLET_ADDRESS,
            "status": "BUSY" if self.is_busy else "IDLE",
            "specs": {"gpu_temp_c": 0, "power_watts": 0}
        }
        if IS_JETSON and jetson_interface and jetson_interface.ok():
            s = jetson_interface.stats
            stats["specs"]["gpu_temp_c"] = int(s.get('Temp', {}).get('GPU', 0))
            stats["specs"]["power_watts"] = int((s.get('Power', {}).get('tot', 0) or 0) / 1000.0)
        
        if stats["specs"]["gpu_temp_c"] > MAX_SAFE_TEMP_C:
            stats["status"] = "COOLDOWN"
        return stats

    async def execute_task(self, job_data: dict) -> bool:
        job_id = job_data.get('job_id', 'UNKNOWN')
        job_type = job_data.get('type', 'UNKNOWN')
        prompt = job_data.get('prompt', '')
        self.is_busy = True
        self.current_job_id = job_id
        
        logger.info(f"MISSION ACCEPTED: Job {job_id} [{job_type}]")
        executor = os.path.join(SCRIPTS_DIR, "execute_task.sh")
        outfile = os.path.join(WAREHOUSE_PATH, f"{job_id}.json")
        shell_cmd = "zsh" if IS_MAC else "bash"

        try:
            cmd = [shell_cmd, executor, "--type", job_type, "--prompt", prompt, "--out", outfile]
            process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            _, stderr = await process.communicate()

            if process.returncode == 0:
                logger.info(f"MISSION SUCCESS: Job {job_id}")
                self.is_busy = False
                return True
            else:
                logger.error(f"MISSION FAILED: {stderr.decode()}")
                self.is_busy = False
                return False
        except Exception as e:
            logger.critical(f"EXEC ERROR: {e}")
            self.is_busy = False
            return False

    async def run(self):
        jetson_context = None
        if IS_JETSON:
            try:
                jetson_context = jtop()
                jetson_context.start()
            except: pass

        logger.info(f"TITAN LIMB ONLINE. ID: {NODE_ID}")

        while True:
            try:
                logger.info(f"Connecting to: {self.uri}")
                
                # --- FIX: Library Version Detection ---
                connect_args = {"uri": self.uri}
                try:
                    import websockets.version
                    ver = int(websockets.version.version.split('.')[0])
                    if ver >= 14: connect_args["additional_headers"] = self.headers
                    else: connect_args["extra_headers"] = self.headers
                except:
                    connect_args["extra_headers"] = self.headers

                async with websockets.connect(**connect_args) as ws:
                    logger.info("UPLINK ESTABLISHED.")
                    self.reconnect_attempts = 0
                    await ws.send(json.dumps(await self.get_telemetry(jetson_context)))

                    while True:
                        telemetry = await self.get_telemetry(jetson_context)
                        if not self.is_busy and self.current_job_id:
                            telemetry["last_event"] = "JOB_COMPLETE"
                            telemetry["job_id"] = self.current_job_id
                            self.current_job_id = None
                        
                        await ws.send(json.dumps(telemetry))

                        try:
                            msg = await asyncio.wait_for(ws.recv(), timeout=HEARTBEAT_INTERVAL)
                            try:
                                job = json.loads(msg)
                            except Exception:
                                logger.debug("Received non-json message, ignoring")
                                continue

                            # Validate message is a real job payload
                            if not isinstance(job, dict) or 'job_id' not in job or 'type' not in job:
                                logger.debug("Ignoring non-job message from dispatcher")
                                continue
                            # Ignore ACK or control messages
                            if job.get('type') == 'ACK_JOB':
                                logger.debug("Ignoring ACK_JOB message")
                                continue

                            self.is_busy = True
                            telemetry["status"] = "BUSY"
                            await ws.send(json.dumps(telemetry))
                            await self.execute_task(job)
                        except asyncio.TimeoutError: pass
                        except websockets.exceptions.ConnectionClosed: break

            except Exception as e:
                self.reconnect_attempts += 1
                delay = min(RECONNECT_DELAY * self.reconnect_attempts, 60)
                logger.error(f"Connection Lost: {e}. Retry in {delay}s...")
                await asyncio.sleep(delay)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--connect", default=None)
    args = parser.parse_args()
    try: asyncio.run(TitanLimb(args.connect).run())
    except KeyboardInterrupt: sys.exit(0)
import asyncio
import websockets
import json
import logging
import os
import sys
import platform
import argparse
from datetime import datetime
from typing import Dict, Optional

# --- CONFIG LOADING ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from titan_config import *
except ImportError:
    GENESIS_KEY = "TITAN_GENESIS_KEY_V1_SECURE"
    WEBSOCKET_URL = "ws://127.0.0.1:8000/connect"
    MAX_SAFE_TEMP_C = 85
    SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
    WAREHOUSE_PATH = "/tmp/titan_warehouse"
    RECONNECT_DELAY = 5
    HEARTBEAT_INTERVAL = 1.0

# --- IDENTITY ---
WALLET_ADDRESS = "FpFtUESU6Rvy7uS85sLDg7iayjczrsFNJa4Q2dFV8z6q"

# --- HARDWARE ---
ARCH = platform.machine().lower()
SYSTEM = platform.system().lower()
IS_JETSON = False
IS_MAC = (SYSTEM == 'darwin' and ARCH == 'arm64')

try:
    from jtop import jtop
    IS_JETSON = True
except ImportError:
    pass

# --- LOGGING ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
LOGGER_NAME = "TITAN_LIMB_ORIN" if IS_JETSON else "TITAN_LIMB_GENERIC"
logger = logging.getLogger(LOGGER_NAME)
NODE_ID = f"{platform.node()}_{LOGGER_NAME.split('_')[-1]}"

class TitanLimb:
    def __init__(self, connect_url=None):
        self.uri = connect_url if connect_url else WEBSOCKET_URL
        self.headers = {"x-genesis-key": GENESIS_KEY}
        self.is_busy = False
        self.current_job_id: Optional[str] = None
        self.reconnect_attempts = 0
        os.makedirs(SCRIPTS_DIR, exist_ok=True)
        os.makedirs(WAREHOUSE_PATH, exist_ok=True)

    async def get_telemetry(self, jetson_interface=None) -> Dict:
        stats = {
            "node_id": NODE_ID, "wallet_address": WALLET_ADDRESS,
            "status": "BUSY" if self.is_busy else "IDLE",
            "specs": {"gpu_temp_c": 0, "power_watts": 0}
        }
        if IS_JETSON and jetson_interface and jetson_interface.ok():
            s = jetson_interface.stats
            stats["specs"]["gpu_temp_c"] = int(s.get('Temp', {}).get('GPU', 0))
            stats["specs"]["power_watts"] = int((s.get('Power', {}).get('tot', 0) or 0) / 1000.0)
        
        if stats["specs"]["gpu_temp_c"] > MAX_SAFE_TEMP_C:
            stats["status"] = "COOLDOWN"
        return stats

    async def execute_task(self, job_data: dict) -> bool:
        job_id = job_data.get('job_id', 'UNKNOWN')
        job_type = job_data.get('type', 'UNKNOWN')
        prompt = job_data.get('prompt', '')
        self.is_busy = True
        self.current_job_id = job_id
        
        logger.info(f"MISSION ACCEPTED: Job {job_id} [{job_type}]")
        executor = os.path.join(SCRIPTS_DIR, "execute_task.sh")
        outfile = os.path.join(WAREHOUSE_PATH, f"{job_id}.json")
        shell_cmd = "zsh" if IS_MAC else "bash"

        try:
            cmd = [shell_cmd, executor, "--type", job_type, "--prompt", prompt, "--out", outfile]
            process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            _, stderr = await process.communicate()

            if process.returncode == 0:
                logger.info(f"MISSION SUCCESS: Job {job_id}")
                self.is_busy = False
                return True
            else:
                logger.error(f"MISSION FAILED: {stderr.decode()}")
                self.is_busy = False
                return False
        except Exception as e:
            logger.critical(f"EXEC ERROR: {e}")
            self.is_busy = False
            return False

    async def run(self):
        jetson_context = None
        if IS_JETSON:
            try:
                jetson_context = jtop()
                jetson_context.start()
            except: pass

        logger.info(f"TITAN LIMB ONLINE. ID: {NODE_ID}")

        while True:
            try:
                logger.info(f"Connecting to: {self.uri}")
                
                # --- FIX: Library Version Detection ---
                connect_args = {"uri": self.uri}
                try:
                    import websockets.version
                    ver = int(websockets.version.version.split('.')[0])
                    if ver >= 14: connect_args["additional_headers"] = self.headers
                    else: connect_args["extra_headers"] = self.headers
                except:
                    connect_args["extra_headers"] = self.headers

                async with websockets.connect(**connect_args) as ws:
                    logger.info("UPLINK ESTABLISHED.")
                    self.reconnect_attempts = 0
                    await ws.send(json.dumps(await self.get_telemetry(jetson_context)))

                    while True:
                        telemetry = await self.get_telemetry(jetson_context)
                        if not self.is_busy and self.current_job_id:
                            telemetry["last_event"] = "JOB_COMPLETE"
                            telemetry["job_id"] = self.current_job_id
                            self.current_job_id = None
                        
                        await ws.send(json.dumps(telemetry))

                        try:
                            msg = await asyncio.wait_for(ws.recv(), timeout=HEARTBEAT_INTERVAL)
                            job = json.loads(msg)
                            self.is_busy = True
                            telemetry["status"] = "BUSY"
                            await ws.send(json.dumps(telemetry))
                            await self.execute_task(job)
                        except asyncio.TimeoutError: pass
                        except websockets.exceptions.ConnectionClosed: break

            except Exception as e:
                self.reconnect_attempts += 1
                delay = min(RECONNECT_DELAY * self.reconnect_attempts, 60)
                logger.error(f"Connection Lost: {e}. Retry in {delay}s...")
                await asyncio.sleep(delay)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--connect", default=None)
    args = parser.parse_args()
    try: asyncio.run(TitanLimb(args.connect).run())
    except KeyboardInterrupt: sys.exit(0)
