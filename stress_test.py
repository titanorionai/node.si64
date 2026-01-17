#!/usr/bin/env python3
import asyncio
import subprocess
import time
import os
import sys
import signal
import json
from pathlib import Path

import httpx

BASE = Path(__file__).resolve().parent
VENV_PY = BASE / 'venv' / 'bin' / 'python'
DISPATCHER_URL = 'http://127.0.0.1:8000'
GENESIS_KEY = os.environ.get('GENESIS_KEY', 'TITAN_GENESIS_KEY_V1_SECURE')

async def submit_jobs(total: int, concurrent: int = 50):
    async with httpx.AsyncClient(timeout=30.0) as client:
        sem = asyncio.Semaphore(concurrent)

        async def submit(i):
            async with sem:
                payload = {"type": "LLAMA", "prompt": f"stress test #{i}", "bounty": 0.001}
                try:
                    r = await client.post(f"{DISPATCHER_URL}/submit_job", json=payload, headers={"x-genesis-key": GENESIS_KEY})
                    return r.status_code, r.text
                except Exception as e:
                    return 0, str(e)

        tasks = [asyncio.create_task(submit(i)) for i in range(1, total + 1)]
        results = await asyncio.gather(*tasks)
        return results

def spawn_workers(n: int):
    procs = []
    for i in range(n):
        cmd = [str(VENV_PY), str(BASE / 'limb' / 'worker_node.py'), '--connect', 'ws://127.0.0.1:8000/connect']
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        procs.append(p)
    return procs

def kill_procs(procs):
    for p in procs:
        try:
            p.terminate()
        except Exception:
            pass

def poll_stats(timeout=120, interval=1):
    import requests
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            r = requests.get(f"{DISPATCHER_URL}/api/stats", timeout=5)
            j = r.json()
            print(json.dumps(j)[:1000])
            if j.get('queue_depth', 0) == 0:
                return j
            last = j
        except Exception as e:
            print('poll error', e)
        time.sleep(interval)
    return last

def main():
    total_jobs = int(os.environ.get('STRESS_JOBS', '200'))
    workers = int(os.environ.get('STRESS_WORKERS', '3'))

    print(f"Spawning {workers} worker processes...")
    procs = spawn_workers(workers)
    time.sleep(3)

    print(f"Submitting {total_jobs} jobs...")
    res = asyncio.run(submit_jobs(total_jobs, concurrent=50))
    ok = sum(1 for s, _ in res if s == 200)
    print(f"Submitted: {len(res)}, accepted: {ok}")

    print("Polling /api/stats until queue empties...")
    final = poll_stats(timeout=180, interval=2)
    print('Final stats:', json.dumps(final, indent=2))

    print('Cleaning up worker processes...')
    kill_procs(procs)

if __name__ == '__main__':
    main()
