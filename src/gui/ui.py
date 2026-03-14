from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.runtime import RuntimeContext

import os
import time
import re
import asyncio
import tkinter as tk
from tkinter import ttk, colorchooser
import tkinter.font as tkfont
from datetime import datetime
from src.ui.log_buffer import log_buffer
from src.core.config import settings, update_env_variable, load_settings
from src.core.logger import get_logger
from src.core.dispatcher import handle_command
from src.utils.history import CommandHistory
from src.utils.tools import flatten_dict, str_to_hex, invert_color
from src.services.fetcher import get_event, load_events
from src.gui.theme import ThemeManager
from src.gui.tags import TagManager

logger = get_logger(__name__)

class GUIApp:
    def __init__(self, ctx: RuntimeContext = None):
        if not ctx:
            logger.error(f"missing RuntimeContext")
        
        ctx.ui = self
        self.ctx = ctx
        
        # store screen size dynamically in new state
        if "window_width" not in self.ctx.state:
            self.ctx.state["window_width"] = 1200
        
        if "window_height" not in self.ctx.state:
            self.ctx.state["window_height"] = 800
        
        # ---- loops ----
        
        # tkinter loop (main thread)
        self.root = ctx.root
        
        # asyncio background loop (sepparate thread)
        self.loop = ctx.loop
        
        # ---- create theme object ----
        
        self.theme = ThemeManager(self)

        # Apply saved font-size settings (from config/env)
        self.theme.font_size = settings.font_size_main
        self.theme.font_size_output = settings.font_size_main
        self.theme.font_size_input = settings.font_size_input
        self.theme.font_size_detail = settings.font_size_detail
        self.theme.font_size_footer_label = settings.font_size_other
        self.theme.font_size_other = settings.font_size_other
        
        # ---- ui variables ----
        self.current_event = {}
        self.current_event_id = ""
        self.last_time_clicked = time.perf_counter()
        self.last_hover = 0
        self.compact_mode = False
        self.active_flashes = {}
        self.rendered_lines = 0
        
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
        
        # "bump" window because it appears that root.geometry returns
        # that x=0 and y=0 at start untill window has been moved/resized
        self.force_geometry_update_at_start()
        
        # On screen window configure, resize etc
        self.root.bind("<Configure>", self.on_window_configure)
        
        # Save window geometry info
        self.save_window_position()
        
        
        # Apply theme from config, fallback default
        theme = settings.default_theme
        
        try:
            if theme:
                self.theme.apply(theme)
                
            else:
                self.theme.apply("dark")
        
        except Exception:
            self.theme.apply("default")

        # Apply optional base colors from settings (overrides theme defaults)
        if settings.base_bg_color and settings.base_fg_color:
            self.theme.set_base_colors(settings.base_bg_color, settings.base_fg_color)

        # configure tags for text widgets
        self.tag_manager = TagManager(self.theme)
        self.use_color_tags = True


        # ---- loop ----
        
        # start loop
        self.schedule_update()
    
    def force_geometry_update_at_start(self):
        self.root.update_idletasks()
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        self.root.geometry(f"+{x+1}+{y+1}")
        
        
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
        
        
    def on_window_configure(self, event):
        if event.widget is self.root:
            self.save_window_position()
            
        
    def reload_ui(self):
        saved_output = self.output.get("1.0", "end-1c")
        scroll_pos = self.output.yview()
        
        for child in self.root.winfo_children():
            child.destroy()
        
        self.theme.clear_registries()
        self.build_layout()
        self.theme.apply(self.theme.current_theme)
        
        self.rendered_lines = 0
        self.print_output(saved_output, auto_scroll=False)
        self.output.yview_moveto(scroll_pos[0])
        
        if self.current_event and self.current_event_id:
            self.show_event_details(self.current_event_id)
        
        logger.debug(f"Reloaded UI")
    

    def rebuild(self):
        self.save_window_position()
        self.reload_ui()
        geom = self.ctx.state["window_geometry"]
        
        def restore_window_pos():
            self.root.geometry(geom)
            
        self.root.after_idle(restore_window_pos)
        
        # ---- on theme selection ----
    
    def on_select_theme(self, theme_name):
        theme_name = theme_name.lower()

        self.theme.current_theme = theme_name
        update_env_variable(
            "POLIS_SCANNER_DEFAULT_THEME",
            theme_name
        )
        
        # Stop all active flashes to prevent bugged colors
        self.stop_all_flashes()

        # Rebuild UI structure
        self.rebuild()

        # Then apply visual theme after rebuild
        self.theme.apply(theme_name=theme_name)
        
        # Info log theme change
        logger.info(f"Theme changed to '{self.theme.current_theme}'")

    def on_press_edit_settings(self):
        settings_to_apply = {}

        win = tk.Toplevel(self.root)
        win.title("Edit Settings")
        win.geometry("600x600")
        win.transient(self.root)
        win.resizable(True, True)

        win.grid_rowconfigure(0, weight=1)
        win.grid_columnconfigure(0, weight=1)

        frame = ttk.Frame(win, padding=10)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_columnconfigure(1, weight=1)

        title_label = ttk.Label(frame, text="Settings")
        title_label.grid(row=0, column=0, columnspan=3, sticky="n")
        title_label.config(font=tkfont.Font(size=14, weight="bold"))

        # Theme & color selection
        theme_frame = ttk.Frame(frame)
        theme_frame.configure(borderwidth=1, relief="solid", padding=10)
        theme_frame.grid(row=1, column=0, columnspan=3, sticky="new", pady=(10, 0))

        theme_label = ttk.Label(theme_frame, text="Theme & colors", anchor="nw")
        theme_label.grid(row=0, column=0, sticky="nw", columnspan=3)
        theme_label.config(font=tkfont.Font(size=12, weight="bold"))

        theme_var = tk.StringVar(value=self.theme.current_theme)
        theme_select = ttk.Combobox(
            theme_frame,
            textvariable=theme_var,
            values=list(self.theme.themes.keys()),
            state="readonly",
            width=12
        )
        theme_select.grid(row=1, column=0, sticky="w", padx=(0, 6), pady=(4, 0))

        def on_theme_select(event=None):
            selected = theme_var.get()
            settings_to_apply["POLIS_SCANNER_DEFAULT_THEME"] = selected
            self.on_select_theme(selected)
            # Reapply base colors if the user set them
            if settings.base_bg_color and settings.base_fg_color:
                self.theme.set_base_colors(settings.base_bg_color, settings.base_fg_color)
            
            self.on_press_edit_settings()  # Reopen settings to update color pickers with new theme colors

        theme_select.bind("<<ComboboxSelected>>", on_theme_select)

        # Background/foreground color pickers
        base_bg = settings.base_bg_color or self.theme.palette[self.theme.current_theme].get("text", {}).get("background", "#ffffff")
        base_fg = settings.base_fg_color or self.theme.palette[self.theme.current_theme].get("text", {}).get("foreground", "#000000")

        base_bg_var = tk.StringVar(value=base_bg)
        base_fg_var = tk.StringVar(value=base_fg)

        def pick_color(var, label_text):
            # Ensure the settings window is above other windows so the dialog appears in front
            win.lift()
            win.focus_force()

            color = colorchooser.askcolor(title=label_text, initialcolor=var.get(), parent=win)
            if not color or not color[1]:
                return
            var.set(color[1])
            settings_to_apply["POLIS_SCANNER_BASE_BG_COLOR"] = base_bg_var.get()
            settings_to_apply["POLIS_SCANNER_BASE_FG_COLOR"] = base_fg_var.get()
            self.theme.set_base_colors(base_bg_var.get(), base_fg_var.get())

        bg_button = ttk.Button(
            theme_frame,
            text="Background",
            command=lambda: pick_color(base_bg_var, "Pick background color")
        )
        bg_button.grid(row=1, column=1, sticky="w", padx=(0, 6), pady=(4, 0))

        fg_button = ttk.Button(
            theme_frame,
            text="Foreground",
            command=lambda: pick_color(base_fg_var, "Pick foreground color")
        )
        fg_button.grid(row=1, column=2, sticky="w", pady=(4, 0))

        # ----------

        font_frame = ttk.Frame(frame)
        font_frame.configure(borderwidth=1, relief="solid", padding=10)
        font_frame.grid(row=2, column=0, columnspan=3, sticky="new", pady=(10,0))

        font_label = ttk.Label(font_frame, text="Font Settings",  anchor="nw")
        font_label.grid(row=0, column=0, sticky="nw", columnspan=2)
        font_label.config(font=tkfont.Font(size=12, weight="bold"))

        main_font_label = ttk.Label(font_frame, text="Main text size:")
        main_font_label.grid(row=1, column=0, sticky="w")
        main_font_label.config(font=tkfont.Font(size=10))
        main_font_size = tk.IntVar(value=self.theme.font_size)
        main_font_spin = ttk.Spinbox(
            font_frame,
            from_=6,
            to=72,
            textvariable=main_font_size,
            width=6
        )
        main_font_spin.config(font=tkfont.Font(size=10))
        main_font_spin.set(self.theme.font_size)
        main_font_spin.grid(row=1, column=1, sticky="ne", padx=5)

        def on_main_font_size_change(*args):
            size = main_font_size.get()
            settings_to_apply["POLIS_SCANNER_FONT_SIZE_MAIN"] = size
            self.theme.font_size = size
            self.theme.font_size_output = size
            self.theme.fonts[self.theme.current_theme]["text"]["size"] = size
            self.theme.fonts[self.theme.current_theme]["log"]["size"] = size
            self.theme.fonts[self.theme.current_theme]["output_bold"]["size"] = size
            self.theme.set_fonts()

        main_font_size.trace_add("write", on_main_font_size_change)

        input_font_label = ttk.Label(font_frame, text="Input (entry/combobox) size:")
        input_font_label.grid(row=2, column=0, sticky="w")
        input_font_label.config(font=tkfont.Font(size=10))
        input_font_size = tk.IntVar(value=settings.font_size_input)
        input_font_spin = ttk.Spinbox(
            font_frame,
            from_=6,
            to=72,
            textvariable=input_font_size,
            width=6
        )
        input_font_spin.config(font=tkfont.Font(size=10))
        input_font_spin.set(settings.font_size_input)
        input_font_spin.grid(row=2, column=1, sticky="ne", padx=5)

        def on_input_font_size_change(*args):
            size = input_font_size.get()
            settings_to_apply["POLIS_SCANNER_FONT_SIZE_INPUT"] = size
            self.theme.font_size_input = size
            self.theme.set_fonts()

        input_font_size.trace_add("write", on_input_font_size_change)

        detail_font_label = ttk.Label(font_frame, text="Detail panel size:")
        detail_font_label.grid(row=3, column=0, sticky="w")
        detail_font_label.config(font=tkfont.Font(size=10))
        detail_font_size = tk.IntVar(value=settings.font_size_detail)
        detail_font_spin = ttk.Spinbox(
            font_frame,
            from_=6,
            to=72,
            textvariable=detail_font_size,
            width=6
        )
        detail_font_spin.config(font=tkfont.Font(size=10))
        detail_font_spin.set(settings.font_size_detail)
        detail_font_spin.grid(row=3, column=1, sticky="ne", padx=5)

        def on_detail_font_size_change(*args):
            size = detail_font_size.get()
            settings_to_apply["POLIS_SCANNER_FONT_SIZE_DETAIL"] = size
            self.theme.font_size_detail = size
            self.theme.set_fonts()

        detail_font_size.trace_add("write", on_detail_font_size_change)

        other_font_label = ttk.Label(font_frame, text="Other widgets size:")
        other_font_label.grid(row=4, column=0, sticky="w")
        other_font_label.config(font=tkfont.Font(size=10))
        other_font_size = tk.IntVar(value=settings.font_size_other)
        other_font_spin = ttk.Spinbox(
            font_frame,
            from_=6,
            to=72,
            textvariable=other_font_size,
            width=6
        )
        other_font_spin.config(font=tkfont.Font(size=10))
        other_font_spin.set(settings.font_size_other)
        other_font_spin.grid(row=4, column=1, sticky="ne", padx=5)

        def on_other_font_size_change(*args):
            size = other_font_size.get()
            settings_to_apply["POLIS_SCANNER_FONT_SIZE_OTHER"] = size
            self.theme.font_size_other = size
            self.theme.font_size_footer_label = size
            self.theme.set_fonts()

        other_font_size.trace_add("write", on_other_font_size_change)

        developer_frame = ttk.Frame(frame, borderwidth=1, relief="solid", padding=10)
        developer_frame.grid(row=3, column=0, columnspan=3, sticky="new", pady=(10, 0))
        developer_label = ttk.Label(developer_frame, text="Developer settings (requires restart)", anchor="nw")
        developer_label.grid(row=0, column=0, columnspan=2, sticky="nw", pady=(10, 0))
        developer_label.config(font=tkfont.Font(size=12, weight="bold"))
        debug_mode_var = tk.BooleanVar(value=settings.debug_mode)
        debug_mode_label = ttk.Label(developer_frame, text=f"Debug mode:", anchor="w")
        debug_mode_label.grid(row=1, column=0, sticky="w", pady=(4, 0))
        debug_mode_check = ttk.Checkbutton(developer_frame, style="ToolbuttonCheck.TCheckbutton", text=f"Toggle: {debug_mode_var.get()}", variable=debug_mode_var)
        #debug_mode_check.config(width=len(debug_mode_check.cget("text")))
        debug_mode_check.grid(row=1, column=1, sticky="w", pady=(4, 0))

        def on_debug_mode_change(*args):
            value = debug_mode_var.get()
            debug_mode_check.config(text=f"Debug: {value}")
            settings_to_apply["POLIS_SCANNER_DEBUG_MODE"] = value

        debug_mode_var.trace_add("write", on_debug_mode_change) 


        def on_save_settings():
            for key, value in settings_to_apply.items():
                update_env_variable(key, str(value))
            self.theme.set_fonts()
            win.destroy()

        def on_cancel_settings():
            win.destroy()

        button_frame = ttk.Frame(frame)
        last_row = frame.grid_size()[1]
        button_frame.grid(row=last_row, column=0, columnspan=3, sticky="e", pady=(10, 0))

        def on_reset_settings():
            # Remove the current env file and reload defaults
            try:
                if settings.env_path and settings.env_path.exists():
                    settings.env_path.unlink()
            except Exception:
                pass

            load_settings(force_reload=True)

            # Re-apply defaults in UI
            self.theme.font_size = settings.font_size_main
            self.theme.font_size_output = settings.font_size_main
            self.theme.font_size_input = settings.font_size_input
            self.theme.font_size_detail = settings.font_size_detail
            self.theme.font_size_footer_label = settings.font_size_other
            self.theme.font_size_other = settings.font_size_other
            self.theme.apply(settings.default_theme)

            win.destroy()

        reset_button = ttk.Button(button_frame, text="Reset defaults", command=on_reset_settings)
        reset_button.grid(row=0, column=0, padx=5)

        save_button = ttk.Button(button_frame, text="Save", command=on_save_settings)
        save_button.grid(row=0, column=1, padx=5)

        cancel_button = ttk.Button(button_frame, text="Cancel", command=on_cancel_settings)
        cancel_button.grid(row=0, column=2, padx=5)

        self.root.update_idletasks()



        self.root.update_idletasks()

        

    
    def save_window_position(self):
        self.root.update_idletasks()
        self.ctx.state["window_geometry"] = self.root.geometry()
        self.ctx.state["window_pos_x"] = self.root.winfo_x()
        self.ctx.state["window_pos_y"] = self.root.winfo_y()
        self.ctx.state["window_width"] = self.root.winfo_width()
        self.ctx.state["window_height"] = self.root.winfo_height()
        
    
    # ----------------------------
    # Layout
    # ----------------------------
    
    def build_layout(self):
        # TODO: rename widgets with consistent names
        # just like all the ttk.Buttons, example: name_button
        
        self.root.geometry(f"{self.ctx.state['window_width']}x{self.ctx.state['window_height']}")
        # ---- Root ----
        
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=0)
        self.root.grid_rowconfigure(1, weight=0)
        self.root.grid_rowconfigure(2, weight=1)
        self.root.grid_rowconfigure(3, weight=0)
        self.root.grid_rowconfigure(4, weight=0)
        self.root.grid_rowconfigure(5, weight=0)
        self.root.grid_rowconfigure(6, weight=0)

        # ---- Title bar ----
        
        # Title bar container
        self.title_bar = ttk.Frame(self.root)
        self.title_bar.grid(row=0, column=0, sticky="ew")

        self.title_bar.grid_columnconfigure(0, weight=0)
        self.title_bar.grid_columnconfigure(1, weight=1)
        self.title_bar.grid_columnconfigure(2, weight=0)

        # Title label (centered behind the buttons)
        self.title_label = ttk.Label(self.title_bar, anchor="center")
        self.title_label.grid(row=0, column=0, columnspan=3, sticky="ew")

        # Make title label lower priority than the menubuttons (so buttons remain clickable)
        self.title_label.lower()

        # Settings button (left aligned)
        self.settings_menu_button = ttk.Menubutton(
            self.title_bar,
            text="Settings",
            style="TMenubutton"
        )
        self.settings_menu_button.grid(row=0, column=0, padx=2, sticky="w")

        # Settings menu
        self.settings_menu = tk.Menu(self.settings_menu_button, tearoff=0)
        self.settings_menu.add_command(
            label="Edit settings",
            command=self.on_press_edit_settings
        )
        
        self.settings_menu_button.config(menu=self.settings_menu)


        # Theme menu button (right aligned)
        self.theme_menu_button = ttk.Menubutton(
            self.title_bar,
            text="Theme",
            style="TMenubutton"
        )
        self.theme_menu_button.grid(row=0, column=2, padx=2, sticky="e")

        # Theme menu
        self.theme_menu = tk.Menu(self.theme_menu_button, tearoff=0)
        
        theme_names = [*self.theme.themes.keys()]
        
        for theme in theme_names:
            self.theme_menu.add_command(
                label=theme.title(),
                command=lambda t=theme: self.on_select_theme(t)
            )
            
        self.theme_menu_button.config(menu=self.theme_menu)
        

        # ---- Output ----
        
        self.output_frame = ttk.Frame(self.root)
        self.output_frame.grid(row=2, column=0, sticky="nsew")

        self.output = tk.Text(
            self.output_frame,
            wrap="word",
            state="disabled",
        )

        self.output.grid(row=0, column=0, sticky="nsew")

        self.output_vbar = ttk.Scrollbar(
            self.output_frame,
            orient="vertical",
            command=self.output.yview
        )

        self.output.configure(yscrollcommand=self.output_vbar.set)

        self.output_vbar.grid(row=0, column=1, sticky="ns")

        # Allow text widget to expand
        self.output_frame.grid_rowconfigure(0, weight=1)
        self.output_frame.grid_columnconfigure(0, weight=1)
        
        self.output.bind("<Button-1>", self.on_output_click)
        self.output.bind("<Motion>", self.on_output_hover)
        self.output.bind("<Leave>", self.on_output_leave)
        
        # ---- Input ----
        
        self.input_frame = ttk.Frame(self.root)
        self.input_frame.grid(row=3, column=0, sticky="ew")
        self.input_frame.grid_columnconfigure(1, weight=1)

        self.input_label = ttk.Label(self.input_frame, text="> ").grid(row=0, column=0, padx=2)

        self.input = ttk.Entry(self.input_frame)
        self.input.grid(row=0, column=1, sticky="ew", padx=2)
        
        self.input.bind("<Return>", self.on_enter)
        self.input.bind("<Up>", self.history_up)
        self.input.bind("<Down>", self.history_down)
        self.input.bind("<Prior>", lambda e: (self.output.yview_scroll(-1, "pages"), "break"))
        self.input.bind("<Next>", lambda e: (self.output.yview_scroll(1, "pages"), "break"))

        # ---- Command Toolbar ----
        
        self.command_toolbar = ttk.Frame(self.root)
        self.command_toolbar.grid(row=4, column=0, sticky="sew")
        self.command_toolbar.grid_rowconfigure(4, weight=0)

        col = 0
        
        # Buttons
        for butt in ["load", "refresh", "clear"]:
            b = ttk.Button(
                self.command_toolbar,
                text=butt.title(),
                command=getattr(self, f"on_press_{butt}")
            )
            setattr(self, f"{butt}_button", b)
            b.grid(row=0, column=col, padx=2, pady=2)
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
        
        self.tasks_label = ttk.Label(self.command_toolbar, text="Tasks: ").grid(row=0, column=col, padx=0)
        col += 1
        
        # Combobox widget for kill button
        self.kill_input = ttk.Combobox(self.command_toolbar, width=12)
        self.kill_input.grid(row=0, column=col, pady=2, padx=2)
        
        self.kill_input
        
        col += 1
        
        
        # Kill button
        b = ttk.Button(
            self.command_toolbar,
            text="kill".title(),
            command=self.on_press_kill
        )
        setattr(self, "kill_button", b)
        b.grid(row=0, column=col, padx=2, pady=2)
        col += 1
        
        
        self.kill_input.bind("<Button-1>", self.on_kill_input_click)
        self.kill_input.bind("<Return>", self.on_press_kill)
        
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
        self.poll_input = ttk.Entry(self.command_toolbar, width=8)
        self.poll_input.grid(row=0, column=col, padx=2)

        self.poll_input.config(state="normal")
        self.poll_input.delete(0, tk.END)
        self.poll_input.insert(0, settings.poll_interval)

        col += 1
        
        self.poll_input.bind("<Return>", self.on_press_poll)
        
        # Poll button
        b = ttk.Button(
            self.command_toolbar,
            text="poll".title(),
            command=self.on_press_poll
        )
        setattr(self, "poll_button", b)
        b.grid(row=0, column=col, padx=2, pady=2)
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
        self.right_button_spacer= ttk.Frame(self.command_toolbar)
        self.right_button_spacer.grid(row=0, column=col, sticky="ew")
        col += 1

        # Right aligned buttons
        for butt in ["exit", "help", "hide"]:
            b = ttk.Button(
                self.command_toolbar,
                text=butt.title(),
                command=getattr(self, f"on_press_{butt}")
            )
            setattr(self, f"{butt}_button", b)
            b.grid(row=0, column=col, padx=2)
            col += 1
        
        
        # ---- Detail widget ----

        self.detail_frame = ttk.Frame(self.root)
        self.detail_frame.grid(row=5, column=0, sticky="nsew")

        self.detail = tk.Text(
            self.detail_frame,
            wrap="word",
            height=10
        )
        self.detail.configure(state="normal")
        self.detail.delete("1.0", tk.END)
        self.detail.insert("1.0", "Click on an event in the output to see details here...")
        self.detail.config(state="disabled")

        self.detail.grid(row=0, column=0, sticky="nsew")

        self.detail_frame.grid_rowconfigure(0, weight=1)
        self.detail_frame.grid_columnconfigure(0, weight=1)

        self.detail.bind("<Button-1>", self.on_detail_click)
        self.detail.bind("<Motion>", self.on_detail_hover)
        self.detail.bind("<Leave>", self.on_detail_leave)
        
        # ---- Footer widget ----
        self.footer = ttk.Frame(self.root)
        self.footer.grid(row=6, column=0, sticky="ew")

        self.footer_label = tk.Text(
            self.footer,
            height=1,
            borderwidth=0,
            highlightthickness=0,
            wrap="none"
        )
        
        self.footer_label.grid(row=0, column=0, sticky="ew")
        

        # ---- append widgets to to theme widget registry ----
        self.theme.menus = [v for v in vars(self).values() if isinstance(v, tk.Menu)]
        self.theme.menubuttons = [v for v in vars(self).values() if isinstance(v, ttk.Menubutton)]
        self.theme.text_widgets = [v for v in vars(self).values() if isinstance(v, tk.Text)]
        self.theme.inputs = [v for v in vars(self).values() if isinstance(v, ttk.Entry)]
        self.theme.comboboxes = [v for v in vars(self).values() if isinstance(v, ttk.Combobox)]
        self.theme.listboxes = [v for v in vars(self).values() if isinstance(v, tk.Listbox)]
        self.theme.labels = [v for v in vars(self).values() if isinstance(v, ttk.Label)]
        self.theme.frames = [v for v in vars(self).values() if isinstance(v, ttk.Frame)]
        self.theme.buttons = [v for v in vars(self).values() if isinstance(v, ttk.Button)]
            
        # Store grid settings for later use
        self.detail_grid_info = self.detail.grid_info()
        self.detail_frame = self.detail_frame
        self.footer_frame = self.footer
        self.footer_grid_info = self.footer.grid_info()

        # set input field as focus after a short amount of time
        self.root.after(150, lambda: self.input.focus_set())
        

    def resize_footer_to_text(self):
        text = self.footer_label.get("1.0", "end-1c")
        if not text:
            text = " "
        
        font = self.footer_label.cget("font")
        try:
            tk_font = tk.font.Font(font=font)
            pixel_width = tk_font.measure(text)
            
        except Exception:
            pixel_width = len(text) * 7
        
        char_width = max(1, len(text))
        self.footer_label.config(width=char_width)
        

    def print_footer(self, line=None):
        self.footer_label.config(state="normal")
        self.footer_label.delete("1.0", "end")

        if not line:
            self.footer_label.config(state="disabled")
            return

        if all(x in line.lower() for x in ("click ", ": ")):
            try:
                parts = line.split(": ")
                sepparator = ": "
                prefix = parts[0].strip()
                key = parts[1].strip()
                rest = parts[2:].strip() if len(parts) >= 3 else None
                
                self.footer_label.insert("end", f"{prefix}{sepparator}")
                self.footer_label.insert("end", key, "bold")
                self.footer_label.insert("end", f"{rest if rest else '' }")
            
            except Exception:
                pass
            
        else:
            self.footer_label.insert("1.0", line)
            
        self.resize_footer_to_text()
        self.footer_label.config(state="disabled")
    
    
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

        # Stop existing flash on this widget
        if widget in self.active_flashes:
            self.stop_flash(widget)

        style = getattr(self.theme, "style", None)
        is_text = isinstance(widget, tk.Text)

        # -------------------------------------------------
        # Capture original colors
        # -------------------------------------------------
        if is_text:
            try:
                orig_bg = widget.cget("background")
            except tk.TclError:
                orig_bg = bg or "white"

            try:
                orig_fg = widget.cget("foreground")
            except tk.TclError:
                orig_fg = fg or "black"

            style_name = None

        else:
            if "style" in widget.keys():
                style_name = widget.cget("style")
            else:
                style_name = widget.winfo_class()

            if style and style_name:
                orig_bg = style.lookup(style_name, "background") or bg
                orig_fg = style.lookup(style_name, "foreground") or fg
            else:
                orig_bg = bg or "white"
                orig_fg = fg or "black"

        # -------------------------------------------------
        # Calculate flash colors
        # -------------------------------------------------
        if invert:
            try:
                temp_bg = invert_color(orig_bg) if orig_bg else bg
                temp_fg = invert_color(orig_fg) if orig_fg else fg
            except Exception:
                temp_bg = bg or orig_bg
                temp_fg = fg or orig_fg
        else:
            temp_bg = bg or orig_bg
            temp_fg = fg or orig_fg

        # -------------------------------------------------
        # Apply flash
        # -------------------------------------------------
        if is_text:
            widget.config(state="normal")
            widget.configure(background=temp_bg, foreground=temp_fg)

        else:
            if style and style_name:
                if temp_bg:
                    style.configure(style_name, background=temp_bg)
                if temp_fg:
                    style.configure(style_name, foreground=temp_fg)

        # -------------------------------------------------
        # Schedule restore
        # -------------------------------------------------
        timer = self.root.after(duration, lambda: self.stop_flash(widget))

        self.active_flashes[widget] = {
            "timer": timer,
            "orig_bg": orig_bg,
            "orig_fg": orig_fg,
            "style_name": style_name,
            "is_text": is_text
        }
        
        
    def stop_flash(self, widget):
        data = self.active_flashes.get(widget)
        if not data:
            return

        timer = data.get("timer")

        try:
            self.root.after_cancel(timer)
        except Exception:
            pass

        self._restore_widget(widget)
        
    
    def stop_all_flashes(self):
        for widget in list(self.active_flashes.keys()):
            self.stop_flash(widget)
    
    
    def is_widget_flashing(self, widget):
        status = self.active_flashes.get(widget, None) is not None
        return status
        
    
    def _restore_widget(self, widget):
        data = self.active_flashes.pop(widget, None)
        if not data:
            return

        style = getattr(self.theme, "style", None)

        orig_bg = data["orig_bg"]
        orig_fg = data["orig_fg"]
        style_name = data["style_name"]
        is_text = data["is_text"]

        if is_text:
            if orig_bg:
                widget.configure(background=orig_bg)
            if orig_fg:
                widget.configure(foreground=orig_fg)

            if widget is self.footer_label:
                self.print_footer()

            widget.config(state="disabled")

        else:
            if style and style_name:
                if orig_bg:
                    style.configure(style_name, background=orig_bg)
                if orig_fg:
                    style.configure(style_name, foreground=orig_fg)
    
    
    
    def toggle_compact_mode(self):
        self.compact_mode = not self.compact_mode

        if self.compact_mode:

            # --- Save layout state ---
            if hasattr(self, "detail_frame"):
                self.detail_frame_grid_info = self.detail_frame.grid_info()

            if hasattr(self, "footer"):
                self.footer_grid_info = self.footer.grid_info()

            # --- Remove widgets ---
            if hasattr(self, "detail_frame"):
                self.detail_frame.grid_remove()

            if hasattr(self, "footer"):
                self.footer.grid_remove()

        else:

            # --- Restore widgets ---
            if hasattr(self, "detail_frame") and hasattr(self, "detail_frame_grid_info"):
                self.detail_frame.grid(**self.detail_frame_grid_info)

            if hasattr(self, "footer") and hasattr(self, "footer_grid_info"):
                self.footer.grid(**self.footer_grid_info)

        # --- Let Tkinter settle layout before repaint ---
        self.root.after_idle(lambda: self.root.update_idletasks())
        
        
    
    def extract_event_id(self, line: str):
        if not line:
            return
            
        line = line.lower()
        matches = re.findall(r"\s(\d{6,})\s", line)
        event_ids = set()
        event_ids = [str(eid.get("id")) for eid in load_events() if eid.get("id", None) != None]
        if matches:
            for match in matches:
                if match in event_ids:
                    try:
                        return match
                        
                    except Exception as e:
                        pass

        return None
    
    def has_valid_eid_format(self, line: str):
        if not line:
            return
            
        matches = re.findall(r"\s(\d{6,})\s", line)
        
        if matches:
            return matches[0]

    # ----------------------------
    # (on) Widget Actions
    # ----------------------------
    
    
    # ---- output widget area ----
    
    def on_output_hover(self, event):
        if time.perf_counter() - self.last_hover < 0.05:
            return

        self.last_hover = time.perf_counter()
        line = self.hover_text(self.output, event, "hover")
        
        e = self.has_valid_eid_format(line)
        
        if e and not self.is_widget_flashing(self.footer_label):
            self.print_footer(f"Click for more info: {e}")

    
    def on_output_leave(self, event):
        self.hover_text(self.output, event, "leave")
        if not self.is_widget_flashing(self.footer_label):
            self.print_footer()
            
    
    def on_output_click(self, event):
        self.update_click()
        line = self.hover_text(self.output, event, "click")
        
        if not line:
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
    def on_press_poll(self, event=None):
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
        
    def on_press_kill(self, event=None):
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

        self.current_event_id = str(event_id)
        self.current_event = flat

        self.render_detail_lines(flat)


    def render_detail_lines(self, flat):
        self.detail.config(state="normal")
        self.detail.delete("1.0", tk.END)

        for i, (k, v) in enumerate(flat.items(), start=1):
            line = f"{k}: {v}\n"
            self.detail.insert(tk.END, line)

        self.detail.insert(tk.END, "(all)")

        self.tag_manager.apply_detail_tags(self.detail, self.detail.get("1.0", tk.END))
        self.detail.config(state="disabled")
            
            
            
    def on_detail_hover(self, event):
        now = time.perf_counter()
        if now - self.last_hover < 0.05:
            return
            
        self.last_hover = now
        line = self.hover_text(self.detail, event, "hover")
        
        if not line:
            return
            
        if not self.is_widget_flashing(self.footer_label):
            try:
                key, value = line.split(": ", 1)
                key = key.split()[-1]
            
            except ValueError:
                key, value = (None, None)
            
            if key and value:
                self.print_footer(f"Click to copy: {key}")
            
            elif "(all)" in line:
                self.print_footer("Click to copy: all")
            
            else:
                self.print_footer()
                
        
    def on_detail_leave(self, event):
        line = self.hover_text(self.detail, event, "leave")
        
        if not self.is_widget_flashing(self.footer_label):
            self.print_footer()
            return
            
    
    def on_detail_click(self, event):
        self.update_click()
        line = self.hover_text(self.detail, event, "click")
        
        if not line:
            return
        
        if not "(all)" in line and ": " in line:
            try:
                key, value = line.split(": ", 1)
                key = key.split()[-1]
                self.root.clipboard_clear()
                self.root.clipboard_append(str(value))
                self.flash_widget(self.footer_label)
                self.print_footer(f"Copied {key.upper()} to clipboard!")
                    
            except ValueError:
                pass
        
        elif "(all)" in line and ": " not in line:
            try:
                lines = "\n".join([str(v) for v in self.current_event.values()])
                self.root.clipboard_clear()
                self.root.clipboard_append(str(lines))
                self.flash_widget(self.footer_label)
                self.print_footer("Copied ALL to clipboard!")
                    
            except ValueError:
                pass
                
    
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
        
        self.ctx.state["force_scroll"] = True
        
    
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
        
        
    def is_near_bottom(self, widget, total_rendered_lines: int) -> bool:
        first_visible = int(widget.index("@0,0").split(".")[0])
        last_visible = int(widget.index(f"@0,{widget.winfo_height()}").split(".")[0])
        visible_lines = last_visible - first_visible
        
        return total_rendered_lines - last_visible <= visible_lines


    def print_output(self, snapshot: str, auto_scroll=True):
        LOG_RE = re.compile(r"^\[[+\-!i]\]\s\d{2}:\d{2}:\d{2}")
        lines = snapshot.splitlines()
        new_lines = lines[self.rendered_lines:]

        if not new_lines:
            return

        self.output.config(state="normal")

        if auto_scroll:
            near_bottom = self.is_near_bottom(self.output, total_rendered_lines = self.rendered_lines)
        else:
            near_bottom = False

        new_lines_start = self.rendered_lines + 1
        for line in new_lines:
            if LOG_RE.match(line):
                parts = line.split(" | ", 1)
                separator = " | "
                log_text = parts[0].strip()
                rest = parts[1] if len(parts) >= 2 else ""
                self.output.insert("end", f"{log_text}{separator}", "log")
                self.output.insert("end", f"{rest}\n")
            else:
                self.output.insert("end", f"{line}\n")

        self.tag_manager.apply_color_tags(self.output, "\n".join(new_lines), new_lines_start)

        if auto_scroll and near_bottom:
            self.output.see("end")

        self.output.config(state="disabled")
        self.rendered_lines = len(lines)

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
            f"{self.rendered_lines} lines {right_siren}"
        )
        self.title_label.config(text=title_text)
        
        if self.ctx.state.get("force_scroll", False):
            self.output.see("end")
            
        # ---- Output update ----
        if snapshot != self.last_snapshot:
            self.print_output(snapshot)
            self.last_snapshot = snapshot
            
            
            

