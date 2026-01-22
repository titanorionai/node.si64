import json
import base58
import os
from solders.keypair import Keypair

BANK_PATH = os.path.expanduser("~/TitanNetwork/titan_bank.json")

print("\n--- TITAN TREASURY DIAGNOSTIC ---")

if not os.path.exists(BANK_PATH):
    print(f"[!] ERROR: Treasury file not found at {BANK_PATH}")
    print("    Run 'python3 ~/TitanNetwork/scripts/init_treasury.py' first.")
    exit()

try:
    with open(BANK_PATH, "r") as f:
        key_array = json.load(f)

    # Load Keypair
    kp = Keypair.from_bytes(bytes(key_array))
    
    # Encode Private Key for Phantom (Base58)
    priv_key_b58 = base58.b58encode(bytes(key_array)).decode("utf-8")

    print(f"STATUS:      ONLINE")
    print(f"FILE:        {BANK_PATH}")
    print(f"PUBLIC KEY:  {kp.pubkey()}")
    print(f"PRIVATE KEY: {priv_key_b58}")
    print("\n[INSTRUCTIONS]")
    print("1. Copy the PUBLIC KEY.")
    print("2. Send 0.05 SOL to it from your Phantom App.")
    print("3. (Optional) Import the PRIVATE KEY into Phantom to watch the bot work.")
    print("-----------------------------------\n")

except Exception as e:
    print(f"[!] CRITICAL FAILURE: {e}")
