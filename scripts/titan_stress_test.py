#!/usr/bin/env python3
"""
TITAN ORDNANCE DELIVERY SYSTEM v2.0
===================================
CLASSIFICATION: UNCLASSIFIED // INTERNAL TRAINING
MISSION: SUSTAINED LOAD GENERATION (80% CAPACITY)
TARGET: LOCALHOST BRAIN API
"""

import os
import requests
import time
import random
import sys
import statistics
import argparse
from concurrent.futures import ThreadPoolExecutor
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime

# --- [ TACTICAL CONFIGURATION ] ---
# Prefer environment variables so we can safely switch between
# local and live targets without editing the script.
TARGET_URL = os.getenv("TITAN_STRESS_TARGET", "https://si64.net/submit_job")
GENESIS_KEY = os.getenv("TITAN_GENESIS_KEY", "TITAN_GENESIS_KEY_V1_SECURE")

# LOAD PARAMETERS
CONCURRENCY_LEVEL = 8       # Number of simultaneous "users"
TARGET_JPS = 5.0            # Target Jobs Per Second (80% of est. max capacity)
BATCH_SIZE = 10             # How many rounds to fire per volley

# TELEMETRY COLORS
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    WARN = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# --- [ ORDNANCE PACKAGES ] ---
# Payloads calibrated for 80% stress. 
# HEAVY payloads are excluded to prevent thermal runaway.
SAFE_PAYLOADS = [
    {
        "type": "LLM_INFERENCE_INT8", 
        "prompt": "Analyze market liquidity depth (Standard)",
        "complexity": "MEDIUM",
        "weight": 0.6
    },
    {
        "type": "LLM_INFERENCE_4BIT",
        "prompt": "Render 3D asset metadata block (Pro)",
        "complexity": "HIGH",
        "weight": 0.4
    }
]

# --- [ GLOBAL TELEMETRY ] ---
STATS = {
    "sent": 0,
    "success": 0,
    "failed": 0,
    "latencies": []
}

def create_session():
    """Builds a high-performance connection pool."""
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(pool_connections=CONCURRENCY_LEVEL, pool_maxsize=CONCURRENCY_LEVEL, max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

# Initialize Global Session
CMD_SESSION = create_session()

def fire_mission(mission_id):
    """Executes a single ordnance delivery task."""
    try:
        # 1. Select Payload based on weight
        task = random.choices(SAFE_PAYLOADS, weights=[p['weight'] for p in SAFE_PAYLOADS], k=1)[0]
        
        # 2. Assign Bounty (Simulation of market rate)
        bounty = round(random.uniform(0.002, 0.005), 4)

        payload = {
            "type": task["type"],
            "prompt": f"{task['prompt']} [SRT-{mission_id}]",
            "bounty": bounty
        }
        
        headers = {
            "x-genesis-key": GENESIS_KEY, 
            "Content-Type": "application/json",
            "User-Agent": "TITAN_LOAD_GENERATOR/2.0"
        }
        
        # 3. Engage
        start_t = time.perf_counter()
        resp = CMD_SESSION.post(TARGET_URL, json=payload, headers=headers, timeout=5)
        end_t = time.perf_counter()
        
        latency = (end_t - start_t) * 1000 # ms

        # 4. Report
        if resp.status_code == 200:
            return True, latency, resp.status_code
        else:
            return False, latency, resp.status_code

    except Exception as e:
        return False, 0.0, str(e)

def print_telemetry():
    """Displays live Battle Damage Assessment (BDA)."""
    if not STATS["latencies"]: return
    
    avg_lat = statistics.mean(STATS["latencies"])
    p95_lat = statistics.quantiles(STATS["latencies"], n=20)[18] # 95th percentile
    success_rate = (STATS["success"] / STATS["sent"]) * 100 if STATS["sent"] else 0
    
    print(f"\r{Colors.BLUE}>> STATS: {STATS['sent']} Jobs | {success_rate:.1f}% OK | Avg: {avg_lat:.0f}ms | P95: {p95_lat:.0f}ms{Colors.ENDC}", end="")

def run_stress_test():
    print(f"{Colors.HEADER}{Colors.BOLD}")
    print("/// TITAN ORDNANCE DELIVERY SYSTEM v2.0 ///")
    print(f"/// TARGET: {TARGET_URL}")
    print(f"/// INTENSITY: {TARGET_JPS} JPS (Jobs Per Sec)")
    print(f"/// CONCURRENCY: {CONCURRENCY_LEVEL} Threads")
    print(f"==========================================={Colors.ENDC}")

    mission_counter = 0
    
    try:
        with ThreadPoolExecutor(max_workers=CONCURRENCY_LEVEL) as executor:
            while True:
                batch_start = time.perf_counter()
                futures = []
                
                # Fire Volley
                for _ in range(BATCH_SIZE):
                    mission_counter += 1
                    STATS["sent"] += 1
                    futures.append(executor.submit(fire_mission, mission_counter))
                
                # Await Impact
                for f in futures:
                    success, lat, code = f.result()
                    if success:
                        STATS["success"] += 1
                        STATS["latencies"].append(lat)
                        # Keep memory usage low
                        if len(STATS["latencies"]) > 1000: STATS["latencies"].pop(0)
                    else:
                        STATS["failed"] += 1
                        print(f"\n{Colors.FAIL}FAILURE: {code}{Colors.ENDC}")

                print_telemetry()

                # Adaptive Cool-down (Rate Limiting)
                # If we fired 10 jobs, and want 5 JPS, this batch should take 2.0 seconds total.
                # If it took 0.5s to fire, we sleep for 1.5s.
                batch_duration = time.perf_counter() - batch_start
                target_duration = BATCH_SIZE / TARGET_JPS
                
                sleep_time = target_duration - batch_duration
                if sleep_time > 0:
                    time.sleep(sleep_time)

    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARN}CEASE FIRE. MISSION TERMINATED.{Colors.ENDC}")
        print(f"Final Report: {STATS['success']}/{STATS['sent']} Successful Missions.")
        sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Titan Network sustained load generator")
    parser.add_argument("--target", "-t", help="Override target URL (defaults to TITAN_STRESS_TARGET or si64.net)")
    parser.add_argument("--concurrency", "-c", type=int, default=CONCURRENCY_LEVEL, help="Number of concurrent threads")
    parser.add_argument("--jps", type=float, default=TARGET_JPS, help="Target jobs per second")
    parser.add_argument("--batch-size", "-b", type=int, default=BATCH_SIZE, help="Jobs per volley batch")

    args = parser.parse_args()

    if args.target:
        TARGET_URL = args.target
    CONCURRENCY_LEVEL = max(1, args.concurrency)
    TARGET_JPS = max(0.1, args.jps)
    BATCH_SIZE = max(1, args.batch_size)

    # Rebuild session to honor updated concurrency
    CMD_SESSION = create_session()

    run_stress_test()
