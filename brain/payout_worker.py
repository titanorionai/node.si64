"""Payout worker: consumes 'titan_payout_queue' and performs rate-limited on-chain payouts.

Run with the project's venv Python.
"""
import asyncio
import json
import logging
import os

from brain import dispatcher

logger = logging.getLogger("TITAN_PAYOUT")
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

redis = dispatcher.redis_client
bank = dispatcher.bank
vault = dispatcher.vault
# Configurable delay between payouts (seconds). Can be overridden with env `PAYOUT_RATE_DELAY`.
RATE_DELAY = float(os.getenv("PAYOUT_RATE_DELAY", "1.0"))  # seconds between payouts


async def worker_loop():
    logger.info("Payout worker starting, polling 'titan_payout_queue'")
    while True:
        try:
            item = await redis.rpop("titan_payout_queue")
            if not item:
                await asyncio.sleep(RATE_DELAY)
                continue
            payload = json.loads(item)
            job_id = payload.get("job_id")
            wallet = payload.get("wallet")
            total_bounty = payload.get("total_bounty", dispatcher.BOUNTY_PER_JOB)
            node_id = payload.get("node_id", "UNKNOWN")

            logger.info(f"Processing payout for job {job_id} -> {wallet[:6]}...")
            sig = await bank.process_payout(wallet, total_bounty)
            # Map bank results to explicit ledger statuses
            if sig == "FAILED_RENT":
                status = "FAILED_RENT"
            elif sig == "FAILED_TX":
                status = "FAILED_TX"
            elif sig == "SKIPPED_DUST":
                status = "SKIPPED_DUST"
            elif sig is None:
                status = "BANK_OFFLINE"
            else:
                status = "CONFIRMED"

            amount = total_bounty * dispatcher.WORKER_FEE_PERCENT
            vault.record_job(job_id, wallet, amount, sig, status)
            logger.info(f"Payout result for {job_id}: {status} ({sig})")

            await asyncio.sleep(RATE_DELAY)
        except Exception as e:
            logger.exception(f"Payout worker encountered error: {e}")
            await asyncio.sleep(1)


if __name__ == "__main__":
    try:
        asyncio.run(worker_loop())
    except KeyboardInterrupt:
        logger.info("Payout worker stopped by user")
