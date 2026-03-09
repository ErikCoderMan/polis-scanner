import tkinter as tk
from tkinter import ttk
from src.utils.tools import str_to_hex, generate_highlight_colors


class ThemeManager:
    def __init__(self, app):
        self.app = app
        self.root = app.root

        self.current_theme = "default"

        self.style = ttk.Style(self.root)
        
        self.menus: list[tk.Menu] = []
        self.text_widgets: list[tk.Text] = []
        self.footer_widgets: list[ttk.Label] = []
        self.comboboxes: list[ttk.Combobox] = []
        self.listboxes: list[tk.Listbox] = []

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

    def clear_registries(self):
        self.menus.clear()
        self.text_widgets.clear()
        self.footer_widgets.clear()
        self.comboboxes.clear()
        self.listboxes.clear()
        
        self.root.option_clear()

    # -------------------------------------------------
    # Runtime snapshot (called manually after layout build)
    # -------------------------------------------------
    def store_defaults(self):
        """
        Capture runtime palette snapshot after layout construction.
        """

        def snapshot_text(widget: tk.Text):
            self.palette["default"]["text"] = {
                "background": widget.cget("background"),
                "foreground": widget.cget("foreground"),
                "insertbackground": widget.cget("insertbackground"),
                "selectbackground": widget.cget("selectbackground"),
                "selectforeground": widget.cget("selectforeground"),
                "highlightbackground": widget.cget("highlightbackground"),
                "highlightcolor": widget.cget("highlightcolor"),
                "highlightthickness": widget.cget("highlightthickness"),
            }

            bg = widget.cget("background")
            fg = widget.cget("foreground")

            h_bg, h_fg = generate_highlight_colors(bg=bg, fg=fg)

            self.hover_text["default"]["bg"] = h_bg
            self.hover_text["default"]["fg"] = h_fg

        def snapshot_menus(self):
            palette = {}

            for menu_widget in self.menus:
                palette.update({
                    k: menu_widget.cget(k)
                    for k in menu_widget.configure().keys()
                    if menu_widget.cget(k) is not None
                })

            if palette:
                self.palette["default"]["menu"] = palette

        def snapshot_footer(widget):
            if not widget:
                return

            style_name = widget.cget("style") or "Footer.TLabel"

            bg = self.style.lookup(style_name, "background") or widget.cget("background")
            fg = self.style.lookup(style_name, "foreground") or widget.cget("foreground")

            self.palette["default"]["footer"] = {
                "background": bg,
                "foreground": fg,
            }

        # --- Capture runtime widgets ---
        if isinstance(getattr(self.app, "output", None), tk.Text):
            snapshot_text(self.app.output)

        snapshot_menus(self)
        snapshot_footer(getattr(self.app, "footer_label", None))


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

        self.root.option_clear()

        self.themes[theme_name]()

        self.propagate_theme()
        self._apply_combobox_palette()
        self._apply_listbox_palette()
        self._apply_menu_palette()

        self.root.update_idletasks()

    # -------------------------------------------------

    def propagate_theme(self):
        """
        Explicit registry-based theme propagation.
        """
        theme_palette = self.palette[self.current_theme]
        
        if not theme_palette:
            return

        # --- Text widgets ---
        for attr_name in ["output", "detail"]:
            widget = getattr(self.app, attr_name, None)

            if isinstance(widget, tk.Text):
                palette = theme_palette.get("text")

                if palette:
                    valid_keys = widget.configure().keys()

                    apply_dict = {
                        k: v for k, v in palette.items()
                        if k in valid_keys and v is not None
                    }

                    if apply_dict:
                        widget.configure(**apply_dict)


        # --- Footer ---
        if hasattr(self.app, "footer_label"):
            footer_palette = theme_palette.get("footer")

            if footer_palette:
                self._set_style(
                    "Footer.TLabel",
                    background=footer_palette["background"],
                    foreground=footer_palette["foreground"],
                    anchor="w"
                )


    # -------------------------------------------------
    
    def _apply_menu_palette(self):
        """
        Apply palette only to explicitly registered menus.
        """
        menu_palette = self.palette[self.current_theme].get("menu")
        
        if not menu_palette:
            return

        for menu in self.menus:
            try:
                valid_keys = menu.configure().keys()

                apply_dict = {
                    k: v for k, v in menu_palette.items()
                    if k in valid_keys and v is not None
                }

                if apply_dict:
                    menu.configure(**apply_dict)

            except Exception:
                continue
    
    
    def _apply_combobox_palette(self):
        palette = self.palette[self.current_theme].get("combobox", {})
        
        if not palette:
            return
        self._set_style(
            "TCombobox",
            fieldbackground=palette.get("fieldbackground"),
            background=palette.get("background"),
            foreground=palette.get("foreground"),
            arrowcolor=palette.get("arrowcolor"),
            insertcolor=palette.get("foreground"),
            bordercolor=palette.get("background"),
            borderwidth=palette.get("borderwidth"),
            lightcolor=palette.get("lightcolor"),
            darkcolor=palette.get("darkcolor"),
            relief=palette.get("relief")
        )

        self.style.map(
            "TCombobox",
            bordercolor=[("focus", palette["bordercolor_focus"])],
            background=[("active", palette["background_active"])],
            lightcolor=[("focus", palette["lightcolor_focus"])],
            darkcolor=[("focus", palette["darkcolor_focus"])]
        )

        palette = self.palette[self.current_theme].get("combobox", {}).get("listbox", {})
        
        if not palette:
            return
        
        self.root.option_add("*TCombobox*Listbox.background",
            palette["background"])
            
        self.root.option_add("*TCombobox*Listbox.foreground",
            palette["foreground"])
            
        self.root.option_add("*TCombobox*Listbox.selectBackground",
            palette["selectbackground"])
            
        self.root.option_add("*TCombobox*Listbox.selectForeground",
            palette["selectforeground"])
            
        self.root.option_add("*TCombobox*Listbox.highlightThickness", 1)
        self.root.option_add("*TCombobox*Listbox.borderWidth", 1)
        
        
        for combo in self.comboboxes:
            try:
                if not combo.winfo_exists():
                    continue
                    
                combo.tk.call("ttk::combobox::PopdownWindow", combo)
                combo.event_generate("<Button-1>")
                combo.event_generate("<Alt-Down>")
                
            except tk.TclError:
                continue
            
            finally:
                combo.update_idletasks()
                combo.event_generate("<Escape>")

        
    
    def _apply_listbox_palette(self):
        palette = self.palette[self.current_theme].get("listbox", {})
        
        if not palette:
            palette = self.palette[self.current_theme].get("combobox", {})
            
            if palette:
                palette = palette.get("listbox")
        
        if not palette:
            return

        for lb in self.listboxes:
            if not lb.winfo_exists():
                continue
            
            try:
                lb.configure(
                    bg=palette["background"],
                    fg=palette["foreground"],
                    selectbackground=palette["selectbackground"],
                    selectforeground=palette["selectforeground"]
                )
                
            except tk.TclError:
                continue
    
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
        # =====================================================
        # Palette base
        # =====================================================

        bg_main = "#252525"
        bg_surface = "#353535"
        bg_input = "#151515"
        bg_output = "#151515"

        fg_main = "#d9d9d9"
        fg_secondary = "#c0c0c0"
        fg_list = "#252525"

        outline_inactive = "#404040"
        outline_active = "#202020"
        outline_thickness = 1
        borderwidth = 1

        input_border_color = "#353535"
        input_border_color_focus = "#353535"

        accent_active = "#454545"
        accent_hover = "#454545"

        light_color = "#505050"
        dark_color = "#060606"

        sepparator_color = "#454545"

        menu_active_fg = "#efefef"

        select_bg = "#454545"

        # Hover text snapshot
        self.hover_text["dark"]["bg"] = "#252525"
        self.hover_text["dark"]["fg"] = "#ffffff"
            

        # =====================================================
        # Text palette
        # =====================================================

        self.palette["dark"]["text"] = {
            "background": bg_output,
            "foreground": fg_main,
            "insertbackground": fg_main,
            "selectbackground": select_bg,
            "selectforeground": fg_main,
            "highlightthickness": outline_thickness,
            "highlightbackground": outline_inactive,
            "highlightcolor": outline_active
        }
        
        # =====================================================
        # Input palette
        # =====================================================
        
        self.palette["dark"]["input"] = {
            "fieldbackground": bg_input,
            "foreground": fg_main,
            "insertcolor": fg_main,
            "bordercolor": input_border_color,
            "lightcolor": input_border_color,
            "darkcolor": input_border_color,
            "relief": "sunken",
            "focuscolor": input_border_color,
            "borderwidth": outline_thickness,
            "padding": 0
        }

        # =====================================================
        # Menu palette
        # =====================================================

        self.palette["dark"]["menu"] = {
            "background": bg_surface,
            "foreground": fg_main,
            "activebackground": accent_hover,
            "activeforeground": menu_active_fg
        }
        
        # =====================================================
        # Layout widgets
        # =====================================================

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
            borderwidth=0,
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

        # =====================================================
        # Entry
        # =====================================================

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
            borderwidth=borderwidth,
            padding=1
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

        # =====================================================
        # Combobox
        # =====================================================
        
        self.palette["dark"]["combobox"] = {
            "fieldbackground": bg_input,
            "background": bg_surface,
            "background_active": accent_hover,
            "foreground": fg_main,
            "arrowcolor": fg_secondary,
            "insertcolor": fg_main,
            "bordercolor": bg_input,
            "borderwidth": borderwidth,
            "bordercolor_focus": input_border_color_focus,
            "lightcolor": input_border_color,
            "lightcolor_focus": input_border_color_focus,
            "darkcolor": input_border_color,
            "darkcolor_focus": input_border_color_focus,
            "relief": "solid",
            "listbox": {
                "background": bg_input,
                "foreground": fg_secondary,
                "selectbackground": input_border_color_focus,
                "selectforeground": fg_main
                }
            }
            

        # =====================================================
        # Scrollbar
        # =====================================================

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

        # =====================================================
        # Footer Label
        # =====================================================

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
        # =====================================================
        # Palette base
        # =====================================================

        bg_main = "#d5d5d5"
        bg_surface = "#b6b6b6"
        bg_input = "#ffffff"
        bg_output = "#ffffff"

        fg_main = "#000000"
        fg_secondary = "#1f1f1f"
        fg_list = "#1f1f1f"

        outline_inactive = "#e0e0e0"
        outline_active = "#a0a0a0"
        outline_thickness = 1
        borderwidth = 1

        input_border_color = "#b6b6b6"
        input_border_color_focus = "#b6b6b6"

        accent_active = "#a6a6a6"
        accent_hover = "#a6a6a6"

        light_color = "#e8e8e8"
        dark_color = "#404040"

        sepparator_color = "#808080"

        menu_active_fg = "#000000"

        select_bg = "#a6a6a6"

        # Hover text snapshot
        self.hover_text["light"]["bg"] = "#d5d5d5"
        self.hover_text["light"]["fg"] = "#000000"
            

        # =====================================================
        # Text palette
        # =====================================================

        self.palette["light"]["text"] = {
            "background": bg_output,
            "foreground": fg_main,
            "insertbackground": fg_main,
            "selectbackground": select_bg,
            "selectforeground": fg_main,
            "highlightthickness": outline_thickness,
            "highlightbackground": outline_inactive,
            "highlightcolor": outline_active
        }
        
        # =====================================================
        # Input palette
        # =====================================================
        
        self.palette["light"]["input"] = {
            "fieldbackground": bg_input,
            "foreground": fg_main,
            "insertcolor": fg_main,
            "bordercolor": input_border_color,
            "lightcolor": input_border_color,
            "darkcolor": input_border_color,
            "relief": "sunken",
            "focuscolor": input_border_color,
            "borderwidth": outline_thickness,
            "padding": 0
        }

        # =====================================================
        # Menu palette
        # =====================================================

        self.palette["light"]["menu"] = {
            "background": bg_surface,
            "foreground": fg_main,
            "activebackground": accent_hover,
            "activeforeground": menu_active_fg
        }
        
        # =====================================================
        # Layout widgets
        # =====================================================

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
            borderwidth=0,
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

        # =====================================================
        # Entry
        # =====================================================

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
            borderwidth=borderwidth,
            padding=1
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

        # =====================================================
        # Combobox
        # =====================================================
        
        self.palette["light"]["combobox"] = {
            "fieldbackground": bg_input,
            "background": bg_surface,
            "background_active": accent_hover,
            "foreground": fg_main,
            "arrowcolor": fg_secondary,
            "insertcolor": fg_main,
            "bordercolor": bg_input,
            "borderwidth": borderwidth,
            "bordercolor_focus": input_border_color_focus,
            "lightcolor": input_border_color,
            "lightcolor_focus": input_border_color_focus,
            "darkcolor": input_border_color,
            "darkcolor_focus": input_border_color_focus,
            "relief": "solid",
            "listbox": {
                "background": bg_input,
                "foreground": fg_secondary,
                "selectbackground": input_border_color_focus,
                "selectforeground": fg_main
                }
            }
            

        # =====================================================
        # Scrollbar
        # =====================================================

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

        # =====================================================
        # Footer Label
        # =====================================================

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

        # -------------------------------------------------
