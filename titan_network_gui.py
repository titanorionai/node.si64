#!/home/titan/TitanNetwork/venv/bin/python3
"""
TITAN NETWORK | SI64.NET CONTROL DECK
Standalone GUI for monitoring the TITAN backend and driving
core SI64.NET network operations.
"""

import os
import sys
from pathlib import Path
import threading
import subprocess
import webbrowser

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

import requests

# Local imports
try:
    import titan_config as tcfg
except SystemExit:
    # titan_config can hard-exit if GENESIS_KEY is missing. For the GUI we
    # degrade gracefully so at least the shell opens.
    tcfg = None


class TitanNetworkGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("TITAN NETWORK | CONTROL DECK")
        self.geometry("1180x720")
        self.configure(bg="#000000")

        self._init_styles()

        # Project root for running scripts/commands
        self.project_root = Path(__file__).resolve().parent
        # Local API base for stats / dashboard
        self.api_base = os.getenv("TITAN_GUI_API_BASE", "http://127.0.0.1:8000")

        self._build_layout()
        self._refresh_backend_panel()
        # Start live telemetry polling
        self._poll_api_stats()

    # ------------------------------------------------------------------
    # Styling
    # ------------------------------------------------------------------
    def _init_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")

        base_bg = "#000000"       # pure black
        panel_bg = "#050505"      # near-black panel
        accent_green = "#00ff00"  # bright green
        border_silver = "#c0c0c0" # silver border

        style.configure("TFrame", background=base_bg)
        style.configure(
            "Panel.TFrame", background=panel_bg, relief="solid", borderwidth=1
        )
        style.configure("HeaderStrip.TFrame", background="#000000")
        style.configure(
            "Header.TLabel",
            background="#000000",
            foreground=accent_green,
            font=("Segoe UI", 18, "bold"),
        )
        style.configure(
            "SubHeader.TLabel",
            background="#000000",
            foreground=border_silver,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Section.TLabel",
            background=panel_bg,
            foreground=accent_green,
            font=("Segoe UI", 12, "bold"),
        )
        style.configure(
            "Data.TLabel",
            background=panel_bg,
            foreground=accent_green,
            font=("Segoe UI", 10),
        )
        style.configure(
            "StatusOk.TLabel",
            background=panel_bg,
            foreground=accent_green,
            font=("Segoe UI", 10, "bold"),
        )
        style.configure(
            "StatusWarn.TLabel",
            background=panel_bg,
            foreground="#ff5555",
            font=("Segoe UI", 10, "bold"),
        )
        style.configure(
            "Neon.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=8,
            foreground=accent_green,
        )
        style.map(
            "Neon.TButton",
            foreground=[("active", "#ffffff")],
            background=[("active", panel_bg)],
        )

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build_layout(self) -> None:
        root = ttk.Frame(self, style="TFrame")
        root.pack(fill="both", expand=True, padx=14, pady=14)

        # Header strip
        header = ttk.Frame(root, style="HeaderStrip.TFrame")
        header.pack(fill="x", pady=(0, 10))

        left_header = ttk.Frame(header, style="TFrame")
        left_header.pack(side="left", anchor="w")

        ttk.Label(
            left_header,
            text="TITAN NETWORK CONTROL DECK",
            style="Header.TLabel",
        ).pack(anchor="w")
        ttk.Label(
            left_header,
            text="BACKEND TELEMETRY  •  FLEET CONTROL  •  STRESS TOOLS",
            style="SubHeader.TLabel",
        ).pack(anchor="w")

        # Underline accent
        underline = tk.Frame(header, bg="#00ff00", height=1)
        underline.pack(fill="x", pady=(8, 0))

        # Main layout (single pane)
        main = ttk.Frame(root, style="TFrame")
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(0, weight=1)

        # Backend telemetry and controls
        self.backend_panel = ttk.Frame(main, style="Panel.TFrame")
        self.backend_panel.grid(row=0, column=0, sticky="nsew")
        self._build_backend_panel(self.backend_panel)

    # ------------------------------------------------------------------
    # Backend pane
    # ------------------------------------------------------------------
    def _build_backend_panel(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="TITAN BACKEND STATUS", style="Section.TLabel").pack(
            anchor="w", padx=12, pady=(10, 6)
        )

        self.backend_status_label = ttk.Label(parent, text="● Initializing…", style="StatusWarn.TLabel")
        self.backend_status_label.pack(anchor="w", padx=12, pady=(0, 8))

        # Live network telemetry summary
        stats_frame = ttk.Frame(parent, style="Panel.TFrame")
        stats_frame.pack(fill="x", padx=10, pady=(0, 8))

        ttk.Label(stats_frame, text="Fleet", style="Data.TLabel").grid(row=0, column=0, sticky="w", padx=6)
        ttk.Label(stats_frame, text="Queue", style="Data.TLabel").grid(row=1, column=0, sticky="w", padx=6)
        ttk.Label(stats_frame, text="Revenue", style="Data.TLabel").grid(row=2, column=0, sticky="w", padx=6)

        self.fleet_value = ttk.Label(stats_frame, text="--", style="Data.TLabel")
        self.queue_value = ttk.Label(stats_frame, text="--", style="Data.TLabel")
        self.revenue_value = ttk.Label(stats_frame, text="--", style="Data.TLabel")

        self.fleet_value.grid(row=0, column=1, sticky="w", padx=6)
        self.queue_value.grid(row=1, column=1, sticky="w", padx=6)
        self.revenue_value.grid(row=2, column=1, sticky="w", padx=6)

        # Control deck for core operations
        controls = ttk.Frame(parent, style="Panel.TFrame")
        controls.pack(fill="x", padx=10, pady=(0, 8))

        row1 = ttk.Frame(controls, style="Panel.TFrame")
        row1.pack(fill="x", pady=2)
        ttk.Button(
            row1,
            text="OPEN WEB DASHBOARD",
            style="Neon.TButton",
            command=self._open_dashboard,
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            row1,
            text="RUN API TESTS",
            style="Neon.TButton",
            command=self._run_api_tests,
        ).pack(side="left", padx=6)

        row2 = ttk.Frame(controls, style="Panel.TFrame")
        row2.pack(fill="x", pady=2)
        ttk.Button(
            row2,
            text="DEPLOY FLEET (REMOTE)",
            style="Neon.TButton",
            command=self._deploy_fleet_remote,
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            row2,
            text="DEPLOY FLEET (LOCAL)",
            style="Neon.TButton",
            command=self._deploy_fleet_local,
        ).pack(side="left", padx=6)

        row3 = ttk.Frame(controls, style="Panel.TFrame")
        row3.pack(fill="x", pady=2)
        ttk.Button(
            row3,
            text="STRESS TEST (REMOTE)",
            style="Neon.TButton",
            command=self._stress_remote,
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            row3,
            text="STRESS TEST (LOCAL)",
            style="Neon.TButton",
            command=self._stress_local,
        ).pack(side="left", padx=6)

        self.backend_info_frame = ttk.Frame(parent, style="Panel.TFrame")
        self.backend_info_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.backend_text = scrolledtext.ScrolledText(
            self.backend_info_frame,
            bg="#000000",
            fg="#00ff00",
            insertbackground="#00ff00",
            font=("Courier New", 10),
            relief="flat",
            wrap="word",
        )
        self.backend_text.pack(fill="both", expand=True, padx=4, pady=4)
        self.backend_text.configure(state="disabled")

    def _refresh_backend_panel(self) -> None:
        if tcfg is None:
            self.backend_status_label.configure(text="● titan_config not available", style="StatusWarn.TLabel")
            return

        try:
            # Build a tactical summary similar to run_diagnostics(), but structured.
            bank_exists = os.path.exists(tcfg.BANK_WALLET_PATH)

            lines = [
                "[TITAN PROTOCOL MANIFEST]",
                f"MODE       : {tcfg.DEPLOYMENT_ENV}",
                f"IDENTITY   : {tcfg.NODE_ID}",
                f"UPLINK     : {getattr(tcfg, 'WEBSOCKET_URL', 'n/a')}",
                f"RPC        : {tcfg.SOLANA_RPC_URL}",
                "",
                "[FINANCIAL ECONOMY]",
                f"BOUNTY/OP  : {tcfg.BOUNTY_PER_JOB} SOL",
                f"SPLIT      : {int(tcfg.WORKER_FEE_PERCENT * 100)}/{int(tcfg.PROTOCOL_TAX * 100)} (Worker/DAO)",
                "",
                "[HARDWARE SAFETY]",
                f"MAX TEMP   : {tcfg.MAX_SAFE_TEMP_C}°C",
                f"HEARTBEAT  : {tcfg.HEARTBEAT_INTERVAL}s",
                "",
                "[NEURAL INTERFACES]",
                f"OLLAMA     : {tcfg.TITAN_OLLAMA_HOST}",
                f"COMFY      : {tcfg.TITAN_COMFY_HOST}",
                "",
                "[FILESYSTEM]",
                f"BANK WALLET: {'ACTIVE' if bank_exists else 'MISSING (SIM)'}",
                f"WAREHOUSE  : {tcfg.WAREHOUSE_PATH}",
                f"LOGS       : {tcfg.LOGS_DIR}",
            ]

            self.backend_text.configure(state="normal")
            self.backend_text.delete("1.0", tk.END)
            self.backend_text.insert("1.0", "\n".join(lines))
            self.backend_text.configure(state="disabled")

            self.backend_status_label.configure(text="● Backend manifest loaded", style="StatusOk.TLabel")
        except Exception as exc:  # noqa: BLE001
            self.backend_text.configure(state="normal")
            self.backend_text.delete("1.0", tk.END)
            self.backend_text.insert("1.0", f"Error loading backend config: {exc}")
            self.backend_text.configure(state="disabled")
            self.backend_status_label.configure(text="● Error reading titan_config", style="StatusWarn.TLabel")

    # ------------------------------------------------------------------
    # Live telemetry + command runners
    # ------------------------------------------------------------------
    def _append_backend_log(self, text: str) -> None:
        self.backend_text.configure(state="normal")
        self.backend_text.insert(tk.END, text)
        self.backend_text.see(tk.END)
        self.backend_text.configure(state="disabled")

    def _poll_api_stats(self) -> None:
        """Poll /api/stats on the local Brain and update summary labels."""
        url = f"{self.api_base}/api/stats"
        try:
            resp = requests.get(url, timeout=2)
            if resp.ok:
                data = resp.json()
                fleet = data.get("fleet_size") or data.get("fleet") or 0
                queue = data.get("queue_depth") or data.get("queue") or 0
                revenue = float(data.get("total_revenue") or data.get("paid") or 0.0)

                self.fleet_value.configure(text=str(fleet))
                self.queue_value.configure(text=str(queue))
                self.revenue_value.configure(text=f"◎ {revenue:.4f}")
                self.backend_status_label.configure(text="● Brain online", style="StatusOk.TLabel")
            else:
                self.backend_status_label.configure(text="● Brain API error", style="StatusWarn.TLabel")
        except Exception:
            self.backend_status_label.configure(text="● Brain offline", style="StatusWarn.TLabel")

        # Schedule next poll
        self.after(3000, self._poll_api_stats)

    def _run_command_async(self, label: str, cmd, env_extra=None) -> None:
        """Run a shell command in the background and stream output to backend log."""

        def _worker() -> None:
            env = os.environ.copy()
            if env_extra:
                env.update(env_extra)

            self.after(0, lambda: self._append_backend_log(f"[CMD] {label}: {' '.join(cmd)}\n"))
            try:
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(self.project_root),
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                assert proc.stdout is not None
                for line in proc.stdout:
                    self.after(0, lambda l=line: self._append_backend_log(l))
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda: self._append_backend_log(f"[ERROR] {label}: {exc}\n"))

        threading.Thread(target=_worker, daemon=True).start()

    def _open_dashboard(self) -> None:
        try:
            webbrowser.open(self.api_base)
        except Exception:
            messagebox.showwarning("TITAN", f"Could not open {self.api_base}")

    def _run_api_tests(self) -> None:
        self._run_command_async("API tests", ["pytest", "src/tests/test_api_endpoints.py", "-q"])

    def _deploy_fleet_remote(self) -> None:
        self._run_command_async("Deploy fleet (remote)", ["bash", "deploy_fleet.sh", "5"], {"TARGET_MODE": "remote"})

    def _deploy_fleet_local(self) -> None:
        self._run_command_async("Deploy fleet (local)", ["bash", "deploy_fleet.sh", "5"], {"TARGET_MODE": "local"})

    def _stress_remote(self) -> None:
        # Default of titan_stress_test is remote si64.net
        self._run_command_async("Stress test (remote)", [sys.executable, "scripts/titan_stress_test.py"])

    def _stress_local(self) -> None:
        self._run_command_async(
            "Stress test (local)",
            [sys.executable, "scripts/titan_stress_test.py"],
            {"TITAN_STRESS_TARGET": "http://127.0.0.1:8000/submit_job"},
        )


def main() -> None:
    if "DISPLAY" not in os.environ:
        os.environ["DISPLAY"] = ":1"
    app = TitanNetworkGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
