#!/usr/bin/env python3
import customtkinter as ctk
import threading
import subprocess
import os
import signal
import revenue_b_factory
import random
import string
import time
import json
from datetime import datetime

# --- SOLANA IMPORTS ---
try:
    from solana.rpc.api import Client
    from solana.transaction import Transaction
    from solders.system_program import TransferParams, transfer
    from solders.pubkey import Pubkey
    from solders.keypair import Keypair
except ImportError:
    print("CRITICAL: Solana libraries missing. Run: pip install solana solders")
    # mark solana libs unavailable so runtime logic can skip wallet/sweep features
    Client = None
    Transaction = None
    TransferParams = None
    transfer = None
    Pubkey = None
    Keypair = None
    SOLANA_AVAILABLE = False
else:
    SOLANA_AVAILABLE = True

# --- MASTER CONTROL CONFIGURATION ---
RPC_URL = "https://api.mainnet-beta.solana.com"
KEYPAIR_PATH = "bot_keypair.json"
REVENUE_WALLET_STR = "FpFtUESU6Rvy7uS85sLDg7iayjczrsFNJa4Q2dFV8z6q"

# --- AI CODING PATHS (INJECTED) ---
HOME_DIR = os.path.expanduser("~")
LLAMA_DIR = os.path.join(HOME_DIR, "llama.cpp")
LLAMA_BUILD_DIR = os.path.join(LLAMA_DIR, "build")
LLAMA_BINARY = os.path.join(LLAMA_BUILD_DIR, "bin/llama-server")

# Auto-Find Model
POSSIBLE_MODEL_PATHS = [
    os.path.join(LLAMA_DIR, "codestral-22b-v0.1-q6_k.gguf"),
    os.path.join(HOME_DIR, "codestral-22b-v0.1-q6_k.gguf")
]
MODEL_PATH = POSSIBLE_MODEL_PATHS[0]
for p in POSSIBLE_MODEL_PATHS:
    if os.path.exists(p):
        MODEL_PATH = p
        break

# SWEEP LOGIC
TRIGGER_THRESHOLD_SOL = 1.0   
MIN_KEEP_SOL = 0.1            
SWEEP_PERCENTAGE = 0.50       
CHECK_INTERVAL = 60           

# --- THEME COLORS ---
COLOR_BG = "#000000"
COLOR_PANEL = "#050505"
COLOR_ACCENT = "#00FF41"
COLOR_TEXT_DIM = "#008F11"
COLOR_ERROR = "#FF0000"
COLOR_WARN = "#FFD700"
COLOR_CYAN = "#00FFFF" # Added for Coding Module

ctk.set_appearance_mode("Dark")

class TitanCommand(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("TITAN ORION | MAINFRAME")
        self.geometry("1400x950")
        self.configure(fg_color=COLOR_BG)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # SIDEBAR
        self.sidebar = ctk.CTkFrame(self, width=280, corner_radius=0, fg_color=COLOR_PANEL, border_width=2, border_color=COLOR_TEXT_DIM)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        self.logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent", border_width=2, border_color=COLOR_ACCENT, corner_radius=0)
        self.logo_frame.pack(pady=(30, 40), padx=20, fill="x")
        self.logo_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.logo_frame, text="TITAN OS\nv10.0", font=("Courier", 28, "bold"), text_color=COLOR_ACCENT).pack(pady=15)

        # --- MENU BUTTONS ---
        self.btn_mev = self.create_matrix_button(self.sidebar, "SOLANA SNIPER", self.show_mev_frame)
        self.btn_mev.pack(pady=10, padx=20, fill="x")

        self.btn_factory = self.create_matrix_button(self.sidebar, "DATA FACTORY", self.show_factory_frame)
        self.btn_factory.pack(pady=10, padx=20, fill="x")

        # [INJECTED] AI CODING BUTTON
        self.btn_coding = ctk.CTkButton(self.sidebar, text="> AI CODING ASSISTANT", fg_color="transparent", border_color=COLOR_CYAN, border_width=1, text_color=COLOR_CYAN, hover_color="#002222", font=("Courier", 16, "bold"), anchor="w", corner_radius=0, height=45, command=self.show_coding_frame)
        self.btn_coding.pack(pady=10, padx=20, fill="x")

        # Backup / Git button
        self.btn_backup = ctk.CTkButton(self.sidebar, text="> BACKUP REPO", fg_color="transparent", border_color=COLOR_TEXT_DIM, border_width=1, text_color=COLOR_TEXT_DIM, hover_color="#001100", font=("Courier", 14, "bold"), anchor="w", corner_radius=0, height=40, command=self.backup_repo)
        self.btn_backup.pack(pady=6, padx=20, fill="x")

        ctk.CTkButton(self.sidebar, text="[ SYSTEM HALT ]", fg_color="transparent", border_color=COLOR_ERROR, border_width=2, text_color=COLOR_ERROR, hover_color="#220000", font=("Courier", 16, "bold"), corner_radius=0, height=50, command=self.close_app).pack(side="bottom", pady=40, padx=20, fill="x")

        # FRAMES
        self.mev_frame = ctk.CTkFrame(self, corner_radius=0, fg_color=COLOR_BG)
        self.factory_frame = ctk.CTkFrame(self, corner_radius=0, fg_color=COLOR_BG)
        self.coding_frame = ctk.CTkFrame(self, corner_radius=0, fg_color=COLOR_BG) # [INJECTED]

        self.setup_mev_ui()
        self.setup_factory_ui()
        self.setup_coding_ui() # [INJECTED]
        
        # Default View
        self.show_factory_frame()
        # Start background dataset scheduler (auto-publish jobs)
        try:
            revenue_b_factory.start_scheduler()
            self.log_factory(">>> SCHEDULER: Started background dataset scheduler.")
        except Exception:
            pass
        
        # Process Handles
        self.proc_brain = None
        self.proc_sniper = None
        self.proc_llama_coding = None # [INJECTED]
        self.running = False

    def create_matrix_button(self, parent, text, cmd):
        return ctk.CTkButton(parent, text=f"> {text}", fg_color="transparent", border_color=COLOR_ACCENT, border_width=1, text_color=COLOR_ACCENT, hover_color="#003300", font=("Courier", 16, "bold"), anchor="w", corner_radius=0, height=45, command=cmd)

    def create_header(self, parent, text, color=COLOR_ACCENT):
        frame = ctk.CTkFrame(parent, fg_color="transparent", border_width=2, border_color=color, corner_radius=0)
        ctk.CTkLabel(frame, text=f"/// {text} ///", font=("Courier", 22, "bold"), text_color=color).pack(pady=10, padx=20, anchor="w")
        return frame

    def _append_console(self, console_widget, tag, msg):
        """Thread-safe append to a CTkTextbox via the main thread, and mirror to runtime log."""
        # write to runtime log immediately (thread-safe)
        try:
            with open("master_control_runtime.log", "a") as lf:
                lf.write(f"[{tag}] {msg}\n")
        except Exception:
            pass

        # schedule GUI update on main thread
        def _do_update():
            try:
                console_widget.configure(state="normal")
                console_widget.insert("end", f"{msg}\n")
                console_widget.see("end")
                console_widget.configure(state="disabled")
            except Exception:
                pass

        try:
            self.after(0, _do_update)
        except Exception:
            # if after is not available, fallback to direct write (best-effort)
            try:
                _do_update()
            except Exception:
                pass

    def generate_batch_id(self):
        date_str = datetime.now().strftime("%Y%m%d")
        hex_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        return f"TITAN-AGX-{date_str}-{hex_suffix}"

    # -------------------------------------------------------------------------
    # UI SETUP: FACTORY
    # -------------------------------------------------------------------------
    def setup_factory_ui(self):
        self.factory_frame.grid_rowconfigure(1, weight=10)
        self.factory_frame.grid_rowconfigure(3, weight=1)
        self.factory_frame.grid_columnconfigure(0, weight=1)
        header = self.create_header(self.factory_frame, "MODULE: SYNTHETIC_DATA_GEN")
        header.grid(row=0, column=0, sticky="ew", padx=40, pady=(30, 20))

        controls_area = ctk.CTkFrame(self.factory_frame, fg_color="transparent")
        controls_area.grid(row=1, column=0, sticky="nsew", padx=40)
        controls_area.grid_columnconfigure(0, weight=1, uniform="group1")
        controls_area.grid_columnconfigure(1, weight=1, uniform="group1")
        controls_area.grid_rowconfigure(0, weight=1)

        # LEFT CONFIG
        left_col = ctk.CTkFrame(controls_area, fg_color="transparent")
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left_col.grid_rowconfigure(1, weight=1)
        left_col.grid_columnconfigure(0, weight=1)

        static_box = ctk.CTkFrame(left_col, fg_color="#0a0a0a", border_width=1, border_color=COLOR_TEXT_DIM, corner_radius=0)
        static_box.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkLabel(static_box, text="[ PRIMARY CONFIG ]", font=("Courier", 16, "bold"), text_color=COLOR_ACCENT).pack(pady=10, anchor="w", padx=15)
        
        ctk.CTkLabel(static_box, text="BATCH ID:", font=("Courier", 12), text_color=COLOR_ACCENT).pack(anchor="w", padx=15, pady=(5,0))
        self.entry_name = ctk.CTkEntry(static_box, font=("Courier", 14), fg_color="black", border_color=COLOR_ACCENT, text_color=COLOR_ACCENT, corner_radius=0)
        self.entry_name.insert(0, self.generate_batch_id())
        self.entry_name.pack(fill="x", padx=15, pady=(0, 10))
        
        ctk.CTkLabel(static_box, text="DATASET SIZE:", font=("Courier", 12), text_color=COLOR_ACCENT).pack(anchor="w", padx=15, pady=(5,0))
        self.entry_size = ctk.CTkComboBox(static_box, values=["5000", "50000", "100000", "1000000"], font=("Courier", 14), fg_color="black", border_color=COLOR_ACCENT, text_color=COLOR_ACCENT, dropdown_fg_color="black", dropdown_text_color=COLOR_ACCENT, corner_radius=0)
        self.entry_size.set("5000")
        self.entry_size.pack(fill="x", padx=15, pady=(0, 20))

        scen_box = ctk.CTkScrollableFrame(left_col, fg_color="#0a0a0a", border_width=1, border_color=COLOR_TEXT_DIM, corner_radius=0, label_text="[ SCENARIO MIXER ]", label_font=("Courier", 16, "bold"), label_text_color=COLOR_ACCENT)
        scen_box.grid(row=1, column=0, sticky="nsew")
        self.scenario_vars = {}
        scenarios = ["MEV Heavy", "Liquidity Snipe", "Pump & Dump", "Flash Crash", "Bull Run", "Bear Market", "Low Volatility"]
        for sc in scenarios:
            var = ctk.StringVar(value="on" if sc == "MEV Heavy" else "off") 
            cb = ctk.CTkCheckBox(scen_box, text=sc, variable=var, onvalue=sc, offvalue="off", font=("Courier", 14), text_color=COLOR_ACCENT, fg_color=COLOR_ACCENT, hover_color=COLOR_TEXT_DIM, corner_radius=0, border_color=COLOR_ACCENT, border_width=2)
            cb.pack(anchor="w", padx=10, pady=8)
            self.scenario_vars[sc] = var

        # RIGHT TARGETS
        target_box = ctk.CTkScrollableFrame(controls_area, fg_color="#0a0a0a", border_width=1, border_color=COLOR_TEXT_DIM, corner_radius=0, label_text="[ UPLOAD TARGETS ]", label_font=("Courier", 16, "bold"), label_text_color=COLOR_ACCENT)
        target_box.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        
        self.check_vars = {}
        repo_list = [
            ("[SPARK] Mempool Synthetic (5k)", "MEMPOOL_SYNTH_SPARK"),
            ("[STANDARD] Mempool Synthetic (100k)", "MEMPOOL_SYNTH_STD"),
            ("[OMEGA] Mempool Synthetic (1M)", "MEMPOOL_SYNTH_OMEGA"),
            ("---", None),
            ("[SPARK] Mempool Organic (5k)", "MEMPOOL_ORG_SPARK"),
            ("[STANDARD] Mempool Organic (100k)", "MEMPOOL_ORG_STD"),
            ("[OMEGA] Mempool Organic (1M)", "MEMPOOL_ORG_OMEGA"),
            ("--- MEV DATA ---", None),
            ("[SPARK] MEV Synthetic (5k)", "MEV_SYNTH_SPARK"),
            ("[STANDARD] MEV Synthetic (100k)", "MEV_SYNTH_STD"),
            ("[OMEGA] MEV Synthetic (1M)", "MEV_SYNTH_OMEGA"),
            ("---", None),
            ("[SPARK] MEV Organic (5k)", "MEV_ORG_SPARK"),
            ("[STANDARD] MEV Organic (100k)", "MEV_ORG_STD"),
            ("[OMEGA] MEV Organic (1M)", "MEV_ORG_OMEGA"),
        ]

        for label, key in repo_list:
            if key is None:
                ctk.CTkLabel(target_box, text=label, font=("Courier", 12), text_color=COLOR_TEXT_DIM).pack(anchor="w", padx=10, pady=5)
            else:
                var = ctk.StringVar(value="off")
                cb = ctk.CTkCheckBox(target_box, text=label, variable=var, onvalue=key, offvalue="off", font=("Courier", 13), text_color=COLOR_ACCENT, fg_color=COLOR_ACCENT, hover_color=COLOR_TEXT_DIM, corner_radius=0, border_color=COLOR_ACCENT, border_width=2)
                cb.pack(anchor="w", padx=10, pady=5)
                self.check_vars[key] = var

        # Button row: generate + explicit organic upload
        btn_row = ctk.CTkFrame(self.factory_frame, fg_color="transparent")
        btn_row.grid(row=2, column=0, sticky="ew", padx=40, pady=20)

        self.btn_gen = ctk.CTkButton(btn_row, text="[ INITIATE SEQUENCE ]", fg_color="transparent", border_color=COLOR_ACCENT, border_width=2, text_color=COLOR_ACCENT, hover_color="#003300", font=("Courier", 16, "bold"), height=50, corner_radius=0, command=self.run_factory)
        self.btn_gen.pack(side="left", padx=(0,20))

        self.btn_upload_organic = ctk.CTkButton(btn_row, text="[ UPLOAD ORGANIC ]", fg_color=COLOR_ACCENT, text_color="black", hover_color=COLOR_TEXT_DIM, font=("Courier", 16, "bold"), height=50, corner_radius=0, command=self.upload_organic)
        self.btn_upload_organic.pack(side="left")
        self.console_factory = ctk.CTkTextbox(self.factory_frame, height=150, font=("Courier", 12), fg_color="#050505", text_color=COLOR_ACCENT, border_color=COLOR_TEXT_DIM, border_width=1, corner_radius=0)
        self.console_factory.grid(row=3, column=0, sticky="ew", padx=40, pady=(0, 30))

    # -------------------------------------------------------------------------
    # UI SETUP: AI CODING (INJECTED)
    # -------------------------------------------------------------------------
    def setup_coding_ui(self):
        header = self.create_header(self.coding_frame, "MODULE: NEURAL_CODING_ENGINE", COLOR_CYAN)
        header.pack(pady=30, padx=40, fill="x")

        # Info Box
        info_box = ctk.CTkFrame(self.coding_frame, fg_color="transparent")
        info_box.pack(pady=(0, 20))
        ctk.CTkLabel(info_box, text=f"TARGET MODEL: {os.path.basename(MODEL_PATH)}", text_color="gray").pack()
        if not os.path.exists(MODEL_PATH):
             ctk.CTkLabel(info_box, text="[WARNING] MODEL FILE NOT FOUND", text_color=COLOR_ERROR).pack()

        # Control Deck
        ctrl_box = ctk.CTkFrame(self.coding_frame, fg_color="#0a0a0a", border_width=1, border_color=COLOR_CYAN, corner_radius=0)
        ctrl_box.pack(pady=0, padx=40, fill="x")

        self.btn_compile = ctk.CTkButton(ctrl_box, text="[ COMPILE ENGINE ]", fg_color="transparent", border_color=COLOR_CYAN, border_width=2, text_color=COLOR_CYAN, hover_color="#002222", font=("Courier", 14, "bold"), corner_radius=0, width=200, height=50, command=self.compile_llama)
        self.btn_compile.pack(side="left", padx=30, pady=30)

        self.btn_serve = ctk.CTkButton(ctrl_box, text="[ ACTIVATE SERVER ]", fg_color=COLOR_CYAN, text_color="black", hover_color=COLOR_TEXT_DIM, font=("Courier", 14, "bold"), corner_radius=0, width=200, height=50, command=self.launch_coding_server)
        self.btn_serve.pack(side="left", padx=30, pady=30)

        self.btn_stop_code = ctk.CTkButton(ctrl_box, text="[ TERMINATE ]", fg_color="transparent", border_color=COLOR_ERROR, border_width=2, text_color=COLOR_ERROR, hover_color="#330000", font=("Courier", 14, "bold"), corner_radius=0, width=150, height=50, command=self.stop_coding_server)
        self.btn_stop_code.pack(side="right", padx=30, pady=30)

        self.console_coding = ctk.CTkTextbox(self.coding_frame, font=("Courier", 12), fg_color="#050505", text_color=COLOR_CYAN, border_color=COLOR_CYAN, border_width=1, corner_radius=0)
        self.console_coding.pack(pady=20, padx=40, fill="both", expand=True)

    # -------------------------------------------------------------------------
    # UI SETUP: SOLANA SNIPER
    # -------------------------------------------------------------------------
    def setup_mev_ui(self):
        header = self.create_header(self.mev_frame, "MODULE: TITAN_SOLANA_SNIPER")
        header.pack(pady=30, padx=40, fill="x")

        # Strategy Controls
        strategy_frame = ctk.CTkFrame(self.mev_frame, fg_color="#0a0a0a", border_width=1, border_color=COLOR_TEXT_DIM, corner_radius=0)
        strategy_frame.pack(pady=(0, 20), padx=40, fill="x")
        strategy_frame.grid_columnconfigure((0, 1, 2), weight=1)

        # 1. SCOUT
        col1 = ctk.CTkFrame(strategy_frame, fg_color="transparent")
        col1.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        ctk.CTkLabel(col1, text="[ ENTRY ]", font=("Courier", 14, "bold"), text_color=COLOR_ACCENT).pack(anchor="w")
        self.var_autopilot = ctk.StringVar(value="on")
        ctk.CTkSwitch(col1, text="AUTO-PILOT", variable=self.var_autopilot, onvalue="on", offvalue="off", button_color=COLOR_ACCENT, progress_color=COLOR_TEXT_DIM, text_color=COLOR_ACCENT).pack(anchor="w", pady=5)
        self.entry_manual = ctk.CTkEntry(col1, placeholder_text="MANUAL CA...", width=200, fg_color="black", border_color=COLOR_TEXT_DIM, text_color=COLOR_ACCENT)
        self.entry_manual.pack(anchor="w", pady=5)

        # 2. RISK
        col2 = ctk.CTkFrame(strategy_frame, fg_color="transparent")
        col2.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        ctk.CTkLabel(col2, text="[ RISK ]", font=("Courier", 14, "bold"), text_color=COLOR_ACCENT).pack(anchor="w")
        
        self.lbl_impact = ctk.CTkLabel(col2, text="IMPACT: 5%", text_color=COLOR_TEXT_DIM)
        self.lbl_impact.pack(anchor="w")
        self.sl_impact = ctk.CTkSlider(col2, from_=1, to=20, button_color=COLOR_ACCENT, command=lambda v: self.lbl_impact.configure(text=f"IMPACT: {int(v)}%"))
        self.sl_impact.set(5)
        self.sl_impact.pack(fill="x")

        self.lbl_liq = ctk.CTkLabel(col2, text="LIQ: $20k", text_color=COLOR_TEXT_DIM)
        self.lbl_liq.pack(anchor="w")
        self.sl_liq = ctk.CTkSlider(col2, from_=5000, to=100000, button_color=COLOR_ACCENT, command=lambda v: self.lbl_liq.configure(text=f"LIQ: ${int(v):,}"))
        self.sl_liq.set(20000)
        self.sl_liq.pack(fill="x")

        # 3. EXIT
        col3 = ctk.CTkFrame(strategy_frame, fg_color="transparent")
        col3.grid(row=0, column=2, padx=20, pady=20, sticky="nsew")
        ctk.CTkLabel(col3, text="[ EXIT ]", font=("Courier", 14, "bold"), text_color=COLOR_WARN).pack(anchor="w")
        self.var_autosell = ctk.StringVar(value="on")
        ctk.CTkSwitch(col3, text="AUTO-SELL", variable=self.var_autosell, onvalue="on", offvalue="off", button_color=COLOR_WARN, progress_color=COLOR_TEXT_DIM, text_color=COLOR_WARN).pack(anchor="w", pady=5)
        
        self.lbl_tp = ctk.CTkLabel(col3, text="TP: +50%", text_color=COLOR_WARN)
        self.lbl_tp.pack(anchor="w")
        self.sl_tp = ctk.CTkSlider(col3, from_=10, to=500, button_color=COLOR_WARN, command=lambda v: self.lbl_tp.configure(text=f"TP: +{int(v)}%"))
        self.sl_tp.set(50)
        self.sl_tp.pack(fill="x")
        
        self.lbl_sl = ctk.CTkLabel(col3, text="SL: -15%", text_color=COLOR_ERROR)
        self.lbl_sl.pack(anchor="w")
        self.sl_sl = ctk.CTkSlider(col3, from_=5, to=50, button_color=COLOR_ERROR, command=lambda v: self.lbl_sl.configure(text=f"SL: -{int(v)}%"))
        self.sl_sl.set(15)
        self.sl_sl.pack(fill="x")

        ctrl_box = ctk.CTkFrame(self.mev_frame, fg_color="#0a0a0a", border_width=1, border_color=COLOR_TEXT_DIM, corner_radius=0)
        ctrl_box.pack(pady=0, padx=40, fill="x")

        self.btn_start = ctk.CTkButton(ctrl_box, text="[ EXECUTE BOT ]", fg_color=COLOR_ACCENT, text_color="black", hover_color=COLOR_TEXT_DIM, font=("Courier", 14, "bold"), corner_radius=0, width=150, command=self.start_mev)
        self.btn_start.pack(side="left", padx=20, pady=20)

        self.btn_stop = ctk.CTkButton(ctrl_box, text="[ TERMINATE ]", fg_color="transparent", border_color=COLOR_ERROR, border_width=2, text_color=COLOR_ERROR, hover_color="#330000", font=("Courier", 14, "bold"), corner_radius=0, width=150, state="disabled", command=self.stop_mev)
        self.btn_stop.pack(side="left", padx=20, pady=20)

        self.lbl_status = ctk.CTkLabel(ctrl_box, text="STATUS: IDLE", font=("Courier", 16, "bold"), text_color=COLOR_TEXT_DIM)
        self.lbl_status.pack(side="right", padx=30)

        self.console_mev = ctk.CTkTextbox(self.mev_frame, font=("Courier", 12), fg_color="#050505", text_color=COLOR_ACCENT, border_color=COLOR_ACCENT, border_width=1, corner_radius=0)
        self.console_mev.pack(pady=20, padx=40, fill="both", expand=True)

    def show_mev_frame(self):
        self.forget_all()
        self.mev_frame.grid(row=0, column=1, sticky="nsew")

    def show_factory_frame(self):
        self.forget_all()
        self.factory_frame.grid(row=0, column=1, sticky="nsew")

    def show_coding_frame(self): # [INJECTED]
        self.forget_all()
        self.coding_frame.grid(row=0, column=1, sticky="nsew")

    def forget_all(self):
        self.mev_frame.grid_forget()
        self.factory_frame.grid_forget()
        self.coding_frame.grid_forget() # [INJECTED]

    def log_coding(self, msg): # [INJECTED]
        # thread-safe append
        try:
            self._append_console(self.console_coding, "CODING", msg)
        except Exception:
            try:
                with open("master_control_runtime.log", "a") as lf:
                    lf.write(f"[CODING] {msg}\n")
            except Exception:
                pass

    def log_backup(self, msg):
        try:
            self._append_console(self.console_factory, "BACKUP", msg)
        except Exception:
            try:
                with open("master_control_runtime.log", "a") as lf:
                    lf.write(f"[BACKUP] {msg}\n")
            except Exception:
                pass

    def backup_repo(self):
        threading.Thread(target=self._backup_thread, daemon=True).start()

    def _backup_thread(self):
        """Create .gitignore, init git repo, add remote, commit and push."""
        try:
            remote = "https://github.com/titanorionai/AGX-ORIN.git"
            gitignore_contents = """
# ORIN AGX - auto-generated .gitignore
data_warehouse/
BACKUPS/
*.whl
target/
__pycache__/
*.pyc
master_control_runtime.log
predictor.out
*.log
bot_keypair.json
.env
.vscode/
/.idea/
"""
            # write .gitignore
            try:
                with open('.gitignore', 'w') as gf:
                    gf.write(gitignore_contents)
                self.log_backup(".gitignore written")
            except Exception as e:
                self.log_backup(f"Failed to write .gitignore: {e}")

            cmds = [
                ["git", "init"],
                ["git", "add", "-A"],
                ["git", "commit", "-m", "ORIN full backup commit"],
                ["git", "remote", "add", "origin", remote],
                ["git", "branch", "-M", "main"],
                ["git", "push", "-u", "origin", "main"]
            ]

            for cmd in cmds:
                try:
                    self.log_backup(f"Running: {' '.join(cmd)}")
                    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                    out, _ = p.communicate()
                    if out:
                        for line in out.splitlines():
                            self.log_backup(line)
                    if p.returncode != 0:
                        self.log_backup(f"Command {' '.join(cmd)} exited {p.returncode}")
                        # stop on push failures
                        if cmd[0] == 'git' and cmd[-1] == 'main' and cmd[1] == 'push':
                            break
                except Exception as e:
                    self.log_backup(f"Exception running {' '.join(cmd)}: {e}")
                    break

            self.log_backup("Backup routine finished.")
        except Exception as e:
            try:
                self.log_backup(f"Backup failed: {e}")
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # LOGIC: FACTORY
    # -------------------------------------------------------------------------
    def run_factory(self):
        threading.Thread(target=self._factory_thread, daemon=True).start()

    def _factory_thread(self):
        name = self.entry_name.get() 
        size = int(self.entry_size.get())
        selected_scenarios = [sc for sc, var in self.scenario_vars.items() if var.get() != "off"]
        targets = [key for key, var in self.check_vars.items() if var.get() != "off"]
        scen_log = ", ".join(selected_scenarios) if selected_scenarios else "Balanced"
        
        self.log_factory(f">>> INIT: {name} | {size} ROWS")
        self.log_factory(f">>> SCENARIOS: {scen_log}")
        
        try:
            success = revenue_b_factory.run_factory_pipeline(name, size, selected_scenarios, targets)
        except ImportError:
            success = True
            self.log_factory("[WARN] revenue_b_factory missing. Skipping.")

        if success: self.log_factory(">>> SEQUENCE COMPLETE.")
        else: self.log_factory(">>> SEQUENCE FAILED.")

    def upload_organic(self):
        threading.Thread(target=self._upload_organic_thread, daemon=True).start()

    def _upload_organic_thread(self):
        name = self.entry_name.get()
        size = int(self.entry_size.get())
        # collect selected organic repo keys
        selected_org_keys = [k for k, var in self.check_vars.items() if var.get() != "off" and ("_ORG_" in k)]
        if not selected_org_keys:
            self.log_factory("[FACTORY] No organic targets selected. Check an ORGANIC repo checkbox to upload.")
            return

        self.log_factory(f"[FACTORY] Preparing to upload organic batch: {name} | {size} rows -> {selected_org_keys}")
        try:
            ok = revenue_b_factory.upload_organic_batch(name, size, os.path.join(os.path.abspath('.'), 'data_warehouse', 'organic_capture.csv'), selected_org_keys)
            if ok:
                self.log_factory("[FACTORY] ORGANIC UPLOAD: Success.")
            else:
                self.log_factory("[FACTORY] ORGANIC UPLOAD: Failed. See logs.")
        except Exception as e:
            self.log_factory(f"[FACTORY] ORGANIC UPLOAD ERROR: {e}")

    def log_factory(self, msg):
        try:
            self._append_console(self.console_factory, "FACTORY", msg)
        except Exception:
            try:
                with open("master_control_runtime.log", "a") as lf:
                    lf.write(f"[FACTORY] {msg}\n")
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # LOGIC: AI CODING (INJECTED)
    # -------------------------------------------------------------------------
    def compile_llama(self):
        self.log_coding(">>> INITIATING CMAKE BUILD PROTOCOL...")
        threading.Thread(target=self._compile_thread, daemon=True).start()

    def _compile_thread(self):
        try:
            if os.path.exists(LLAMA_BUILD_DIR):
                self.log_coding("[BUILD] Cleaning old artifacts...")
                subprocess.run(f"rm -rf {LLAMA_BUILD_DIR}", shell=True)
            
            self.log_coding("[BUILD] Configuring CMake (CUDA=ON)...")
            cmd_config = f"cmake -B build -DGGML_CUDA=ON"
            ret = subprocess.run(cmd_config, shell=True, cwd=LLAMA_DIR, capture_output=True, text=True)
            if ret.returncode != 0:
                self.log_coding(f"[ERROR] Config Failed:\n{ret.stderr}")
                return

            self.log_coding("[BUILD] Compiling binaries (Max Cores)...")
            cmd_build = f"cmake --build build --config Release -j$(nproc)"
            process = subprocess.Popen(cmd_build, shell=True, cwd=LLAMA_DIR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in process.stdout:
                self.log_coding(line.strip())
            process.wait()
            if process.returncode == 0:
                self.log_coding(">>> BUILD COMPLETE.")
            else:
                self.log_coding(">>> BUILD FAILED.")
        except Exception as e:
            self.log_coding(f"[ERROR] {e}")

    def launch_coding_server(self):
        self.log_coding(f">>> LAUNCHING CODESTRAL...")
        threading.Thread(target=self._coding_server_thread, daemon=True).start()

    def _coding_server_thread(self):
        if not os.path.exists(LLAMA_BINARY):
            self.log_coding("[ERROR] Binary missing. Click COMPILE.")
            return
        
        cmd = [
            LLAMA_BINARY,
            "-m", MODEL_PATH,
            "-c", "32768",
            "-ngl", "99",
            "--host", "0.0.0.0",
            "--port", "8080",
            "-fa", "on",
            "--mlock"
        ]
        try:
            self.proc_llama_coding = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, preexec_fn=os.setsid)
            for line in self.proc_llama_coding.stdout:
                self.log_coding(line.strip())
        except Exception as e:
            self.log_coding(f"[ERROR] {e}")

    def stop_coding_server(self):
        if self.proc_llama_coding:
            os.killpg(os.getpgid(self.proc_llama_coding.pid), signal.SIGTERM)
            self.proc_llama_coding = None
            self.log_coding(">>> HALTED.")

    # -------------------------------------------------------------------------
    # LOGIC: SNIPER BOT (PROCESS + PROFIT SWEEPER)
    # -------------------------------------------------------------------------
    def start_mev(self):
        try:
            if not self.running:
                self.running = True
                self.log_mev(">>> INITIALIZING TITAN ORIN SYSTEMS...")
                self.lbl_status.configure(text="STATUS: BOOTING...", text_color="#FFFF00")
                self.btn_start.configure(state="disabled")
                self.btn_stop.configure(state="normal")

                self._save_strategy_config()

                threading.Thread(target=self._launch_processes, daemon=True).start()
                threading.Thread(target=self._run_profit_sweeper, daemon=True).start()
        except Exception as e:
            try:
                self.log_mev(f"[ERROR] start_mev failed: {e}")
            except Exception:
                try:
                    with open("master_control_runtime.log", "a") as lf:
                        lf.write(f"[ERROR] start_mev failed: {e}\n")
                except Exception:
                    pass

    def _save_strategy_config(self):
        config = {
            "autopilot": self.var_autopilot.get() == "on",
            "manual_target": self.entry_manual.get().strip(),
            "max_impact": int(self.sl_impact.get()),
            "min_liquidity": int(self.sl_liq.get()),
            "autosell_enabled": self.var_autosell.get() == "on",
            "take_profit_pct": int(self.sl_tp.get()),
            "stop_loss_pct": int(self.sl_sl.get())
        }
        with open("strategy_config.json", "w") as f:
            json.dump(config, f)
        self.log_mev(f"[CONFIG] Updated: {config}")

    def _launch_processes(self):
        try:
            # Kill Zombies safely (avoid killing this GUI process)
            def safe_kill(pattern):
                try:
                    out = subprocess.check_output(["pgrep", "-f", pattern], text=True)
                    pids = [int(x) for x in out.strip().split() if x.strip()]
                    for pid in pids:
                        if pid == os.getpid():
                            continue
                        try:
                            os.kill(pid, signal.SIGTERM)
                        except Exception:
                            try:
                                os.kill(pid, signal.SIGKILL)
                            except Exception:
                                pass
                except subprocess.CalledProcessError:
                    # no matching processes
                    return

            try:
                safe_kill("predictor.py")
            except Exception:
                pass

            for pattern in ["cargo run", "target/debug/orin_mev_bot", "target/release/orin_mev_bot"]:
                try:
                    safe_kill(pattern)
                except Exception:
                    pass

            time.sleep(1)

            # Launch Brain
            self.log_mev("[SYSTEM] Launching Neural Module (predictor.py)...")
            self.proc_brain = subprocess.Popen(
                ["python3", "predictor.py"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                preexec_fn=os.setsid
            )
            threading.Thread(target=self.monitor_stream, args=(self.proc_brain, "[BRAIN]"), daemon=True).start()

            # Launch Sniper - prefer prebuilt binary to avoid heavy cargo builds
            time.sleep(1)
            sniper_cmd = None
            if os.path.exists("target/debug/orin_mev_bot"):
                sniper_cmd = [os.path.join("target", "debug", "orin_mev_bot")]
            elif os.path.exists("target/release/orin_mev_bot"):
                sniper_cmd = [os.path.join("target", "release", "orin_mev_bot")]
            else:
                # cargo run may trigger a full rebuild which is heavy and can destabilize the GUI
                self.log_mev("[SYSTEM] Prebuilt sniper binary not found. Skipping cargo build to keep GUI stable.")

            if sniper_cmd:
                try:
                    self.log_mev(f"[SYSTEM] Launching Rust Sniper: {' '.join(sniper_cmd)}")
                    self.proc_sniper = subprocess.Popen(
                        sniper_cmd,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                        preexec_fn=os.setsid
                    )
                    threading.Thread(target=self.monitor_stream, args=(self.proc_sniper, "[SNIPER]"), daemon=True).start()
                except Exception as e:
                    self.log_mev(f"[ERROR] Failed to launch sniper binary: {e}")
            threading.Thread(target=self.monitor_stream, args=(self.proc_sniper, "[SNIPER]"), daemon=True).start()

            self.lbl_status.configure(text="STATUS: ACTIVE", text_color=COLOR_ACCENT)
            self.log_mev(">>> ALL SYSTEMS ONLINE. WAITING FOR SIGNALS.")

        except Exception as e:
            self.log_mev(f"[ERROR] LAUNCH FAILED: {str(e)}")
            self.stop_mev()

    def _run_profit_sweeper(self):
        try:
            if not SOLANA_AVAILABLE:
                self.log_mev("[MASTER CONTROL] Solana libs unavailable; skipping profit sweeper.")
                return

            client = Client(RPC_URL)
            if not os.path.exists(KEYPAIR_PATH):
                self.log_mev(f"[MASTER CONTROL] ERROR: {KEYPAIR_PATH} not found.")
                return
                
            with open(KEYPAIR_PATH, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    bot_keypair = Keypair.from_bytes(data)
                else:
                    return
            
            revenue_pubkey = Pubkey.from_string(REVENUE_WALLET_STR)
            self.log_mev(f"[MASTER CONTROL] Profit Sweeper Active: {str(bot_keypair.pubkey())[:6]}...")

            while self.running:
                try:
                    balance_resp = client.get_balance(bot_keypair.pubkey())
                    current_sol = balance_resp.value / 1_000_000_000.0

                    if current_sol >= TRIGGER_THRESHOLD_SOL:
                        self.log_mev(f"[PROFIT] Threshold Hit: {current_sol:.4f} SOL")
                        sweep_lamports = int((balance_resp.value - int(MIN_KEEP_SOL * 1e9)) * SWEEP_PERCENTAGE)
                        
                        if sweep_lamports > 1000000:
                            self.log_mev(f"[PROFIT] Sweeping {sweep_lamports/1e9:.4f} SOL...")
                            ix = transfer(TransferParams(from_pubkey=bot_keypair.pubkey(), to_pubkey=revenue_pubkey, lamports=sweep_lamports))
                            tx = Transaction().add(ix)
                            tx.recent_blockhash = client.get_latest_blockhash().value.blockhash
                            sig = client.send_transaction(tx, bot_keypair)
                            self.log_mev(f"[PROFIT] SECURED! Tx: {sig.value}")
                    
                except Exception as e:
                    pass

                for _ in range(CHECK_INTERVAL):
                    if not self.running: break
                    time.sleep(1)

        except Exception as e:
             self.log_mev(f"[MASTER CONTROL] CRITICAL FAILURE: {e}")

    def stop_mev(self):
        self.log_mev(">>> TERMINATING SYSTEMS...")
        self.running = False 

        # Kill Processes
        for proc, name in [(self.proc_brain, "Brain"), (self.proc_sniper, "Sniper")]:
            if proc:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                    self.log_mev(f"[SYSTEM] {name} Module Halted.")
                except: pass
        
        self.proc_brain = None
        self.proc_sniper = None
        
        self.lbl_status.configure(text="STATUS: OFFLINE", text_color=COLOR_TEXT_DIM)
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")

    def monitor_stream(self, process, tag):
        while self.running and process.poll() is None:
            line = process.stdout.readline()
            if line:
                self.log_mev(f"{tag} {line.strip()}")
            else:
                break

    def log_mev(self, msg):
        try:
            self._append_console(self.console_mev, "MEV", msg)
        except Exception:
            try:
                with open("master_control_runtime.log", "a") as lf:
                    lf.write(f"[MEV] {msg}\n")
            except Exception:
                pass

    def close_app(self):
        try:
            revenue_b_factory.stop_scheduler()
        except Exception:
            pass
        self.stop_mev()
        self.stop_coding_server()
        self.destroy()

if __name__ == "__main__":
    app = TitanCommand()
    app.mainloop()
