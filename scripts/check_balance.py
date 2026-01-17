import json
import os
from solders.keypair import Keypair
from solana.rpc.api import Client

BANK_PATH = os.path.expanduser("~/TitanNetwork/titan_bank.json")
RPC_URL = "https://api.mainnet-beta.solana.com" # Public RPC just for checking balance

if not os.path.exists(BANK_PATH):
    print("NO WALLET FILE.")
    exit()

with open(BANK_PATH, "r") as f:
    kp = Keypair.from_bytes(bytes(json.load(f)))

print(f"ADDRESS: {kp.pubkey()}")
try:
    client = Client(RPC_URL)
    balance = client.get_balance(kp.pubkey()).value / 1e9
    print(f"BALANCE: {balance} SOL")
    
    if balance > 0.0005:
        print("STATUS:  [READY FOR COMBAT]")
    else:
        print("STATUS:  [EMPTY - SEND SOL NOW]")
except Exception as e:
    print(f"RPC ERROR: {e}")
