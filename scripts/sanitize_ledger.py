#!/usr/bin/env python3
"""
Sanitize the titan_ledger.db by backing up and redacting any wallet addresses
that are not in the allowed set (BANK + ORIN).

Usage: python3 scripts/sanitize_ledger.py
"""
import sqlite3
import shutil
import time
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, 'titan_ledger.db')
BACKUP = DB + f'.bak.{int(time.time())}'

# Allowed external wallets: bank address (if available) and ORIN worker default
ORIN_DEFAULT = '5mEvgLUE2MvNTSr9mGRo6zvL2M2Jng132sDCP4411FHZ'

def get_bank_address():
    # Try reading titan_bank.json
    jb = os.path.join(BASE, 'titan_bank.json')
    if os.path.exists(jb):
        try:
            with open(jb, 'r') as f:
                j = json.load(f)
                addr = j.get('pubkey') or j.get('address') or j.get('wallet')
                if addr:
                    return addr
        except Exception:
            pass
    # Fallback: query local dispatcher HTTP API
    try:
        import urllib.request, urllib.error
        resp = urllib.request.urlopen('http://127.0.0.1:8000/api/wallet', timeout=3)
        data = json.loads(resp.read().decode())
        if data.get('address'):
            return data['address']
    except Exception:
        pass
    return None


def main():
    if not os.path.exists(DB):
        print('DB not found at', DB)
        return

    print('Backing up DB to', BACKUP)
    shutil.copy2(DB, BACKUP)

    bank_addr = get_bank_address()
    allowed = set([ORIN_DEFAULT])
    if bank_addr:
        allowed.add(bank_addr)

    print('Allowed wallets:', allowed)

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    # Sanitize transactions.worker_wallet
    try:
        cur.execute("SELECT job_id, worker_wallet FROM transactions")
        rows = cur.fetchall()
        for jid, w in rows:
            if w and w not in allowed:
                cur.execute("UPDATE transactions SET worker_wallet = 'REDACTED' WHERE job_id = ?", (jid,))
        conn.commit()
        print('Sanitized transactions table')
    except Exception as e:
        print('Error sanitizing transactions:', e)

    # Sanitize rentals.renter_wallet
    try:
        cur.execute("SELECT contract_id, renter_wallet FROM rentals")
        rows = cur.fetchall()
        for cid, w in rows:
            if w and w not in allowed:
                cur.execute("UPDATE rentals SET renter_wallet = 'REDACTED' WHERE contract_id = ?", (cid,))
        conn.commit()
        print('Sanitized rentals table')
    except Exception as e:
        print('Error sanitizing rentals:', e)

    # Sanitize settlements.renter_wallet
    try:
        cur.execute("SELECT contract_id, renter_wallet FROM settlements")
        rows = cur.fetchall()
        for cid, w in rows:
            if w and w not in allowed:
                cur.execute("UPDATE settlements SET renter_wallet = 'REDACTED' WHERE contract_id = ?", (cid,))
        conn.commit()
        print('Sanitized settlements table')
    except Exception as e:
        print('Error sanitizing settlements:', e)

    conn.close()
    print('Sanitization complete. Backup at', BACKUP)

if __name__ == '__main__':
    main()
