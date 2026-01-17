# TITAN Frontend-Backend Integration

## ✅ Full Integration Complete

All placeholders have been removed. The frontend now fetches **100% of data from the backend API**.

---

## API Endpoints (All Live)

### 1. **`GET /api/stats`** - System Telemetry
Returns real-time system status
```json
{
  "status": "OPERATIONAL",
  "treasury_mode": "MAINNET",
  "fleet_size": 3,
  "queue_depth": 109,
  "total_revenue": 0.8012,
  "transactions": [...]
}
```
**Frontend Usage**: Updates fleet size, queue depth, revenue, transaction ledger every 2 seconds

### 2. **`GET /api/wallet`** - Treasury Status
Returns TITAN bank wallet information
```json
{
  "connected": true,
  "address": "5mEvgLUE2MvNTSr9mGRo6zvL2M2Jng132sDCP4411FHZ",
  "balance": 0.062385001,
  "mode": "MAINNET"
}
```
**Frontend Usage**: Wallet connection modal displays connected address and balance

### 3. **`GET /api/devices/{tier}`** - Hardware Catalog
Returns available devices for specified tier (M2, ORIN, M3_ULTRA, THOR)
```json
[
  {
    "id": "device-orin-001",
    "name": "ORIN-CV-01",
    "uri": "node004.si64.network",
    "address": "192.168.1.201",
    "region": "Pacific NW",
    "ram": "12GB",
    "leases": 0,
    "uptime": "99.8%",
    "audited": true
  },
  ...
]
```
**Frontend Usage**: 
- Populates device selection modal when user clicks "RENT GPU"
- Updates device availability counts in dashboard (Real-time)
- Shows up-to-date device metrics (leases, uptime, audit status)

---

## Frontend Removed Placeholders

### Before (Hardcoded):
```javascript
const DEVICE_INVENTORY = {
  'M2': [
    { id: 'device-m2-001', name: 'M2-DEV-01', ... },
    ...
  ],
  'ORIN': [ ... ],
  'M3_ULTRA': [ ... ],
  'THOR': [ ... ]
};
```

### After (Dynamic):
```javascript
let DEVICE_INVENTORY = {
  'M2': [],
  'ORIN': [],
  'M3_ULTRA': [],
  'THOR': []
};

// Populated from API
async function updateDashboard() {
  for (const tier of ['M2', 'ORIN', 'M3_ULTRA', 'THOR']) {
    const devices = await fetch(`/api/devices/${tier}`).json();
    DEVICE_INVENTORY[tier] = devices;
  }
}
```

---

## Real-Time Data Flow

### Dashboard Updates (Every 2 seconds)
```
[Frontend] setInterval(updateDashboard, 2000)
    ↓
[Request] GET /api/stats + GET /api/devices/{M2,ORIN,M3_ULTRA,THOR}
    ↓
[Backend] Query Redis + Return real-time metrics
    ↓
[Display] Update:
  - Fleet size
  - Queue depth
  - Total revenue
  - Device availability
  - Transaction ledger
  - System status
```

### Device Selection Flow
```
[User] Clicks "RENT GPU" button
    ↓
[Modal] Opens with "LOADING..." message
    ↓
[Request] GET /api/devices/{tier}
    ↓
[Display] Renders live device list with:
  - Current lease count
  - Uptime percentage
  - Audit status
  - Available resources (RAM)
```

### Wallet Integration Flow
```
[User] Clicks "CONNECT WALLET"
    ↓
[Backend] GET /api/wallet (TITAN bank)
    ↓
[Display] Shows:
  - Wallet address (truncated)
  - Balance in SOL
  - Connection status
  - Mode (MAINNET/SIMULATION)
```

---

## Removed Hardcoded Data

✅ Device inventory - Now from `/api/devices/{tier}`
✅ Device counts - Now from device array length
✅ Fleet size - Now from `/api/stats`
✅ Queue depth - Now from `/api/stats`
✅ Revenue - Now from `/api/stats`
✅ Transaction ledger - Now from `/api/stats` transactions array
✅ Wallet info - Now from `/api/wallet`
✅ System status - Now from `/api/stats` status field

---

## Frontend Architecture

### Load Sequence
1. **Page Load** → Execute `window.load` event
2. **Initialize Dashboard** → Call `updateDashboard()`
3. **Fetch All Data** → 
   - `/api/stats` (fleet, queue, revenue, transactions)
   - `/api/devices/M2` (3 devices)
   - `/api/devices/ORIN` (4 devices)
   - `/api/devices/M3_ULTRA` (2 devices)
   - `/api/devices/THOR` (3 devices)
4. **Populate UI** → Display all real-time data
5. **Set Interval** → Refresh every 2 seconds

### User Interactions
- **"CONNECT WALLET"** → Fetch `/api/wallet`, display TITAN bank info
- **"RENT GPU"** → Fetch `/api/devices/{tier}`, show available hardware
- **Select Device** → Store selection, proceed to rental modal
- **Submit Rental** → Send to `/api/rent` (POST endpoint)

---

## Verification

### Test All Endpoints
```bash
# System stats
curl http://127.0.0.1:8000/api/stats | jq .

# Wallet
curl http://127.0.0.1:8000/api/wallet | jq .

# Devices by tier
curl http://127.0.0.1:8000/api/devices/ORIN | jq .
curl http://127.0.0.1:8000/api/devices/M2 | jq .
curl http://127.0.0.1:8000/api/devices/M3_ULTRA | jq .
curl http://127.0.0.1:8000/api/devices/THOR | jq .

# Frontend dashboard
curl http://127.0.0.1:8000/ | grep -o "API_ENDPOINT\|DEVICE_INVENTORY"
```

---

## System Status (Current)

| Component | Status | Details |
|-----------|--------|---------|
| **Frontend Dashboard** | ✅ Live | Real-time data from API |
| **Backend Dispatcher** | ✅ Container | titan-brain (port 8000) |
| **Redis State** | ✅ Container | titan-memory (port 6379) |
| **Ollama Engine** | ✅ Container | titan-ollama-engine (port 11434) |
| **Job Executor** | ✅ Container | titan-job-executor (host network) |
| **Wallet Integration** | ✅ Live | TITAN bank (0.0624 SOL) |
| **Device Catalog** | ✅ Live | 12 devices (3+4+2+3) |
| **Fleet Status** | ✅ Operational | 3 workers active |

---

## Next Steps

Optional enhancements:
- [ ] Add `/api/billing/ledger` to frontend
- [ ] Add rental contract UI (`/api/contracts`)
- [ ] Add job submission UI (`/api/submit_job`)
- [ ] Add real-time WebSocket updates for live notifications
- [ ] Add user authentication/sessions

**Note**: All core functionality is live and fully integrated. No placeholder data remains.
