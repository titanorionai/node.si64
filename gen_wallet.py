from solders.keypair import Keypair
import json

# Generate a new random wallet
kp = Keypair()

# Save it securely
with open("titan_bank.json", "w") as f:
    json.dump(json.loads(kp.to_json()), f)

print(f"VAULT CREATED.")
print(f"Public Address: {kp.pubkey()}")
print("KEEP 'titan_bank.json' SAFE. IT CONTAINS THE PRIVATE KEY.")
