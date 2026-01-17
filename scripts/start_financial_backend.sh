#!/bin/bash
# SI64.NET FINANCIAL BACKEND STARTUP SCRIPT
# Initializes Redis, databases, and starts dispatcher with full financial stack

set -e

cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

DISPATCHER_DIR="$(pwd)/brain"
SCRIPTS_DIR="$(pwd)/scripts"
LOGS_DIR="$(pwd)/brain/logs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                            ║${NC}"
echo -e "${BLUE}║    SI64.NET FINANCIAL BACKEND INITIALIZATION              ║${NC}"
echo -e "${BLUE}║    Launching Dispatcher with Billing & Settlement         ║${NC}"
echo -e "${BLUE}║                                                            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"

# Create directories
echo -e "${YELLOW}[1/5] Creating directories...${NC}"
mkdir -p "$LOGS_DIR"
mkdir -p "$(pwd)/brain/logs"
echo -e "${GREEN}[✓] Directories created${NC}"

# Check Redis
echo -e "${YELLOW}[2/5] Checking Redis...${NC}"
if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}[✓] Redis is running${NC}"
else
    echo -e "${YELLOW}[!] Starting Redis server...${NC}"
    sudo systemctl start redis-server 2>/dev/null || redis-server --daemonize yes
    sleep 1
    if redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}[✓] Redis started successfully${NC}"
    else
        echo -e "${RED}[✗] Failed to start Redis${NC}"
        exit 1
    fi
fi

# Initialize databases
echo -e "${YELLOW}[3/5] Initializing databases...${NC}"
python3 << 'PYTHON_DB_INIT'
import sqlite3
import os
import sys
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "titan_ledger.db")

try:
    with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
        conn.execute('PRAGMA journal_mode=WAL;')
        
        # Rentals table
        conn.execute('''CREATE TABLE IF NOT EXISTS rentals (
            contract_id TEXT PRIMARY KEY, 
            renter_wallet TEXT, 
            hardware_tier TEXT,
            duration_hours INTEGER, 
            cost_sol REAL, 
            start_time DATETIME,
            status TEXT, 
            tx_proof TEXT, 
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        
        # Settlements table
        conn.execute('''CREATE TABLE IF NOT EXISTS settlements (
            contract_id TEXT PRIMARY KEY, 
            renter_wallet TEXT, 
            prepaid_sol REAL,
            used_sol REAL, 
            refund_sol REAL, 
            settlement_tx TEXT, 
            settled_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        
        # Devices table
        conn.execute('''CREATE TABLE IF NOT EXISTS devices (
            device_id TEXT PRIMARY KEY, 
            device_name TEXT, 
            hardware_tier TEXT,
            region TEXT, 
            uri TEXT, 
            address TEXT, 
            ram TEXT, 
            audited INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        
        # Billing events table
        conn.execute('''CREATE TABLE IF NOT EXISTS billing_events (
            event_id TEXT PRIMARY KEY, 
            contract_id TEXT, 
            event_type TEXT,
            amount_sol REAL, 
            cpu_percent REAL, 
            memory_mb REAL, 
            timestamp DATETIME)''')
        
        # Transactions table
        conn.execute('''CREATE TABLE IF NOT EXISTS transactions (
            job_id TEXT PRIMARY KEY, 
            worker_wallet TEXT, 
            amount_sol REAL,
            tx_signature TEXT, 
            timestamp DATETIME, 
            status TEXT)''')
        
        conn.commit()
    print("[✓] Database schema initialized")
except Exception as e:
    print(f"[✗] Database initialization failed: {e}")
    sys.exit(1)
PYTHON_DB_INIT

if [ $? -eq 0 ]; then
    echo -e "${GREEN}[✓] Databases initialized${NC}"
else
    echo -e "${RED}[✗] Failed to initialize databases${NC}"
    exit 1
fi

# Clear Redis state (optional)
echo -e "${YELLOW}[4/5] Preparing Redis state...${NC}"
redis-cli FLUSHDB > /dev/null 2>&1 || true
redis-cli SET "system:status" "INITIALIZING" > /dev/null 2>&1 || true
redis-cli SET "system:startup_time" "$(date +%s)" > /dev/null 2>&1 || true
echo -e "${GREEN}[✓] Redis state prepared${NC}"

# Start dispatcher
echo -e "${YELLOW}[5/5] Starting Dispatcher...${NC}"
echo -e "${BLUE}"
echo "═══════════════════════════════════════════════════════════════"
echo "SI64.NET DISPATCHER LAUNCHING"
echo "═══════════════════════════════════════════════════════════════"
echo -e "${NC}"

cd "$DISPATCHER_DIR/.."

# Run dispatcher with proper logging
python3 -c "
import logging
import sys
import os
sys.path.insert(0, '$(pwd)')

# Import and run dispatcher
from brain.dispatcher import app, logger, redis_client
import uvicorn

logger.info('='*60)
logger.info('SI64.NET DISPATCHER FINANCIAL BACKEND')
logger.info('='*60)
logger.info(f'Redis: Connected')
logger.info(f'Database: titan_ledger.db')
logger.info(f'API Endpoints:')
logger.info(f'  POST /api/rent                     - Create rental')
logger.info(f'  GET  /api/contracts/:id            - Get contract status')
logger.info(f'  POST /api/contracts/:id/settle     - Settle contract')
logger.info(f'  GET  /api/devices/:tier            - List tier devices')
logger.info(f'  GET  /api/billing/ledger           - View ledger')
logger.info(f'  POST /api/metrics/:contract_id     - Record metrics')
logger.info(f'')
logger.info(f'Listening on http://0.0.0.0:8000')
logger.info(f'='*60)

try:
    uvicorn.run(app, host='0.0.0.0', port=8000, log_level='info')
except KeyboardInterrupt:
    logger.info('Dispatcher shutdown requested')
    sys.exit(0)
"

