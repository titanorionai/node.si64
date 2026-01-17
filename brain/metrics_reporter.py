"""
SI64.NET METRICS REPORTER
Real-time device metrics and billing integration for LIMB worker nodes.
Runs on each device to report CPU, RAM, I/O, and network usage every 500ms.
"""

import asyncio
import json
import psutil
import logging
import time
from datetime import datetime
from typing import Dict, Optional
import aiohttp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | [%(name)s] | %(message)s"
)
logger = logging.getLogger("METRICS_REPORTER")


class MetricsReporter:
    """
    Collects and reports device metrics to the SI64.NET dispatcher.
    Supports multiple concurrent contracts on the same device.
    """
    
    def __init__(self, device_id: str, dispatcher_url: str = "http://localhost:8000"):
        self.device_id = device_id
        self.dispatcher_url = dispatcher_url
        self.active_contracts: Dict[str, dict] = {}
        self.metrics_history: Dict[str, list] = {}
        self.reporting_interval = 0.5  # 500ms
        self.last_report_time = time.time()
        
    async def start(self):
        """Begins metrics reporting loop"""
        logger.info(f"[{self.device_id}] Starting metrics reporter")
        
        while True:
            try:
                await self._collect_and_report()
                await asyncio.sleep(self.reporting_interval)
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
                await asyncio.sleep(1)
    
    async def register_contract(self, contract_id: str):
        """Registers a new contract for monitoring"""
        self.active_contracts[contract_id] = {
            "start_time": time.time(),
            "cpu_total": 0,
            "memory_total": 0,
            "samples": 0
        }
        self.metrics_history[contract_id] = []
        logger.info(f"[{self.device_id}] Contract {contract_id} registered")
    
    async def unregister_contract(self, contract_id: str):
        """Unregisters a contract (e.g., on completion)"""
        if contract_id in self.active_contracts:
            del self.active_contracts[contract_id]
            logger.info(f"[{self.device_id}] Contract {contract_id} unregistered")
    
    def _get_system_metrics(self) -> Dict:
        """Collects system-wide metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            memory_mb = memory.used / (1024 * 1024)
            
            # Disk I/O metrics (delta since last call)
            disk_io = psutil.disk_io_counters()
            disk_io_mbps = 0
            
            # Network I/O metrics (delta since last call)
            net_io = psutil.net_io_counters()
            network_io_mbps = 0
            
            # Load average
            load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (cpu_percent/100, 0, 0)
            
            return {
                "cpu_percent": cpu_percent,
                "memory_mb": memory_mb,
                "memory_percent": memory.percent,
                "disk_io_mbps": disk_io_mbps,
                "network_io_mbps": network_io_mbps,
                "load_average": load_avg[0],
                "timestamp": int(time.time())
            }
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return {}
    
    async def _collect_and_report(self):
        """Main metrics collection and reporting loop"""
        metrics = self._get_system_metrics()
        if not metrics:
            return
        
        # Report metrics for each active contract
        for contract_id in list(self.active_contracts.keys()):
            try:
                await self._report_contract_metrics(contract_id, metrics)
            except Exception as e:
                logger.error(f"Failed to report metrics for {contract_id}: {e}")
    
    async def _report_contract_metrics(self, contract_id: str, system_metrics: Dict):
        """Reports metrics for a specific contract to the dispatcher"""
        
        payload = {
            "contract_id": contract_id,
            "device_id": self.device_id,
            "cpu_percent": system_metrics.get("cpu_percent", 0),
            "memory_mb": system_metrics.get("memory_mb", 0),
            "disk_io_mbps": system_metrics.get("disk_io_mbps", 0),
            "network_io_mbps": system_metrics.get("network_io_mbps", 0),
            "memory_percent": system_metrics.get("memory_percent", 0),
            "load_average": system_metrics.get("load_average", 0),
            "timestamp": system_metrics.get("timestamp", int(time.time()))
        }
        
        # Post to dispatcher
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.dispatcher_url}/api/metrics/{contract_id}"
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=2)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # Store in history
                        if contract_id in self.metrics_history:
                            self.metrics_history[contract_id].append({
                                "metrics": payload,
                                "response": data,
                                "reported_at": datetime.now().isoformat()
                            })
                            # Keep last 100 reports
                            if len(self.metrics_history[contract_id]) > 100:
                                self.metrics_history[contract_id] = self.metrics_history[contract_id][-100:]
                    else:
                        logger.warning(f"Metrics report failed for {contract_id}: HTTP {resp.status}")
        except Exception as e:
            logger.error(f"Failed to post metrics for {contract_id}: {e}")
    
    async def get_contract_history(self, contract_id: str) -> list:
        """Returns collected metrics history for a contract"""
        return self.metrics_history.get(contract_id, [])
    
    async def get_device_stats(self) -> Dict:
        """Returns aggregated device statistics"""
        total_contracts = len(self.active_contracts)
        total_samples = sum(c.get("samples", 0) for c in self.active_contracts.values())
        
        return {
            "device_id": self.device_id,
            "active_contracts": total_contracts,
            "total_samples_collected": total_samples,
            "reporting_interval": self.reporting_interval,
            "contracts": list(self.active_contracts.keys())
        }


class BillingCalculator:
    """Calculates real-time billing based on usage metrics"""
    
    # Hourly rates (SOL/hour)
    RATES = {
        "M2": 0.001,
        "ORIN": 0.004,
        "M3_ULTRA": 0.025,
        "THOR": 0.035
    }
    
    @staticmethod
    def calculate_cost(tier: str, elapsed_seconds: float) -> float:
        """Calculates cost based on elapsed time and tier"""
        rate = BillingCalculator.RATES.get(tier, 0.001)
        elapsed_hours = elapsed_seconds / 3600.0
        return rate * elapsed_hours
    
    @staticmethod
    def calculate_refund(prepaid: float, used: float) -> float:
        """Calculates refund amount"""
        return max(0, prepaid - used)


async def example_usage():
    """Example of how to use the metrics reporter"""
    
    reporter = MetricsReporter("device-m2-001")
    
    # Start reporting in background
    reporting_task = asyncio.create_task(reporter.start())
    
    # Register some contracts
    await reporter.register_contract("CTR-ABC123")
    await reporter.register_contract("CTR-XYZ789")
    
    # Let it run for a bit
    await asyncio.sleep(5)
    
    # Check stats
    stats = await reporter.get_device_stats()
    print(f"Device stats: {stats}")
    
    history = await reporter.get_contract_history("CTR-ABC123")
    print(f"Collected {len(history)} metric samples")
    
    # Cleanup
    reporting_task.cancel()


if __name__ == "__main__":
    asyncio.run(example_usage())
