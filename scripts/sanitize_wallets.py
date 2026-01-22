#!/usr/bin/env python3
"""Backup the ledger and normalize worker_wallet values so only the BANK and ORIN addresses exist on-chain.

This script will:
 - create a timestamped backup of `titan_ledger.db`
 - replace any `worker_wallet` value not equal to BANK or ORIN with the ORIN address
"""
import sqlite3
import os
import sys
import shutil
import importlib
from datetime import datetime

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

def backup_db():
    ts = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    bak_dir = os.path.join(ROOT, 'BACKUPS')
    os.makedirs(bak_dir, exist_ok=True)
    dst = os.path.join(bak_dir, f'titan_ledger.db.bak.{ts}')
    shutil.copy2(DB, dst)
    print('Backup created at', dst)
    return dst

def sanitize():
    if not os.path.exists(DB):
        print('DB not found:', DB)
        return
    backup_db()
    with sqlite3.connect(DB) as conn:
        cur = conn.cursor()
        # Build list of allowed wallets
        allowed = [ORIN]
        if BANK:
            allowed.append(BANK)

        # Update any worker_wallet not in allowed -> set to ORIN (so only two wallets remain)
        placeholders = ','.join('?' for _ in allowed)
        cur.execute(f"UPDATE transactions SET worker_wallet = ? WHERE worker_wallet NOT IN ({placeholders})", tuple([ORIN] + allowed))
        conn.commit()
        print('Sanitization complete. Any non-canonical wallets have been set to ORIN.')

if __name__ == '__main__':
    sanitize()
