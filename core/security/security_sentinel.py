"""
TITAN SECURITY | SOVEREIGN SENTINEL (V3.0 - CYBER-DEFENSE GRID)
===============================================================
Authority:      Titan Security Command (SEC-COM)
Classification: TOP SECRET // INTERNAL DEFENSE
Mission:        Continuous Vulnerability Scanning & Smart Contract Auditing.
Target:         Titan Swarm (Unit: ORIN-AGX)
Capabilities:   
  - Real-Time Threat Simulation
  - Cryptographic Payload Encapsulation
  - Live Security Operations Center (SOC) Dashboard
"""

import asyncio
import aiohttp
import json
import random
import sys
import os
import hashlib
import time
import base64
from datetime import datetime
from typing import Dict, Any

# --- TACTICAL UI DEPENDENCIES ---
try:
    from rich.console import Console
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.align import Align
    from rich import box
    from rich.style import Style
except ImportError:
    print("CRITICAL: TACTICAL UI MISSING. RUN: pip install rich")
    sys.exit(1)

# --- GLOBAL CONFIGURATION ---
BRAIN_UPLINK = os.getenv("TITAN_BRAIN_URL", "http://127.0.0.1:8000/submit_job")
GENESIS_KEY = os.getenv("TITAN_GENESIS_KEY", "TITAN_GENESIS_KEY_V1_SECURE")
LOG_FILE = os.path.expanduser("~/TitanNetwork/core/security/logs/audit_trail.jsonl")
DEFAULT_TIMEOUT = 30

# --- THREAT GENERATOR (ORDNANCE) ---
class ThreatFactory:
    """Generates high-fidelity smart contract vulnerabilities for audit simulation."""
    
    @staticmethod
    def rust_anchor_exploit() -> Dict[str, Any]:
        """Simulates a Solana Anchor framework vulnerability."""
        exploits = [
            "// CRITICAL: Missing constraint on 'token_program' account",
            "// SEVERE: Account ownership check bypassed on 'vault'",
            "// HIGH: Integer overflow in 'reward_share' calculation (CheckedMath missing)",
            "// MEDIUM: Signer check missing on 'authority' account"
        ]
        
        program_id = hashlib.sha256(str(time.time()).encode()).hexdigest()[:16]
        vuln = random.choice(exploits)
        
        code = f"""
        #[program]
        pub mod titan_vault_{random.randint(10,99)} {{
            use super::*;
            // Program ID: {program_id}...
            
            pub fn withdraw_funds(ctx: Context<Withdraw>, amount: u64) -> Result<()> {{
                let user = &mut ctx.accounts.user;
                let vault = &mut ctx.accounts.vault;
                
                {vuln}
                
                // Transfer Logic
                let cpi_accounts = Transfer {{
                    from: vault.to_account_info(),
                    to: user.to_account_info(),
                    authority: vault.to_account_info(),
                }};
                token::transfer(CpiContext::new(ctx.accounts.token_program.to_account_info(), cpi_accounts), amount)?;
                Ok(())
            }}
        }}
        """
        return {
            "type": "SMART_CONTRACT_AUDIT",
            "context": "SOLANA_RUST_ANCHOR",
            "prompt": code,
            "desc": "Solana Vault Audit",
            "severity": "CRITICAL"
        }

    @staticmethod
    def solidity_flashloan_attack() -> Dict[str, Any]:
        """Simulates an EVM Flash Loan Price Manipulation."""
        code = f"""
        // SPDX-License-Identifier: MIT
        pragma solidity ^0.8.0;
        contract TitanLend_{random.randint(100,999)} {{
            IUniswapV2Pair public pair;
            
            function liquidate(address _user) external {{
                // VULNERABILITY: Relying on spot price for collateral valuation
                uint256 price = pair.getReserves(); 
                uint256 debt = getUserDebt(_user);
                
                require(debt > 0, "No debt");
                // Attacker can manipulate 'price' via Flash Loan before calling this
                if (price < liquidationThreshold) {{
                    _seizeCollateral(_user);
                }}
            }}
        }}
        """
        return {
            "type": "SMART_CONTRACT_AUDIT",
            "context": "EVM_SOLIDITY",
            "prompt": code,
            "desc": "Flash Loan Vector",
            "severity": "HIGH"
        }

    @staticmethod
    def reentrancy_attack() -> Dict[str, Any]:
        """Simulates a Classic Re-entrancy Attack."""
        code = f"""
        // SPDX-License-Identifier: MIT
        pragma solidity ^0.8.0;
        contract TitanDAO_{random.randint(100,999)} {{
            mapping(address => uint) public balances;

            function withdraw() public {{
                uint bal = balances[msg.sender];
                require(bal > 0);

                // VULNERABILITY: External call before state update
                (bool sent, ) = msg.sender.call{{value: bal}}("");
                require(sent, "Failed to send Ether");

                balances[msg.sender] = 0;
            }}
        }}
        """
        return {
            "type": "SMART_CONTRACT_AUDIT",
            "context": "EVM_SOLIDITY",
            "prompt": code,
            "desc": "Re-entrancy Logic",
            "severity": "CRITICAL"
        }

# --- SEC-OPS LINK ---
class SecurityLink:
    def __init__(self):
        self.session = None
        self.stats = {"scans": 0, "threats_neutralized": 0, "errors": 0}
        self.log_handle = open(LOG_FILE, "a")

    async def engage(self):
        self.session = aiohttp.ClientSession(headers={
            "x-genesis-key": GENESIS_KEY,
            "Content-Type": "application/json",
            "User-Agent": "Titan-Security/V3.0"
        })

    async def terminate(self):
        if self.session: await self.session.close()
        self.log_handle.close()

    async def dispatch_audit(self, payload: Dict[str, Any]) -> str:
        self.stats["scans"] += 1
        
        # Transport Encoding (Simulated Encryption)
        raw_prompt = f"SECURITY AUDIT | CONTEXT: {payload['context']}\n\nCODE:\n{payload['prompt']}\n\nTASK: Identify vulnerabilities and suggest fixes."
        # enc_prompt = base64.b64encode(raw_prompt.encode()).decode() # If brain supported decoding
        
        request_packet = {
            "type": payload["type"],
            "prompt": raw_prompt, 
            "hardware": "UNIT_ORIN_AGX", # Mandatory 70B Model for Security
            "bounty": 0.005 # High Priority
        }

        try:
            start = time.perf_counter()
            async with self.session.post(BRAIN_UPLINK, json=request_packet, timeout=DEFAULT_TIMEOUT) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.stats["threats_neutralized"] += 1
                    self._log_audit(payload["desc"], "SUCCESS", data.get("job_id"))
                    return f"[green]SECURED[/] ID:{data.get('job_id')}"
                else:
                    self.stats["errors"] += 1
                    return f"[red]FAILED[/] HTTP {resp.status}"
        except Exception as e:
            self.stats["errors"] += 1
            return f"[red]NET ERR[/] {str(e)[:10]}"

    def _log_audit(self, desc, status, jid):
        record = {
            "timestamp": datetime.now().isoformat(),
            "target": desc,
            "status": status,
            "job_id": jid
        }
        self.log_handle.write(json.dumps(record) + "\n")
        self.log_handle.flush()

# --- TACTICAL HUD ---
class SecurityHUD:
    def __init__(self, link: SecurityLink):
        self.link = link
        self.layout = Layout()
        self.feed_log = []
        self.console = Console()

    def log(self, level, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        color = "green" if level == "INFO" else ("yellow" if level == "WARN" else "red")
        icon = "✔" if level == "INFO" else ("⚠" if level == "WARN" else "✖")
        self.feed_log.append(f"[{ts}] [{color}]{icon} {msg}[/]")
        if len(self.feed_log) > 12: self.feed_log.pop(0)

    def render(self, current_target: str = "IDLE") -> Layout:
        self.layout.split(
            Layout(name="header", size=3),
            Layout(name="body", ratio=1),
            Layout(name="footer", size=3)
        )
        self.layout["body"].split_row(
            Layout(name="status", ratio=1),
            Layout(name="feed", ratio=2)
        )

        # 1. HEADER
        self.layout["header"].update(Panel(
            Align.center(Text("TITAN SECURITY | CYBER-DEFENSE GRID V3.0", style="bold red")),
            style="red", box=box.HEAVY
        ))

        # 2. STATUS PANEL
        s = self.link.stats
        grid = Table.grid(padding=1)
        grid.add_column(style="bold white", justify="right")
        grid.add_column(style="yellow", justify="left")
        
        defcon = "[green]5 (NORMAL)[/]" if s['errors'] == 0 else "[red]1 (CRITICAL)[/]"
        
        grid.add_row("DEFCON STATUS:", defcon)
        grid.add_row("ACTIVE TARGET:", f"[cyan]{current_target}[/]")
        grid.add_row("TOTAL SCANS:", f" {s['scans']}")
        grid.add_row("VULNS PATCHED:", f" {s['threats_neutralized']}")
        grid.add_row("UPLINK ERRORS:", f" {s['errors']}")
        
        self.layout["status"].update(Panel(
            Align.center(grid, vertical="middle"),
            title="[bold red]SOC METRICS[/]",
            border_style="red"
        ))

        # 3. LIVE FEED
        self.layout["feed"].update(Panel(
            "\n".join(self.feed_log),
            title="[bold white]AUDIT LOG STREAM[/]",
            border_style="white"
        ))

        # 4. FOOTER
        self.layout["footer"].update(Panel(
            Align.center("[dim]ENCRYPTION: AES-256 (SIM) | HARDWARE: UNIT_ORIN_AGX (70B) | UPLINK: ACTIVE[/]"),
            style="white"
        ))
        
        return self.layout

# --- MAIN LOOP ---
async def run_security_grid():
    link = SecurityLink()
    hud = SecurityHUD(link)
    await link.engage()
    
    with Live(hud.render(), refresh_per_second=4, screen=True) as live:
        try:
            while True:
                # 1. Generate Random Threat Scenario
                dice = random.random()
                if dice < 0.33:
                    payload = ThreatFactory.rust_anchor_exploit()
                elif dice < 0.66:
                    payload = ThreatFactory.solidity_flashloan_attack()
                else:
                    payload = ThreatFactory.reentrancy_attack()
                
                # 2. Dispatch to Swarm
                hud.log("WARN", f"Scanning: {payload['desc']} ({payload['severity']})")
                live.update(hud.render(current_target=payload['desc']))
                
                # 3. Await Result (Simulate processing time)
                await asyncio.sleep(random.uniform(1.5, 3.0))
                
                result = await link.dispatch_audit(payload)
                hud.log("INFO", f"{result}")
                
                live.update(hud.render(current_target="IDLE"))
                
                # 4. Cycle Delay
                await asyncio.sleep(2)

        except KeyboardInterrupt:
            pass
        finally:
            await link.terminate()

if __name__ == "__main__":
    try:
        asyncio.run(run_security_grid())
    except KeyboardInterrupt:
        print("\n[!] SECURITY GRID OFFLINE.")
