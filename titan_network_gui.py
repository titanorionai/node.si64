#!/home/titan/TitanNetwork/venv/bin/python3
"""
TITAN NETWORK | SI64.NET CONTROL DECK
Standalone cyberpunk GUI for monitoring the TITAN backend and driving the
SI64.NET Twitter bot.

Left pane  : TITAN backend status & key telemetry
Right pane : SI64.NET Twitter bot console
Header     : SI64.NET logo strip with neon cyan cyberpunk styling
"""

import os
import sys
from pathlib import Path
import threading

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

# Local imports
try:
    import titan_config as tcfg
except SystemExit:
    # titan_config can hard-exit if GENESIS_KEY is missing. For the GUI we
    # degrade gracefully so at least the shell opens.
    tcfg = None

try:
    from si64_twitter_bot import SI64TwitterBot
except Exception:  # noqa: BLE001
    SI64TwitterBot = None


class TitanNetworkGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("TITAN NETWORK | SI64.NET CONTROL DECK")
        self.geometry("1180x720")
        self.configure(bg="#040712")

        self._init_styles()

        self.bot = None
        self.bot_stats = {}

        self._build_layout()
        self._init_bot_async()
        self._refresh_backend_panel()

    # ------------------------------------------------------------------
    # Styling
    # ------------------------------------------------------------------
    def _init_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")

        base_bg = "#02040b"
        panel_bg = "#050816"
        accent_cyan = "#00e5ff"
        accent_magenta = "#ff2fd8"

        style.configure("TFrame", background=base_bg)
        style.configure("Panel.TFrame", background=panel_bg, relief="solid", borderwidth=1)
        style.configure("HeaderStrip.TFrame", background="#030612")
        style.configure(
            "Header.TLabel",
            background="#030612",
            foreground=accent_cyan,
            font=("Courier", 24, "bold"),
        )
        style.configure(
            "SubHeader.TLabel",
            background="#030612",
            foreground=accent_magenta,
            font=("Courier", 12),
        )
        style.configure(
            "Section.TLabel",
            background=panel_bg,
            foreground=accent_cyan,
            font=("Courier", 14, "bold"),
        )
        style.configure(
            "Data.TLabel",
            background=panel_bg,
            foreground="#d0faff",
            font=("Courier", 11),
        )
        style.configure(
            "StatusOk.TLabel",
            background=panel_bg,
            foreground="#5dff9e",
            font=("Courier", 11),
        )
        style.configure(
            "StatusWarn.TLabel",
            background=panel_bg,
            foreground="#ff6b81",
            font=("Courier", 11),
        )
        style.configure(
            "Neon.TButton",
            font=("Courier", 11, "bold"),
            padding=8,
            foreground=accent_cyan,
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
            text="SI64.NET // TITAN NETWORK",
            style="Header.TLabel",
        ).pack(anchor="w")
        ttk.Label(
            left_header,
            text="NEON CONTROL DECK  •  BACKEND TELEMETRY  •  TWITTER OPERATIONS",
            style="SubHeader.TLabel",
        ).pack(anchor="w")

        # Thin cyan underline for a sharper, more professional look
        underline = tk.Frame(header, bg="#00e5ff", height=1)
        underline.pack(fill="x", pady=(8, 0))

        # Main two-panel layout
        main = ttk.Frame(root, style="TFrame")
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        # Left: Backend telemetry
        self.backend_panel = ttk.Frame(main, style="Panel.TFrame")
        self.backend_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self._build_backend_panel(self.backend_panel)

        # Right: Twitter bot console
        self.twitter_panel = ttk.Frame(main, style="Panel.TFrame")
        self.twitter_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self._build_twitter_panel(self.twitter_panel)

    # ------------------------------------------------------------------
    # Backend pane
    # ------------------------------------------------------------------
    def _build_backend_panel(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="TITAN BACKEND STATUS", style="Section.TLabel").pack(
            anchor="w", padx=12, pady=(10, 6)
        )

        self.backend_status_label = ttk.Label(parent, text="● Initializing…", style="StatusWarn.TLabel")
        self.backend_status_label.pack(anchor="w", padx=12, pady=(0, 8))

        self.backend_info_frame = ttk.Frame(parent, style="Panel.TFrame")
        self.backend_info_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.backend_text = scrolledtext.ScrolledText(
            self.backend_info_frame,
            bg="#050816",
            fg="#d0faff",
            insertbackground="#00f5ff",
            font=("Courier", 10),
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
    # Twitter pane
    # ------------------------------------------------------------------
    def _build_twitter_panel(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="SI64.NET TWITTER BOT", style="Section.TLabel").pack(
            anchor="w", padx=12, pady=(10, 4)
        )

        self.twitter_status_label = ttk.Label(parent, text="● Initializing bot…", style="StatusWarn.TLabel")
        self.twitter_status_label.pack(anchor="w", padx=12, pady=(0, 8))

        controls = ttk.Frame(parent, style="Panel.TFrame")
        controls.pack(fill="x", padx=10, pady=(0, 8))

        # Buttons row 1
        row1 = ttk.Frame(controls, style="Panel.TFrame")
        row1.pack(fill="x", pady=4)
        ttk.Button(
            row1,
            text="STATUS UPDATE",
            style="Neon.TButton",
            command=self._post_status_update,
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            row1,
            text="DAILY DIGEST",
            style="Neon.TButton",
            command=self._post_daily_digest,
        ).pack(side="left", padx=6)

        # Buttons row 2
        row2 = ttk.Frame(controls, style="Panel.TFrame")
        row2.pack(fill="x", pady=4)
        ttk.Button(
            row2,
            text="TOGGLE AUTO-POST",
            style="Neon.TButton",
            command=self._toggle_autopost,
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            row2,
            text="REFRESH STATS",
            style="Neon.TButton",
            command=self._refresh_bot_stats,
        ).pack(side="left", padx=6)

        # Promotion input
        promo_frame = ttk.Frame(parent, style="Panel.TFrame")
        promo_frame.pack(fill="x", padx=10, pady=(0, 8))
        ttk.Label(promo_frame, text="PROMOTION BLAST:", style="Data.TLabel").pack(
            anchor="w", padx=6, pady=(4, 2)
        )
        self.promo_entry = tk.Entry(
            promo_frame,
            bg="#050816",
            fg="#d0faff",
            insertbackground="#00f5ff",
            relief="flat",
            font=("Courier", 10),
        )
        self.promo_entry.pack(fill="x", padx=6, pady=(0, 4))
        ttk.Button(
            promo_frame,
            text="SEND PROMO TWEET",
            style="Neon.TButton",
            command=self._post_promotion,
        ).pack(anchor="e", padx=6, pady=(0, 4))

        # Bot stats / log output
        self.twitter_log = scrolledtext.ScrolledText(
            parent,
            bg="#050816",
            fg="#d0faff",
            insertbackground="#00f5ff",
            font=("Courier", 10),
            relief="flat",
            wrap="word",
        )
        self.twitter_log.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.twitter_log.insert("1.0", "SI64.NET Twitter console ready.\n")
        self.twitter_log.configure(state="disabled")

    # ------------------------------------------------------------------
    # Bot wiring
    # ------------------------------------------------------------------
    def _init_bot_async(self) -> None:
        if SI64TwitterBot is None:
            self.twitter_status_label.configure(
                text="● si64_twitter_bot not available (import error)",
                style="StatusWarn.TLabel",
            )
            return

        def _worker() -> None:
            try:
                bot = SI64TwitterBot()
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda: self._append_log(f"Error initializing bot: {exc}\n"))
                self.after(
                    0,
                    lambda: self.twitter_status_label.configure(
                        text="● Bot initialization failed", style="StatusWarn.TLabel"
                    ),
                )
                return

            self.bot = bot
            self.after(0, self._refresh_bot_stats)

        threading.Thread(target=_worker, daemon=True).start()

    def _append_log(self, text: str) -> None:
        self.twitter_log.configure(state="normal")
        self.twitter_log.insert(tk.END, text)
        self.twitter_log.see(tk.END)
        self.twitter_log.configure(state="disabled")

    def _ensure_bot(self) -> bool:
        if self.bot is None:
            messagebox.showwarning("SI64.NET", "Twitter bot is not ready yet.")
            return False
        if not getattr(self.bot, "authenticated", False):
            self.twitter_status_label.configure(
                text="● Bot not authenticated (check API keys)",
                style="StatusWarn.TLabel",
            )
            self._append_log("Bot not authenticated. Set SI64_TWITTER_* env vars.\n")
            return False
        return True

    # ------------------------------------------------------------------
    # Bot actions (run in background threads to keep UI responsive)
    # ------------------------------------------------------------------
    def _post_status_update(self) -> None:
        if not self._ensure_bot():
            return

        def _worker() -> None:
            self.after(0, lambda: self._append_log("Posting SI64.NET status update…\n"))
            tweet_id = self.bot.post_si64_status_update()
            if tweet_id:
                self.after(0, lambda: self._append_log(f"✅ Status tweet posted: {tweet_id}\n"))
                self.after(0, self._refresh_bot_stats)

        threading.Thread(target=_worker, daemon=True).start()

    def _post_daily_digest(self) -> None:
        if not self._ensure_bot():
            return

        def _worker() -> None:
            self.after(0, lambda: self._append_log("Posting daily digest thread…\n"))
            result = self.bot.post_daily_digest()
            if result:
                self.after(0, lambda: self._append_log(f"✅ Daily digest posted ({len(result)} tweets).\n"))
                self.after(0, self._refresh_bot_stats)

        threading.Thread(target=_worker, daemon=True).start()

    def _post_promotion(self) -> None:
        if not self._ensure_bot():
            return

        msg = self.promo_entry.get().strip()
        if not msg:
            messagebox.showinfo("SI64.NET", "Enter a promotion message first.")
            return

        def _worker() -> None:
            self.after(0, lambda: self._append_log("Sending promotion tweet…\n"))
            tweet_id = self.bot.post_promotion(msg)
            if tweet_id:
                self.after(0, lambda: self._append_log(f"✅ Promotion tweet posted: {tweet_id}\n"))
                self.after(0, self._refresh_bot_stats)

        threading.Thread(target=_worker, daemon=True).start()

    def _toggle_autopost(self) -> None:
        if not self._ensure_bot():
            return

        def _worker() -> None:
            enabled = self.bot.config.get("enable_auto_post", False)
            new_state = not enabled
            self.bot.set_auto_posting(new_state)
            if new_state:
                self.bot.start_auto_scheduler()
            status_txt = "enabled" if new_state else "disabled"
            self.after(0, lambda: self._append_log(f"Auto-posting {status_txt}.\n"))
            self.after(0, self._refresh_bot_stats)

        threading.Thread(target=_worker, daemon=True).start()

    def _refresh_bot_stats(self) -> None:
        if self.bot is None:
            return

        stats = self.bot.get_bot_stats()
        self.bot_stats = stats

        aut = "AUTH" if stats.get("authenticated") else "NO AUTH"
        auto = "AUTO" if stats.get("auto_post_enabled") else "MANUAL"
        label_txt = f"● Bot: {aut} | Mode: {auto} | Tweets: {stats.get('posts_count', 0)}"
        style = "StatusOk.TLabel" if stats.get("authenticated") else "StatusWarn.TLabel"
        self.twitter_status_label.configure(text=label_txt, style=style)

        last = stats.get("last_broadcast") or "never"
        self._append_log(f"[BOT] Posts: {stats.get('posts_count', 0)}, Last: {last}, Auto: {auto}.\n")


def main() -> None:
    if "DISPLAY" not in os.environ:
        os.environ["DISPLAY"] = ":1"
    app = TitanNetworkGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
