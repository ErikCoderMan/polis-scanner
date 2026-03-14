import re
import tkinter as tk

class TagManager:
    def __init__(self, theme_manager):
        self.theme = theme_manager  # Reference to ThemeManager for theme-aware colors

        colors = self.theme.get_tag_colors()  # Get colors for tags based on current theme

        # Define color tags for different log types/patterns
        self.color_tags = {
            "success": {"foreground": colors.get("success", "green")},      # For [+] logs
            "error": {"foreground": colors.get("error", "red")},          # For [-] logs
            "warning": {"foreground": colors.get("warning", "orange")},     # For [!] logs
            "info": {"foreground": colors.get("info", "blue")},          # For [i] logs
            # Add more as needed, e.g., for custom patterns
        }

        # Register tags with the theme's text widgets (e.g., output, detail)
        self._configure_tags()

    def _configure_tags(self):
        """Configure color tags on relevant text widgets."""
        for widget_name in ["output", "detail"]:
            widget = getattr(self.theme.app, widget_name, None)
            if widget and isinstance(widget, tk.Text):
                for tag_name, config in self.color_tags.items():
                    widget.tag_configure(tag_name, **config)

    def update_tags(self):
        """Update tag configurations when the theme changes."""
        colors = self.theme.get_tag_colors()
        for tag_name, config in self.color_tags.items():
            if tag_name in colors:
                config["foreground"] = colors[tag_name]
        
        # Reconfigure tags on text widgets to apply new colors
        self._configure_tags()
        
    def apply_color_tags(self, widget: tk.Text, text: str, new_line_start: int):
        """
        Apply color tags to a text widget based on patterns in the text.
        This is called when inserting text (e.g., in print_output).
        """
        # Example: Tag log prefixes
        patterns = {
            r"^\[\+\]": "success",   # Matches [+] at start of line
            r"^\[\-\]": "error",     # Matches [-]
            r"^\[\!\]": "warning",   # Matches [!]
            r"^\[i\]": "info",       # Matches [i]
        }
        
        lines = text.splitlines()
        for line_num, line in enumerate(lines, start=new_line_start):
            for pattern, tag in patterns.items():
                match = re.match(pattern, line)
                if match:
                    # Tag the entire line or just the prefix—adjust as needed
                    start_idx = f"{line_num}.0"
                    end_idx = f"{line_num}.{len(match.group())}"
                    widget.tag_add(tag, start_idx, end_idx)
                    break  # Stop at first match per line
    
    def apply_detail_tags(self, widget: tk.Text, text: str):
        """
        Apply tags to the detail view based on content patterns.
        """
        bold_tags  = ["id", "datetime", "name", "summary", "url", "type", "location.name", "location.gps", "(all)"]
        
        patterns = {}

        for bt in bold_tags:
            if bt.startswith("(") and bt.endswith(")"):
                patterns[re.compile(re.escape(bt), re.IGNORECASE)] = "bold"
            else:
                patterns[re.compile(rf"\b{re.escape(bt)}\b", re.IGNORECASE)] = "bold"
        
        for pattern, tag in patterns.items():
            for match in pattern.finditer(text):
                start_idx = f"1.0 + {match.start()} chars"
                end_idx = f"1.0 + {match.end()} chars"
                widget.tag_add(tag, start_idx, end_idx)
        