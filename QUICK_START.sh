#!/usr/bin/env python3
"""
SI64.NET FINANCIAL BACKEND - QUICK START GUIDE
Copy & paste these commands to test the system
"""

# ============================================================================
# QUICK START: 30 SECONDS TO LIVE BILLING
# ============================================================================

"""
Terminal 1 - Start Backend:
$ cd /home/titan/TitanNetwork
$ ./scripts/start_financial_backend.sh

Terminal 2 - Monitor Dashboard:
$ python3 scripts/financial_dashboard.py watch 2

Terminal 3 - Test API (copy commands below):
"""

# ============================================================================
# TEST COMMANDS
# ============================================================================

# 1. CREATE A CONTRACT (1 minute M2 rental = 0.00001666 SOL)
curl -X POST http://localhost:8000/api/rent \
  -H "Content-Type: application/json" \
  -d '{
    "wallet": "5mEvgLUE2MvNTSr9mGRo6zvL2M2Jng132sDCP4411FHZ",
    "tier": "M2",
    "duration_hours": 0.01666,
    "tx_signature": "test_tx",
    "amount": 0.00001666
  }' | jq .

# Store the contract ID from response
CONTRACT_ID="CTR-XXXXXXXX"  # Replace with actual ID

# 2. CHECK CONTRACT STATUS (should show 0 cost, full refund)
curl http://localhost:8000/api/contracts/${CONTRACT_ID} | jq .

# 3. SIMULATE WORKLOAD - Post metrics 10 times (5 second intervals = 50 seconds of usage)
for i in {1..10}; do
  echo "Metric batch $i..."
  curl -s -X POST http://localhost:8000/api/metrics/${CONTRACT_ID} \
    -H "Content-Type: application/json" \
    -d '{
      "cpu_percent": '$(( 30 + RANDOM % 40 ))',
      "memory_mb": '$(( 3000 + RANDOM % 2000 ))',
      "disk_io_mbps": '$(( 10 + RANDOM % 30 ))',
      "network_io_mbps": 5
    }' | jq '.cost_so_far, .refund_available'
  sleep 5
done

# 4. CHECK UPDATED STATUS (should show non-zero cost & refund)
curl http://localhost:8000/api/contracts/${CONTRACT_ID} | jq .

# 5. LIST DEVICES
curl http://localhost:8000/api/devices/M2 | jq .

# 6. VIEW BILLING LEDGER
curl http://localhost:8000/api/billing/ledger | jq .

# 7. SETTLE CONTRACT (calculates and records refund)
curl -X POST http://localhost:8000/api/contracts/${CONTRACT_ID}/settle | jq .

# 8. VERIFY SETTLEMENT IN LEDGER
curl http://localhost:8000/api/billing/ledger | jq '.completed_settlements'

# ============================================================================
# ENDPOINTS AT A GLANCE
# ============================================================================

# Create rental:     POST /api/rent
# Get status:        GET /api/contracts/{id}
# Extend:            POST /api/contracts/{id}/extend
# Settle:            POST /api/contracts/{id}/settle
# Record metrics:    POST /api/metrics/{id}
# List devices:      GET /api/devices/{tier}
# View ledger:       GET /api/billing/ledger
# System stats:      GET /api/stats

# ============================================================================
# PRICING REFERENCE
# ============================================================================

# M2:        0.001 SOL/hour   (8-16GB RAM)
# ORIN:      0.004 SOL/hour   (12GB RAM)
# M3_ULTRA:  0.025 SOL/hour   (128GB RAM)
# THOR:      0.035 SOL/hour   (144GB RAM)

# ============================================================================
# MONITORING
# ============================================================================

# Live dashboard:
python3 /home/titan/TitanNetwork/scripts/financial_dashboard.py watch 2

# Check logs:
tail -f /home/titan/TitanNetwork/brain/logs/overlord.log

# Inspect database:
sqlite3 /home/titan/TitanNetwork/titan_ledger.db \
  "SELECT contract_id, renter_wallet, hardware_tier, cost_sol, status FROM rentals LIMIT 5;"

# Redis state:
redis-cli SMEMBERS "contracts:active"
redis-cli LRANGE "settlements:completed" -5 -1

# ============================================================================
# TROUBLESHOOTING
# ============================================================================

# Redis not running?
redis-server --daemonize yes

# Database locked?
rm -f /home/titan/TitanNetwork/titan_ledger.db-wal
rm -f /home/titan/TitanNetwork/titan_ledger.db-shm

# Clear test data:
redis-cli FLUSHDB
sqlite3 /home/titan/TitanNetwork/titan_ledger.db "DELETE FROM rentals;"

# ============================================================================
# EXPECTED OUTPUTS
# ============================================================================

"""
Contract Creation Response:
{
  "contract_id": "CTR-A1B2C3D4",
  "cost_sol": 0.001,
  "duration_hours": 1,
  "status": "ACTIVE",
  "tier": "M2"
}

Metrics Response:
{
  "contract_id": "CTR-A1B2C3D4",
  "cost_so_far": 0.000001234,
  "metrics_recorded": true,
  "elapsed_hours": 0.001234,
  "refund_available": 0.000998766
}

Settlement Response:
{
  "contract_id": "CTR-A1B2C3D4",
  "prepaid_sol": 0.001,
  "refund_sol": 0.000998766,
  "status": "SETTLED",
  "tx_signature": "SIMULATION_MODE",
  "used_sol": 0.000001234
}
"""

# ============================================================================
# PYTHON INTEGRATION EXAMPLE
# ============================================================================

"""
import requests
import asyncio
import time

BASE = "http://localhost:8000"
WALLET = "5mEvgLUE2MvNTSr9mGRo6zvL2M2Jng132sDCP4411FHZ"

# Create contract
r = requests.post(f"{BASE}/api/rent", json={
    "wallet": WALLET,
    "tier": "M2",
    "duration_hours": 1,
    "tx_signature": "sig",
    "amount": 0.001
})
contract_id = r.json()["contract_id"]

# Record metrics for 10 seconds
for i in range(10):
    requests.post(f"{BASE}/api/metrics/{contract_id}", json={
        "cpu_percent": 50,
        "memory_mb": 3500,
        "disk_io_mbps": 25,
        "network_io_mbps": 5
    })
    time.sleep(1)

# Check status
status = requests.get(f"{BASE}/api/contracts/{contract_id}").json()
print(f"Used: {status['used_sol']} SOL")
print(f"Refund: {status['refund_available']} SOL")

# Settle
settlement = requests.post(f"{BASE}/api/contracts/{contract_id}/settle").json()
print(f"Settled! Refund: {settlement['refund_sol']} SOL")
"""

# ============================================================================
# DASHBOARD COMMANDS
# ============================================================================

# Single snapshot:
python3 /home/titan/TitanNetwork/scripts/financial_dashboard.py

# Live watch (refresh every 2 seconds):
python3 /home/titan/TitanNetwork/scripts/financial_dashboard.py watch 2

# Live watch (refresh every 10 seconds):
python3 /home/titan/TitanNetwork/scripts/financial_dashboard.py watch 10

# ============================================================================
# SUCCESS CRITERIA
# ============================================================================

# ✓ Contract creation returns contract_id
# ✓ Status query shows cost increasing over time
# ✓ Metrics POST returns refund_available > 0
# ✓ Dashboard shows active contracts count
# ✓ Settlement returns tx_signature
# ✓ Ledger shows completed settlement
# ✓ Device list returns available units
# ✓ No Redis errors in logs

print("✅ SI64.NET Financial Backend Ready!")
print("Start with: ./scripts/start_financial_backend.sh")
