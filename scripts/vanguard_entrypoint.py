import logging

from vanguard_bot import main as vanguard_main

logging.basicConfig(level=logging.INFO, format="%(asctime)s | ENTRYPOINT | %(message)s")
logger = logging.getLogger("VANGUARD_ENTRY")

if __name__ == "__main__":
    logger.info("VANGUARD ENTRYPOINT BOOTING V11 BOT...")
    vanguard_main()
