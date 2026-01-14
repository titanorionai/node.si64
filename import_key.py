import json
from solders.keypair import Keypair

# --- PASTE YOUR PRIVATE KEY STRING BELOW ---
PRIVATE_KEY_STRING = "2Yy6TcCUy1ceZ4zEohZ93mDxnvpgHNNv483VWHbwEq4fGiNH8z2maLuv4ZcR5uewNdQgexsNsmLeYcJVxoFVEpKZ"
# -------------------------------------------

try:
    # 1. Decode the string to a Keypair object
    kp = Keypair.from_base58_string(PRIVATE_KEY_STRING)

    # 2. CORRECTED LINE: Convert keypair to bytes, then to a list of integers
    keypair_as_integers = list(bytes(kp))

    # 3. Save as JSON
    with open("bot_keypair.json", "w") as f:
        json.dump(keypair_as_integers, f)

    print(f"✅ SUCCESS! Wallet imported.")
    print(f"Public Key: {kp.pubkey()}")
    print("Saved to: bot_keypair.json")

except Exception as e:
    print(f"❌ ERROR: {e}")
