
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

def is_using_dark_theme(color: str) -> bool:
    # Simple heuristic: if the color is dark, use light text; otherwise, use dark text
    hex_color = str_to_hex(color)
    r = (hex_color >> 16) & 0xFF
    g = (hex_color >> 8) & 0xFF
    b = hex_color & 0xFF
    # Calculate luminance (perceived brightness)
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    return luminance < 128  # True if color is dark

def generate_highlight_colors(fg: str, bg: str, adj: int = 0x20) -> tuple[str, str]:
    """Try to generate readable highlight colors based on theme fg/bg.

    This adjusts the background and foreground colors by shifting RGB channels
    independently, which avoids the artifacts caused by treating the full 0xRRGGBB
    value as a single integer.
    """

    def _hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
        h = hex_str.lstrip("#")
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

    def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
        return "#" + "".join(f"{c:02x}" for c in rgb)

    def _clamp(v: int) -> int:
        return max(0, min(255, v))

    def _adjust(rgb: tuple[int, int, int], delta: int, lighten: bool) -> tuple[int, int, int]:
        if lighten:
            return tuple(_clamp(c + delta) for c in rgb)
        else:
            return tuple(_clamp(c - delta) for c in rgb)

    # Parse colors
    bg_rgb = _hex_to_rgb(bg)
    fg_rgb = _hex_to_rgb(fg)

    # Determine whether background is dark or light (perceived luminance)
    bg_luminance = 0.299 * bg_rgb[0] + 0.587 * bg_rgb[1] + 0.114 * bg_rgb[2]
    bg_is_dark = bg_luminance < 128

    # Adjust background by shifting its RGB channels
    hover_bg_rgb = _adjust(bg_rgb, adj, lighten=bg_is_dark)

    # Make the foreground contrast with the new background
    hover_fg_rgb = _adjust(fg_rgb, adj, lighten=bg_is_dark)

    return _rgb_to_hex(hover_bg_rgb), _rgb_to_hex(hover_fg_rgb)
    
    
    
    
