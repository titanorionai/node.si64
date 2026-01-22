#!/usr/bin/env python3
import asyncio
import sqlite3
import os
import re
import sys
import importlib
from time import time

# Ensure workspace root is on sys.path so `brain.dispatcher` can be imported
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Force real mode: remove FORCE_SIMPLE_MODE if set in environment
os.environ.pop('FORCE_SIMPLE_MODE', None)

try:
    dispatcher = importlib.import_module('brain.dispatcher')
except Exception as e:
    print('Failed to import brain.dispatcher:', e)
    raise

DB = dispatcher.DB_PATH

BASE58_RE = re.compile(r'^[1-9A-HJ-NP-Za-km-z]{32,64}$')

async def main():
    BANK_ADDR = None
    try:
        BANK_ADDR = str(dispatcher.bank.keypair.pubkey()) if getattr(dispatcher.bank, 'keypair', None) else None
    except Exception:
        BANK_ADDR = None
    ORIN_ADDR = os.getenv('ORIN_WALLET', '5mEvgLUE2MvNTSr9mGRo6zvL2M2Jng132sDCP4411FHZ')

    with sqlite3.connect(DB) as conn:
        cur = conn.cursor()
        # Only consider rows for the two canonical wallets
        if BANK_ADDR:
            cur.execute(
                "SELECT job_id, worker_wallet, amount_sol, tx_signature FROM transactions WHERE (tx_signature = 'FAILED' OR tx_signature LIKE 'SIM-%' OR tx_signature IS NULL) AND worker_wallet IN (?,?)",
                (BANK_ADDR, ORIN_ADDR)
            )
        else:
            cur.execute(
                "SELECT job_id, worker_wallet, amount_sol, tx_signature FROM transactions WHERE (tx_signature = 'FAILED' OR tx_signature LIKE 'SIM-%' OR tx_signature IS NULL) AND worker_wallet = ?",
                (ORIN_ADDR,)
            )
        rows = cur.fetchall()

    if not rows:
        print('No candidate settlements found.')
        return

    os.makedirs(os.path.join(ROOT, 'reports'), exist_ok=True)
    invalid_path = os.path.join(ROOT, 'reports', 'invalid_wallets.csv')
    candidates_path = os.path.join(ROOT, 'reports', 'real_retry_candidates.csv')

    valid_rows = []
    invalid_rows = []

    for job_id, wallet, amount, sig in rows:
        if wallet is None:
            invalid_rows.append((job_id, wallet, amount, sig, 'NULL'))
            continue
        if BASE58_RE.match(wallet):
            valid_rows.append((job_id, wallet, amount, sig))
        else:
            invalid_rows.append((job_id, wallet, amount, sig, 'INVALID'))

    # Write reports
    with open(invalid_path, 'w') as f:
        f.write('job_id,worker_wallet,amount_sol,tx_signature,reason\n')
        for r in invalid_rows:
            f.write(','.join([str(x) if x is not None else '' for x in r]) + '\n')

    with open(candidates_path, 'w') as f:
        f.write('job_id,worker_wallet,amount_sol,old_tx_signature\n')
        for job_id, wallet, amount, sig in valid_rows:
            f.write(f'{job_id},{wallet},{amount},{sig}\n')

    print(f'Found {len(valid_rows)} valid candidates and {len(invalid_rows)} invalid rows.')
    print(f'Invalid report: {invalid_path}')
    print(f'Candidates report: {candidates_path}')

    if not valid_rows:
        return

    # Confirm and proceed automatically (user requested run). Execute real settlements.
    print('Starting real on-chain retries for valid candidates (this will attempt live transactions).')

    for job_id, wallet, amount, old_sig in valid_rows:
        print(f'Retrying job {job_id} -> {wallet} ({amount} SOL)')
        try:
            sig = await dispatcher.bank.settle_contract(wallet, amount, job_id, f'RETRY-REAL-{int(time())}')
            dispatcher.vault.record_job(job_id, wallet, amount, sig)
            print(f'Success: {job_id} -> {sig}')
        except Exception as e:
            print(f'Failed: {job_id} -> {e}')

if __name__ == '__main__':
    asyncio.run(main())
