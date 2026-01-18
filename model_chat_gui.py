#!/home/titan/TitanNetwork/venv/bin/python3
"""
Simple model chat GUI

- On startup, loads TITAN_OLLAMA_HOST from .env (fallback http://localhost:11434)
- Queries the Ollama API for installed models and lists them in a dropdown
- Provides a chat console below to talk to the selected model
"""

import os
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

import requests
from dotenv import load_dotenv


class ModelChatGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("TITAN NEON MODEL CONSOLE")
        # Launch in a much larger window; WM will clamp if needed
        self.geometry("1920x1200")
        self.minsize(1280, 880)
        # Cyberpunk dark background
        self.configure(bg="#040712")

        # Load .env so TITAN_OLLAMA_HOST is available
        load_dotenv()
        self.ollama_host = os.getenv("TITAN_OLLAMA_HOST", "http://localhost:11434").rstrip("/")

        self.models: list[str] = []
        self.current_model: str | None = None
        self.chat_history: list[dict] = []  # [{"role": "user"/"assistant", "content": str}, ...]

        self._init_styles()
        self._build_layout()
        self._load_models_async()

    # ------------------------------------------------------------------
    # Styling
    # ------------------------------------------------------------------
    def _init_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")

        # Cyberpunk neon palette (mirrors titan_network_gui)
        base_bg = "#02040b"
        panel_bg = "#050816"
        accent_cyan = "#00e5ff"
        accent_magenta = "#ff2fd8"

        style.configure("TFrame", background=base_bg)
        style.configure(
            "Panel.TFrame",
            background=panel_bg,
            relief="solid",
            borderwidth=1,
        )
        style.configure(
            "Header.TLabel",
            background="#030612",
            foreground=accent_cyan,
            font=("Courier", 20, "bold"),
        )
        style.configure(
            "SubHeader.TLabel",
            background="#030612",
            foreground=accent_magenta,
            font=("Courier", 11),
        )
        style.configure(
            "Label.TLabel",
            background=panel_bg,
            foreground=accent_cyan,
            font=("Courier", 12, "bold"),
        )
        style.configure(
            "Neon.TButton",
            font=("Courier", 11, "bold"),
            padding=6,
            foreground=accent_cyan,
            background=panel_bg,
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
        root.pack(fill="both", expand=True, padx=12, pady=12)

        # Header
        header = ttk.Frame(root, style="TFrame")
        header.pack(fill="x", pady=(0, 10))

        ttk.Label(
            header,
            text="TITAN // NEON MODEL CONSOLE",
            style="Header.TLabel",
        ).pack(anchor="w", pady=(2, 0))
        ttk.Label(
            header,
            text="Select an installed model, then chat below.",
            style="SubHeader.TLabel",
        ).pack(anchor="w")

        underline = tk.Frame(header, bg="#00e5ff", height=1)
        underline.pack(fill="x", pady=(8, 0))

        # Top: model selection
        top = ttk.Frame(root, style="Panel.TFrame")
        top.pack(fill="x", pady=(0, 10))

        left = ttk.Frame(top, style="Panel.TFrame")
        left.pack(side="left", fill="x", expand=True, padx=8, pady=8)

        ttk.Label(left, text="Installed Models", style="Label.TLabel").pack(anchor="w")

        self.model_var = tk.StringVar()
        self.model_combo = ttk.Combobox(left, textvariable=self.model_var, state="readonly")
        self.model_combo.pack(fill="x", pady=(4, 4))
        self.model_combo.bind("<<ComboboxSelected>>", self._on_model_selected)

        self.model_status = ttk.Label(left, text=f"Ollama host: {self.ollama_host}", style="SubHeader.TLabel")
        self.model_status.pack(anchor="w", pady=(4, 0))

        right = ttk.Frame(top, style="Panel.TFrame")
        right.pack(side="right", padx=8, pady=8)

        ttk.Button(
            right,
            text="Reload Models",
            style="Neon.TButton",
            command=self._load_models_async,
        ).pack()

        # Bottom: chat console
        chat_panel = ttk.Frame(root, style="Panel.TFrame")
        chat_panel.pack(fill="both", expand=True)

        ttk.Label(chat_panel, text="Chat", style="Label.TLabel").pack(anchor="w", padx=8, pady=(8, 4))

        self.chat_text = scrolledtext.ScrolledText(
            chat_panel,
            bg="#050816",
            fg="#d0faff",
            insertbackground="#00f5ff",
            font=("Courier", 12),
            relief="sunken",
            wrap="word",
        )
        self.chat_text.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.chat_text.configure(state="disabled")

        input_row = ttk.Frame(chat_panel, style="Panel.TFrame")
        input_row.pack(fill="x", padx=8, pady=(0, 8))

        self.input_var = tk.StringVar()
        self.input_entry = tk.Entry(
            input_row,
            textvariable=self.input_var,
            bg="#02040b",
            fg="#d0faff",
            insertbackground="#00f5ff",
            font=("Courier", 12),
            relief="sunken",
        )
        # Extra internal padding so it's easier to click and type into
        self.input_entry.pack(side="left", fill="x", expand=True, padx=(0, 6), ipady=4)
        self.input_entry.bind("<Return>", lambda event: self._on_send_clicked())

        self.send_button = ttk.Button(
            input_row,
            text="Send",
            style="Neon.TButton",
            command=self._on_send_clicked,
        )
        self.send_button.pack(side="right")

    # ------------------------------------------------------------------
    # Model handling
    # ------------------------------------------------------------------
    def _load_models_async(self) -> None:
        self.model_status.configure(text="Loading models from Ollama…")
        threading.Thread(target=self._load_models, daemon=True).start()

    def _load_models(self) -> None:
        try:
            url = f"{self.ollama_host}/api/tags"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            models = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
        except Exception as exc:  # noqa: BLE001
            self.after(0, lambda: self._set_models([], error=str(exc)))
            return

        self.after(0, lambda: self._set_models(models, error=None))

    def _set_models(self, models: list[str], error: str | None) -> None:
        self.models = models
        if error:
            self.model_status.configure(text=f"Error loading models: {error}")
            self.model_combo["values"] = []
            self.current_model = None
            return

        self.model_combo["values"] = models
        if models:
            self.model_status.configure(text=f"Loaded {len(models)} models from {self.ollama_host}")
            # Auto-select first model if nothing picked yet
            if not self.current_model:
                self.model_var.set(models[0])
                self.current_model = models[0]
        else:
            self.model_status.configure(text=f"No models reported by {self.ollama_host}")
            self.current_model = None

    def _on_model_selected(self, event: object) -> None:  # noqa: ANN001, ARG002
        name = self.model_var.get().strip()
        self.current_model = name or None
        if self.current_model:
            self._append_chat(f"[SYSTEM] Switched to model: {self.current_model}\n")

    # ------------------------------------------------------------------
    # Chat handling
    # ------------------------------------------------------------------
    def _append_chat(self, text: str) -> None:
        self.chat_text.configure(state="normal")
        self.chat_text.insert(tk.END, text)
        self.chat_text.see(tk.END)
        self.chat_text.configure(state="disabled")

    def _on_send_clicked(self) -> None:
        message = self.input_var.get().strip()
        if not message:
            return
        if not self.current_model:
            messagebox.showwarning("No model selected", "Select a model before sending a message.")
            return

        # Push user message to chat and clear input
        self._append_chat(f"You > {message}\n")
        self.input_var.set("")

        # Disable send while request is in flight
        self.send_button.configure(state="disabled")
        self.input_entry.configure(state="disabled")

        threading.Thread(
            target=self._send_to_model,
            args=(self.current_model, message),
            daemon=True,
        ).start()

    def _send_to_model(self, model: str, message: str) -> None:
        # Maintain a simple history the model can use
        self.chat_history.append({"role": "user", "content": message})

        try:
            url = f"{self.ollama_host}/api/chat"
            payload = {
                "model": model,
                "messages": self.chat_history,
                "stream": False,
            }
            resp = requests.post(url, json=payload, timeout=600)
            resp.raise_for_status()
            data = resp.json()
            assistant_msg = data.get("message", {}).get("content", "")
            if not assistant_msg:
                assistant_msg = "[No content returned from model]"
        except Exception as exc:  # noqa: BLE001
            assistant_msg = f"[ERROR] Request failed: {exc}"

        # Record assistant message in history
        self.chat_history.append({"role": "assistant", "content": assistant_msg})

        # Update UI back on main thread
        def _finish() -> None:
            self._append_chat(f"{model} > {assistant_msg}\n")
            self.send_button.configure(state="normal")
            self.input_entry.configure(state="normal")
            self.input_entry.focus_set()

        self.after(0, _finish)


if __name__ == "__main__":
    app = ModelChatGUI()
    app.mainloop()
