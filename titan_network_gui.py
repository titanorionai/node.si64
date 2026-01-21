#!/usr/bin/env python3
"""
TITAN NETWORK // COMMAND DECK v2.0
CLASSIFICATION: COMMANDER EYES ONLY
MISSION: DRIVING CORE SI64.NET OPERATIONS
"""

import os
import sys
import time
import threading
import subprocess
import webbrowser
from pathlib import Path
from datetime import datetime

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

# --- [ EXTERNAL DEPENDENCIES ] ---
try:
    import requests
except ImportError:
    print("[CRITICAL] 'requests' library missing. Install via pip.")
    sys.exit(1)

try:
    import psutil
except ImportError:
    psutil = None  # Graceful degradation if monitoring isn't installed

# --- [ CONFIGURATION ] ---
API_BASE = os.getenv("TITAN_GUI_API_BASE", "http://127.0.0.1:8000")
GENESIS_KEY = os.getenv("GENESIS_KEY", "TITAN_GENESIS_KEY_V1_SECURE")

# --- [ VISUAL THEME ] ---
COLOR_BG_MAIN = "#050505"      # Void Black
COLOR_BG_PANEL = "#111111"     # Carbon Fiber
COLOR_ACCENT = "#00ffcc"       # Cyan Neon (Primary)
COLOR_ALERT = "#ff3333"        # Red Alert (Critical)
COLOR_SUCCESS = "#33ff33"      # Terminal Green (Good)
COLOR_TEXT = "#e0e0e0"         # Off-White
FONT_MAIN = ("Segoe UI", 10)
FONT_MONO = ("Consolas", 10)
FONT_HEADER = ("Segoe UI", 12, "bold")

class TitanCommandDeck(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("TITAN NETWORK // COMMAND DECK")
        self.geometry("1600x950")
        self.configure(bg=COLOR_BG_MAIN)
        
        # Project Root
        self.project_root = Path(__file__).resolve().parent

        # Initialize
        self._init_styles()
        self._build_layout()
        
        # Start Background Processes
        self._start_clock()
        if psutil:
            self._start_hardware_monitor()
        self._poll_api_stats()
        self.log_tactical("SYSTEM INITIALIZED. WELCOME, COMMANDER.", "INFO")

    # ------------------------------------------------------------------
    # VISUAL CORE
    # ------------------------------------------------------------------
    def _init_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")

        # Global Config
        style.configure("TFrame", background=COLOR_BG_MAIN)
        style.configure("TLabel", background=COLOR_BG_MAIN, foreground=COLOR_TEXT, font=FONT_MAIN)
        
        # Panels
        style.configure("Panel.TFrame", background=COLOR_BG_PANEL, relief="flat")
        style.configure("PanelHeader.TLabel", background=COLOR_BG_PANEL, foreground=COLOR_ACCENT, font=FONT_HEADER)
        
        # Buttons
        style.configure("Command.TButton", 
                        background="#222", 
                        foreground=COLOR_ACCENT, 
                        borderwidth=1, 
                        font=("Segoe UI", 9, "bold"))
        style.map("Command.TButton", 
                  background=[("active", COLOR_ACCENT)], 
                  foreground=[("active", "#000")])

        style.configure("Alert.TButton", 
                        background="#330000", 
                        foreground=COLOR_ALERT, 
                        borderwidth=1,
                        font=("Segoe UI", 9, "bold"))
        style.map("Alert.TButton", 
                  background=[("active", COLOR_ALERT)], 
                  foreground=[("active", "#fff")])

        # Progress Bars (Hardware Monitors)
        style.configure("Cyan.Horizontal.TProgressbar", background=COLOR_ACCENT, troughcolor="#222", borderwidth=0)
        style.configure("Red.Horizontal.TProgressbar", background=COLOR_ALERT, troughcolor="#222", borderwidth=0)

    def _build_layout(self) -> None:
        # --- TOP HEADER ---
        header = ttk.Frame(self, style="TFrame")
        header.pack(fill="x", padx=15, pady=10)
        
        # Logo / Title
        ttk.Label(header, text="SI64 // SOVEREIGN COMPUTE PROTOCOL", font=("Impact", 24), foreground=COLOR_TEXT).pack(side="left")
        
        # Live Clock
        self.clock_label = ttk.Label(header, text="00:00:00 UTC", font=("Consolas", 14), foreground=COLOR_ACCENT)
        self.clock_label.pack(side="right")
        
        # Divider
        tk.Frame(self, bg=COLOR_ACCENT, height=2).pack(fill="x", padx=15, pady=(0, 15))

        # --- MAIN CONTAINER ---
        main_container = ttk.Frame(self, style="TFrame")
        main_container.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # --- LEFT COLUMN (TELEMETRY) ---
        left_col = ttk.Frame(main_container, style="TFrame", width=400)
        left_col.pack(side="left", fill="y", padx=(0, 10))
        left_col.pack_propagate(False) # Force width

        self._build_telemetry_panel(left_col)
        self._build_hardware_panel(left_col)
        self._build_quick_actions(left_col)

        # --- RIGHT COLUMN (TABS & TERMINAL) ---
        right_col = ttk.Frame(main_container, style="TFrame")
        right_col.pack(side="left", fill="both", expand=True)

        self._build_mission_tabs(right_col)

    # ------------------------------------------------------------------
    # PANELS
    # ------------------------------------------------------------------
    def _build_telemetry_panel(self, parent):
        frame = ttk.LabelFrame(parent, text=" NETWORK TELEMETRY ", style="Panel.TFrame", padding=10)
        frame.pack(fill="x", pady=(0, 10))

        # Grid layout for stats
        self.stat_labels = {}
        stats = [("FLEET SIZE", "0"), ("JOB QUEUE", "0"), ("REVENUE (SOL)", "0.0000"), ("BRAIN STATUS", "OFFLINE")]
        
        for i, (label, default) in enumerate(stats):
            ttk.Label(frame, text=label, font=("Segoe UI", 8), background=COLOR_BG_PANEL, foreground="#888").grid(row=i, column=0, sticky="w", pady=2)
            lbl = ttk.Label(frame, text=default, font=("Consolas", 12, "bold"), background=COLOR_BG_PANEL, foreground=COLOR_ACCENT)
            lbl.grid(row=i, column=1, sticky="e", pady=2)
            self.stat_labels[label] = lbl
            
        # Specific styling for status
        self.stat_labels["BRAIN STATUS"].configure(foreground=COLOR_ALERT)

    def _build_hardware_panel(self, parent):
        frame = ttk.LabelFrame(parent, text=" LOCAL HARDWARE ", style="Panel.TFrame", padding=10)
        frame.pack(fill="x", pady=(0, 10))

        if not psutil:
            ttk.Label(frame, text="PSUTIL LIB MISSING", background=COLOR_BG_PANEL, foreground=COLOR_ALERT).pack()
            return

        ttk.Label(frame, text="CPU LOAD", background=COLOR_BG_PANEL, font=("Segoe UI", 8)).pack(anchor="w")
        self.cpu_bar = ttk.Progressbar(frame, style="Cyan.Horizontal.TProgressbar", length=100, mode='determinate')
        self.cpu_bar.pack(fill="x", pady=(0, 8))

        ttk.Label(frame, text="RAM USAGE", background=COLOR_BG_PANEL, font=("Segoe UI", 8)).pack(anchor="w")
        self.ram_bar = ttk.Progressbar(frame, style="Cyan.Horizontal.TProgressbar", length=100, mode='determinate')
        self.ram_bar.pack(fill="x", pady=(0, 5))
        
        self.hw_label = ttk.Label(frame, text="Scanning...", background=COLOR_BG_PANEL, font=("Consolas", 8))
        self.hw_label.pack(anchor="e")

    def _build_quick_actions(self, parent):
        frame = ttk.LabelFrame(parent, text=" RAPID DEPLOYMENT ", style="Panel.TFrame", padding=10)
        frame.pack(fill="x", pady=(0, 10))

        ttk.Button(frame, text="LAUNCH DASHBOARD (WEB)", style="Command.TButton", command=self._open_web).pack(fill="x", pady=2)
        tk.Frame(frame, bg="#333", height=1).pack(fill="x", pady=5)
        ttk.Button(frame, text="FIRE STRESS TEST (LOCAL)", style="Alert.TButton", command=self._stress_local).pack(fill="x", pady=2)
        ttk.Button(frame, text="FIRE STRESS TEST (REMOTE)", style="Alert.TButton", command=self._stress_remote).pack(fill="x", pady=2)

    def _build_mission_tabs(self, parent):
        # Custom Notebook styling
        style = ttk.Style()
        style.configure("TNotebook", background=COLOR_BG_MAIN, borderwidth=0)
        style.configure("TNotebook.Tab", background="#222", foreground="#888", padding=[15, 5], font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab", background=[("selected", COLOR_ACCENT)], foreground=[("selected", "#000")])

        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill="both", expand=True)

        # Tabs
        self.tab_sitrep = self._create_tab("SITREP")
        self.tab_battle_group = self._create_tab("BATTLE GROUP")
        self.tab_ledger = self._create_tab("LEDGER")
        self.tab_contracts = self._create_tab("CONTRACTS")
        self.tab_black_box = self._create_tab("BLACK BOX")

        # Build Tab Content
        self._build_sitrep_tab(self.tab_sitrep)
        self._build_fleet_tab(self.tab_battle_group)
        self._build_log_tab(self.tab_black_box)
        
        # Build Ledger/Contracts (Reusing generic text viewers for now, can expand later)
        self._build_generic_viewer(self.tab_ledger, "Ledger Data")
        self._build_generic_viewer(self.tab_contracts, "Active Contracts")

    def _create_tab(self, title):
        frame = ttk.Frame(self.notebook, style="Panel.TFrame")
        self.notebook.add(frame, text=title)
        return frame

    # ------------------------------------------------------------------
    # TAB CONTENTS
    # ------------------------------------------------------------------
    def _build_sitrep_tab(self, parent):
        # A large tactical terminal for general output
        self.sitrep_term = self._create_terminal(parent)
        self.sitrep_term.insert("1.0", "WAITING FOR INTELLIGENCE REPORT...\n")

    def _build_fleet_tab(self, parent):
        # Controls
        ctrl = ttk.Frame(parent, style="Panel.TFrame")
        ctrl.pack(fill="x", padx=10, pady=10)
        ttk.Button(ctrl, text="SCAN NETWORK TOPOLOGY", style="Command.TButton", command=self._refresh_fleet).pack(side="right")

        # Deploy Fleet Buttons
        ttk.Button(ctrl, text="DEPLOY FLEET [LOCAL]", style="Command.TButton", command=self._deploy_fleet_local).pack(side="left", padx=5)
        ttk.Button(ctrl, text="DEPLOY FLEET [REMOTE]", style="Command.TButton", command=self._deploy_fleet_remote).pack(side="left", padx=5)

        # ORIN Worker Controls
        ttk.Button(ctrl, text="START ORIN (SYSTEMD)", style="Command.TButton", command=self._start_orin).pack(side="left", padx=5)
        ttk.Button(ctrl, text="RESTART ORIN (SYSTEMD)", style="Command.TButton", command=self._restart_orin).pack(side="left", padx=5)
        ttk.Button(ctrl, text="KILL ORIN (SYSTEMD)", style="Alert.TButton", command=self._stop_orin).pack(side="left", padx=5)
        ttk.Button(ctrl, text="START ORIN (PYTHON)", style="Command.TButton", command=self._start_orin_python).pack(side="left", padx=5)
        ttk.Button(ctrl, text="RESTART ORIN (PYTHON)", style="Command.TButton", command=self._restart_orin_python).pack(side="left", padx=5)
        ttk.Button(ctrl, text="KILL ORIN (PYTHON)", style="Alert.TButton", command=self._stop_orin_python).pack(side="left", padx=5)

        # Kill Bots Feature
        ttk.Button(ctrl, text="KILL ALL BOTS", style="Alert.TButton", command=self._kill_all_bots).pack(side="left", padx=5)

        self.fleet_term = self._create_terminal(parent)
    def _start_orin(self):
        self._run_shell_cmd("START ORIN (SYSTEMD)", ["systemctl", "start", "si64-genesis.service"])

    def _restart_orin(self):
        self._run_shell_cmd("RESTART ORIN (SYSTEMD)", ["systemctl", "restart", "si64-genesis.service"])

    def _stop_orin(self):
        self._run_shell_cmd("STOP ORIN (SYSTEMD)", ["systemctl", "stop", "si64-genesis.service"])

    def _start_orin_python(self):
        self._run_shell_cmd("START ORIN (PYTHON)", [sys.executable, "core/limb/worker_node.py"])

    def _restart_orin_python(self):
        self._run_shell_cmd("RESTART ORIN (PYTHON)", ["bash", "-c", "pkill -f core/limb/worker_node.py && sleep 2 && nohup python3 core/limb/worker_node.py > logs/worker_node.log 2>&1 &"])

    def _stop_orin_python(self):
        self._run_shell_cmd("KILL ORIN (PYTHON)", ["pkill", "-f", "core/limb/worker_node.py"])

    def _kill_all_bots(self):
        self._run_shell_cmd("KILL ALL BOTS", ["pkill", "-f", "vanguard_bot.py"])

    def _build_log_tab(self, parent):
        ctrl = ttk.Frame(parent, style="Panel.TFrame")
        ctrl.pack(fill="x", padx=10, pady=10)
        ttk.Button(ctrl, text="FETCH SYSTEM LOGS", style="Command.TButton", command=self._fetch_logs).pack(side="right")
        
        self.log_term = self._create_terminal(parent)

    def _build_generic_viewer(self, parent, placeholder):
        self._create_terminal(parent).insert("1.0", f"AWAITING DATA STREAM: {placeholder}...\n")

    def _create_terminal(self, parent):
        """Creates a Matrix-style scrolling text box."""
        term = scrolledtext.ScrolledText(parent, bg="#080808", fg=COLOR_TEXT, insertbackground=COLOR_ACCENT, 
                                         font=FONT_MONO, relief="flat", padx=10, pady=10)
        term.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Color Tags
        term.tag_config("INFO", foreground=COLOR_ACCENT)
        term.tag_config("WARN", foreground="#ffaa00")
        term.tag_config("CRIT", foreground=COLOR_ALERT, font=("Consolas", 10, "bold"))
        term.tag_config("HEADER", foreground="#fff", font=("Consolas", 11, "bold", "underline"))
        
        return term

    # ------------------------------------------------------------------
    # LOGIC & ACTIONS
    # ------------------------------------------------------------------
    def log_tactical(self, message, level="INFO"):
        """Logs to the SITREP terminal with timestamps."""
        ts = datetime.utcnow().strftime("%H:%M:%S")
        full_msg = f"[{ts}] [{level}] {message}\n"
        
        self.sitrep_term.configure(state="normal")
        self.sitrep_term.insert(tk.END, full_msg, level)
        self.sitrep_term.see(tk.END)
        self.sitrep_term.configure(state="disabled")

    def _start_clock(self):
        now = datetime.utcnow().strftime("%H:%M:%S UTC")
        self.clock_label.configure(text=now)
        self.after(1000, self._start_clock)

    def _start_hardware_monitor(self):
        """Updates CPU/RAM bars."""
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        
        self.cpu_bar['value'] = cpu
        self.ram_bar['value'] = ram
        
        # Change color if critical
        style_cpu = "Red.Horizontal.TProgressbar" if cpu > 85 else "Cyan.Horizontal.TProgressbar"
        style_ram = "Red.Horizontal.TProgressbar" if ram > 85 else "Cyan.Horizontal.TProgressbar"
        
        self.cpu_bar.configure(style=style_cpu)
        self.ram_bar.configure(style=style_ram)
        
        self.hw_label.configure(text=f"CPU: {cpu}% | RAM: {ram}%")
        
        self.after(2000, self._start_hardware_monitor)

    def _poll_api_stats(self):
        """Fetches live data from the Brain."""
        try:
            resp = requests.get(f"{API_BASE}/api/stats", timeout=1)
            if resp.ok:
                data = resp.json()
                self.stat_labels["FLEET SIZE"].configure(text=str(data.get("fleet_size", 0)))
                self.stat_labels["JOB QUEUE"].configure(text=str(data.get("queue_depth", 0)))
                rev = data.get("total_revenue", 0.0)
                self.stat_labels["REVENUE (SOL)"].configure(text=f"{rev:.4f}")
                
                self.stat_labels["BRAIN STATUS"].configure(text="ONLINE", foreground=COLOR_SUCCESS)
            else:
                self.stat_labels["BRAIN STATUS"].configure(text=f"ERR {resp.status_code}", foreground=COLOR_ALERT)
        except:
            self.stat_labels["BRAIN STATUS"].configure(text="UNREACHABLE", foreground=COLOR_ALERT)
        
        self.after(3000, self._poll_api_stats)

    # --- COMMANDS ---

    def _run_shell_cmd(self, title, cmd, env=None):
        self.log_tactical(f"EXECUTING: {title}...", "WARN")
        
        def worker():
            full_env = os.environ.copy()
            if env: full_env.update(env)
            
            try:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                        text=True, cwd=str(self.project_root), env=full_env)
                for line in proc.stdout:
                    self.sitrep_term.configure(state="normal")
                    self.sitrep_term.insert(tk.END, f"   > {line}")
                    self.sitrep_term.see(tk.END)
                    self.sitrep_term.configure(state="disabled")
                
                self.log_tactical(f"{title} COMPLETE.", "SUCCESS")
            except Exception as e:
                self.log_tactical(f"{title} FAILED: {str(e)}", "CRIT")

        threading.Thread(target=worker, daemon=True).start()

    def _deploy_fleet_local(self):
        self._run_shell_cmd("DEPLOY FLEET (LOCAL)", ["bash", "deploy_fleet.sh", "5"])

    def _deploy_fleet_remote(self):
        self._run_shell_cmd("DEPLOY FLEET (REMOTE)", ["bash", "deploy_fleet.sh", "5"], {"TARGET_MODE": "remote"})

    def _stress_local(self):
        if messagebox.askyesno("CONFIRM LAUNCH", "AUTHORIZE LOCAL ORDNANCE RELEASE?\nThis will hammer the CPU."):
            self._run_shell_cmd("STRESS TEST (LOCAL)", [sys.executable, "scripts/titan_stress_test.py"])

    def _stress_remote(self):
        if messagebox.askyesno("CONFIRM LAUNCH", "AUTHORIZE REMOTE ORDNANCE RELEASE?\nTarget: si64.net"):
            self._run_shell_cmd("STRESS TEST (REMOTE)", [sys.executable, "scripts/titan_stress_test.py"])

    def _refresh_fleet(self):
        try:
            resp = requests.get(f"{API_BASE}/api/fleet", timeout=2)
            if resp.ok:
                data = resp.json()
                self.fleet_term.configure(state="normal")
                self.fleet_term.delete("1.0", tk.END)
                self.fleet_term.insert(tk.END, "FLEET TOPOLOGY SCAN COMPLETE\n", "HEADER")
                self.fleet_term.insert(tk.END, "--------------------------------\n")
                
                for pool, info in data.get("pools", {}).items():
                    self.fleet_term.insert(tk.END, f"CLASS: {pool} | COUNT: {info['count']}\n", "INFO")
                    for node in info.get("nodes", []):
                        self.fleet_term.insert(tk.END, f"  > ID: {node['id']} | REP: {node['reputation']}\n")
                    self.fleet_term.insert(tk.END, "\n")
                
                self.fleet_term.configure(state="disabled")
        except Exception as e:
            self.log_tactical(f"FLEET SCAN FAILED: {e}", "CRIT")

    def _fetch_logs(self):
        log_path = self.project_root / "brain/logs/overlord.log"
        if log_path.exists():
            with open(log_path, "r") as f:
                lines = f.readlines()[-50:]
            self.log_term.configure(state="normal")
            self.log_term.delete("1.0", tk.END)
            self.log_term.insert(tk.END, "".join(lines))
            self.log_term.configure(state="disabled")
        else:
            self.log_tactical("LOG FILE NOT FOUND", "WARN")

    def _open_web(self):
        webbrowser.open(API_BASE)

if __name__ == "__main__":
    if "DISPLAY" not in os.environ or not os.environ["DISPLAY"]:
        os.environ["DISPLAY"] = ":0" # Fallback for desktop launch
    app = TitanCommandDeck()
    app.mainloop()
