from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.runtime import RuntimeContext

import time
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
import asyncio
from datetime import datetime
from src.ui.log_buffer import log_buffer
from src.core.config import settings
from src.core.logger import get_logger
from src.core.dispatcher import handle_command
from src.utils.history import CommandHistory
from src.utils.tools import flatten_dict
from src.services.fetcher import get_event

logger = get_logger(__name__)

class GUIApp:
    def __init__(self, ctx: RuntimeContext = None):
        if not ctx:
            logger.error(f"missing RuntimeContext")
        
        ctx.ui = self
        self.ctx = ctx
        
        self.current_event = {}
        
        self.last_time_clicked = time.perf_counter()
        
        self.last_hover = 0
        
        self.compact_mode = False
        
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
    
    def toggle_compact_mode(self):
        self.compact_mode = True if not self.compact_mode else False
        if self.compact_mode:
            self.detail.grid_remove()
        else:
            self.detail.grid()
    
    def clicked_recently(self):
        now = time.perf_counter()

        if now - self.last_time_clicked <= 3:
            return True

        return False
    
    def update_click(self):
        now = time.perf_counter()
        self.last_time_clicked = now

    async def shutdown(self):
        self.root.after(0, self.root.quit)

    # ----------------------------
    # Layout
    # ----------------------------

    def build_layout(self):
        self.root.geometry("1200x800")

        # ---- Root ----
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(2, weight=1)

        # ---- Title ----
        self.title_label = tk.Label(self.root, anchor="center")
        self.title_label.grid(row=0, column=0, sticky="ew")

        # ---- Output ----
        self.output = ScrolledText(self.root, wrap="word")
        self.output.grid(row=2, column=0, sticky="nsew")
        self.output.config(state="disabled")
        
        self.output.tag_configure("hover", background="#eaeaea", underline=True)
        
        self.output.bind("<Button-1>", self.on_output_click)
        self.output.bind("<Motion>", self.on_output_hover)
        self.output.bind("<Leave>", self.on_output_leave)
        
        # ---- Input ----
        input_frame = tk.Frame(self.root)
        input_frame.grid(row=3, column=0, sticky="ew")
        input_frame.grid_columnconfigure(1, weight=1)

        tk.Label(input_frame, text="> ").grid(row=0, column=0)
        self.input = tk.Entry(input_frame)
        self.input.grid(row=0, column=1, sticky="ew")
        
        self.input.bind("<Return>", self.on_enter)

        # ---- Command Toolbar ----
        self.command_toolbar = tk.Frame(self.root)
        self.command_toolbar.grid(row=4, column=0, sticky="ew")
        self.root.geometry("1200x800")

        col = 0

        for butt in ["load", "refresh", "clear"]:
            tk.Button(
                self.command_toolbar,
                text=butt.title(),
                command=getattr(self, f"on_press_{butt}")
            ).grid(row=0, column=col, padx=2, pady=2)
            col += 1

        # separator
        tk.Frame(self.command_toolbar, width=1, bg="black").grid(row=0, column=col, sticky="ns", padx=12)
        col += 1

        self.kill_input = ttk.Combobox(self.command_toolbar, width=16)
        self.kill_input.grid(row=0, column=col, padx=2)
        col += 1
        
        for butt in ["tasks", "kill"]:
            tk.Button(
                self.command_toolbar,
                text=butt.title(),
                command=getattr(self, f"on_press_{butt}")
            ).grid(row=0, column=col, padx=2)
            col += 1
        
        self.kill_input.bind("<Button-1>", self.on_kill_input_click)
        
        # separator
        tk.Frame(self.command_toolbar, width=1, bg="black").grid(row=0, column=col, sticky="ns", padx=12)
        col += 1
        
        self.poll_input = tk.Entry(self.command_toolbar, width=10)
        self.poll_input.grid(row=0, column=col, padx=2)
        self.poll_input.config(state="normal")
        self.poll_input.delete(0, tk.END)
        self.poll_input.insert(0, settings.poll_interval)
        
        col +=1
        tk.Button(
            self.command_toolbar,
            text="Poll",
            command=self.on_press_poll
        ).grid(row=0, column=col, padx=2, sticky="w")
        
        self.poll_input.bind("<Return>", self.on_press_poll)
        
        self.command_toolbar.grid_columnconfigure(col, weight=1)
        col += 1
        
        for butt in ["exit", "help", "hide"]:
            tk.Button(
                self.command_toolbar,
                text=butt.title(),
                command=getattr(self, f"on_press_{butt}")
            ).grid(row=0, column=col, padx=2)
            col += 1
        
        # ---- Detail widget ----
        
        self.root.grid_rowconfigure(5, weight=0)
        self.detail = tk.Text(self.root, wrap="word", height=9)
        self.detail.grid(row=5, column=0, sticky="ew")
        
        self.detail.tag_configure("hover", background="#eaeaea", underline=True)
        
        self.detail.bind("<Button-1>", self.on_detail_click)
        self.detail.bind("<Motion>", self.on_detail_hover)
        self.detail.bind("<Leave>", self.on_detail_leave)
        
        # ---- Footer widget ----
        self.footer = tk.Frame(self.root)
        self.footer.grid(row=6, column=0, sticky="ew")

        self.footer_label = tk.Label(self.footer, anchor="w")
        self.footer_label.grid(row=0, column=0, sticky="ew")
        self.footer = tk.Frame(self.root)
        self.footer.grid(row=6, column=0, sticky="ew")

        self.footer_label = tk.Label(self.footer, anchor="w")
        self.footer_label.grid(row=0, column=0, sticky="ew")
    
    def invert_footer_temporarily(self):
        self._footer_bg = self.footer_label["bg"]
        self._footer_fg = self.footer_label["fg"]
        self.footer_label.config(bg="#454545", fg="#ffffff")
        self.root.after(
            3000,
            lambda: self.footer_label.config(bg=self._footer_bg, fg=self._footer_fg)
        )

    # ----------------------------
    # Input
    # ----------------------------
    
    # ---- output widget ----
    
    def on_output_hover(self, event):
        now = time.perf_counter()
        if now - self.last_hover < 0.01:
            return
        self.last_hover = now
        
        index = self.output.index(f"@{event.x},{event.y}")
        line_number = index.split(".")[0]
        self.output.tag_remove("hover", "1.0", tk.END)
        start = f"{line_number}.0"
        end = f"{line_number}.end"
        self.output.tag_add("hover", start, end)
        self.output.config(cursor="hand2")
    
    def on_output_leave(self, event):
        self.output.tag_remove("hover", "1.0", tk.END)
        self.output.config(cursor="arrow")
    
    def on_output_click(self, event):
        index = self.output.index(f"@{event.x},{event.y}")
        line_number = index.split(".")[0]
        line = self.output.get(f"{line_number}.0", f"{line_number}.end")
        event_id = self.extract_event_id(line)

        if not event_id:
            return

        self.show_event_details(event_id)
    
    # ---- command widgets ----
    
    def on_press_load(self):
        asyncio.run_coroutine_threadsafe(
            handle_command(text="load", ctx=self.ctx),
            self.loop
        )
    def on_press_refresh(self):
        asyncio.run_coroutine_threadsafe(
            handle_command(text="refresh", ctx=self.ctx),
            self.loop
        )
    def on_press_clear(self):
        asyncio.run_coroutine_threadsafe(
            handle_command(text="clear", ctx=self.ctx),
            self.loop
        )
    def on_press_poll(self):
        asyncio.run_coroutine_threadsafe(
            handle_command(text=f"poll {self.poll_input.get().strip()}", ctx=self.ctx),
            self.loop
        )
    def on_press_tasks(self):
        running = self.ctx.scheduler.list_workers()
        asyncio.run_coroutine_threadsafe(
            handle_command(text="tasks", ctx=self.ctx),
            self.loop
        )
        if not running:
            return
        
        self.kill_input["values"] = [s for s in running.keys()]
        
    def on_press_kill(self):
        asyncio.run_coroutine_threadsafe(
            handle_command(text=f"kill {self.kill_input.get()}", ctx=self.ctx),
            self.loop
        )
        self.kill_input["values"] = []
        self.kill_input.set("")
        
    def on_kill_input_click(self, event):
        running = self.ctx.scheduler.list_workers()
        if not running:
            return
        
        self.kill_input["values"] = [s for s in running.keys()]
        
    def on_press_help(self):
        asyncio.run_coroutine_threadsafe(
            handle_command(text="help", ctx=self.ctx),
            self.loop
        )
    def on_press_exit(self):
        asyncio.run_coroutine_threadsafe(
            handle_command(text="exit", ctx=self.ctx),
            self.loop
        )
    
    def on_press_hide(self):
        self.toggle_compact_mode()
    
    # ---- detail widget ----
    
    def on_detail_hover(self, event):
        now = time.perf_counter()
        if now - self.last_hover < 0.01:
            return
        self.last_hover = now
        
        
        index = self.detail.index(f"@{event.x},{event.y}")
        line_number = index.split(".")[0]
        self.detail.tag_remove("hover", "1.0", tk.END)
        start = f"{line_number}.0"
        end = f"{line_number}.end"
        self.detail.tag_add("hover", start, end)
        self.detail.config(cursor="hand2")
        line = self.detail.get(f"{line_number}.0", f"{line_number}.end")
        
        if not self.clicked_recently():
            if line and "http" in line and "/" in line:
                self.footer_label.config(text="Click to copy URL")
            
            else:
                self.footer_label.config(text="")
        
    def on_detail_leave(self, event):
        self.detail.tag_remove("hover", "1.0", tk.END)
        self.detail.config(cursor="arrow")
        self.footer_label.config(text="")
    
    def on_detail_click(self, event):
        self.update_click()
        index = self.detail.index(f"@{event.x},{event.y}")
        line_number = index.split(".")[0]
        line = self.detail.get(f"{line_number}.0", f"{line_number}.end")
        if line and "http" in line and "/" in line:
            line = str(line[line.find("http"):])
            self.root.clipboard_clear()
            self.root.clipboard_append(line)
            self.footer_label.config(text="URL copied to clipboard!")
            self.invert_footer_temporarily()
    
    # ---- input widget ----
    
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
    
    # --------------------
    # Widget output
    # --------------------
    
    def extract_event_id(self, line: str):
        if " - " not in line:
            return None

        parts = line.split(" - ")
        first_part = parts[0]

        if ":" in first_part:
            eid = first_part.split(":")[1].strip()
            try:
                return int(eid)
            
            except ValueError:
                pass

        return None
    
    def show_event_details(self, event_id):
        event = get_event(event_id)

        if not event:
            return

        flat = flatten_dict(event)
        self.current_event = flat

        self.detail.config(state="normal")
        self.detail.delete("1.0", tk.END)

        for k, v in flat.items():
            self.detail.insert(tk.END, f"{k}: {v}\n")

        self.detail.config(state="disabled")
    
    def on_copy_url(self):
        if not self.current_event:
            return

        event = self.current_event

        url = event.get("url")
        if not url:
            return

        self.root.clipboard_clear()
        self.root.clipboard_append(url)

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

