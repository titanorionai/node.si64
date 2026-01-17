#!/usr/bin/env python3
"""
SI64.NET FINANCIAL DASHBOARD
Real-time billing and contract monitoring CLI.
"""

import asyncio
import json
import sys
import os
import time
from datetime import datetime
from typing import Dict, List

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import redis.asyncio as redis


class FinancialDashboard:
    """Real-time billing and contract monitoring"""
    
    def __init__(self, redis_host='localhost', redis_port=6379):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis = None
    
    async def connect(self):
        """Connect to Redis"""
        self.redis = redis.Redis(host=self.redis_host, port=self.redis_port, decode_responses=True)
        await self.redis.ping()
        print(f"[✓] Connected to Redis at {self.redis_host}:{self.redis_port}")
    
    async def close(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
    
    async def get_active_contracts(self) -> List[Dict]:
        """Retrieve all active contracts"""
        active_ids = await self.redis.smembers("contracts:active")
        
        contracts = []
        for contract_id in active_ids:
            wallet = await self.redis.get(f"contract:{contract_id}:wallet")
            tier = await self.redis.get(f"contract:{contract_id}:tier")
            cost_sol = float(await self.redis.get(f"contract:{contract_id}:cost_sol") or 0)
            usage_cost = float(await self.redis.get(f"contract:{contract_id}:usage_cost") or 0)
            status = await self.redis.get(f"contract:{contract_id}:status")
            start_time = int(await self.redis.get(f"contract:{contract_id}:start_time") or 0)
            
            elapsed = int(time.time()) - start_time
            refund = max(0, cost_sol - usage_cost)
            
            contracts.append({
                "contract_id": contract_id,
                "wallet": wallet[:10] + "..." if wallet else "UNKNOWN",
                "tier": tier,
                "prepaid_sol": round(cost_sol, 6),
                "used_sol": round(usage_cost, 6),
                "refund_sol": round(refund, 6),
                "status": status,
                "elapsed_seconds": elapsed
            })
        
        return contracts
    
    async def get_settlement_history(self, limit: int = 10) -> List[Dict]:
        """Retrieve completed settlements"""
        settlements_raw = await self.redis.lrange("settlements:completed", -limit, -1)
        
        settlements = []
        for s_json in settlements_raw:
            try:
                s = json.loads(s_json)
                settlements.append({
                    "contract_id": s.get("contract_id"),
                    "wallet": s.get("wallet", "")[:10] + "...",
                    "prepaid": round(s.get("prepaid", 0), 6),
                    "used": round(s.get("used", 0), 6),
                    "refund": round(s.get("refund", 0), 6),
                    "settlement_time": datetime.fromtimestamp(s.get("settlement_time", 0)).strftime("%Y-%m-%d %H:%M:%S")
                })
            except json.JSONDecodeError:
                pass
        
        return settlements
    
    async def get_financial_summary(self) -> Dict:
        """Get overall financial summary"""
        active = await self.get_active_contracts()
        
        total_active_prepaid = sum(c["prepaid_sol"] for c in active)
        total_active_used = sum(c["used_sol"] for c in active)
        total_active_refund = sum(c["refund_sol"] for c in active)
        
        # Get completed settlements
        all_settlements_raw = await self.redis.lrange("settlements:completed", 0, -1)
        total_settled_value = 0.0
        
        for s_json in all_settlements_raw:
            try:
                s = json.loads(s_json)
                total_settled_value += s.get("used", 0)
            except json.JSONDecodeError:
                pass
        
        return {
            "active_contracts_count": len(active),
            "active_prepaid_sol": round(total_active_prepaid, 6),
            "active_used_sol": round(total_active_used, 6),
            "active_pending_refund": round(total_active_refund, 6),
            "total_historical_settled": round(total_settled_value, 6),
            "total_revenue": round(total_settled_value + total_active_used, 6),
            "timestamp": datetime.now().isoformat()
        }
    
    async def display_dashboard(self):
        """Display formatted dashboard"""
        print("\n" + "=" * 100)
        print("SI64.NET FINANCIAL DASHBOARD".center(100))
        print("=" * 100)
        
        # Summary
        summary = await self.get_financial_summary()
        print(f"\n📊 FINANCIAL SUMMARY")
        print(f"  Active Contracts:        {summary['active_contracts_count']}")
        print(f"  Prepaid (Active):        {summary['active_prepaid_sol']:.6f} SOL")
        print(f"  Used (Active):           {summary['active_used_sol']:.6f} SOL")
        print(f"  Pending Refunds:         {summary['active_pending_refund']:.6f} SOL")
        print(f"  Historical Settled:      {summary['total_historical_settled']:.6f} SOL")
        print(f"  Total Revenue:           {summary['total_revenue']:.6f} SOL")
        
        # Active Contracts
        active = await self.get_active_contracts()
        if active:
            print(f"\n📋 ACTIVE CONTRACTS ({len(active)})")
            print(f"  {'Contract ID':<15} {'Tier':<10} {'Prepaid':<10} {'Used':<10} {'Refund':<10} {'Elapsed':<10}")
            print("  " + "-" * 75)
            for c in active:
                mins = c['elapsed_seconds'] // 60
                secs = c['elapsed_seconds'] % 60
                elapsed_str = f"{mins}m {secs}s"
                print(f"  {c['contract_id']:<15} {c['tier']:<10} {c['prepaid_sol']:<10.6f} {c['used_sol']:<10.6f} {c['refund_sol']:<10.6f} {elapsed_str:<10}")
        else:
            print(f"\n📋 ACTIVE CONTRACTS (0)")
        
        # Settlement History
        settlements = await self.get_settlement_history(5)
        if settlements:
            print(f"\n✅ RECENT SETTLEMENTS ({len(settlements)})")
            print(f"  {'Contract ID':<15} {'Prepaid':<10} {'Used':<10} {'Refund':<10} {'Settled At':<20}")
            print("  " + "-" * 75)
            for s in settlements:
                print(f"  {s['contract_id']:<15} {s['prepaid']:<10.6f} {s['used']:<10.6f} {s['refund']:<10.6f} {s['settlement_time']:<20}")
        else:
            print(f"\n✅ RECENT SETTLEMENTS (0)")
        
        print("\n" + "=" * 100 + "\n")
    
    async def watch_live(self, interval: int = 2):
        """Continuously display live dashboard"""
        try:
            while True:
                await self.display_dashboard()
                print(f"Last updated: {datetime.now().strftime('%H:%M:%S')} | Refreshing in {interval}s...")
                await asyncio.sleep(interval)
        except KeyboardInterrupt:
            print("\n[✓] Dashboard stopped")


async def main():
    """Main entry point"""
    
    dashboard = FinancialDashboard()
    await dashboard.connect()
    
    # Parse command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "watch":
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 2
        await dashboard.watch_live(interval=interval)
    else:
        # Single display
        await dashboard.display_dashboard()
    
    await dashboard.close()


if __name__ == "__main__":
    asyncio.run(main())
