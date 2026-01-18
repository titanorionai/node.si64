#!/home/titan/TitanNetwork/venv/bin/python3
"""
TITAN ORION | Master Control Nova (tkinter)
Crash-safe control surface for SI64 + Vanguard bot.
"""

import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

import requests
import tkinter as tk
from tkinter import ttk

# Palette
COLOR_BG_DARK = "#0a0a0e"
COLOR_BG_PANEL = "#0f0f1a"
COLOR_ACCENT = "#00d4ff"
COLOR_PURPLE = "#7c3aed"
COLOR_SUCCESS = "#51cf66"
COLOR_WARN = "#ff6b6b"
COLOR_DIM = "#00a8cc"
COLOR_ERROR = "#ff3333"


class SI64Monitor:
    def __init__(self, api_url="http://127.0.0.1:8000"):
        self.api_url = api_url
        self.data = {}
        self.error = None

    def fetch(self):
        try:
            resp = requests.get(f"{self.api_url}/api/stats", timeout=4)
            resp.raise_for_status()
            self.data = resp.json()
            self.error = None
            return True
        except Exception as exc:  # noqa: BLE001
            self.error = str(exc)
            return False

    def view(self):
        return {
            "status": self.data.get("status", "unknown"),
            "fleet_size": self.data.get("fleet_size", 0),
            "jobs_queued": self.data.get("jobs_queued", 0),
            "jobs_completed": self.data.get("jobs_completed", 0),
            "total_compute": self.data.get("total_compute_hours", 0.0),
            "uptime": self.data.get("uptime_seconds", 0),
            "error": self.error,
        }


class MasterControlNova(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TITAN ORION | Master Control Nova")
        self.geometry("1280x780")
        self.configure(bg=COLOR_BG_DARK)
        self.monitor = SI64Monitor()
        self.bot_running = False

        self._init_styles()
        self._build_layout()
        self._refresh_bot_state()
        self._update_stats()
        self._update_stats_loop()
        self._update_clock()

    # ---------- Styles ----------
    def _init_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Panel.TFrame", background=COLOR_BG_PANEL, relief="solid", borderwidth=1)
        style.configure("TFrame", background=COLOR_BG_DARK)
        style.configure("Title.TLabel", background=COLOR_BG_PANEL, foreground=COLOR_ACCENT, font=("Courier", 24, "bold"))
        style.configure("Header.TLabel", background=COLOR_BG_PANEL, foreground=COLOR_PURPLE, font=("Courier", 14, "bold"))
        style.configure("Value.TLabel", background=COLOR_BG_PANEL, foreground=COLOR_ACCENT, font=("Courier", 14))
        style.configure("Dim.TLabel", background=COLOR_BG_PANEL, foreground=COLOR_DIM, font=("Courier", 12))
        style.configure("Status.TLabel", background=COLOR_BG_PANEL, foreground=COLOR_SUCCESS, font=("Courier", 13, "bold"))
        style.configure("Btn.TButton", font=("Courier", 14, "bold"), padding=10)

    # ---------- Layout ----------
    def _build_layout(self):
        # Header
        header = ttk.Frame(self, style="Panel.TFrame")
        header.pack(fill="x", padx=10, pady=10)

        ttk.Label(header, text="▓▒░ TITAN ORION ░▒▓", style="Title.TLabel").pack(side="left", padx=12, pady=10)
        self.clock_label = ttk.Label(header, text="--:--:--", style="Dim.TLabel")
        self.clock_label.pack(side="right", padx=12)
        self.status_label = ttk.Label(header, text="● READY", style="Status.TLabel")
        self.status_label.pack(side="right", padx=12)

        # Main content
        body = ttk.Frame(self, style="TFrame")
        body.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(1, weight=1)

        # Controls panel
        ctrl = ttk.Frame(body, style="Panel.TFrame")
        ctrl.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        ctrl.columnconfigure(0, weight=1)
        ttk.Label(ctrl, text="CONTROL CENTER", style="Header.TLabel").grid(row=0, column=0, sticky="w", padx=12, pady=(12, 8))

        self.bot_btn = ttk.Button(ctrl, text="▶ START VANGUARD BOT", style="Btn.TButton", command=self._toggle_bot)
        self.bot_btn.grid(row=1, column=0, sticky="ew", padx=12, pady=6)

        ttk.Button(ctrl, text="🔄 RESTART SI64 NETWORK", style="Btn.TButton", command=self._restart_network).grid(
            row=2, column=0, sticky="ew", padx=12, pady=6
        )
        ttk.Button(ctrl, text="▶ LAUNCH DATA FACTORY", style="Btn.TButton", command=self._launch_data_factory).grid(
            row=3, column=0, sticky="ew", padx=12, pady=6
        )
        ttk.Button(ctrl, text="▶ MEV SNIPER", style="Btn.TButton", command=lambda: self._log("MEV Sniper opened")).grid(
            row=4, column=0, sticky="ew", padx=12, pady=6
        )
        ttk.Button(ctrl, text="▶ CODING ENGINE", style="Btn.TButton", command=lambda: self._log("Coding Engine opened")).grid(
            row=5, column=0, sticky="ew", padx=12, pady=6
        )
        ttk.Button(ctrl, text="⊘ EXIT UI", style="Btn.TButton", command=self.destroy).grid(
            row=6, column=0, sticky="ew", padx=12, pady=(6, 14)
        )

        # Stats panel
        stats = ttk.Frame(body, style="Panel.TFrame")
        stats.grid(row=0, column=1, sticky="nsew", padx=6, pady=6)
        stats.columnconfigure(1, weight=1)
        ttk.Label(stats, text="SI64 NETWORK", style="Header.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(12, 8))

        self.stat_labels = {
            "status": tk.StringVar(value="Status: unknown"),
            "fleet": tk.StringVar(value="Fleet Size: --"),
            "jobsq": tk.StringVar(value="Jobs Queued: --"),
            "jobsc": tk.StringVar(value="Jobs Completed: --"),
            "compute": tk.StringVar(value="Compute Hours: --"),
            "uptime": tk.StringVar(value="Uptime: --"),
            "error": tk.StringVar(value="")
        }

        ttk.Label(stats, textvariable=self.stat_labels["status"], style="Value.TLabel").grid(row=1, column=0, columnspan=2, sticky="w", padx=12, pady=4)
        ttk.Label(stats, textvariable=self.stat_labels["fleet"], style="Value.TLabel").grid(row=2, column=0, sticky="w", padx=12, pady=4)
        ttk.Label(stats, textvariable=self.stat_labels["jobsq"], style="Value.TLabel").grid(row=3, column=0, sticky="w", padx=12, pady=4)
        ttk.Label(stats, textvariable=self.stat_labels["jobsc"], style="Value.TLabel").grid(row=3, column=1, sticky="w", padx=12, pady=4)
        ttk.Label(stats, textvariable=self.stat_labels["compute"], style="Value.TLabel").grid(row=4, column=0, sticky="w", padx=12, pady=4)
        ttk.Label(stats, textvariable=self.stat_labels["uptime"], style="Value.TLabel").grid(row=4, column=1, sticky="w", padx=12, pady=4)
        ttk.Label(stats, textvariable=self.stat_labels["error"], style="Dim.TLabel").grid(row=5, column=0, columnspan=2, sticky="w", padx=12, pady=(6, 10))

        ttk.Button(stats, text="⟳ REFRESH STATS", style="Btn.TButton", command=self._update_stats).grid(
            row=6, column=0, sticky="w", padx=12, pady=(0, 12)
        )

        # Log panel
        log_panel = ttk.Frame(body, style="Panel.TFrame")
        log_panel.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=6, pady=6)
        log_panel.columnconfigure(0, weight=1)
        log_panel.rowconfigure(1, weight=1)
        ttk.Label(log_panel, text="EVENT LOG", style="Header.TLabel").grid(row=0, column=0, sticky="w", padx=12, pady=(12, 6))

        self.log_area = tk.Text(
            log_panel,
            height=10,
            bg=COLOR_BG_PANEL,
            fg=COLOR_ACCENT,
            insertbackground=COLOR_ACCENT,
            relief="solid",
            bd=1,
            font=("Courier", 12),
        )
        self.log_area.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.log_area.configure(state="disabled")

    # ---------- Helpers ----------
    def _set_status(self, text, color=COLOR_SUCCESS):
        self.status_label.configure(text=text, foreground=color)

    def _log(self, message, color=COLOR_ACCENT):
        self.log_area.configure(state="normal")
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_area.insert("end", f"[{timestamp}] {message}\n")
        self.log_area.see("end")
        self.log_area.configure(state="disabled")

    def _update_clock(self):
        self.clock_label.configure(text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.after(1000, self._update_clock)

    # ---------- Bot controls ----------
    def _refresh_bot_state(self):
        try:
            res = subprocess.run([
                "docker", "inspect", "-f", "{{.State.Running}}", "titan-vanguard-unit"
            ], capture_output=True, text=True, timeout=5)
            self.bot_running = res.stdout.strip() == "true"
        except Exception:
            self.bot_running = False
        self._sync_bot_button()

    def _sync_bot_button(self):
        if self.bot_running:
            self.bot_btn.configure(text="⏸ STOP VANGUARD BOT")
        else:
            self.bot_btn.configure(text="▶ START VANGUARD BOT")

    def _toggle_bot(self):
        try:
            if self.bot_running:
                subprocess.run(["docker", "stop", "titan-vanguard-unit"], timeout=12, check=False)
                self.bot_running = False
                self._log("⊘ Vanguard bot stopped", COLOR_WARN)
                self._set_status("BOT: OFFLINE", COLOR_WARN)
            else:
                subprocess.run(["docker", "start", "titan-vanguard-unit"], timeout=12, check=False)
                self.bot_running = True
                self._log("▶ Vanguard bot started", COLOR_SUCCESS)
                self._set_status("BOT: ONLINE", COLOR_SUCCESS)
        except Exception as exc:  # noqa: BLE001
            self._log(f"Bot control error: {exc}", COLOR_ERROR)
            self._set_status("BOT: ERROR", COLOR_ERROR)
        finally:
            self._sync_bot_button()

    # ---------- Network ----------
    def _restart_network(self):
        self._set_status("NETWORK: RESTARTING", COLOR_WARN)
        self._log("🔄 Restarting SI64 network...")
        try:
            res = subprocess.run([
                "docker", "network", "ls", "--filter", "name=titan", "-q"
            ], capture_output=True, text=True, timeout=6)
            if res.stdout.strip():
                subprocess.run(["docker", "restart", "titan-vanguard-unit"], timeout=12, check=False)
            subprocess.run(["resolvectl", "flush-caches"], timeout=5, check=False)
            self._set_status("NETWORK: REFRESHED", COLOR_SUCCESS)
            self._log("SI64 network refresh complete", COLOR_SUCCESS)
            self._update_stats()
        except subprocess.TimeoutExpired:
            self._set_status("NETWORK: TIMEOUT", COLOR_WARN)
            self._log("Network restart timed out", COLOR_WARN)
        except Exception as exc:  # noqa: BLE001
            self._set_status("NETWORK: ERROR", COLOR_ERROR)
            self._log(f"Network restart failed: {exc}", COLOR_ERROR)

    # ---------- Launchers ----------
    def _launch_data_factory(self):
        script_path = Path(__file__).parent / "start_datafactory.sh"
        try:
            subprocess.Popen(["bash", str(script_path)], env={**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":1")})
            self._log("Data Factory launched", COLOR_SUCCESS)
        except Exception as exc:  # noqa: BLE001
            self._log(f"Launch failed: {exc}", COLOR_ERROR)

    # ---------- Stats ----------
    def _update_stats(self):
        if self.monitor.fetch():
            data = self.monitor.view()
            up = data.get("uptime", 0)
            hrs, mins = up // 3600, (up % 3600) // 60
            self.stat_labels["status"].set(f"Status: {data.get('status', 'unknown')}")
            self.stat_labels["fleet"].set(f"Fleet Size: {data.get('fleet_size', 0)}")
            self.stat_labels["jobsq"].set(f"Jobs Queued: {data.get('jobs_queued', 0)}")
            self.stat_labels["jobsc"].set(f"Jobs Completed: {data.get('jobs_completed', 0)}")
            self.stat_labels["compute"].set(f"Compute Hours: {data.get('total_compute', 0):.1f}h")
            self.stat_labels["uptime"].set(f"Uptime: {hrs}h {mins}m")
            self.stat_labels["error"].set("Last update: " + datetime.now().strftime("%H:%M:%S"))
            self._set_status("● ONLINE", COLOR_SUCCESS)
        else:
            self.stat_labels["error"].set(f"Error: {self.monitor.error}")
            self._set_status("● SI64 OFFLINE", COLOR_WARN)

    def _update_stats_loop(self):
        self._update_stats()
        self.after(10000, self._update_stats_loop)


def main():
    if "DISPLAY" not in os.environ:
        os.environ["DISPLAY"] = ":1"
    app = MasterControlNova()
    app.mainloop()


if __name__ == "__main__":
    main()
