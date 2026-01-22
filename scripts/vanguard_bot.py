import os
import time
import random
import logging
import tweepy
import sys

# LOGGING SETUP
logging.basicConfig(level=logging.INFO, format="%(asctime)s | JUGGERNAUT | %(message)s")
logger = logging.getLogger("VANGUARD")

# LOAD KEYS
API_KEY = os.getenv("X_API_KEY")
API_SECRET = os.getenv("X_API_SECRET")
ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("X_ACCESS_SECRET")
AMMO_PATH = "/app/tweets.txt"

def main():
    logger.info("=== JUGGERNAUT V11: IMMEDIATE FIRE ===")
    
    # 1. DEBUG KEYS (Don't print them, just check length)
    if not API_KEY or len(API_KEY) < 5:
        logger.critical("CRITICAL: API KEY NOT LOADED FROM .ENV!")
        time.sleep(30)
        sys.exit(1)
    
    # 2. SETUP CLIENT
    try:
        client = tweepy.Client(
            consumer_key=API_KEY,
            consumer_secret=API_SECRET,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_SECRET,
        )
        logger.info("WEAPON ARMED. KEYS LOADED.")

        try:
            me = client.get_me()
            if getattr(me, "data", None):
                logger.info(
                    f"ENGAGED PROFILE: @{me.data.username} (id={me.data.id})"
                )
            else:
                logger.warning("ENGAGED PROFILE: UNKNOWN (get_me() returned no data)")
        except Exception as e:
            logger.warning(f"FAILED TO QUERY CURRENT PROFILE: {e}")
    except Exception as e:
        logger.critical(f"AUTH FAILED: {e}")
        sys.exit(1)

    # 3. LOAD AMMO
    try:
        with open(AMMO_PATH, "r") as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        if not lines:
            logger.error("AMMO FILE EMPTY!")
            return
    except Exception as e:
        logger.error(f"AMMO READ ERROR: {e}")
        return

    # 4. FIRE IMMEDIATELY
    payload = random.choice(lines)
    logger.info(f"ATTEMPTING SHOT: {payload[:30]}...")
    
    try:
        resp = client.create_tweet(text=payload)
        logger.info(f"KILL CONFIRMED. ID: {resp.data['id']}")
    except tweepy.TooManyRequests:
        logger.warning("RATE LIMITED (429). STANDING BY.")
    except Exception as e:
        logger.error(f"MISFIRE: {e}")

    # 5. ENTER SLEEP CYCLE
    logger.info("GOING DARK FOR 3 HOURS...")
    time.sleep(10800)

if __name__ == "__main__":
    main()
