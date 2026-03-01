from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.runtime import RuntimeContext

import tkinter as tk
import asyncio
from datetime import datetime
from src.ui.log_buffer import log_buffer
from src.core.config import settings
from src.core.logger import get_logger
from src.commands.commands import handle_command
from src.utils.history import CommandHistory

logger = get_logger(__name__)

class GUIApp:
    def __init__(self, ctx: RuntimeContext = None):
        if not ctx:
            logger.error(f"missing RuntimeContext")
            
        self.ctx = ctx
        self.ctx.app_gui = self
        
        # ---- loops ----
        
        # tkinter loop (main thread)
        self.root = ctx.root
        
        # asyncio background loop (sepparate thread)
        self.loop = ctx.loop
        
        # ---- buffers ----
        
        # output UI buffer
        self.last_snapshot = ""
        
        # command history
        self.history = CommandHistory()
        self.saved_text = ""
        
        # ---- siren title ----
        
        self.title_patterns = ["*-*-*-", "-*-*-*"]
        self.title_index = 0
        
        # ---- build layout ----
        
        self.build_layout()
        self.schedule_update()

    # ----------------------------
    # Layout
    # ----------------------------

    def build_layout(self):
        self.root.geometry("900x600")

        # Title
        self.title_label = tk.Label(self.root, anchor="center")
        self.title_label.pack(fill="x")

        # Separator
        tk.Frame(self.root, height=2, bd=1, relief="sunken").pack(fill="x")

        # Output
        self.output = tk.Text(self.root, wrap="word")
        self.output.pack(fill="both", expand=True)
        self.output.config(state="disabled")

        # Separator
        tk.Frame(self.root, height=2, bd=1, relief="sunken").pack(fill="x")

        # Input container
        input_frame = tk.Frame(self.root)
        input_frame.pack(fill="x")

        # Prompt label
        tk.Label(input_frame, text="> ").pack(side="left")

        # Input field
        self.input = tk.Entry(input_frame)
        self.input.pack(side="left", fill="x", expand=True)

        self.input.bind("<Return>", self.on_enter)
        self.input.bind("<Up>", self.history_up)
        self.input.bind("<Down>", self.history_down)

    # ----------------------------
    # Input handlers
    # ----------------------------

    def on_enter(self, event):
        text = self.input.get().strip()
        if not text:
            return
        
        # save command in history
        self.history.append(text)
        
        # reset history index on (enter) press
        self.history.reset_cursor()

        self.input.delete(0, tk.END)

        # Dispatch async command to background loop
        asyncio.run_coroutine_threadsafe(
            handle_command(text=text, ctx=self.ctx),
            self.loop
        )
    
    def history_up(self, event):
        text = self.history.previous()
        
        if not text:
            return
            
        self.input.delete(0, tk.END)
        self.input.insert(0, text)
        self.input.icursor(tk.END)

    def history_down(self, event):
        text = self.history.next()
        
        if not text:
            text = ""
            
        self.input.delete(0, tk.END)
        self.input.insert(0, text)
        self.input.icursor(tk.END)

    # ----------------------------
    # Updater
    # ----------------------------

    def schedule_update(self):
        self.update_ui()
        self.ctx.state["force_scroll"] = False
        self.root.after(500, self.schedule_update)

    def update_ui(self):
        snapshot = log_buffer.get_text()

        # ---- Title animation ----
        self.title_index = (self.title_index + 1) % len(self.title_patterns)
        left_siren = self.title_patterns[self.title_index]
        right_siren = self.title_patterns[1 if self.title_index==0 else 0]
        clock = datetime.now().strftime("%H:%M:%S")

        title_text = (
            f"{left_siren} {clock} | "
            f"{settings.app_name} v{settings.version} (GUI) | "
            f"{len(snapshot.splitlines())} lines {right_siren}"
        )
        self.title_label.config(text=title_text)

        # ---- Output update ----
        if snapshot != self.last_snapshot:
            self.output.config(state="normal")

            # Check if user is near bottom
            bottom_visible = self.output.yview()[1] > 0.95

            self.output.delete("1.0", tk.END)
            self.output.insert(tk.END, snapshot)

            if bottom_visible or self.ctx.state.get("force_scroll", None):
                self.output.see(tk.END)

            self.output.config(state="disabled")
            self.last_snapshot = snapshot

