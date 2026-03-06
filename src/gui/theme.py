import tkinter as tk
from tkinter import ttk
from src.utils.tools import str_to_hex, generate_highlight_colors


# ----------------------------------------
# Example usage when used by src/gui/ui.py:
# ----------------------------------------
# 1. self.theme = ThemeManager(self)
# 2. self.build_layout()
# 3. self.theme.store_defaults()
# ----------------------------------------
# We have to create the object, then build layout
# and after that use store_defaults metod to store
# the default system color settings.
# ---------------------------------------- 
# These steps have to be sepparated because
# class A needs data from class B
# but class B also needs data from class A
# ---------------------------------------- 
# It is worth mentioning that it is best to
# always start the program with system default settings
# initially every time, then:
# ---------------------------------------- 
# 1. Save the systems default theme 
# 2. Apply another theme if prefered (read settings or .env etc)
#    because then the default theme exists in RAM memory in the object.
# ---------------------------------------- 
# Because its harder to obtain the system values
# after a custom theme has been applied.
# This is why we store the original values before overwriting.
# ---------------------------------------- 

class ThemeManager:
    def __init__(self, app):
        self.app = app
        self.root = app.root

        self.current_theme = "default"

        self.style = ttk.Style(self.root)

        # Palette registry
        self.palette = {
            "default": {},
            "dark": {},
            "light": {}
        }

        self.themes = {
            "default": self._define_default,
            "dark": self._define_dark,
            "light": self._define_light
        }
        
        # sepparating this from "palette dict"
        # because it has predefined values,
        # these don't have to be.
        self.hover_text = {
            "default": {
                "bg": "",
                "fg": "",
            },
            "dark": {
                "bg": "",
                "fg": "",
            },
            "light": {
                "bg": "",
                "fg": "",
            }
        }
        
        
        self.menus: list[tk.Menu] = []
        

    # -------------------------------------------------
    # Runtime snapshot (called manually after layout build)
    # -------------------------------------------------
    def store_defaults(self):
        """Capture runtime default palette snapshot."""

        def snapshot_text(widget: tk.Text):

            self.palette["default"]["text"] = {
                "background": widget.cget("background"),
                "foreground": widget.cget("foreground"),
                "insertbackground": widget.cget("insertbackground"),
                "selectbackground": widget.cget("selectbackground"),
                "selectforeground": widget.cget("selectforeground"),
                "highlightbackground": widget.cget("highlightbackground"),
                "highlightcolor": widget.cget("highlightcolor"),
                "highlightthickness": widget.cget("highlightthickness")
            }
            # ----------------------------------------
            # Try to find a decent highlight BG and FG for default
            # By meassuring if system BG color is below or above
            # "medium grey" we can assume if brighter or darker is better
            # ----------------------------------------
            
            # Use BG and FG that was applied to tk.Text widget
            # by the system, those values indicates
            # wether system is using a dark or light theme
            bg = self.palette["default"]["text"]["background"]
            fg = self.palette["default"]["text"]["foreground"]
            
            # Generate highlight colors
            h_bg, h_fg = generate_highlight_colors(bg = bg, fg = fg)
            
            # And store the values
            self.hover_text["default"]["bg"] = h_bg
            self.hover_text["default"]["fg"] = h_fg
            

        def snapshot_menu(widget):
            """
            Snapshot menu even if menu is attached to Menubutton.
            """

            menu_widget = None

            # If widget itself is Menu
            if isinstance(widget, tk.Menu):
                menu_widget = widget

            # If Menubutton → extract attached menu
            elif isinstance(widget, ttk.Menubutton):
                try:
                    menu_name = widget.cget("menu")
                    if menu_name:
                        menu_widget = widget.nametowidget(menu_name)
                except Exception:
                    menu_widget = None

            if menu_widget:
                self.palette["default"]["menu"] = {
                    k: menu_widget.cget(k)
                    for k in menu_widget.configure().keys()
                    if menu_widget.cget(k) is not None
                }
            
        def snapshot_footer(widget: ttk.Label):
            style_name = widget.cget("style") or "Footer.TLabel"

            bg = self.style.lookup(style_name, "background") or widget.cget("background")
            fg = self.style.lookup(style_name, "foreground") or widget.cget("foreground")

            self.palette["default"]["footer"] = {
                "background": bg,
                "foreground": fg
            }

        if hasattr(self.app, "output") and isinstance(self.app.output, tk.Text):
            snapshot_text(self.app.output)

        # Snapshot menu if exists
        if hasattr(self.app, "menu"):
            snapshot_menu(self.app.menu)
        
        if hasattr(self.app, "footer_label"):
            snapshot_footer(self.app.footer_label)


    # -------------------------------------------------

    def apply(self, theme_name: str):
        if getattr(self, "is_theme_locked", False):
            return
            
        if theme_name not in self.themes:
            raise ValueError(f"Unknown theme: {theme_name}")

        self.current_theme = theme_name

        if theme_name == "default":
            self.style.theme_use("default")
        else:
            self.style.theme_use("clam")

        # Build palette first
        self.themes[theme_name]()

        # Then propagate runtime widgets
        self._recursive_style_apply(self.root)
        
        self._apply_menu_palette()

        self.root.update_idletasks()

    # -------------------------------------------------

    def _recursive_style_apply(self, widget):

        theme_palette = self.palette[self.current_theme]
        if not theme_palette:
            return

        # -----------------------------
        # Text widget
        # -----------------------------
        if isinstance(widget, tk.Text):
            palette = theme_palette.get("text")
            if palette:
                valid_options = widget.configure().keys()

                apply_dict = {
                    k: v for k, v in palette.items()
                    if k in valid_options and v is not None
                }

                if apply_dict:
                    widget.configure(**apply_dict)

        # -----------------------------
        # Menu widget OR menu attached to Menubutton
        # -----------------------------
        menu_palette = theme_palette.get("menu")

        menu_widget = None

        if isinstance(widget, tk.Menu):
            menu_widget = widget

        elif isinstance(widget, ttk.Menubutton):
            try:
                menu_name = widget.cget("menu")
                if menu_name:
                    menu_widget = widget.nametowidget(menu_name)
            except Exception:
                menu_widget = None

        if menu_widget and menu_palette:
            valid_options = menu_widget.configure().keys()

            apply_dict = {
                k: v for k, v in menu_palette.items()
                if k in valid_options and v is not None
            }

            if apply_dict:
                menu_widget.configure(**apply_dict)

        # -----------------------------
        # Traverse children
        # -----------------------------
        if hasattr(widget, "winfo_children"):
            for child in widget.winfo_children():
                self._recursive_style_apply(child)

    # -------------------------------------------------
    
    def _apply_menu_palette(self):

        menu_palette = self.palette[self.current_theme].get("menu")
        if not menu_palette:
            return

        for menu in self.menus:
            valid = menu.configure().keys()

            apply_dict = {
                k: v for k, v in menu_palette.items()
                if k in valid and v is not None
            }

            if apply_dict:
                menu.configure(**apply_dict)
    
    
    # -------------------------------------------------
    
    def _set_style(self, widget_style: str, **kwargs):
        self.style.configure(widget_style, **kwargs)

    def _set_map(self, widget_style: str, **kwargs):
        self.style.map(widget_style, **kwargs)

    # -------------------------------------------------
    # Themes
    # -------------------------------------------------

    def _define_default(self):
        # Default value for custom divider
        self._set_style(
            "ToolbarDivider.TFrame",
            background="#808080",
            width=1
        )
        
        footer_palette = self.palette["default"].get("footer")
        if footer_palette:
            self._set_style(
                "Footer.TLabel",
                background=footer_palette["background"],
                foreground=footer_palette["foreground"],
                anchor="w"
            )

    # -------------------------------------------------

    def _define_dark(self):
        
        # ---------- Palette base ----------
        bg_main = "#252525"
        bg_surface = "#353535"
        bg_input = "#151515"
        bg_output = "#151515"

        fg_main = "#c0c0c0"
        fg_secondary = "#ffffff"

        outline_inactive = "#202020"
        outline_active = "#404040"
        outline_thickness=2

        input_border_color = "#353535"
        input_border_color_focus = "#252525"

        accent_active = "#454545"
        accent_hover = "#454545"

        light_color = "#505050"
        dark_color = "#060606"
        
        sepparator_color = "#505050"
        
        menu_active_fg = "#efefef"
        
        self.hover_text["dark"]["bg"] = "#303030"
        self.hover_text["dark"]["fg"] = "#ffffff"
        

        # ---------- Text palette ----------
        self.palette["dark"]["text"] = {
            "background": bg_output,
            "foreground": fg_main,
            "insertbackground": fg_main,
            "selectbackground": accent_active,
            "selectforeground": fg_main,
            "highlightthickness": outline_thickness,
            "highlightbackground": outline_inactive,
            "highlightcolor": outline_active
        }

        # ---------- Menu palette ----------
        self.palette["dark"]["menu"] = {
            "background": bg_surface,
            "foreground": fg_main,
            "activebackground": accent_hover,
            "activeforeground": menu_active_fg
        }

        # ---------- Layout widgets ----------
        self._set_style("TFrame", background=bg_main)

        self._set_style(
            "TLabel",
            background=bg_main,
            foreground=fg_main
        )

        self._set_style(
            "TButton",
            background=bg_surface,
            foreground=fg_main,
            borderwidth=0,
            relief="flat",
            lightcolor=light_color,
            darkcolor=dark_color
        )

        self._set_map(
            "TButton",
            background=[("active", accent_hover)]
        )
        
        self._set_style(
            "TMenubutton",
            background=bg_surface,
            foreground=fg_main,
            borderwidth=1,
            relief="flat",
            arrowcolor=fg_secondary
        )

        self._set_map(
            "TMenubutton",
            background=[("active", accent_hover)]
        )
        
        self._set_style(
            "ToolbarDivider.TFrame",
            background=sepparator_color,
            width=1
        )

        # ---------- Entry ----------
        self._set_style(
            "TEntry",
            fieldbackground=bg_input,
            foreground=fg_main,
            insertcolor=fg_main,
            bordercolor=input_border_color,
            lightcolor=input_border_color,
            darkcolor=input_border_color,
            relief="sunken",
            focuscolor=input_border_color,
            borderwidth=0,
            padding=0
        )

        self.style.map(
            "TEntry",
            bordercolor=[
                ("focus", input_border_color_focus),
                ("!focus", input_border_color)
            ],
            lightcolor=[
                ("focus", input_border_color_focus),
                ("!focus", input_border_color)
            ],
            darkcolor=[
                ("focus", input_border_color_focus),
                ("!focus", input_border_color)
            ]
        )

        # ---------- Combobox ----------
        self._set_style(
            "TCombobox",
            fieldbackground=bg_input,
            background=input_border_color,
            foreground=fg_main,
            arrowcolor=fg_secondary,
            insertcolor=fg_main,
            bordercolor=input_border_color,
            lightcolor=input_border_color,
            darkcolor=input_border_color,
            relief="flat"
        )

        self.root.option_add("*TCombobox*Listbox.background", bg_input)
        self.root.option_add("*TCombobox*Listbox.foreground", fg_secondary)
        self.root.option_add("*TCombobox*Listbox.selectBackground", accent_hover)
        self.root.option_add("*TCombobox*Listbox.selectForeground", fg_main)

        self.style.map(
            "TCombobox",
            bordercolor=[("focus", input_border_color_focus)],
            background=[("active", input_border_color_focus)],
            lightcolor=[("focus", input_border_color_focus)],
            darkcolor=[("focus", input_border_color_focus)]
        )

        # ---------- Scrollbar ----------
        self._set_style(
            "TScrollbar",
            background=bg_surface,
            troughcolor=bg_output,
            arrowcolor=fg_secondary,
            bordercolor=input_border_color,
            lightcolor=light_color,
            darkcolor=dark_color
        )

        self.style.map(
            "TScrollbar",
            background=[
                ("active", accent_hover),
                ("pressed", accent_active)
            ]
        )
        
        # ---------- Footer ----------
        
        self.palette["dark"]["footer"] = {
            "background": bg_main,
            "foreground": fg_secondary
        }
        
        footer_palette = self.palette["dark"]["footer"]

        if footer_palette:
            self._set_style(
                "Footer.TLabel",
                background=footer_palette["background"],
                foreground=footer_palette["foreground"],
                anchor="w"
            )

        self.root.configure(bg=bg_main)

    # -------------------------------------------------

    def _define_light(self):

        # ---------- Palette base ----------
        bg_main = "#d5d5d5"
        bg_surface = "#b6b6b6"
        bg_input = "#ffffff"
        bg_output = "#ffffff"

        fg_main = "#000000"
        fg_secondary = "#1f1f1f"

        outline_inactive = "#e0e0e0"
        outline_active = "#808080"
        outline_thickness=1

        input_border_color = "#b6b6b6"
        input_border_color_focus = "#d5d5d5"

        accent_active = "#a0a0a0"
        accent_hover = "#a0a0a0"

        light_color = "#e8e8e8"
        dark_color = "#404040"
        
        sepparator_color = "#808080"
        
        menu_active_fg = "#000000"
        
        self.hover_text["light"]["bg"] = "#c8c8c8"
        self.hover_text["light"]["fg"] = "#000000"

        # ---------- Text palette ----------
        self.palette["light"]["text"] = {
            "background": bg_output,
            "foreground": fg_main,
            "insertbackground": fg_main,
            "selectbackground": accent_active,
            "selectforeground": fg_main,
            "highlightbackground": outline_inactive,
            "highlightcolor": outline_active,
            "highlightthickness": outline_thickness
        }

        # ---------- Menu palette ----------
        self.palette["light"]["menu"] = {
            "background": bg_surface,
            "foreground": fg_main,
            "activebackground": accent_active,
            "activeforeground": menu_active_fg
        }

        # ---------- Layout widgets ----------
        self._set_style("TFrame", background=bg_main)

        self._set_style(
            "TLabel",
            background=bg_main,
            foreground=fg_main
        )

        self._set_style(
            "TButton",
            background=bg_surface,
            foreground=fg_main,
            borderwidth=0,
            relief="flat",
            lightcolor=outline_inactive,
            darkcolor=outline_inactive
        )

        self._set_map(
            "TButton",
            background=[("active", accent_hover)]
        )
        
        self._set_style(
            "TMenubutton",
            background=bg_surface,
            foreground=fg_main,
            borderwidth=1,
            relief="flat",
            arrowcolor=fg_secondary
        )
        
        self._set_map(
            "TMenubutton",
            background=[("active", accent_hover)]
        )
        
        self._set_style(
            "ToolbarDivider.TFrame",
            background=sepparator_color,
            width=1
        )


        # ---------- Entry ----------
        self._set_style(
            "TEntry",
            fieldbackground=bg_input,
            foreground=fg_main,
            insertcolor=fg_main,
            bordercolor=input_border_color,
            lightcolor=input_border_color,
            darkcolor=input_border_color,
            relief="flat",
            focuscolor=input_border_color,
            borderwidth=0,
            padding=0
        )

        self.style.map(
            "TEntry",
            bordercolor=[
                ("focus", input_border_color_focus),
                ("!focus", input_border_color)
            ],
            lightcolor=[
                ("focus", input_border_color_focus),
                ("!focus", input_border_color)
            ],
            darkcolor=[
                ("focus", input_border_color_focus),
                ("!focus", input_border_color)
            ]
        )

        # ---------- Combobox ----------
        self._set_style(
            "TCombobox",
            fieldbackground=bg_input,
            background=bg_surface,
            foreground=fg_main,
            arrowcolor=fg_secondary,
            insertcolor=fg_main,
            bordercolor=input_border_color,
            lightcolor=input_border_color,
            darkcolor=input_border_color,
            relief="flat"
        )

        self.root.option_add("*TCombobox*Listbox.background", bg_input)
        self.root.option_add("*TCombobox*Listbox.foreground", fg_secondary)
        self.root.option_add("*TCombobox*Listbox.selectBackground", accent_hover)
        self.root.option_add("*TCombobox*Listbox.selectForeground", fg_main)

        self.style.map(
            "TCombobox",
            bordercolor=[("focus", input_border_color_focus)],
            background=[("active", accent_hover)],
            lightcolor=[("focus", input_border_color_focus)],
            darkcolor=[("focus", input_border_color_focus)]
        )

        # ---------- Scrollbar ----------
        self._set_style(
            "TScrollbar",
            background=bg_surface,
            troughcolor=bg_main,
            arrowcolor=fg_secondary,
            bordercolor=input_border_color,
            lightcolor=light_color,
            darkcolor=dark_color
        )

        self.style.map(
            "TScrollbar",
            background=[
                ("active", accent_hover),
                ("pressed", accent_active)
            ]
        )
        
        # ---------- Footer Label ----------
        self.palette["light"]["footer"] = {
            "background": bg_main,
            "foreground": fg_secondary
        }
        
        footer_palette = self.palette["light"]["footer"]

        if footer_palette:
            self._set_style(
                "Footer.TLabel",
                background=footer_palette["background"],
                foreground=footer_palette["foreground"],
                anchor="w"
            )

        self.root.configure(bg=bg_main)
