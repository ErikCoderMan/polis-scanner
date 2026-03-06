from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.runtime import RuntimeContext

import time
import tkinter as tk
from tkinter import ttk
import asyncio
from datetime import datetime
from src.ui.log_buffer import log_buffer
from src.core.config import settings, update_env_variable
from src.core.logger import get_logger
from src.core.dispatcher import handle_command
from src.utils.history import CommandHistory
from src.utils.tools import flatten_dict, str_to_hex, invert_color
from src.services.fetcher import get_event
from src.gui.theme import ThemeManager

logger = get_logger(__name__)

class GUIApp:
    def __init__(self, ctx: RuntimeContext = None):
        if not ctx:
            logger.error(f"missing RuntimeContext")
        
        ctx.ui = self
        self.ctx = ctx
        
        # ---- loops ----
        
        # tkinter loop (main thread)
        self.root = ctx.root
        
        # asyncio background loop (sepparate thread)
        self.loop = ctx.loop
        
        # ---- create theme object ----
        
        self.theme = ThemeManager(self)
        
        # ---- ui variables ----
        
        self.current_event = {}
        self.last_time_clicked = time.perf_counter()
        self.last_hover = 0
        self.compact_mode = False
        
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
        
        # build widgets
        self.build_layout()
        
        # Store default theme
        self.theme.store_defaults()
        
        # Apply theme from config, fallback default
        theme = settings.default_theme
        self.theme.apply("default")
        
        if theme:
            self.theme.apply(theme)
            
        else:
            self.theme.apply("default")
        
        
        
        # ---- loop ----
        
        # set input field as focus after 100ms
        self.root.after(100, lambda: self.input.focus_set())
        
        # start loop
        self.schedule_update()
    
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

        # ---- Title bar ----
        
        # Title bar container
        title_bar = ttk.Frame(self.root)
        title_bar.grid(row=0, column=0, sticky="ew")

        title_bar.grid_columnconfigure(0, weight=1)
        title_bar.grid_columnconfigure(1, weight=0)

        # Title label (center expand)
        self.title_label = ttk.Label(title_bar, anchor="center")
        self.title_label.grid(row=0, column=0, sticky="ew", columnspan=2)

        # Theme menu button (right aligned)
        self.theme_menu_button = ttk.Menubutton(
            title_bar,
            text="Theme",
            style="TMenubutton"
        )
        self.theme_menu_button.grid(row=0, column=1, padx=2, sticky="e")
        
        # Make title label lower prio then menubutton
        self.title_label.lower()
        
        # Menu
        self.theme_menu = tk.Menu(self.theme_menu_button, tearoff=0)
        
        self.theme.menus.append(self.theme_menu)
        theme_names = [*self.theme.themes.keys()]
        
        for theme in theme_names:
            self.theme_menu.add_command(
                label=theme.title(),
                command=lambda t=theme: self.on_select_theme(t)
            )
            
        self.theme_menu_button.config(menu=self.theme_menu)
        

        # ---- Output ----
        
        output_frame = ttk.Frame(self.root)
        output_frame.grid(row=2, column=0, sticky="nsew")

        self.output = tk.Text(
            output_frame,
            wrap="word",
            state="disabled"
        )

        self.output.grid(row=0, column=0, sticky="nsew")

        self.output_vbar = ttk.Scrollbar(
            output_frame,
            orient="vertical",
            command=self.output.yview
        )

        self.output.configure(yscrollcommand=self.output_vbar.set)

        self.output_vbar.grid(row=0, column=1, sticky="ns")

        # Allow text widget to expand
        output_frame.grid_rowconfigure(0, weight=1)
        output_frame.grid_columnconfigure(0, weight=1)
        
        self.output.bind("<Button-1>", self.on_output_click)
        self.output.bind("<Motion>", self.on_output_hover)
        self.output.bind("<Leave>", self.on_output_leave)
        
        # ---- Input ----
        
        input_frame = ttk.Frame(self.root)
        input_frame.grid(row=3, column=0, sticky="ew")
        input_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(input_frame, text="> ").grid(row=0, column=0, padx=2)

        self.input = ttk.Entry(input_frame)
        self.input.grid(row=0, column=1, sticky="ew", padx=2)
        
        self.input.bind("<Return>", self.on_enter)
        self.input.bind("<Up>", self.history_up)
        self.input.bind("<Down>", self.history_down)
        self.input.bind("<Prior>", lambda e: (self.output.yview_scroll(-1, "pages"), "break"))
        self.input.bind("<Next>", lambda e: (self.output.yview_scroll(1, "pages"), "break"))

        # ---- Command Toolbar ----
        
        self.command_toolbar = ttk.Frame(self.root)
        self.command_toolbar.grid(row=4, column=0, sticky="ew")
        self.root.geometry("1200x800")

        col = 0
        
        # Buttons
        for butt in ["load", "refresh", "clear"]:
            ttk.Button(
                self.command_toolbar,
                text=butt.title(),
                command=getattr(self, f"on_press_{butt}")
            ).grid(row=0, column=col, padx=2, pady=2)
            col += 1

        # Separator
        ttk.Frame(
            self.command_toolbar,
            style="ToolbarDivider.TFrame"
        ).grid(
            row=0,
            column=col,
            sticky="ns",
            padx=10,
            pady=2
        )
        col += 1
        
        ttk.Label(self.command_toolbar, text="Tasks: ").grid(row=0, column=col, padx=0)
        col += 1
        
        # Combobox widget for kill button
        self.kill_input = ttk.Combobox(self.command_toolbar, width=10)
        self.kill_input.grid(row=0, column=col, pady=2, padx=2)
        col += 1
        
        
        # Kill button
        ttk.Button(
            self.command_toolbar,
            text="kill".title(),
            command=self.on_press_kill
        ).grid(row=0, column=col, padx=2, pady=2)
        
        col += 1
        
        
        self.kill_input.bind("<Button-1>", self.on_kill_input_click)
        
        # Separator
        ttk.Frame(
            self.command_toolbar,
            style="ToolbarDivider.TFrame"
        ).grid(
            row=0,
            column=col,
            sticky="ns",
            padx=10,
            pady=2
        )
        col += 1
        
        # Input entry widget for poll button
        self.poll_input = ttk.Entry(self.command_toolbar, width=6)
        self.poll_input.grid(row=0, column=col, padx=2)

        self.poll_input.config(state="normal")
        self.poll_input.delete(0, tk.END)
        self.poll_input.insert(0, settings.poll_interval)

        col += 1
        
        self.poll_input.bind("<Return>", self.on_press_poll)
        
        # Poll button
        ttk.Button(
            self.command_toolbar,
            text="poll".title(),
            command=self.on_press_poll
            ).grid(row=0, column=col, padx=2, pady=2)
        col += 1
        
        # Separator
        ttk.Frame(
            self.command_toolbar,
            style="ToolbarDivider.TFrame"
        ).grid(
            row=0,
            column=col,
            sticky="ns",
            padx=10,
            pady=2
        )
        col += 1
        
        # Spacer before right-aligned buttons
        self.command_toolbar.grid_columnconfigure(col, weight=1)
        ttk.Frame(self.command_toolbar).grid(row=0, column=col, sticky="ew")
        col += 1

        # Right aligned buttons
        for butt in ["exit", "help", "hide"]:
            ttk.Button(
                self.command_toolbar,
                text=butt.title(),
                command=getattr(self, f"on_press_{butt}")
            ).grid(row=0, column=col, padx=2)
            col += 1
        
        # ---- Detail widget ----
        
        detail_frame = ttk.Frame(self.root)
        detail_frame.grid(row=5, column=0, sticky="ew")

        self.detail = tk.Text(
            detail_frame,
            wrap="word",
            height=9
        )

        self.detail.pack(fill="x")
        self.detail.config(state="disabled")
        
        self.detail.bind("<Button-1>", self.on_detail_click)
        self.detail.bind("<Motion>", self.on_detail_hover)
        self.detail.bind("<Leave>", self.on_detail_leave)
        
        # ---- Footer widget ----
        self.footer = ttk.Frame(self.root)
        self.footer.grid(row=6, column=0, sticky="ew")

        self.footer_label = ttk.Label(
            self.footer, text="", style="Footer.TLabel", anchor="w"
        )
        
        self.footer_label.grid(row=0, column=0, sticky="ew")
        
        
    def hover_text(self, widget: tk.Text, event, tag_name="hover"):
        """
        Universal hover handler for tk.Text.
        Returns hovered line string if exists.
        """

        if tag_name == "leave":
            widget.tag_remove("hover", "1.0", tk.END)
            widget.tag_remove("click", "1.0", tk.END)
            widget.config(cursor="arrow")
            return None

        try:
            index = widget.index(f"@{event.x},{event.y}")
            line_number = index.split(".")[0]

            start = f"{line_number}.0"
            end = f"{line_number}.end"

            line = widget.get(start, end).strip()

            underline = tag_name == "click" or (event.state & 0x0100)

            widget.tag_remove("hover", "1.0", tk.END)
            widget.tag_remove("click", "1.0", tk.END)

            hover = self.theme.hover_text[self.theme.current_theme]

            widget.tag_add("hover", start, end)
            widget.tag_config(
                "hover",
                background=hover["bg"],
                foreground=hover["fg"],
                underline=underline
            )
            widget.tag_lower("hover")

            if underline:
                widget.tag_add("click", start, end)
                widget.tag_config("click", underline=True)
                widget.tag_raise("click")

            widget.config(cursor="hand2")

            return line

        except Exception:
            widget.config(cursor="arrow")
            return None
    
    
    def flash_widget(self, widget, duration: int = 3000, invert=True, bg=None, fg=None):
        duration = max(duration, 3000)

        timer_attr = f"_flash_id_{id(widget)}"
        color_attr = f"_flash_colors_{id(widget)}"

        existing = getattr(self, timer_attr, None)
        if existing:
            self.root.after_cancel(existing)

        style = self.theme.style

        style_name = widget.cget("style") if "style" in widget.keys() else widget.winfo_class()
        if not style_name:
            style_name = widget.winfo_class()

        # ---- get original colors once ----
        orig_bg = style.lookup(style_name, "background") or bg
        orig_fg = style.lookup(style_name, "foreground") or fg

        setattr(self, color_attr, (orig_bg, orig_fg))

        # ---- calculate flash colors ----
        if invert:
            try:
                temp_bg = invert_color(orig_bg) if orig_bg else bg
                temp_fg = invert_color(orig_fg) if orig_fg else fg
            except Exception:
                temp_bg, temp_fg = bg, fg
        else:
            temp_bg, temp_fg = bg, fg

        # ---- lock theme while flashing ----
        self.theme.is_theme_locked = True

        if temp_bg:
            style.configure(style_name, background=temp_bg)

        if temp_fg:
            style.configure(style_name, foreground=temp_fg)

        def restore():
            orig_bg, orig_fg = getattr(self, color_attr, (None, None))

            if orig_bg:
                style.configure(style_name, background=orig_bg)

            if orig_fg:
                style.configure(style_name, foreground=orig_fg)

            if widget is self.footer_label:
                self.footer_label.configure(text="")

            setattr(self, timer_attr, None)
            setattr(self, color_attr, None)

            self.theme.is_theme_locked = False

        flash_id = self.root.after(duration, restore)
        setattr(self, timer_attr, flash_id)
        
    def is_widget_flashing(self, widget):
        timer_attr = f"_flash_id_{id(widget)}"
        return getattr(self, timer_attr, None) is not None
    
    def toggle_compact_mode(self):
        self.compact_mode = True if not self.compact_mode else False
        if self.compact_mode:
            self.detail.grid_remove()
            self.footer.grid_remove()
        else:
            self.detail.grid()
            self.footer.grid()
    
    def extract_event_id(self, line: str):
        # todo: should upgrade this to instead
        # perform regex matching at some point
        
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

    # ----------------------------
    # (on) Widget Actions
    # ----------------------------
    
    # ---- theme menu selection area ----
    
    def on_select_theme(self, theme_name):
        theme_name = theme_name.lower()
        self.theme.apply(theme_name=theme_name)
        update_env_variable("POLIS_SCANNER_DEFAULT_THEME", theme_name)
    
    # ---- output widget area ----
    
    def on_output_hover(self, event):
        if time.perf_counter() - self.last_hover < 0.05:
            return

        self.last_hover = time.perf_counter()
        line = self.hover_text(self.output, event, "hover")

    
    def on_output_leave(self, event):
        self.hover_text(self.output, event, "leave")
    
    def on_output_click(self, event):
        self.update_click()
        line = self.hover_text(self.output, event, "click")
        
        if not line or line == "break":
            return
            
        event_id = self.extract_event_id(line)

        if not event_id:
            return

        self.show_event_details(event_id)
    
    # ---- command toolbar widget area ----
    
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
    
    # ---- detail widget area ----
    
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
    
    def on_detail_hover(self, event):
        now = time.perf_counter()
        if now - self.last_hover < 0.05:
            return
            
        self.last_hover = now
        
        line = self.hover_text(self.detail, event, "hover")
        if line == "break" or not line:
            return
            
        if not self.is_widget_flashing(self.footer_label):
            if line and "http" in line and "/" in line:
                self.footer_label.config(text="Click to copy URL")
            
            else:
                self.footer_label.config(text="")
        
    def on_detail_leave(self, event):
        line = self.hover_text(self.detail, event, "leave")
        
        if not self.is_widget_flashing(self.footer_label):
            self.footer_label.config(text="")
            return
            
    
    def on_detail_click(self, event):
        self.update_click()
        line = self.hover_text(self.detail, event, "click")
        if line and "http" in line and "/" in line:
            line = str(line[line.find("http"):])
            self.root.clipboard_clear()
            self.root.clipboard_append(line)
            
            if not self.is_widget_flashing(self.footer_label):
                self.footer_label.config(text="URL copied to clipboard!")
                self.flash_widget(self.footer_label)
    
    # ---- input widget area ----
    
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
    
    # ---- Not In Use / Not Yet Implemented ----
    
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

