"""
TITAN WARHEAD FACTORY v2.0
==========================
Mission: Autonomous High-Grade Twitter Ammo Generation
Protocol: Replenish buffer to MAX_CAPACITY, then enter standby.
Target:   /home/titan/TitanNetwork/tweets.txt
"""

import requests
import json
import os
import sys
import time
from datetime import datetime

# --- CONFIGURATION ---
OLLAMA_URL = "http://localhost:11434/api/generate"
OUTPUT_FILE = os.path.expanduser("~/TitanNetwork/tweets.txt")
MAX_CAPACITY = 100  # The stockpile limit
MODEL_NAME = "llama3"
TIMEOUT_SEC = 30

PROMPT_TEMPLATE = """
SYSTEM: You are the voice of 'SI64.net', a sovereign compute network for elite hardware (Nvidia Jetson, Apple Silicon).
TONE: Aggressive, Cyberpunk, High-Status, Cryptic, Industrial.
THEMES: The Cloud is dead, Idle GPUs are a crime, Sovereign Infrastructure, DePIN.
CONSTRAINT 1: Write ONE tweet (under 180 chars). 
CONSTRAINT 2: No hashtags. No emojis (except maybe ⚡ or 💎).
CONSTRAINT 3: Do NOT use quotation marks.
CONTENT: Mock people renting AWS. Tell them to own their hardware.
"""

def log(message, level="INFO"):
    """Styled logging for the console."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    icons = {"INFO": "ℹ️", "WARN": "⚠️", "CRIT": "🛑", "SUCCESS": "✅", "FORGE": "⚡"}
    print(f"[{timestamp}] {icons.get(level, '')} {message}")

def assess_stockpile():
    """Checks how many tweets currently exist in the file."""
    if not os.path.exists(OUTPUT_FILE):
        return 0
    try:
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]
        return len(lines)
    except Exception as e:
        log(f"Stockpile assessment failed: {e}", "CRIT")
        sys.exit(1)

def forge_warhead():
    """Generates a single tweet using the local LLM."""
    payload = {
        "model": MODEL_NAME, 
        "prompt": PROMPT_TEMPLATE,
        "stream": False,
        "options": {
            "temperature": 0.95,  # Slightly higher for more variety
            "top_k": 40,
            "top_p": 0.9
        }
    }
    
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=TIMEOUT_SEC)
        if resp.status_code == 200:
            raw_tweet = resp.json()['response'].strip()
            # Sanitation: Remove quotes and newlines
            clean_tweet = raw_tweet.replace('"', '').replace('\n', ' ')
            
            # Branding: Append link if not present
            if "si64.net" not in clean_tweet.lower():
                clean_tweet = f"{clean_tweet} si64.net"
                
            return clean_tweet
        else:
            log(f"Neural failure: {resp.status_code}", "WARN")
            return None
    except requests.exceptions.ConnectionError:
        log("Cannot reach Ollama. Is the neural engine running?", "CRIT")
        return None
    except Exception as e:
        log(f"Generation error: {e}", "WARN")
        return None

def store_warhead(tweet):
    """Appends a valid tweet to the stockpile."""
    try:
        with open(OUTPUT_FILE, "a", encoding='utf-8') as f:
            f.write(tweet + "\n")
        return True
    except Exception as e:
        log(f"Storage failure: {e}", "CRIT")
        return False

def main():
    print("\n🏭 TITAN WARHEAD FACTORY v2.0 ONLINE")
    print("========================================")
    
    # 1. Check current inventory
    current_count = assess_stockpile()
    deficit = MAX_CAPACITY - current_count
    
    log(f"Stockpile Status: {current_count}/{MAX_CAPACITY} rounds detected.")

    if deficit <= 0:
        log("Stockpile at maximum capacity. Standing by.", "SUCCESS")
        print("========================================\n")
        sys.exit(0)
    
    log(f"Production Order: Forging {deficit} new rounds.", "INFO")
    print("----------------------------------------")

    # 2. Production Loop
    produced = 0
    failures = 0
    
    while produced < deficit:
        # Circuit breaker for too many consecutive failures
        if failures >= 5:
            log("Too many consecutive failures. Aborting production.", "CRIT")
            break

        print(f"\r⚡ Forging round {produced + 1}/{deficit}...", end="", flush=True)
        
        warhead = forge_warhead()
        
        if warhead:
            saved = store_warhead(warhead)
            if saved:
                produced += 1
                failures = 0 # Reset failure counter on success
                # Clear line and print success
                sys.stdout.write(f"\r✅ Secured: {warhead[:40]}...\n")
            else:
                failures += 1
        else:
            failures += 1
            time.sleep(1) # Backoff slightly on failure

    # 3. Final Report
    print("----------------------------------------")
    log(f"Batch complete. {produced} rounds added to {OUTPUT_FILE}", "SUCCESS")
    print("========================================\n")

if __name__ == "__main__":
    main()
