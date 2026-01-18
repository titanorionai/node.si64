#!/home/titan/TitanNetwork/venv/bin/python3
"""
TITAN LAUNCHER (Nova)
Launcher for Master Control Nova (tkinter-only).
"""

import os
import sys
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from datetime import datetime


class TitanLauncher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TITAN LAUNCHER | Nova")
        self.geometry("520x320")
        self.configure(bg="#0a0a0e")
        self._init_styles()
        self._build_ui()

    def _init_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#0a0a0e")
        style.configure("Panel.TFrame", background="#0f0f1a", relief="solid", borderwidth=1)
        style.configure("Title.TLabel", background="#0f0f1a", foreground="#00d4ff", font=("Courier", 24, "bold"))
        style.configure("Sub.TLabel", background="#0f0f1a", foreground="#00d4ff", font=("Courier", 12))
        style.configure("Btn.TButton", font=("Courier", 14, "bold"), padding=10)
        style.configure("Status.TLabel", background="#0f0f1a", foreground="#51cf66", font=("Courier", 11))

    def _build_ui(self):
        root = ttk.Frame(self, style="Panel.TFrame")
        root.pack(fill="both", expand=True, padx=12, pady=12)

        ttk.Label(root, text="▓▒░ TITAN LAUNCHER ░▒▓", style="Title.TLabel").pack(pady=(10, 6))
        ttk.Label(root, text="Master Control Nova • SI64.NET", style="Sub.TLabel").pack(pady=(0, 16))

        btn_frame = ttk.Frame(root, style="Panel.TFrame")
        btn_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Button(btn_frame, text="▶ LAUNCH MASTER CONTROL", style="Btn.TButton", command=self._launch_master_control).pack(fill="x", pady=8)
        ttk.Button(btn_frame, text="▶ LAUNCH DATA FACTORY", style="Btn.TButton", command=self._launch_factory).pack(fill="x", pady=8)
        ttk.Button(btn_frame, text="⚙ SYSTEM SETTINGS", style="Btn.TButton", command=self._show_settings).pack(fill="x", pady=8)

        self.status = ttk.Label(root, text="● Ready", style="Status.TLabel")
        self.status.pack(pady=(6, 4))

    def _launch_master_control(self):
        self._set_status("⌛ Launching Master Control...", warn=False)
        try:
            python_cmd = sys.executable
            script_path = Path(__file__).parent / "master_control_nova.py"
            env = {**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":1")}
            subprocess.Popen(
                [python_cmd, str(script_path)],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            self._set_status("✅ Master Control Launched", warn=False)
            self._log_event("Master Control Nova launched")
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"❌ Error: {exc}", warn=True)

    def _launch_factory(self):
        self._set_status("⌛ Launching Data Factory...", warn=False)
        try:
            script_path = Path(__file__).parent / "start_datafactory.sh"
            subprocess.Popen(
                ["bash", str(script_path)],
                env={**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":1")},
            )
            self._set_status("✅ Data Factory Launched", warn=False)
            self._log_event("Data Factory launched")
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"❌ Error: {exc}", warn=True)

    def _show_settings(self):
        win = tk.Toplevel(self)
        win.title("TITAN SYSTEM SETTINGS")
        win.geometry("520x320")
        win.configure(bg="#0f0f1a")
        info = (
            f"Python: {sys.version.split()[0]}\n"
            f"Path: {Path(__file__).parent}\n"
            f"Display: {os.environ.get('DISPLAY', 'Not set')}\n"
            f"User: {os.environ.get('USER', 'Unknown')}\n"
            f"Last Launch: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        tk.Label(win, text="SYSTEM CONFIGURATION", fg="#00d4ff", bg="#0f0f1a", font=("Courier", 16, "bold")).pack(pady=12)
        tk.Label(win, text=info, fg="#00d4ff", bg="#0f0f1a", font=("Courier", 11), justify="left").pack(padx=14, pady=10, anchor="w")

    def _set_status(self, text, warn=False):
        color = "#ff6b6b" if warn else "#51cf66"
        self.status.configure(text=text, foreground=color)

    def _log_event(self, event):
        log_file = Path(__file__).parent / "launcher.log"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat()}] {event}\n")


def main():
    if "DISPLAY" not in os.environ:
        os.environ["DISPLAY"] = ":1"
    launcher = TitanLauncher()
    launcher.mainloop()


if __name__ == "__main__":
    main()
