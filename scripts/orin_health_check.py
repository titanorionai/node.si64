#!/usr/bin/env python3
"""
Automated Orin Worker Health Check & Restart
Checks backend, Redis, and Orin connection. Restarts as needed.
"""
import subprocess
import time
import requests
import sys

BACKEND_URL = "http://127.0.0.1:8000/api/stats"
REDIS_SERVICE = "redis-server"
DISPATCHER_SERVICE = "si64-genesis.service"
ORIN_WORKER_CMD = [sys.executable, "core/limb/worker_node.py"]

CHECK_INTERVAL = 10  # seconds


def check_backend():
    try:
        resp = requests.get(BACKEND_URL, timeout=2)
        return resp.ok
    except Exception:
        return False

def check_redis():
    try:
        result = subprocess.run(["systemctl", "is-active", REDIS_SERVICE], capture_output=True, text=True)
        return result.stdout.strip() == "active"
    except Exception:
        return False

def check_orin_connected():
    try:
        resp = requests.get(BACKEND_URL, timeout=2)
        data = resp.json()
        # Check for Orin in fleet/devices
        return (data.get("fleet_size", 0) > 0) or ("ORIN" in str(data))
    except Exception:
        return False

def restart_backend():
    print("[ACTION] Restarting dispatcher backend...")
    # Try non-sudo restart first
    result = subprocess.run(["systemctl", "restart", DISPATCHER_SERVICE], capture_output=True, text=True)
    if result.returncode != 0:
        print("[WARN] Dispatcher restart failed (no sudo). Skipping.")
    time.sleep(3)

def restart_redis():
    print("[ACTION] Restarting Redis...")
    result = subprocess.run(["systemctl", "restart", REDIS_SERVICE], capture_output=True, text=True)
    if result.returncode != 0:
        print("[WARN] Redis restart failed (no sudo). Skipping.")
    time.sleep(3)

def restart_orin_worker():
    print("[ACTION] Restarting Orin worker...")
    subprocess.run(["pkill", "-f", "core/limb/worker_node.py"])
    time.sleep(2)
    subprocess.Popen(ORIN_WORKER_CMD)
    time.sleep(5)

def main():
    failure_count = 0
    max_failures = 5
    backoff = CHECK_INTERVAL
    while True:
        print("[CHECK] Backend status...")
        if not check_backend():
            failure_count += 1
            restart_backend()
            if failure_count >= max_failures:
                print("[CRITICAL] Too many backend failures. Locking out for 5 minutes.")
                time.sleep(300)
                failure_count = 0
            else:
                time.sleep(backoff)
                backoff = min(backoff * 2, 300)
            continue
        print("[CHECK] Redis status...")
        if not check_redis():
            failure_count += 1
            restart_redis()
            if failure_count >= max_failures:
                print("[CRITICAL] Too many Redis failures. Locking out for 5 minutes.")
                time.sleep(300)
                failure_count = 0
            else:
                time.sleep(backoff)
                backoff = min(backoff * 2, 300)
            continue
        print("[CHECK] Orin connection...")
        if not check_orin_connected():
            failure_count += 1
            restart_orin_worker()
            if failure_count >= max_failures:
                print("[CRITICAL] Too many Orin failures. Locking out for 5 minutes.")
                time.sleep(300)
                failure_count = 0
            else:
                time.sleep(backoff)
                backoff = min(backoff * 2, 300)
        else:
            print("[OK] Orin is connected and healthy.")
            failure_count = 0
            backoff = CHECK_INTERVAL
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
