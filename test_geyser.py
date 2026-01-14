import asyncio
from yellowstone_grpc_client import GeyserClient

# PASTE YOUR CHAINSTACK DETAILS HERE
GRPC_URL = "yellowstone-solana-mainnet.core.chainstack.com:443"  # Don't forget the port!
X_TOKEN = "b8dc50df2c1abbbae3faab2bcf308faa"

async def test_connection():
    print(f"🔌 Connecting to {GRPC_URL}...")
    
    # Connect with the token
    async with GeyserClient.connect(GRPC_URL, x_token=X_TOKEN) as client:
        print("✅ Connected! Subscribing to Mempool (Pending Transactions)...")
        
        # Subscribe to "processed" (Mempool) updates
        await client.subscribe_transactions(
            commitment="processed",  # 'processed' = Mempool/Pending
            failed=False
        )

        print("Waiting for data stream...")
        
        # Print the first 10 transactions to prove it works
        count = 0
        async for message in client:
            print(f"🚀 [Speed Test] New Transaction detected! Size: {len(str(message))} bytes")
            count += 1
            if count >= 10:
                print("🎉 SUCCESS: You are receiving high-speed Mempool data.")
                break

if __name__ == "__main__":
    asyncio.run(test_connection())
