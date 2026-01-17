"""
TITAN ORION | DEFI SENTINEL (V6.0 - APEX PREDATOR)
==================================================
Authority:      Titan Central Command
Classification: TOP SECRET // NOFORN
Mission:        Autonomous Intelligence Injection & Grid Stress Testing.
Capabilities:   
  - Real-Time Tactical HUD (Rich TUI)
  - Asynchronous Burst Fire (High-Frequency Dispatch)
  - Telemetry Black Box (Local Mission Logging)
  - Resilient Uplink (Exponential Backoff)
"""

import asyncio
import aiohttp
import json
import random
import sys
import os
import hashlib
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

# --- TACTICAL UI DEPENDENCIES ---
try:
    from rich.console import Console
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
    from rich.text import Text
    from rich.align import Align
    from rich import box
except ImportError:
    print("CRITICAL: TACTICAL UI MISSING. RUN: pip install rich")
    sys.exit(1)

# --- GLOBAL CONFIGURATION ---
BRAIN_UPLINK = os.getenv("TITAN_BRAIN_URL", "http://127.0.0.1:8000/submit_job")
GENESIS_KEY = os.getenv("TITAN_GENESIS_KEY", "TITAN_GENESIS_KEY_V1_SECURE")
LOG_FILE = os.path.expanduser("~/TitanNetwork/core/orion/logs/mission_log.jsonl")
DEFAULT_TIMEOUT = 10

# --- PAYLOAD FACTORY (ORDNANCE) ---
class PayloadFactory:
    """Generates varied, high-fidelity DeFi intelligence packets."""
    
    @staticmethod
    def construct_audit_mission() -> Dict[str, Any]:
        """Simulates a high-value smart contract audit request (Solidity/Rust)."""
        vulnerabilities = [
            "// CRITICAL: Re-entrancy guard missing on external call",
            "// EXPLOIT: Flash loan price manipulation vector via LP token validation",
            "// WARNING: Unchecked return value from low-level call",
            "// SEVERE: Owner privilege escalation via proxy delegatecall",
            "// BUG: Integer overflow in staking reward calculation"
        ]
        
        program_id = hashlib.sha256(str(time.time()).encode()).hexdigest()[:32]
        vuln = random.choice(vulnerabilities)
        
        code_block = f"""
        // SPDX-License-Identifier: MIT
        pragma solidity ^0.8.0;
        contract TitanVault_{random.randint(100,999)} {{
            mapping(address => uint256) public balances;
            // Target ID: {program_id}
            
            function withdraw(uint256 _amount) public {{
                require(balances[msg.sender] >= _amount);
                
                {vuln}
                (bool sent, ) = msg.sender.call{{value: _amount}}("");
                require(sent, "Failed to send Ether");
                
                balances[msg.sender] -= _amount;
            }}
        }}
        """
        return {
            "type": "SMART_CONTRACT_AUDIT",
            "prompt": code_block,
            "hardware": "UNIT_ORIN_AGX", # Heavy Reasoning
            "bounty": round(random.uniform(0.002, 0.005), 4)
        }

    @staticmethod
    def construct_mev_mission() -> Dict[str, Any]:
        """Simulates an atomic arbitrage calculation (Math Intensive)."""
        dex_pool = ["Raydium", "Orca", "Meteora", "Phoenix", "OpenBook"]
        tokens = ["SOL", "USDC", "BONK", "WIF", "JUP"]
        route = random.sample(dex_pool, 2)
        asset = random.choice(tokens)
        amount = random.randint(100, 50000)
        
        prompt = (
            f"CALCULATE ARBITRAGE VECTOR:\n"
            f"Asset: {amount} {asset} | Spread: {random.uniform(0.1, 2.5):.2f}%\n"
            f"Path: {route[0]} (Buy) -> {route[1]} (Sell)\n"
            f"Slippage Tolerance: {random.uniform(0.1, 1.0):.1f}%\n"
            f"Constraint: Compute net profit vs gas cost (0.000005 SOL) & Priority Fee."
        )
        return {
            "type": "MEV_OPPORTUNITY_ANALYSIS",
            "prompt": prompt,
            "hardware": "UNIT_NVIDIA_CUDA", # Heavy Math
            "bounty": round(random.uniform(0.0005, 0.002), 4)
        }

    @staticmethod
    def construct_yield_mission() -> Dict[str, Any]:
        """Simulates a yield farming strategy analysis (Data Science)."""
        strategies = ["Delta Neutral", "Leveraged Farming", "Concentrated Liquidity"]
        strat = random.choice(strategies)
        apy = random.randint(10, 150)
        
        prompt = (
            f"MODEL YIELD STRATEGY: {strat}\n"
            f"Protocol: Kamino / MarginFi\n"
            f"Current APY: {apy}% | IL Risk: {random.choice(['High', 'Medium', 'Low'])}\n"
            f"Task: Project 30-day returns assuming 20% price volatility. Provide Python simulation code."
        )
        return {
            "type": "IMPERMANENT_LOSS_MODEL",
            "prompt": prompt,
            "hardware": "UNIT_APPLE_M_SERIES", # Standard Compute
            "bounty": round(random.uniform(0.0001, 0.001), 4)
        }

# --- COMMS LINK (UPLINK) ---
class CommsLink:
    def __init__(self):
        self.session = None
        self.stats = {
            "sent": 0, "success": 0, "fail": 0, 
            "latency": [], "bytes_tx": 0
        }
        self._log_handle = open(LOG_FILE, "a")

    async def engage(self):
        self.session = aiohttp.ClientSession(headers={
            "x-genesis-key": GENESIS_KEY,
            "Content-Type": "application/json",
            "User-Agent": "Titan-Sentinel/V6.0"
        })

    async def terminate(self):
        if self.session: await self.session.close()
        if self._log_handle: self._log_handle.close()

    async def fire_mission(self, payload: Dict[str, Any]) -> str:
        self.stats["sent"] += 1
        start = time.perf_counter()
        payload_size = len(json.dumps(payload))
        self.stats["bytes_tx"] += payload_size
        
        mission_record = {
            "timestamp": datetime.now().isoformat(),
            "type": payload["type"],
            "hardware": payload["hardware"],
            "status": "PENDING"
        }

        try:
            # RETRY LOGIC (Exponential Backoff)
            for attempt in range(2):
                try:
                    async with self.session.post(BRAIN_UPLINK, json=payload, timeout=DEFAULT_TIMEOUT) as resp:
                        elapsed = (time.perf_counter() - start) * 1000
                        self.stats["latency"].append(elapsed)
                        if len(self.stats["latency"]) > 100: self.stats["latency"].pop(0)
                        
                        if resp.status == 200:
                            data = await resp.json()
                            self.stats["success"] += 1
                            mission_record["status"] = "SUCCESS"
                            mission_record["job_id"] = data.get('job_id')
                            self._log_mission(mission_record)
                            return f"[green]CONFIRMED[/green] ID:{data.get('job_id')}"
                        else:
                            # If server error (500), retry. If client error (400), fail.
                            if resp.status >= 500:
                                raise aiohttp.ClientError("Server Error")
                            
                            self.stats["fail"] += 1
                            mission_record["status"] = f"FAIL_{resp.status}"
                            self._log_mission(mission_record)
                            return f"[red]REJECTED[/red] HTTP {resp.status}"
                except aiohttp.ClientError:
                    if attempt == 0: await asyncio.sleep(0.5) # Quick retry
                    else: raise

        except Exception as e:
            self.stats["fail"] += 1
            mission_record["status"] = "NET_ERROR"
            self._log_mission(mission_record)
            return f"[red]LINK FAILURE[/red] {str(e)[:15]}..."

    def _log_mission(self, record):
        """Writes to Black Box"""
        self._log_handle.write(json.dumps(record) + "\n")
        self._log_handle.flush()

# --- TACTICAL HUD (VISUALIZATION) ---
class SentinelHUD:
    def __init__(self, comms: CommsLink):
        self.comms = comms
        self.layout = Layout()
        self.log_messages = []

    def log(self, message: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_messages.append(f"[{ts}] {message}")
        if len(self.log_messages) > 14: self.log_messages.pop(0)

    def generate_dashboard(self) -> Layout:
        self.layout.split(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=3)
        )
        self.layout["main"].split_row(
            Layout(name="telemetry", ratio=1),
            Layout(name="feed", ratio=2)
        )

        # 1. HEADER
        self.layout["header"].update(Panel(
            Align.center(Text("TITAN ORION | SENTINEL V6.0 | APEX PREDATOR", style="bold cyan")),
            style="blue", box=box.HEAVY
        ))

        # 2. TELEMETRY PANEL
        avg_lat = sum(self.comms.stats["latency"]) / len(self.comms.stats["latency"]) if self.comms.stats["latency"] else 0
        success_rate = (self.comms.stats["success"] / self.comms.stats["sent"] * 100) if self.comms.stats["sent"] > 0 else 100
        kb_sent = self.comms.stats["bytes_tx"] / 1024
        
        stats_table = Table(show_header=False, expand=True, box=None)
        stats_table.add_row("SORTIES FLOWN", str(self.comms.stats["sent"]))
        stats_table.add_row("CONFIRMED HITS", f"[green]{self.comms.stats['success']}[/green]")
        stats_table.add_row("FAILED/DROPPED", f"[red]{self.comms.stats['fail']}[/red]")
        stats_table.add_row("SUCCESS RATE", f"{success_rate:.1f}%")
        stats_table.add_row("AVG LATENCY", f"{avg_lat:.1f} ms")
        stats_table.add_row("DATA UPLINK", f"{kb_sent:.2f} KB")
        
        self.layout["telemetry"].update(Panel(
            stats_table, 
            title="[bold yellow]GRID TELEMETRY[/]", 
            border_style="yellow"
        ))

        # 3. MISSION FEED
        feed_text = "\n".join(self.log_messages)
        self.layout["feed"].update(Panel(
            feed_text, 
            title="[bold green]TACTICAL FEED[/]", 
            border_style="green"
        ))

        # 4. FOOTER
        self.layout["footer"].update(Panel(
            Align.center("[bold]CTRL+C to Cease Fire[/] | [dim]Target: " + BRAIN_UPLINK + "[/] | [dim]Log: " + LOG_FILE + "[/]"), 
            style="white", box=box.HEAVY
        ))
        
        return self.layout

# --- MAIN ORCHESTRATOR ---
async def run_wargame():
    comms = CommsLink()
    hud = SentinelHUD(comms)
    
    await comms.engage()
    
    with Live(hud.generate_dashboard(), refresh_per_second=4, screen=True) as live:
        try:
            while True:
                # 1. Determine Fire Mode (Random Burst)
                # Randomize burst size to simulate organic traffic spikes
                burst_size = random.randint(1, 4)
                tasks = []
                
                # 2. Generate Ordnance (Polymorphic Payloads)
                for _ in range(burst_size):
                    dice = random.random()
                    if dice < 0.4:
                        payload = PayloadFactory.construct_audit_mission()
                        m_type = "AUDIT"
                    elif dice < 0.7:
                        payload = PayloadFactory.construct_mev_mission()
                        m_type = "MEV  "
                    else:
                        payload = PayloadFactory.construct_yield_mission()
                        m_type = "YIELD"
                    
                    # 3. Fire
                    tasks.append((m_type, comms.fire_mission(payload)))

                # 4. Await Results (Async Gather)
                results = await asyncio.gather(*[t[1] for t in tasks])
                
                # 5. Update HUD
                for i, res in enumerate(results):
                    m_type = tasks[i][0]
                    hud.log(f"{m_type} >> {res}")
                
                live.update(hud.generate_dashboard())
                
                # Rate Limiter (Tactical Pause to prevent local network choke)
                await asyncio.sleep(random.uniform(0.8, 2.0))
                
        except KeyboardInterrupt:
            pass
        finally:
            await comms.terminate()

if __name__ == "__main__":
    try:
        asyncio.run(run_wargame())
    except KeyboardInterrupt:
        print("\n[!] SENTINEL DISENGAGED.")
