import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
from src.utils.tools import str_to_hex, generate_highlight_colors, is_using_dark_theme


class ThemeManager:
    def __init__(self, app):
        self.app = app
        self.root = app.root

        self.current_theme = "default"

        self.style = ttk.Style(self.root)
        
        self.menus: list[tk.Menu] = []
        self.menubuttons: list[ttk.Menubutton] = []
        self.text_widgets: list[tk.Text] = []
        self.inputs: list[ttk.Entry] = []
        self.comboboxes: list[ttk.Combobox] = []
        self.listboxes: list[tk.Listbox] = []
        self.labels: list[ttk.Label] = []
        self.frames: list[ttk.Frame] = []
        self.buttons: list[ttk.Button] = []

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

        self.fonts = {}
        
        self.font_size = 10
        self.font_size_output = self.font_size
        self.font_size_input = self.font_size
        self.font_size_detail = self.font_size - 1
        self.font_size_footer_label = self.font_size - 1
        self.font_size_other = self.font_size - 1


    def clear_registries(self):
        self.menus.clear()
        self.menubuttons.clear()
        self.text_widgets.clear()
        self.inputs.clear()
        self.comboboxes.clear()
        self.listboxes.clear()
        self.labels.clear()
        self.frames.clear()
        self.buttons.clear()
        
        self.root.option_clear()

    # -------------------------------------------------

    def apply(self, theme_name: str = "default"):
        
        if self.app.active_flashes: # extra safety to prevent bugged colors
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
        self.set_fonts()

        # Update tag colors based on the new theme
        if hasattr(self.app, "tag_manager"):
            self.app.tag_manager.update_tags()

        self.root.update_idletasks()

    # -------------------------------------------------

    def get_tag_colors(self) -> dict[str, str]:
        fallback = {
            "dark_theme": {
                "success": "#00F000",
                "error": "#F80000",
                "warning": "#F0A000",
                "info": "#00A0F0"
            },
            "light_theme": {
                "success": "#007000",
                "error": "#770000",
                "warning": "#C05000",
                "info": "#000070"
            }
        }

        theme_palette = self.palette.get(self.current_theme, {})
        tag_colors = theme_palette.get("tag_colors", {})

        if not tag_colors:
            if is_using_dark_theme(self.palette[self.current_theme].get("text", {}).get("background", "#FFFFFF")):
                return fallback["dark_theme"]
            else:
                return fallback["light_theme"]

        return tag_colors

    # -------------------------------------------------

    def propagate_theme(self):
        """
        Apply the current theme palette to all registered widgets and styles.
        """
        # Buttons (width only, rest set via style)
        longest_button_text = max(len(b.cget("text")) for b in self.buttons)
        for button in self.buttons:
            button.configure(width=longest_button_text)
        
        # Early return if default theme
        if self.current_theme == "default":
            return
            
        theme_palette = self.palette.get(self.current_theme)
        if not theme_palette:
            return

        # =====================================================
        # General widget styles (TFrame, TLabel, TButton, TMenubutton, TScrollbar)
        # =====================================================
        p = self.palette.get(self.current_theme, {})
        self.style.layout("ToolbuttonCheck.TCheckbutton", self.style.layout("Toolbutton"))
        for widget_name, ttk_name in [
            ("frame", "TFrame"),
            ("label", "TLabel"),
            ("button", "TButton"),
            ("menubutton", "TMenubutton"),
            ("entry", "TEntry"),
            ("scrollbar", "TScrollbar"),
            ("divider", "ToolbarDivider.TFrame"),
            ("spinbox", "TSpinbox"),
            ("checkbutton", "ToolbuttonCheck.TCheckbutton"),
        ]:
            cfg = p.get(widget_name, {})
            style = cfg.get("style")
            state_map = cfg.get("map")

            if style:
                self._set_style(ttk_name, **style)
            if state_map:
                self._set_map(ttk_name, **state_map)
                
        # =====================================================
        # Entry (font only, rest already set via style)
        # =====================================================
        entry_cfg = p.get("entry", {})
        font_obj = entry_cfg.get("font")
        if font_obj:
            for entry in self.inputs:
                entry.configure(font=font_obj)
        
        
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
        # Footer
        # =====================================================
        footer = theme_palette.get("footer", {})
        if footer and hasattr(self.app, "footer_label"):
            widget = self.app.footer_label
            valid_keys = widget.configure().keys()
            apply_dict = {k: v for k, v in footer.items() if k in valid_keys and v is not None}
            if apply_dict:
                widget.configure(**apply_dict)


        # =====================================================
        # Comboboxes
        # =====================================================
        combo_palette = theme_palette.get("combobox", {})
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
                relief=combo_palette.get("relief"),
                selectbackground=combo_palette.get("selectbackground"),
                selectforeground=combo_palette.get("selectforeground")
            )
            self._set_map(
                "TCombobox",
                background=[("active", combo_palette.get("background_active"))],
                bordercolor=[("focus", combo_palette.get("bordercolor_focus"))],
                lightcolor=[("focus", combo_palette.get("lightcolor_focus"))],
                darkcolor=[("focus", combo_palette.get("darkcolor_focus"))]
            )
            self._set_map(
                "TCombobox",
                fieldbackground=[("readonly", combo_palette.get("fieldbackground"))],
                background=[("readonly", combo_palette.get("background"))],
                foreground=[("readonly", combo_palette.get("foreground"))],
                arrowcolor=[("readonly", combo_palette.get("arrowcolor"))]
            )
                
            # Listbox inside combobox
            listbox = combo_palette.get("listbox", {})
            if listbox:
                self.root.option_add("*TCombobox*Listbox.background", listbox.get("background"))
                self.root.option_add("*TCombobox*Listbox.foreground", listbox.get("foreground"))
                self.root.option_add("*TCombobox*Listbox.selectBackground", listbox.get("selectbackground"))
                self.root.option_add("*TCombobox*Listbox.selectForeground", listbox.get("selectforeground"))
                self.root.option_add("*TCombobox*Listbox.relief", "flat")
        
        # =====================================================
        # Listboxes
        # =====================================================
        listbox_palette = theme_palette.get("listbox", {})
        if not listbox_palette:
            # Fall back to combobox's listbox palette if configured
            listbox_palette = theme_palette.get("combobox", {}).get("listbox", {})

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


    def set_base_colors(self, background: str, foreground: str):
        """Update base widget colors (bg/fg) for the current theme."""
        tpl = self.palette.setdefault(self.current_theme, {})

        # Text widgets
        text_palette = tpl.setdefault("text", {})
        text_palette.update({
            "background": background,
            "foreground": foreground,
            "insertbackground": foreground,
            "selectforeground": foreground,
        })

        # Entry widgets
        entry_style = tpl.setdefault("entry", {}).setdefault("style", {})
        entry_style.update({
            "fieldbackground": background,
            "foreground": foreground,
            "insertcolor": foreground,
        })

        # Combobox widgets
        combo_palette = tpl.setdefault("combobox", {})
        combo_palette.update({
            "fieldbackground": background,
            "background": background,
            "foreground": foreground,
            "insertcolor": foreground,
            "selectforeground": foreground,
        })

        # Listbox inside combobox
        listbox_palette = combo_palette.setdefault("listbox", {})
        listbox_palette.update({
            "background": background,
            "foreground": foreground,
            "selectforeground": foreground,
        })

        # Hover highlight colors
        h_bg, h_fg = generate_highlight_colors(fg=foreground, bg=background)
        self.hover_text[self.current_theme]["bg"] = h_bg
        self.hover_text[self.current_theme]["fg"] = h_fg

        self.propagate_theme()


    def set_fonts(self):
        """
        Apply fonts for the current theme to all registered widgets.
        """

        fonts = self.fonts.get(self.current_theme, {})
        if not fonts:
            return

        # -------------------------------------------------
        # Update font sizes
        # -------------------------------------------------
        if "log" in fonts:
            fonts["log"].configure(size=self.font_size_output)
        
        if "text" in fonts:
            fonts["text"].configure(size=self.font_size_output)

        if "entry" in fonts:
            fonts["entry"].configure(size=self.font_size_input)

        if "footer" in fonts:
            fonts["footer"].configure(size=self.font_size_footer_label)

        for k in ("menu", "menubutton", "combobox", "button", "label"):
            if k in fonts:
                fonts[k].configure(size=self.font_size_other)

        # -------------------------------------------------
        # Text widgets
        # -------------------------------------------------
        font = fonts.get("text")
        if font:
            for w in self.text_widgets:
                if w.winfo_exists():
                    w.configure(font=font)

        # -------------------------------------------------
        # Entry widgets
        # -------------------------------------------------
        font = fonts.get("entry")
        if font:
            for w in self.inputs:
                if w.winfo_exists():
                    w.configure(font=font)

        # -------------------------------------------------
        # Menus
        # -------------------------------------------------
        font = fonts.get("menu")
        if font:
            for m in self.menus:
                if m.winfo_exists():
                    m.configure(font=font)

        # -------------------------------------------------
        # Listboxes
        # -------------------------------------------------
        font = fonts.get("text")
        if font:
            for lb in self.listboxes:
                if lb.winfo_exists():
                    lb.configure(font=font)

        # -------------------------------------------------
        # ttk styles
        # -------------------------------------------------
        if "button" in fonts:
            self.style.configure("TButton", font=fonts["button"])

        if "label" in fonts:
            self.style.configure("TLabel", font=fonts["label"])

        if "menubutton" in fonts:
            self.style.configure("TMenubutton", font=fonts["menubutton"])

        if "combobox" in fonts:
            self.style.configure("TCombobox", font=fonts["combobox"])

        # -------------------------------------------------
        # Footer label
        # -------------------------------------------------
        font = fonts.get("footer")
        if font and hasattr(self.app, "footer_label"):
            self.app.footer_label.configure(font=font)

        # -------------------------------------------------
        # Detail widget special case
        # -------------------------------------------------
        if "text" in fonts and hasattr(self.app, "detail"):
            detail_font = fonts["text"].copy()
            self.app.detail.configure(font=detail_font)
            detail_font.configure(size=self.font_size_detail)
            
        
        # -------------------------------------------------
        # Bold copies for specific widgets
        # -------------------------------------------------
        theme_fonts = self.fonts.setdefault(self.current_theme, {})
        text_font = theme_fonts.setdefault("text", tkfont.Font())
        footer_font = theme_fonts.setdefault("footer", tkfont.Font())

        for widget_name in ["output", "detail"]:
            widget = getattr(self.app, widget_name, None)
            if widget and isinstance(widget, tk.Text):
                bold_font = text_font.copy()
                bold_font.configure(weight="bold")
                theme_fonts[f"{widget_name}_bold"] = bold_font
                widget.tag_configure("bold", font=bold_font)

        footer_widget = getattr(self.app, "footer_label", None)
        if footer_widget and isinstance(footer_widget, tk.Text):
            bold_font = footer_font.copy()
            bold_font.configure(weight="bold", size=self.font_size_footer_label)
            theme_fonts["footer_bold"] = bold_font
            footer_widget.tag_configure("bold", font=bold_font)
            
        # -------------------------------------------------
        # Log font
        # -------------------------------------------------
        log_font = theme_fonts.setdefault("log", tkfont.Font())
        
        widget = getattr(self.app, "output", None)
        if widget and isinstance(widget, tk.Text):
            theme_fonts["log_font"] = log_font
            widget.tag_configure("log", font=log_font)
        
    
    # -------------------------------------------------
    
    def _set_style(self, widget_style: str, **kwargs):
        self.style.configure(widget_style, **kwargs)

    def _set_map(self, widget_style: str, **kwargs):
        self.style.map(widget_style, **kwargs)

    # -------------------------------------------------
    # Themes
    # -------------------------------------------------

    def _define_default(self):
        bg = self.text_widgets[0].cget("background") if self.text_widgets else "#FFFFFF"
        fg = self.text_widgets[0].cget("foreground") if self.text_widgets else "#000000"

        self.palette.setdefault("default", {}).setdefault("text", {}).update({
            "background": bg,
            "foreground": fg,
        })

        self.palette["default"]["tag_colors"] = {
            "success": "#007000",
            "error": "#770000",
            "warning": "#C05000",
            "info": "#000070"
        }


        font_log_obj = tkfont.nametofont("TkFixedFont").copy()
        font_text_obj = tkfont.nametofont("TkTextFont").copy()
        font_input_obj = tkfont.nametofont("TkFixedFont").copy()
        font_menu_obj = tkfont.nametofont("TkMenuFont").copy()
        font_menubutton_obj = tkfont.nametofont("TkDefaultFont").copy()
        font_combobox_obj = tkfont.nametofont("TkDefaultFont").copy()
        font_footer_obj = tkfont.nametofont("TkFixedFont").copy()
        font_button_obj = tkfont.nametofont("TkDefaultFont").copy()
        font_label_obj = tkfont.nametofont("TkDefaultFont").copy()
        

        self.fonts.setdefault("default", {}).update({
            "log": font_log_obj,
            "text": font_text_obj,
            "entry": font_input_obj,
            "menu": font_menu_obj,
            "menubutton": font_menubutton_obj,
            "combobox": font_combobox_obj,
            "footer": font_footer_obj,
            "button": font_button_obj,
            "label": font_label_obj,
        })
        
        if hasattr(self.app, "footer_label"):
            self.app.footer_label.configure(
                background=self.style.lookup("TFrame", "background")
            )
        
        if hasattr(self.app, "output"):
            h_bg, h_fg = generate_highlight_colors(
                bg=self.app.output.cget("background"),
                fg=self.app.output.cget("foreground")
            )
        
            self.hover_text["default"]["bg"] = h_bg
            self.hover_text["default"]["fg"] = h_fg

    # -------------------------------------------------

    def _define_dark(self):
        """
        Define dark theme palette only. Do not modify widgets directly.
        """
        # =====================================================
        # Base colors
        # =====================================================
        bg_main = "#3a3a3a"
        bg_surface = "#4c4c4c"
        bg_input = "#1c1c1c"
        bg_output = "#1c1c1c"

        fg_main = "#e6e6e6"
        fg_secondary = "#d0d0d0"

        outline_inactive = "#505050"
        outline_active = "#808080"
        outline_thickness = 1
        borderwidth = 1

        input_border_color = bg_surface
        input_border_color_focus = "#808080"

        accent_active = bg_main
        accent_hover = "#666666"

        lightcolor = bg_surface
        darkcolor = bg_surface
        lightcolor_focus = bg_surface
        darkcolor_focus = bg_surface

        separator_color = outline_active
        menu_active_fg = fg_main
        select_bg = "#505050"

        # Hover text
        self.hover_text["dark"]["bg"] = "#303030"
        self.hover_text["dark"]["fg"] = fg_main
        
        self.palette["dark"]["tag_colors"] = {
            "success": "#00F000",
            "error": "#F80000",
            "warning": "#F0A000",
            "info": "#00A0F0"
        }

        # =====================================================
        # Text widget
        # =====================================================
        
        self.palette["dark"]["text"] = {
            "background": bg_output,
            "foreground": fg_main,
            "insertbackground": fg_main,
            "selectbackground": select_bg,
            "selectforeground": fg_main,
            "highlightthickness": outline_thickness,
            "highlightbackground": outline_inactive,
            "highlightcolor": outline_active,
        }

        # =====================================================
        # Entry
        # =====================================================
        
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
                "focuscolor": input_border_color_focus,
                "selectbackground": select_bg,
                "selectforeground": fg_main
            },
            "map": {
                "bordercolor": [
                    ("focus", input_border_color_focus),
                    ("!focus", input_border_color)
                ],
                "lightcolor": [
                    ("!focus", input_border_color),
                    ("focus", input_border_color_focus)
                ],
                "darkcolor": [
                    ("!focus", input_border_color),
                    ("focus", input_border_color_focus)
                ]
            }
        }

        # =====================================================
        # Menu
        # =====================================================
        
        self.palette["dark"]["menu"] = {
            "background": bg_surface,
            "foreground": fg_secondary,
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
            "bordercolor": input_border_color,
            "borderwidth": borderwidth,
            "bordercolor_focus": input_border_color_focus,
            "lightcolor": lightcolor,
            "lightcolor_focus": lightcolor_focus,
            "darkcolor": darkcolor,
            "darkcolor_focus": darkcolor_focus,
            "relief": "solid",
            "selectbackground": select_bg,
            "selectforeground": fg_main,
            "listbox": {
                "background": bg_input,
                "foreground": fg_secondary,
                "selectbackground": accent_active,
                "selectforeground": fg_main
            }
        }

        # =====================================================
        # Footer
        # =====================================================
        
        self.palette["dark"]["footer"] = {
            "background": bg_main,
            "foreground": fg_secondary,
            "borderwidth": 0,
            "relief": "flat",
            "highlightthickness": 0,
            "highlightbackground": fg_secondary,
            "highlightcolor": bg_main
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
                "lightcolor": lightcolor,
                "darkcolor": darkcolor
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
                "lightcolor": lightcolor,
                "darkcolor": darkcolor
            },
            "map": {
                "background": [
                    ("active", accent_hover),
                    ("pressed", accent_active)
                ]
            }
        }

        # =====================================================
        # Spinbox
        # =====================================================
        self.palette["dark"]["spinbox"] = {
            "style": {
                "fieldbackground": bg_input,
                "background": bg_input,
                "foreground": fg_main,
                "insertcolor": fg_main,
                "arrowcolor": fg_secondary,
                "arrowsize": 11,
                "arrowbackground": bg_input,
                "bordercolor": input_border_color,
                "lightcolor": lightcolor,
                "darkcolor": darkcolor,
                "focuscolor": input_border_color_focus,
                "borderwidth": 2,
                "padding": 2,
                "relief": "flat",
                "selectbackground": select_bg,
                "selectforeground": fg_main
            },
            "map": {
                "bordercolor": [
                    ("focus", input_border_color_focus),
                    ("!focus", input_border_color)
                ],
                "lightcolor": [
                    ("focus", input_border_color_focus),
                    ("!focus", input_border_color)
                ],
                "darkcolor": [
                    ("focus", input_border_color_focus),
                    ("!focus", input_border_color)
                ],
                "arrowcolor": [
                    ("disabled", "#707070"),
                    ("!disabled", fg_main)
                ]
            }
        }

        self.palette["dark"]["checkbutton"] = {
            "style": {
                "background": bg_main,
                "foreground": fg_main,
                "borderwidth": 1,
                "relief": "flat",
                "lightcolor": lightcolor,
                "darkcolor": darkcolor,
                "padding": 2,
                "bordercolor": outline_inactive,
            },
            "map": {
                "background": [
                    ("active", accent_hover),
                    ("!active", bg_surface)
                ],
                "relief": [
                    ("selected", "solid"),
                    ("!selected", "flat")
                ],
                "bordercolor": [
                    ("selected", outline_active),
                    ("!selected", outline_inactive)
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
        
        # =====================================================
        # Fonts
        # =====================================================
        
        font_log_obj = tkfont.nametofont("TkFixedFont").copy()
        font_log_obj.configure(weight="normal", slant="roman")
        font_text_obj = tkfont.nametofont("TkTextFont").copy()
        font_text_obj.configure(weight="normal", slant="roman")
        font_input_obj = tkfont.nametofont("TkFixedFont").copy()
        font_input_obj.configure(weight="normal", slant="roman")
        font_menu_obj = tkfont.nametofont("TkMenuFont").copy()
        font_menu_obj.configure(weight="normal", slant="roman")
        font_menubutton_obj = tkfont.nametofont("TkDefaultFont").copy()
        font_menubutton_obj.configure(weight="normal", slant="roman")
        font_combobox_obj = tkfont.nametofont("TkDefaultFont").copy()
        font_combobox_obj.configure(weight="normal", slant="roman")
        font_footer_obj = tkfont.nametofont("TkFixedFont").copy()
        font_footer_obj.configure(weight="normal", slant="roman")
        font_button_obj = tkfont.nametofont("TkDefaultFont").copy()
        font_button_obj.configure(weight="normal", slant="roman")
        font_label_obj = tkfont.nametofont("TkDefaultFont").copy()
        font_label_obj.configure(weight="normal", slant="roman")

        self.fonts.setdefault("dark", {}).update({
            "log": font_log_obj,
            "text": font_text_obj,
            "entry": font_input_obj,
            "menu": font_menu_obj,
            "menubutton": font_menubutton_obj,
            "combobox": font_combobox_obj,
            "footer": font_footer_obj,
            "button": font_button_obj,
            "label": font_label_obj,
        })


    # -------------------------------------------------

    def _define_light(self):
        """
        Define light theme palette only. Do not modify widgets directly.
        """
        # =====================================================
        # Base colors
        # =====================================================
        bg_main = "#c5c5c5"
        bg_surface = "#b3b3b3"
        bg_input = "#f0f0f0"
        bg_output = "#f0f0f0"

        fg_main = "#000000"
        fg_secondary = "#202020"

        outline_inactive = "#b0b0b0"
        outline_active = "#7f7f7f"
        outline_thickness = 1
        borderwidth = 1

        input_border_color = bg_surface
        input_border_color_focus = "#7f7f7f"

        accent_active = bg_main
        accent_hover = "#999999"

        lightcolor = bg_surface
        darkcolor = bg_surface
        lightcolor_focus = bg_surface
        darkcolor_focus = bg_surface

        separator_color = outline_active
        menu_active_fg = fg_main
        select_bg = "#b0b0b0"

        # Hover text
        self.hover_text["light"]["bg"] = "#d0d0d0"
        self.hover_text["light"]["fg"] = fg_main


        self.palette["light"]["tag_colors"] = {
            "success": "#007000",
            "error": "#770000",
            "warning": "#C05000",
            "info": "#000070"
        }

        # =====================================================
        # Text widget
        # =====================================================
        self.palette["light"]["text"] = {
            "background": bg_output,
            "foreground": fg_main,
            "insertbackground": fg_main,
            "selectbackground": select_bg,
            "selectforeground": fg_main,
            "highlightthickness": outline_thickness,
            "highlightbackground": outline_inactive,
            "highlightcolor": outline_active,
        }

        # =====================================================
        # Entry
        # =====================================================
        self.palette["light"]["entry"] = {
            "style": {
                "fieldbackground": bg_input,
                "foreground": fg_main,
                "insertcolor": fg_main,
                "bordercolor": input_border_color,
                "lightcolor": input_border_color,
                "darkcolor": input_border_color,
                "relief": "sunken",
                "focuscolor": input_border_color_focus,
                "borderwidth": 1,
                "padding": 1,
                "selectbackground": select_bg,
                "selectforeground": fg_main
            },
            "map": {
                "bordercolor": [
                    ("focus", input_border_color_focus),
                    ("!focus", input_border_color)
                ],
                "lightcolor": [
                    ("!focus", input_border_color),
                    ("focus", input_border_color_focus)
                ],
                "darkcolor": [
                    ("!focus", input_border_color),
                    ("focus", input_border_color_focus)
                ]
            }
        }

        # =====================================================
        # Menu
        # =====================================================
        self.palette["light"]["menu"] = {
            "background": bg_surface,
            "foreground": fg_secondary,
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
            "bordercolor": input_border_color,
            "borderwidth": borderwidth,
            "bordercolor_focus": input_border_color_focus,
            "lightcolor": lightcolor,
            "lightcolor_focus": lightcolor_focus,
            "darkcolor": darkcolor,
            "darkcolor_focus": darkcolor_focus,
            "relief": "solid",
            "selectbackground": select_bg,
            "selectforeground": fg_main,
            "listbox": {
                "background": bg_input,
                "foreground": fg_secondary,
                "selectbackground": accent_active,
                "selectforeground": fg_main
            }
        }

        # =====================================================
        # Footer
        # =====================================================
        self.palette["light"]["footer"] = {
            "background": bg_main,
            "foreground": fg_secondary,
            "borderwidth": 0,
            "relief": "flat",
            "highlightthickness": 0,
            "highlightbackground": fg_secondary,
            "highlightcolor": bg_main
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
                "lightcolor": lightcolor,
                "darkcolor": darkcolor
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
                "lightcolor": lightcolor,
                "darkcolor": darkcolor
            },
            "map": {
                "background": [
                    ("active", accent_hover),
                    ("pressed", accent_active)
                ]
            }
        }

        self.palette["light"]["spinbox"] = {
            "style": {
                "fieldbackground": bg_input,
                "background": bg_input,
                "foreground": fg_main,
                "insertcolor": fg_main,
                "arrowcolor": fg_secondary,
                "arrowsize": 11,
                "arrowbackground": bg_input,
                "bordercolor": input_border_color,
                "lightcolor": lightcolor,
                "darkcolor": darkcolor,
                "focuscolor": input_border_color_focus,
                "borderwidth": 2,
                "padding": 2,
                "relief": "flat",
                "selectbackground": select_bg,
                "selectforeground": fg_main
            },
            "map": {
                "bordercolor": [
                    ("focus", input_border_color_focus),
                    ("!focus", input_border_color)
                ],
                "lightcolor": [
                    ("focus", input_border_color_focus),
                    ("!focus", input_border_color)
                ],
                "darkcolor": [
                    ("focus", input_border_color_focus),
                    ("!focus", input_border_color)
                ],
                "arrowcolor": [
                    ("disabled", "#707070"),
                    ("!disabled", fg_main)
                ]
            }
        }

        self.palette["light"]["checkbutton"] = {
            "style": {
                "background": bg_main,
                "foreground": fg_main,
                "borderwidth": 1,
                "relief": "flat",
                "lightcolor": lightcolor,
                "darkcolor": darkcolor,
                "padding": 2,
                "bordercolor": outline_inactive,
            },
            "map": {
                "background": [
                    ("active", accent_hover),
                    ("!active", bg_surface)
                ],
                "relief": [
                    ("selected", "solid"),
                    ("!selected", "flat")
                ],
                "bordercolor": [
                    ("selected", outline_active),
                    ("!selected", outline_inactive)
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
        
        # =====================================================
        # Fonts
        # =====================================================
        
        font_log_obj = tkfont.nametofont("TkFixedFont").copy()
        font_log_obj.configure(weight="normal", slant="roman")
        font_text_obj = tkfont.nametofont("TkTextFont").copy()
        font_text_obj.configure(weight="normal", slant="roman")
        font_input_obj = tkfont.nametofont("TkFixedFont").copy()
        font_input_obj.configure(weight="normal", slant="roman")
        font_menu_obj = tkfont.nametofont("TkMenuFont").copy()
        font_menu_obj.configure(weight="normal", slant="roman")
        font_menubutton_obj = tkfont.nametofont("TkDefaultFont").copy()
        font_menubutton_obj.configure(weight="normal", slant="roman")
        font_combobox_obj = tkfont.nametofont("TkDefaultFont").copy()
        font_combobox_obj.configure(weight="normal", slant="roman")
        font_footer_obj = tkfont.nametofont("TkFixedFont").copy()
        font_footer_obj.configure(weight="normal", slant="roman")
        font_button_obj = tkfont.nametofont("TkDefaultFont").copy()
        font_button_obj.configure(weight="normal", slant="roman")
        font_label_obj = tkfont.nametofont("TkDefaultFont").copy()
        font_label_obj.configure(weight="normal", slant="roman")

        self.fonts.setdefault("light", {}).update({
            "log": font_log_obj,
            "text": font_text_obj,
            "entry": font_input_obj,
            "menu": font_menu_obj,
            "menubutton": font_menubutton_obj,
            "combobox": font_combobox_obj,
            "footer": font_footer_obj,
            "button": font_button_obj,
            "label": font_label_obj,
        })


