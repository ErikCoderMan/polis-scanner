import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
from src.utils.tools import str_to_hex, generate_highlight_colors


class ThemeManager:
    def __init__(self, app):
        self.app = app
        self.root = app.root

        self.current_theme = "default"

        self.style = ttk.Style(self.root)
        
        self.menus: list[tk.Menu] = []
        self.text_widgets: list[tk.Text] = []
        self.inputs: list[ttk.Entry] = []
        self.footer_widgets: list[ttk.Label | ttk.Text] = []
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
        self.inputs.clear()
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
        All fonts are stored as tkfont.Font objects for direct use in configure().
        Colors are extracted from style when relevant to handle ttk widgets properly.
        """
        style = ttk.Style()

        # ----------------------------
        # Text widgets
        # ----------------------------
        def snapshot_text(widget: tk.Text):
            font_obj = tkfont.Font(font=widget.cget("font"))

            self.palette["default"]["text"] = {
                "background": widget.cget("background"),
                "foreground": widget.cget("foreground"),
                "insertbackground": widget.cget("insertbackground"),
                "selectbackground": widget.cget("selectbackground"),
                "selectforeground": widget.cget("selectforeground"),
                "highlightbackground": widget.cget("highlightbackground"),
                "highlightcolor": widget.cget("highlightcolor"),
                "highlightthickness": widget.cget("highlightthickness"),
                "font": font_obj
            }

            # Optional hover highlight colors
            h_bg, h_fg = generate_highlight_colors(
                bg=widget.cget("background"),
                fg=widget.cget("foreground")
            )
            self.hover_text["default"]["bg"] = h_bg
            self.hover_text["default"]["fg"] = h_fg

        # ----------------------------
        # Entry / Input widgets (ttk)
        # ----------------------------
        def snapshot_entry(widget):
            cls = widget.winfo_class()
            font_obj = tkfont.Font(font=widget.cget("font"))

            field_bg = style.lookup(cls, "fieldbackground") or widget.cget("background")
            fg = style.lookup(cls, "foreground") or widget.cget("foreground")
            insert_fg = fg

            self.palette["default"]["entry"] = {
                "fieldbackground": field_bg,
                "foreground": fg,
                "insertcolor": insert_fg,
                "borderwidth": widget.cget("borderwidth") if "borderwidth" in widget.configure() else 1,
                "font": font_obj
            }

        # ----------------------------
        # Footer text (tk.Text)
        # ----------------------------
        def snapshot_footer(widget: tk.Text):
            font_obj = tkfont.Font(font=widget.cget("font"))
            bold_font = font_obj.copy()
            bold_font.configure(weight="bold")

            self.palette["default"]["footer"] = {
                "background": "black",
                "foreground": widget.cget("foreground"),
                "font": font_obj,
                "bold_font": bold_font
            }

        # ----------------------------
        # Menus
        # ----------------------------
        def snapshot_menus():
            palette = {}
            for menu_widget in self.menus:
                cfg = {}
                for k in menu_widget.configure().keys():
                    try:
                        val = menu_widget.cget(k)
                        if val is not None:
                            cfg[k] = val
                    except tk.TclError:
                        continue
                if cfg:
                    palette.update(cfg)
            if palette:
                self.palette["default"]["menu"] = palette

        # ----------------------------
        # Capture widgets if they exist
        # ----------------------------
        output_widget = getattr(self.app, "output", None)
        if isinstance(output_widget, tk.Text):
            snapshot_text(output_widget)

        input_widget = getattr(self.app, "input", None)
        if isinstance(input_widget, (ttk.Entry, tk.Entry)):
            snapshot_entry(input_widget)

        if self.menus:
            snapshot_menus()

        footer_widget = getattr(self.app, "footer_label", None)
        if isinstance(footer_widget, tk.Text):
            snapshot_footer(footer_widget)
        

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
        
        self.root.update_idletasks()

    # -------------------------------------------------

    def propagate_theme(self):
        """
        Apply the current theme palette to all registered widgets and styles.
        """
        theme_palette = self.palette.get(self.current_theme)
        if not theme_palette:
            return

        # =====================================================
        # General widget styles (TFrame, TLabel, TButton, TMenubutton, TScrollbar)
        # =====================================================
        p = self.palette.get(self.current_theme, {})

        for widget_name, ttk_name in [
            ("frame", "TFrame"),
            ("label", "TLabel"),
            ("button", "TButton"),
            ("menubutton", "TMenubutton"),
            ("entry", "TEntry"),
            ("scrollbar", "TScrollbar"),
            ("divider", "ToolbarDivider.TFrame"),
            ("footer", "Footer.TLabel")
        ]:
            cfg = p.get(widget_name, {})
            style = cfg.get("style")
            state_map = cfg.get("map")

            if style:
                self._set_style(ttk_name, **style)
            if state_map:
                self._set_map(ttk_name, **state_map)

        # =====================================================
        # Text widgets
        # =====================================================
        for widget in self.text_widgets:
            palette = theme_palette.get("text", {})
            if palette:
                valid_keys = widget.configure().keys()
                apply_dict = {k: v for k, v in palette.items() if k in valid_keys and v is not None}
                if apply_dict:
                    widget.configure(**apply_dict)

        # =====================================================
        # Entry widgets
        # =====================================================
        for entry in getattr(self, "inputs", []):
            if not entry.winfo_exists():
                continue

            palette = theme_palette.get("entry", {})
            style_cfg = palette.get("style", {})
            style_map = palette.get("map", {})

            # Applicera via ttk.Style istället för entry.configure()
            if style_cfg:
                self._set_style("TEntry", **style_cfg)
            if style_map:
                self._set_map("TEntry", **style_map)

        # =====================================================
        # Footer
        # =====================================================
        footer = theme_palette.get("footer")

        if footer and hasattr(self.app, "footer_label"):
            style = footer.get("style", {})

            self.app.footer_label.configure(
                background=style.get("background"),
                foreground=style.get("foreground"),
                font=style.get("font")
            )

            if "bold_font" in style:
                self.app.footer_label.tag_config("bold", font=style["bold_font"])

        # =====================================================
        # Comboboxes
        # =====================================================
        combo_palette = theme_palette.get("combobox", {})
        for combo in self.comboboxes:
            if not combo.winfo_exists():
                continue
            if combo_palette:
                self._set_style(
                    "TCombobox",
                    fieldbackground=combo_palette.get("fieldbackground"),
                    background=combo_palette.get("background"),
                    foreground=combo_palette.get("foreground"),
                    arrowcolor=combo_palette.get("arrowcolor"),
                    insertcolor=combo_palette.get("insertcolor"),
                    bordercolor=combo_palette.get("bordercolor"),
                    borderwidth=combo_palette.get("borderwidth"),
                    lightcolor=combo_palette.get("lightcolor"),
                    darkcolor=combo_palette.get("darkcolor"),
                    relief=combo_palette.get("relief")
                )
                # Listbox inside combobox
                listbox = combo_palette.get("listbox", {})
                if listbox:
                    self.root.option_add("*TCombobox*Listbox.background", listbox.get("background"))
                    self.root.option_add("*TCombobox*Listbox.foreground", listbox.get("foreground"))
                    self.root.option_add("*TCombobox*Listbox.selectBackground", listbox.get("selectbackground"))
                    self.root.option_add("*TCombobox*Listbox.selectForeground", listbox.get("selectforeground"))
        
        # =====================================================
        # Listboxes
        # =====================================================
        listbox_palette = theme_palette.get("listbox", {})
        for lb in self.listboxes:
            if not lb.winfo_exists():
                continue
            if listbox_palette:
                lb.configure(
                    bg=listbox_palette.get("background"),
                    fg=listbox_palette.get("foreground"),
                    selectbackground=listbox_palette.get("selectbackground"),
                    selectforeground=listbox_palette.get("selectforeground")
                )

        # =====================================================
        # Menus
        # =====================================================
        menu_palette = theme_palette.get("menu", {})
        for menu in self.menus:
            if not menu.winfo_exists():
                continue
            if menu_palette:
                valid_keys = menu.configure().keys()
                apply_dict = {k: v for k, v in menu_palette.items() if k in valid_keys and v is not None}
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
        """
        Define dark theme palette only. Do not modify widgets directly.
        """
        # =====================================================
        # Base colors
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

        separator_color = "#454545"
        menu_active_fg = "#efefef"
        select_bg = "#454545"

        # Hover text snapshot
        self.hover_text["dark"]["bg"] = bg_main
        self.hover_text["dark"]["fg"] = fg_main

        # =====================================================
        # Text widget
        # =====================================================
        default_font_size = tkfont.Font(font=self.palette["default"]["text"].get("font")).cget("size")
        font_text_obj = tkfont.Font(family="TkFixedFont", size=10, weight="normal", slant="roman")

        self.palette["dark"]["text"] = {
            "background": bg_output,
            "foreground": fg_main,
            "insertbackground": fg_main,
            "selectbackground": select_bg,
            "selectforeground": fg_main,
            "highlightthickness": outline_thickness,
            "highlightbackground": outline_inactive,
            "highlightcolor": outline_active,
            "font": font_text_obj
        }

        # =====================================================
        # Entry
        # =====================================================
        font_input_obj = tkfont.Font(family="TkFixedFont", size=9, weight="normal", slant="roman")

        self.palette["dark"]["entry"] = {
            "style": {
                "fieldbackground": bg_input,
                "foreground": fg_main,
                "insertcolor": fg_main,
                "bordercolor": input_border_color,
                "lightcolor": input_border_color,
                "darkcolor": input_border_color,
                "relief": "sunken",
                "focuscolor": input_border_color,
                "borderwidth": 1,
                "padding": 1,
                "font": font_input_obj
            },
            "map": {
                "bordercolor": [
                    ("focus", input_border_color_focus),
                    ("!focus", input_border_color)
                ]
            }
        }

        # =====================================================
        # Menu
        # =====================================================
        self.palette["dark"]["menu"] = {
            "background": bg_surface,
            "foreground": fg_main,
            "activebackground": accent_hover,
            "activeforeground": menu_active_fg
        }
        
        # =====================================================
        # Menubutton
        # =====================================================
        self.palette["dark"]["menubutton"] = {
            "style": {
                "background": bg_surface,
                "foreground": fg_main,
                "borderwidth": 0,
                "relief": "flat",
                "arrowcolor": fg_secondary
            },
            "map": {
                "background": [
                    ("active", accent_hover)
                ]
            }
        }

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
        # Footer
        # =====================================================
        font_footer = tkfont.Font(family="TkCaptionFont", size=9, weight="normal", slant="roman")
        font_footer_bold = tkfont.Font(family="TkCaptionFont", size=9, weight="bold", slant="roman")

        self.palette["dark"]["footer"] = {
            "style": {
                "background": bg_main,
                "foreground": fg_secondary,
                "font": font_footer,
                "bold_font": font_footer_bold,
                "anchor": "w"
            }
        }

        # =====================================================
        # Frame
        # =====================================================
        self.palette["dark"]["frame"] = {
            "style": {
                "background": bg_main
            }
        }
        
        # =====================================================
        # Button
        # =====================================================
        self.palette["dark"]["button"] = {
            "style": {
                "background": bg_surface,
                "foreground": fg_main,
                "borderwidth": 0,
                "relief": "flat",
                "lightcolor": light_color,
                "darkcolor": dark_color
            },
            "map": {
                "background": [
                    ("active", accent_hover)
                ]
            }
        }
        
        # =====================================================
        # Label
        # =====================================================
        self.palette["dark"]["label"] = {
            "style": {
                "background": bg_main,
                "foreground": fg_main
            }
        }
        
        # =====================================================
        # Scrollbar
        # =====================================================
        self.palette["dark"]["scrollbar"] = {
            "style": {
                "background": bg_surface,
                "troughcolor": bg_output,
                "arrowcolor": fg_secondary,
                "bordercolor": input_border_color,
                "lightcolor": light_color,
                "darkcolor": dark_color
            },
            "map": {
                "background": [
                    ("active", accent_hover),
                    ("pressed", accent_active)
                ]
            }
        }
        
        # =====================================================
        # Toolbar divider
        # =====================================================
        
        self.palette["dark"]["divider"] = {
            "style": {
                "background": separator_color,
                "width": 1
            }
        }
        


    # -------------------------------------------------

    def _define_light(self):
        """
        Define light theme palette only. Do not modify widgets directly.
        """
        # =====================================================
        # Base colors
        # =====================================================
        bg_main = "#d5d5d5"
        bg_surface = "#b6b6b6"
        bg_input = "#ffffff"
        bg_output = "#ffffff"

        fg_main = "#000000"
        fg_secondary = "#1f1f1f"
        fg_list = "#1f1f1f"

        outline_inactive = "#a0a0a0"
        outline_active = "#606060"
        outline_thickness = 1
        borderwidth = 1

        input_border_color = "#b6b6b6"
        input_border_color_focus = "#b6b6b6"

        accent_active = "#a6a6a6"
        accent_hover = "#a6a6a6"

        light_color = "#e8e8e8"
        dark_color = "#404040"

        separator_color = "#808080"
        menu_active_fg = "#000000"
        select_bg = "#a6a6a6"

        # Hover text snapshot
        self.hover_text["light"]["bg"] = bg_main
        self.hover_text["light"]["fg"] = fg_main

        # =====================================================
        # Text widget
        # =====================================================
        default_font_size = tkfont.Font(font=self.palette["default"]["text"].get("font")).cget("size")
        font_text_obj = tkfont.Font(family="TkFixedFont", size=10, weight="normal", slant="roman")

        self.palette["light"]["text"] = {
            "background": bg_output,
            "foreground": fg_main,
            "insertbackground": fg_main,
            "selectbackground": select_bg,
            "selectforeground": fg_main,
            "highlightthickness": outline_thickness,
            "highlightbackground": outline_inactive,
            "highlightcolor": outline_active,
            "font": font_text_obj
        }

        # =====================================================
        # Entry
        # =====================================================
        font_input_obj = tkfont.Font(family="TkFixedFont", size=9, weight="normal", slant="roman")

        self.palette["light"]["entry"] = {
            "style": {
                "fieldbackground": bg_input,
                "foreground": fg_main,
                "insertcolor": fg_main,
                "bordercolor": input_border_color,
                "lightcolor": input_border_color,
                "darkcolor": input_border_color,
                "relief": "sunken",
                "focuscolor": input_border_color,
                "borderwidth": 1,
                "padding": 1,
                "font": font_input_obj
            },
            "map": {
                "bordercolor": [
                    ("focus", input_border_color_focus),
                    ("!focus", input_border_color)
                ]
            }
        }

        # =====================================================
        # Menu
        # =====================================================
        self.palette["light"]["menu"] = {
            "background": bg_surface,
            "foreground": fg_main,
            "activebackground": accent_hover,
            "activeforeground": menu_active_fg
        }
        
        # =====================================================
        # Menubutton
        # =====================================================
        self.palette["light"]["menubutton"] = {
            "style": {
                "background": bg_surface,
                "foreground": fg_main,
                "borderwidth": 0,
                "relief": "flat",
                "arrowcolor": fg_secondary
            },
            "map": {
                "background": [
                    ("active", accent_hover)
                ]
            }
        }

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
        # Footer
        # =====================================================
        font_footer = tkfont.Font(family="TkCaptionFont", size=9, weight="normal", slant="roman")
        font_footer_bold = tkfont.Font(family="TkCaptionFont", size=9, weight="bold", slant="roman")

        self.palette["light"]["footer"] = {
            "style": {
                "background": bg_main,
                "foreground": fg_secondary,
                "font": font_footer,
                "bold_font": font_footer_bold,
                "anchor": "w"
            }
        }

        # =====================================================
        # Frame
        # =====================================================
        self.palette["light"]["frame"] = {
            "style": {
                "background": bg_main
            }
        }
        
        # =====================================================
        # Button
        # =====================================================
        self.palette["light"]["button"] = {
            "style": {
                "background": bg_surface,
                "foreground": fg_main,
                "borderwidth": 0,
                "relief": "flat",
                "lightcolor": light_color,
                "darkcolor": dark_color
            },
            "map": {
                "background": [
                    ("active", accent_hover)
                ]
            }
        }
        
        # =====================================================
        # Label
        # =====================================================
        self.palette["light"]["label"] = {
            "style": {
                "background": bg_main,
                "foreground": fg_main
            }
        }
        
        # =====================================================
        # Scrollbar
        # =====================================================
        self.palette["light"]["scrollbar"] = {
            "style": {
                "background": bg_surface,
                "troughcolor": bg_output,
                "arrowcolor": fg_secondary,
                "bordercolor": input_border_color,
                "lightcolor": light_color,
                "darkcolor": dark_color
            },
            "map": {
                "background": [
                    ("active", accent_hover),
                    ("pressed", accent_active)
                ]
            }
        }
        
        # =====================================================
        # Toolbar divider
        # =====================================================
        
        self.palette["light"]["divider"] = {
            "style": {
                "background": separator_color,
                "width": 1
            }
        }


