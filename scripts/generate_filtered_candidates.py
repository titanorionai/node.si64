#!/usr/bin/env python3
"""Generate a filtered candidates CSV containing only transactions for BANK and ORIN (no live settlements executed).
"""
import sqlite3
import os
import sys
import importlib

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    dispatcher = importlib.import_module('brain.dispatcher')
except Exception as e:
    print('Failed to import brain.dispatcher:', e)
    raise

DB = dispatcher.DB_PATH
BANK = None
try:
    BANK = str(dispatcher.bank.keypair.pubkey()) if getattr(dispatcher.bank, 'keypair', None) else None
except Exception:
    BANK = None
ORIN = os.getenv('ORIN_WALLET', '5mEvgLUE2MvNTSr9mGRo6zvL2M2Jng132sDCP4411FHZ')

OUT = os.path.join(ROOT, 'reports', 'real_retry_candidates.csv')
os.makedirs(os.path.join(ROOT, 'reports'), exist_ok=True)

def gen():
    with sqlite3.connect(DB) as conn:
        cur = conn.cursor()
        if BANK:
            cur.execute("SELECT job_id, worker_wallet, amount_sol, tx_signature FROM transactions WHERE worker_wallet IN (?,?)", (BANK, ORIN))
        else:
            cur.execute("SELECT job_id, worker_wallet, amount_sol, tx_signature FROM transactions WHERE worker_wallet = ?", (ORIN,))
        rows = cur.fetchall()

    with open(OUT, 'w') as f:
        f.write('job_id,worker_wallet,amount_sol,old_tx_signature\n')
        for job_id, wallet, amount, sig in rows:
            f.write(f'{job_id},{wallet},{amount},{sig}\n')

    print(f'Wrote {len(rows)} candidates to {OUT}')

if __name__ == '__main__':
    gen()
