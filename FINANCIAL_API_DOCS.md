# SI64.NET FINANCIAL BACKEND API DOCUMENTATION

## Overview

The SI64.NET financial backend provides real-time billing, contract management, and settlement operations for compute rentals on the SI64.NET platform. All operations are recorded in an immutable SQLite ledger and synchronized through Redis for real-time state management.

---

## Financial Entities

### Contract Lifecycle

```
INITIATION → ACTIVE → EXTENSION* → SETTLED
   ↓         ↓         ↓            ↓
Prepay   Metering   More SOL   Refund issued
```

### Key Rates

| Tier | Rate (SOL/hour) | Memory | Use Case |
|------|---|---|---|
| M2 | 0.001 | 8-16GB | General compute, ML training |
| ORIN | 0.004 | 12GB | Edge computing, inference |
| M3_ULTRA | 0.025 | 128GB | Large models, batch processing |
| THOR | 0.035 | 144GB | HPC workloads, multi-GPU |

---

## Rental Management Endpoints

### POST /api/rent
**Create a new hardware rental contract**

Request:
```json
{
  "wallet": "5mEvgLUE2MvNTSr9mGRo6zvL2M2Jng132sDCP4411FHZ",
  "tier": "M2",
  "duration_hours": 1,
  "tx_signature": "fake_sig_for_now",
  "amount": 0.001001
}
```

Response (201):
```json
{
  "contract_id": "CTR-A1B2C3D4",
  "status": "ACTIVE",
  "cost_sol": 0.001,
  "tier": "M2",
  "duration_hours": 1
}
```

**Status Codes:**
- 201: Contract created successfully
- 402: Payment verification failed
- 500: Contract creation error

---

### GET /api/contracts/{contract_id}
**Retrieve contract status and billing information**

Response:
```json
{
  "contract_id": "CTR-A1B2C3D4",
  "wallet": "5mEvgLU...",
  "tier": "M2",
  "status": "ACTIVE",
  "prepaid_sol": 0.001,
  "used_sol": 0.000234,
  "refund_available": 0.000766,
  "duration_hours": 1.0,
  "elapsed_hours": 0.25,
  "remaining_seconds": 2700,
  "created_at": 1705513800,
  "expires_at": 1705517400
}
```

---

### POST /api/contracts/{contract_id}/extend
**Extend an active contract**

Request:
```json
{
  "additional_hours": 1
}
```

Response:
```json
{
  "contract_id": "CTR-A1B2C3D4",
  "extended_hours": 1,
  "additional_cost_sol": 0.001,
  "new_total_cost": 0.002,
  "new_expiration": 1705521000
}
```

---

### POST /api/contracts/{contract_id}/settle
**Settle a contract and calculate refunds**

Response:
```json
{
  "contract_id": "CTR-A1B2C3D4",
  "status": "SETTLED",
  "prepaid_sol": 0.001,
  "used_sol": 0.000234,
  "refund_sol": 0.000766,
  "tx_signature": "3vQnS..."
}
```

**Behavior:**
1. Calculates actual usage time from `start_time` to `settlement_time`
2. Multiplies elapsed hours by hourly rate to get `used_sol`
3. Calculates `refund = prepaid - used`
4. If `refund > 0`, submits transfer transaction to Solana
5. Records settlement in vault (immutable)
6. Returns settlement proof and transaction signature

---

## Metrics & Billing Endpoints

### POST /api/metrics/{contract_id}
**Record real-time metrics from executing workload**

Called every 500ms by device worker nodes.

Request:
```json
{
  "cpu_percent": 45.2,
  "memory_mb": 3500,
  "disk_io_mbps": 25.1,
  "network_io_mbps": 5.3
}
```

Response:
```json
{
  "contract_id": "CTR-A1B2C3D4",
  "metrics_recorded": true,
  "elapsed_hours": 0.0451,
  "cost_so_far": 0.0000451,
  "refund_available": 0.0009549
}
```

**Behavior:**
- Stores metrics in time-series (Redis FIFO, keeps last 100)
- Updates `contract:CONTRACT_ID:usage_cost` with linear billing
- Billing = `elapsed_hours * hourly_rate`

---

### GET /api/devices/{tier}
**Get available devices for a tier with live metrics**

Response:
```json
[
  {
    "id": "device-m2-001",
    "name": "M2-DEV-01",
    "uri": "node001.si64.network",
    "address": "192.168.1.101",
    "region": "West Coast",
    "ram": "8GB",
    "leases": 3,
    "uptime": "99.8%",
    "audited": true
  }
]
```

**Metrics Source:**
- `leases`: Count from `device:DEVICE_ID:active_leases` (Redis)
- `uptime`: From `device:DEVICE_ID:uptime` (Redis)
- `audited`: From `device:DEVICE_ID:audited` (Redis)

---

## Billing & Ledger Endpoints

### GET /api/billing/ledger
**Get complete billing ledger**

Response:
```json
{
  "active_contracts": [
    {
      "contract_id": "CTR-A1B2C3D4",
      "wallet": "5mEvgLU...",
      "tier": "M2",
      "prepaid": 0.001,
      "used": 0.000234,
      "refund": 0.000766,
      "status": "ACTIVE"
    }
  ],
  "completed_settlements": [
    {
      "contract_id": "CTR-XYZ789",
      "wallet": "7nFgkRS...",
      "prepaid": 0.004,
      "used": 0.0037,
      "refund": 0.0003,
      "settlement_time": 1705511234
    }
  ],
  "total_active_value": 0.005,
  "total_used": 0.001234,
  "total_pending_refunds": 0.003766
}
```

---

## Database Schema

### rentals table
```sql
CREATE TABLE rentals (
  contract_id TEXT PRIMARY KEY,
  renter_wallet TEXT,
  hardware_tier TEXT,
  duration_hours INTEGER,
  cost_sol REAL,
  start_time DATETIME,
  status TEXT,
  tx_proof TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
```

### settlements table
```sql
CREATE TABLE settlements (
  contract_id TEXT PRIMARY KEY,
  renter_wallet TEXT,
  prepaid_sol REAL,
  used_sol REAL,
  refund_sol REAL,
  settlement_tx TEXT,
  settled_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
```

### billing_events table
```sql
CREATE TABLE billing_events (
  event_id TEXT PRIMARY KEY,
  contract_id TEXT,
  event_type TEXT,
  amount_sol REAL,
  cpu_percent REAL,
  memory_mb REAL,
  timestamp DATETIME
)
```

---

## Redis State Keys

### Active Contract State
```
contract:{contract_id}:wallet           → renter wallet address
contract:{contract_id}:tier             → hardware tier (M2, ORIN, etc)
contract:{contract_id}:duration_hours   → contracted duration
contract:{contract_id}:cost_sol         → prepaid amount
contract:{contract_id}:usage_cost       → current usage cost
contract:{contract_id}:start_time       → unix timestamp
contract:{contract_id}:status           → ACTIVE, SETTLED, EXPIRED
contract:{contract_id}:expiration       → unix timestamp of expiration
```

### Metrics & Monitoring
```
device:{device_id}:active_leases    → count of active rentals
device:{device_id}:uptime           → uptime percentage
device:{device_id}:audited          → boolean audit status
contract:{contract_id}:metrics      → FIFO list of metric samples (JSON)
contract:{contract_id}:last_metric_time → timestamp of last metric
```

### Collections
```
contracts:active               → set of active contract IDs
settlements:completed          → list of completed settlement records (JSON)
```

---

## Billing Algorithm

### Real-Time Metering (Every 500ms)
```
elapsed_seconds = now() - contract.start_time
elapsed_hours = elapsed_seconds / 3600
usage_cost = elapsed_hours * tier.hourly_rate

Example:
- M2 @ 0.001 SOL/hour
- After 30 minutes: 0.5 * 0.001 = 0.0005 SOL used
- Remaining refund: 0.001 - 0.0005 = 0.0005 SOL
```

### Settlement & Refunds
```
1. Customer prepays: 0.001 SOL
2. Contract expires or customer terminates early
3. Calculate actual usage: 45 minutes
4. Cost = 45/60 * 0.001 = 0.00075 SOL
5. Refund = 0.001 - 0.00075 = 0.000250 SOL
6. Submit refund transaction to Solana
7. Record in vault (immutable)
```

---

## Integration Examples

### Web Browser (JavaScript/Phantom Wallet)

```javascript
// 1. Connect wallet and approve transaction
const publicKey = await window.solana.connect();

// 2. Initiate rental
const response = await fetch('/api/rent', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    wallet: publicKey.toString(),
    tier: 'M2',
    duration_hours: 1,
    tx_signature: 'phantom_signed_tx',
    amount: 0.001
  })
});

const { contract_id } = await response.json();

// 3. Poll contract status
async function pollContract() {
  const status = await fetch(`/api/contracts/${contract_id}`).then(r => r.json());
  console.log(`Cost so far: ${status.used_sol} SOL`);
  console.log(`Refund available: ${status.refund_available} SOL`);
}

setInterval(pollContract, 2000);  // Every 2 seconds

// 4. Settle when done
await fetch(`/api/contracts/${contract_id}/settle`, { method: 'POST' });
```

### Worker Node (Python/asyncio)

```python
from metrics_reporter import MetricsReporter

reporter = MetricsReporter("device-m2-001")

# Start reporting metrics
asyncio.create_task(reporter.start())

# Register new contract
await reporter.register_contract("CTR-A1B2C3D4")

# Let it run for duration...
await asyncio.sleep(3600)

# Unregister on completion
await reporter.unregister_contract("CTR-A1B2C3D4")
```

---

## Error Handling

### Payment Verification Failed (402)
```json
{
  "detail": "Payment Verification Failed",
  "reason": "Transaction not found on Solana or insufficient amount"
}
```

**Resolution:** Ensure transaction is confirmed and amount matches tier cost.

### Contract Not Found (404)
```json
{
  "detail": "Contract not found"
}
```

**Resolution:** Verify contract_id spelling. Contract may have expired.

### Contract Not Active (400)
```json
{
  "detail": "Contract not active"
}
```

**Resolution:** Cannot perform operations on settled or expired contracts.

---

## Operational Monitoring

### Check System Health
```bash
# View active contracts and revenue
curl http://localhost:8000/api/billing/ledger | jq .

# Monitor real-time dashboard
python3 scripts/financial_dashboard.py watch
```

### Solana Integration

**Mainnet:**
```
RPC: https://api.mainnet-beta.solana.com
Treasury Key: /home/titan/TitanNetwork/titan_bank.json
Status: Check bank initialization in dispatcher logs
```

**Simulation Mode:**
```
No Solana required
All transactions return mocked signatures
Useful for testing without real SOL
```

---

## Performance Targets

| Operation | Target Latency |
|-----------|---|
| Contract creation | 50-200ms |
| Device allocation | 100-500ms |
| Metrics POST | <100ms |
| Ledger query | <50ms |
| Settlement (Solana) | 2-5s (blockchain confirmation) |
| Dashboard refresh | 2s (WebSocket) |

---

## Security Considerations

1. **Transaction Verification:** All rental requests require valid Solana transaction signature
2. **Wallet Authorization:** Renter wallet is extracted from signed transaction
3. **Settlement Immutability:** All completed settlements recorded in SQLite (WAL mode)
4. **Rate Limiting:** 150 requests per 10 seconds per client IP
5. **Contract Expiration:** Automatic cleanup and refund if contract expires

---

## Future Enhancements

- [ ] Spot pricing based on demand
- [ ] Long-term contract discounts
- [ ] GPU-specific pricing tiers
- [ ] Reserved capacity plans
- [ ] Cross-chain settlement (Polygon, Arbitrum)
- [ ] Loyalty rewards program
- [ ] Advanced usage analytics
