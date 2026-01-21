#!/usr/bin/env python3
import asyncio
import sqlite3
from time import time

import importlib
import os
import sys

# Ensure workspace root is on sys.path so `brain.dispatcher` can be imported
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Import the dispatcher module dynamically so we get the shared `bank` and `vault` instances
try:
    dispatcher = importlib.import_module("brain.dispatcher")
except Exception as e:
    print("Failed to import brain.dispatcher:", e)
    raise

DB = dispatcher.DB_PATH

async def retry_failed():
    # Restrict retries to the bank and ORIN worker only
    BANK_ADDR = None
    try:
        BANK_ADDR = str(dispatcher.bank.keypair.pubkey()) if getattr(dispatcher.bank, 'keypair', None) else None
    except Exception:
        BANK_ADDR = None
    ORIN_ADDR = os.getenv('ORIN_WALLET', '5mEvgLUE2MvNTSr9mGRo6zvL2M2Jng132sDCP4411FHZ')

    # Find transactions that previously failed for only the allowed wallets
    with sqlite3.connect(DB) as conn:
        cur = conn.cursor()
        if BANK_ADDR:
            cur.execute(
                "SELECT job_id, worker_wallet, amount_sol FROM transactions WHERE tx_signature = 'FAILED' AND worker_wallet IN (?,?)",
                (BANK_ADDR, ORIN_ADDR)
            )
        else:
            cur.execute(
                "SELECT job_id, worker_wallet, amount_sol FROM transactions WHERE tx_signature = 'FAILED' AND worker_wallet = ?",
                (ORIN_ADDR,)
            )
        rows = cur.fetchall()

    if not rows:
        print("No FAILED settlements found in ledger.")
        return

    print(f"Found {len(rows)} FAILED settlements — retrying in simulated/simple mode.")

    for job_id, wallet, amount in rows:
        print(f"Retrying job {job_id} -> {wallet} ({amount} SOL)")
        try:
            sig = await dispatcher.bank.settle_contract(wallet, amount, job_id, f"RETRY-{int(time())}")
            dispatcher.vault.record_job(job_id, wallet, amount, sig)
            print(f"Updated {job_id} with signature: {sig}")
        except Exception as e:
            print(f"Retry failed for {job_id}: {e}")

if __name__ == '__main__':
    asyncio.run(retry_failed())
