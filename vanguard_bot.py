import os
import sys
import time
import random
import logging
import tweepy

# --- CONFIGURATION ---
# These read from environment variables injected via .env (X_API_*)
API_KEY = os.getenv("X_API_KEY")
API_SECRET = os.getenv("X_API_SECRET")
ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("X_ACCESS_SECRET")

# The Ammo Crate
AMMO_PATH = "/app/tweets.txt"

# RATE LIMIT SAFETY: 
# Free Tier = 50 tweets/day max. 
# 3 Hours = 8 tweets/day (Safe). 
# 1 Hour = 24 tweets/day (Safe).
INTERVAL = 3 * 60 * 60 

# --- LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | STEALTH | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("VANGUARD")

# --- COMMS ---
class XComms:
    def __init__(self):
        # On Free Tier, we CANNOT verify credentials by checking "get_me()".
        # We must trust the keys are valid and just attempt the strike.
        try:
            self.client = tweepy.Client(
                consumer_key=API_KEY,
                consumer_secret=API_SECRET,
                access_token=ACCESS_TOKEN,
                access_token_secret=ACCESS_SECRET
            )
            logger.info("WEAPON LOADED (BLIND MODE).")
        except Exception as e:
            logger.critical(f"SETUP FAILED: {e}")
            sys.exit(1)

    def fire(self, msg):
        try:
            self.client.create_tweet(text=msg)
            logger.info(f"SENT: {msg}")
            return True
        except tweepy.TooManyRequests:
            logger.warning("RATE LIMIT HIT (429). HOLDING FIRE.")
            return False
        except tweepy.Forbidden as e:
            logger.error(f"PERMISSIONS ERROR (403): {e}")
            logger.error("CHECK: Did you enable 'Read and Write' in the Developer Portal?")
            return False
        except Exception as e:
            logger.error(f"MISFIRE: {e}")
            return False

# --- MAIN LOOP ---
def main():
    logger.info("=== TITAN STEALTH BOT ONLINE ===")
    gun = XComms()
    
    # Wait 5s to settle
    time.sleep(5)

    while True:
        try:
            # 1. Grab Ammo
            if os.path.exists(AMMO_PATH):
                with open(AMMO_PATH, "r") as f:
                    lines = f.readlines()
                
                if lines:
                    payload = random.choice(lines).strip()
                    
                    if payload:
                        gun.fire(payload)
                    else:
                        logger.warning("BLANK ROUND. SKIPPING.")
                else:
                    logger.warning("AMMO CRATE EMPTY.")
            else:
                logger.error("AMMO CRATE MISSING (/app/tweets.txt).")

            # 2. Wait
            # Add small random jitter (±5 mins) to look slightly human
            jitter = random.randint(-300, 300)
            sleep_time = INTERVAL + jitter
            
            logger.info(f"SLEEPING FOR {sleep_time/60:.1f} MINS...")
            time.sleep(sleep_time)

        except KeyboardInterrupt:
            logger.info("SHUTTING DOWN.")
            break
        except Exception as e:
            logger.error(f"CRITICAL: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
