
# this is where the helper utils functions live

def flatten_dict(data, parent_key="", sep="."):
    """
    Utility functions for transforming and traversing nested data structures.
    Includes helpers for flattening deeply nested dictionaries
    into dot-notation key paths.
    """
    
    flat = {}

    if isinstance(data, dict):
        for key, value in data.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else str(key)
            flat.update(flatten_dict(value, new_key, sep))

    elif isinstance(data, list):
        for index, value in enumerate(data):
            new_key = f"{parent_key}{sep}{index}" if parent_key else str(index)
            flat.update(flatten_dict(value, new_key, sep))

    else:
        if parent_key:
            flat[parent_key] = data

    return flat

def str_to_hex(string: str) -> int:
    return int(string.lstrip("#"), 16)

def invert_color(color: str) -> str:
    return f"#{(int(color.lstrip('#'), 16) ^ 0xFFFFFF):06x}"

def generate_highlight_colors(fg: str, bg: str, adj: int = 0x121212, middle: int = 0x7fffff) -> tuple[str, str]:
    """
    Try to generate readable highlight colors based on theme fg/bg.
    Returns (highlight_bg, highlight_fg)
    """

    # Convert #RRGGBB -> int
    x_bg = str_to_hex(bg)
    x_fg = str_to_hex(fg)

    # Adjust background
    hover_bg = x_bg - adj if x_bg > middle else x_bg + adj

    # Adjust foreground
    if x_bg > middle:
        hover_fg = max(0x000000, x_fg - adj)
    else:
        hover_fg = min(0xFFFFFF, x_fg + adj)

    # Clamp values inside RGB range
    hover_bg = max(0x000000, min(0xFFFFFF, hover_bg))
    hover_fg = max(0x000000, min(0xFFFFFF, hover_fg))

    # Convert back to "#RRGGBB"
    hover_bg = f"#{hover_bg:06x}"
    hover_fg = f"#{hover_fg:06x}"

    return hover_bg, hover_fg
    
    
    
    
