#!/usr/bin/env python3
import asyncio
import csv
import os
import sys
import time
import importlib
from pathlib import Path

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ensure real mode
os.environ.pop('FORCE_SIMPLE_MODE', None)

try:
    dispatcher = importlib.import_module('brain.dispatcher')
except Exception as e:
    print('Failed to import brain.dispatcher:', e)
    raise

CANDIDATES = os.path.join(ROOT, 'reports', 'real_retry_candidates.csv')

async def settle_with_retries(job_id, wallet, amount, attempts=5):
    backoff = 1
    for i in range(attempts):
        try:
            sig = await dispatcher.bank.settle_contract(wallet, amount, job_id, f'RETRY-REAL-RATE-{int(time.time())}')
            dispatcher.vault.record_job(job_id, wallet, amount, sig)
            return (True, sig)
        except Exception as e:
            last = e
            print(f'Attempt {i+1}/{attempts} failed for {job_id}: {e}')
            if i < attempts - 1:
                time.sleep(backoff)
                backoff *= 2
    return (False, str(last))

async def main():
    if not os.path.exists(CANDIDATES):
        print('Candidates file not found:', CANDIDATES)
        return
    rows = []
    with open(CANDIDATES) as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append((row['job_id'], row['worker_wallet'], float(row['amount_sol'])))

    print(f'Processing {len(rows)} candidates with rate limiting (1s between attempts).')
    for job_id, wallet, amount in rows:
        print(f'Processing {job_id} -> {wallet} ({amount} SOL)')
        success, info = await settle_with_retries(job_id, wallet, amount, attempts=5)
        if success:
            print(f'Success: {job_id} -> {info}')
        else:
            print(f'Failed after retries: {job_id} -> {info}')
        time.sleep(1)

if __name__ == '__main__':
    asyncio.run(main())
