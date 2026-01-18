#!/usr/bin/env python3
"""
TITAN SENTINEL v2.3 [INTELLIGENCE UPDATE]
=========================================
CLASSIFICATION: INTERNAL DEFENSE
MISSION: SECURITY AUDIT & THREAT IDENTIFICATION
TARGET: LOCALHOST [JETSON/ARM64]
"""

import subprocess
import os
import sys
import socket
import urllib.request
import urllib.parse
from datetime import datetime

# --- [ TELEGRAM CONFIGURATION ] ---
# Prefer environment variables so secrets aren't hardcoded; fall back to
# existing values so current deployments keep working.
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8555894547:AAEXFPDKt2WLn1hUl7bYPsmr6C24RhchJPE")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "7247592082")

# --- [ SYSTEM CONFIGURATION ] ---
# UPDATED ALLOW LIST:
# 22(SSH), 53(DNS), 80/443(Web), 3000(UI), 8000(Brain), 6379(Redis), 11434(Ollama)
# plus known dev-tool ports (NoMachine, VS Code, mDNS) on this node.
ALLOWED_PORTS = [
    22, 53, 80, 443, 3000, 8000, 6379, 11434,   # Infrastructure
    4000, 5353, 20000, 23493, 24298, 25001,     # NoMachine + mDNS
    5611                                        # VS Code Server
]

# CRITICAL: Services that MUST be running.
#
# Note: Ollama is managed via Docker on this node (not a systemd service),
# and UFW health is already covered by check_firewall(), so we do not
# duplicate them here to avoid false "OFFLINE" alarms.
CRITICAL_SERVICES = ["docker", "ssh", "fail2ban"]
LOG_FILE = os.path.expanduser("~/TitanNetwork/logs/sentinel_audit.log")

# --- [ VISUAL PROTOCOLS ] ---
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# Processes that are treated as "friend" for port-scanning purposes
# even if their ports are not in ALLOWED_PORTS.
IFF_FRIENDLY_PROCESSES = [
    "tailscaled",   # Tailscale secure overlay network
    "cloudflared",  # Cloudflare tunnel client
    "nxnode"        # NoMachine node processes
]

def print_status(sector, status, message, level="INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    if level == "PASS":
        icon = f"{Colors.GREEN}[PASS]{Colors.ENDC}"
        msg_color = Colors.GREEN
    elif level == "FAIL":
        icon = f"{Colors.FAIL}[FAIL]{Colors.ENDC}"
        msg_color = Colors.FAIL
    elif level == "WARN":
        icon = f"{Colors.WARNING}[WARN]{Colors.ENDC}"
        msg_color = Colors.WARNING
    else:
        icon = f"{Colors.BLUE}[INFO]{Colors.ENDC}"
        msg_color = Colors.CYAN

    print(f"{Colors.BLUE}{timestamp}{Colors.ENDC} | {icon} | {Colors.BOLD}{sector:<15}{Colors.ENDC} : {msg_color}{message}{Colors.ENDC}")
    return f"[{level}] {sector}: {message}"

def send_telegram_alert(message):
    """Transmits critical alerts to Command via secure uplink."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"{Colors.WARNING}TELEGRAM UPLINK DISABLED: missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID.{Colors.ENDC}")
        return
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    # Use plain text (no Markdown) to avoid formatting-related API errors.
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": f"TITAN SENTINEL ALERT\n\n{message}"
    }
    
    try:
        data = urllib.parse.urlencode(payload).encode()
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req) as resp:
            if resp.status == 200:
                print(f"{Colors.GREEN}TELEGRAM UPLINK: ALERT DELIVERED.{Colors.ENDC}")
            else:
                print(f"{Colors.FAIL}TELEGRAM UPLINK ERROR: HTTP {resp.status}{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.FAIL}TELEGRAM UPLINK FAILED: {e}{Colors.ENDC}")

# --- [ INTELLIGENCE MODULES ] ---

def check_uplink():
    sector = "UPLINK"
    try:
        response = subprocess.call(['ping', '-c', '1', '1.1.1.1'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if response == 0:
            return print_status(sector, "ONLINE", "Connection Established", "PASS")
        else:
            return print_status(sector, "OFFLINE", "NO CONNECTION TO GRID", "FAIL")
    except:
        return print_status(sector, "ERROR", "Network Interface Malfunction", "FAIL")

def check_firewall():
    sector = "FIREWALL"
    try:
        result = subprocess.check_output("sudo ufw status | grep 'Status:'", shell=True).decode().strip()
        if "active" in result.lower():
            return print_status(sector, "ACTIVE", "UFW Perimeter Secured", "PASS")
        else:
            return print_status(sector, "INACTIVE", "DEFENSE DOWN - CRITICAL", "FAIL")
    except:
        return print_status(sector, "UNKNOWN", "UFW Check Failed", "WARN")

def check_ghost_users():
    sector = "IDENTITY"
    try:
        rogues = []
        with open('/etc/passwd', 'r') as f:
            for line in f:
                parts = line.split(':')
                # Check for UID 0 (Root) but username is not 'root'
                if int(parts[2]) == 0 and parts[0] != 'root':
                    rogues.append(parts[0])
        
        if rogues:
            return print_status(sector, "BREACH", f"UNAUTHORIZED ROOT USERS: {rogues}", "FAIL")
        else:
            return print_status(sector, "SECURE", "Root Hierarchy Verified", "PASS")
    except Exception as e:
        return print_status(sector, "ERROR", str(e), "WARN")

def check_open_ports():
    sector = "PORTS"
    try:
        # Get all listening ports with process names
        cmd = "ss -tulnp" 
        output = subprocess.check_output(cmd, shell=True).decode().strip().split('\n')
        
        open_ports_info = {} 
        
        # Parse ss output
        for line in output[1:]:
            parts = line.split()
            if len(parts) >= 5:
                addr = parts[4]
                port_str = addr.split(':')[-1]
                
                # Extract process info if available
                process_info = parts[-1] if len(parts) > 6 else "Unknown"
                
                if port_str.isdigit():
                    port = int(port_str)
                    open_ports_info[port] = process_info
        
        rogue_ports = []
        rogue_details = []
        friend_ports = []
        
        for port, info in open_ports_info.items():
            if port in ALLOWED_PORTS:
                continue

            process_name = info.lower()
            # IFF: treat known friendly daemons as trusted even if
            # their ports are not on the strict allow list.
            if any(friend in process_name for friend in IFF_FRIENDLY_PROCESSES):
                friend_ports.append(f"{port} ({info})")
                continue

            rogue_ports.append(port)
            rogue_details.append(f"{port} ({info})")
        
        if rogue_ports:
            details_str = ", ".join(rogue_details)
            return print_status(sector, "BREACH", f"UNAUTHORIZED: {details_str}", "FAIL")
        elif friend_ports:
            details_str = ", ".join(friend_ports)
            return print_status(sector, "SECURE", f"All non-Titan ports identified as FRIEND via IFF: {details_str}", "PASS")
        else:
            return print_status(sector, "SECURE", f"All ports accounted for.", "PASS")
            
    except Exception as e:
        return print_status(sector, "ERROR", f"Scan Failed: {e}", "WARN")

def check_services():
    sector = "SERVICES"
    logs = []
    for service in CRITICAL_SERVICES:
        try:
            cmd = f"systemctl is-active {service}"
            status = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE).stdout.decode().strip()
            if status == "active":
                logs.append(print_status(sector, "ACTIVE", f"{service.upper()} OPERATIONAL", "PASS"))
            else:
                logs.append(print_status(sector, "DOWN", f"{service.upper()} OFFLINE", "FAIL"))
        except:
             logs.append(print_status(sector, "ERROR", f"Could not check {service}", "WARN"))
    return logs

def check_resources():
    sector = "RESOURCES"
    logs = []
    try:
        cmd = "df -h / | tail -1 | awk '{print $5}'"
        usage = int(subprocess.check_output(cmd, shell=True).decode().strip().replace('%',''))
        if usage > 90:
            logs.append(print_status(sector, "CRITICAL", f"Disk: {usage}%", "FAIL"))
        else:
            logs.append(print_status(sector, "NOMINAL", f"Disk: {usage}%", "PASS"))
    except:
        logs.append(print_status(sector, "ERROR", "Disk Check Failed", "WARN"))
    return logs

def check_failed_logins():
    sector = "INTRUSION"
    log_path = "/var/log/auth.log"
    if not os.path.exists(log_path): return print_status(sector, "MISSING", "Auth Log Not Found", "WARN")
        
    try:
        cmd = f"tail -n 500 {log_path} | grep 'Failed password' | wc -l"
        count = int(subprocess.check_output(cmd, shell=True).decode().strip())
        
        if count > 50:
            return print_status(sector, "ATTACK", f"HIGH TRAFFIC: {count} failed logins", "FAIL")
        elif count > 5:
             return print_status(sector, "ALERT", f"Suspicious Activity: {count} failed logins", "WARN")
        else:
             return print_status(sector, "SECURE", "No significant intrusion attempts", "PASS")
    except:
        return print_status(sector, "ERROR", "Log Read Failure", "WARN")

# --- [ MAIN COMMAND LOOP ] ---
def main():
    # Ensure directory exists
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    
    # Banner
    print(f"\n{Colors.HEADER}{Colors.BOLD}")
    print("/// TITAN SENTINEL V2.3 INITIALIZING...")
    print(f"/// TARGET: {socket.gethostname()}")
    print(f"/// TIME:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=====================================================")
    print(f"{Colors.ENDC}")

    audit_log = []
    alerts = []
    
    # Execute Modules
    audit_log.append(check_uplink())
    print("-" * 50)
    audit_log.append(check_firewall())
    audit_log.append(check_ghost_users())
    audit_log.append(check_open_ports())
    audit_log.append(check_failed_logins())
    print("-" * 50)
    audit_log.extend(check_services())
    print("-" * 50)
    audit_log.extend(check_resources())
    
    print(f"\n{Colors.HEADER}/// DIAGNOSTICS COMPLETE. LOGGING TO DISK.{Colors.ENDC}\n")
    
    # File Logging & Alert Aggregation
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(LOG_FILE, "a") as f:
        f.write(f"\n--- SENTINEL REPORT [{timestamp}] ---\n")
        
        # Flatten the list (handle list of lists from services/resources)
        flat_log = []
        for entry in audit_log:
            if isinstance(entry, list):
                flat_log.extend(entry)
            else:
                flat_log.append(entry)

        for entry in flat_log:
            f.write(str(entry) + "\n")
            alerts.append(str(entry))

    # Always send a full status report via Telegram for now.
    alert_msg = "\n".join(alerts)
    print(f"{Colors.BLUE}{Colors.BOLD}TRANSMITTING FULL STATUS REPORT TO TELEGRAM...{Colors.ENDC}")
    send_telegram_alert(f"NODE: {socket.gethostname()}\nTIME: {timestamp}\n\n" + alert_msg)

    print(f"{Colors.GREEN}>> STATUS REPORT DISPATCHED. LOCAL DIAGNOSTICS COMPLETE.{Colors.ENDC}")

if __name__ == "__main__":
    if os.geteuid() != 0:
        print(f"{Colors.FAIL}{Colors.BOLD}CRITICAL ERROR: SENTINEL REQUIRES ROOT PRIVILEGES.{Colors.ENDC}")
        print("Run with: sudo python3 titan_sentinel.py")
        sys.exit(1)
    main()
