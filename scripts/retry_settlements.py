#!/usr/bin/env python3
"""
Retry failed on-chain settlements recorded in titan_ledger.db where tx_signature == 'FAILED'.
Uses the treasury key at titan_bank.json and sends native SOL transfers for the worker share.
"""
import os
import json
import sqlite3
import asyncio
import logging
import sys

# Ensure project root is importable so we can import `brain.dispatcher`
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from solders.keypair import Keypair
    from solders.pubkey import Pubkey
    from solders.system_program import TransferParams, transfer
    from solders.message import Message
    from solders.transaction import Transaction
    from solana.rpc.async_api import AsyncClient
except Exception as e:
    print("Required solana/solders libs not available:", e)
    raise

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "titan_ledger.db")
BANK_WALLET_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "titan_bank.json")
RPC_URL = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
WORKER_FEE_PERCENT = float(os.getenv("WORKER_FEE_PERCENT", "0.90"))

# Operational limits
BATCH_LIMIT = int(os.getenv("RETRY_BATCH_LIMIT", "3"))
CAP_PER_TX = float(os.getenv("RETRY_CAP_PER_TX", "0.001"))  # SOL

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("retry_settlements")


def load_keypair(path: str) -> Keypair:
    with open(path, "r") as f:
        arr = json.load(f)
    kp = Keypair.from_bytes(bytes(arr))
    return kp


async def resend_payment(kp: Keypair, client: AsyncClient, wallet: str, amount_sol: float):
    try:
        to_pub = Pubkey.from_string(wallet)
    except Exception as e:
        logger.error(f"Invalid worker wallet {wallet}: {e}")
        return None

    lamports = int(amount_sol * WORKER_FEE_PERCENT * 1e9)
    if lamports <= 0:
        logger.warning(f"Zero lamports to send for amount {amount_sol}")
        return None

    try:
        ix = transfer(TransferParams(from_pubkey=kp.pubkey(), to_pubkey=to_pub, lamports=lamports))
        blockhash = (await client.get_latest_blockhash()).value.blockhash
        msg = Message.new_with_blockhash([ix], kp.pubkey(), blockhash)
        txn = Transaction([kp], msg, blockhash)
        sig = await client.send_transaction(txn)
        # sig may be an object with .value
        s = getattr(sig, 'value', sig)
        logger.info(f"Sent {amount_sol} SOL -> {wallet} | SIG: {s}")
        return str(s)
    except Exception as e:
        logger.error(f"Failed to send payment to {wallet}: {e}")
        return None


async def main():
    if not os.path.exists(BANK_WALLET_PATH):
        logger.error(f"Bank wallet not found at {BANK_WALLET_PATH}")
        return

    kp = load_keypair(BANK_WALLET_PATH)
    client = AsyncClient(RPC_URL)

    # Fetch candidate entries: NULL, empty, or simulated signatures (SIM- prefix)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT job_id, worker_wallet, amount_sol, tx_signature FROM transactions WHERE tx_signature IS NULL OR tx_signature = '' OR tx_signature LIKE 'SIM-%' ORDER BY timestamp DESC LIMIT ?",
        (BATCH_LIMIT,)
    )
    rows = cur.fetchall()
    if not rows:
        logger.info("No FAILED settlements found in ledger.")
        await client.close()
        conn.close()
        return

    logger.info(f"Found {len(rows)} candidate settlements; attempting retries (limit={BATCH_LIMIT})...")

    # Use TitanBank helper for dry-run then real send
    try:
        from brain.dispatcher import TitanBank
    except Exception as e:
        logger.error(f"Failed to import TitanBank: {e}")
        await client.close()
        conn.close()
        return

    bank = TitanBank(BANK_WALLET_PATH, RPC_URL)
    bal = await bank.get_balance()
    logger.info(f"Bank enabled={bank.enabled} balance={bal}")

    for job_id, wallet, amount, old_sig in rows:
        amount = float(amount or 0.0)
        send_amt = amount if amount > 0 else CAP_PER_TX
        send_amt = min(send_amt, CAP_PER_TX)
        logger.info(f"Candidate {job_id} -> {wallet} amount_field={amount} will attempt {send_amt} SOL")

        # Dry-run (simulate) using bank.simple_mode
        bank.simple_mode = True
        dry_sig = await bank.settle_contract(wallet, send_amt, job_id, 'retry-dry')
        logger.info(f"Dry-run signature: {dry_sig}")

        # If bank enabled and balance sufficient, attempt real send
        if bank.enabled and bal >= (send_amt + 0.001):
            bank.simple_mode = False
            real_sig = await bank.settle_contract(wallet, send_amt, job_id, 'retry-real')
            logger.info(f"Real send signature: {real_sig}")
            if real_sig and not real_sig.startswith('FAILED'):
                try:
                    cur.execute("UPDATE transactions SET tx_signature=?, status=? WHERE job_id=?", (real_sig, 'CONFIRMED', job_id))
                    conn.commit()
                    logger.info(f"Ledger updated for {job_id}")
                except Exception as e:
                    logger.error(f"Failed to update ledger for {job_id}: {e}")
            else:
                logger.warning(f"Real send failed for {job_id}: {real_sig}")
        else:
            logger.info(f"Skipping real send for {job_id}: bank.enabled={bank.enabled} balance={bal}")

    await client.close()
    conn.close()


if __name__ == '__main__':
    asyncio.run(main())
