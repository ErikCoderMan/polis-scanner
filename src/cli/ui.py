import asyncio
import time
from datetime import datetime
from prompt_toolkit.layout import Layout, WindowAlign
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import TextArea

from src.ui.log_buffer import log_buffer
from src.core.config import settings

# ----------------------------
# UI widgets
# ----------------------------
output_field = TextArea(
    text="",
    scrollbar=True,
    focusable=True,
    wrap_lines=True,
    read_only=True
)

input_field = TextArea(
    height=1,
    prompt="> ",
    multiline=False
)

# ----------------------------
# Self-contained dynamic title bar
# ----------------------------
class TitleBar:
    def __init__(self):
        self.siren_patterns = ["*-*-*-", "-*-*-*"]
        self.siren_index = 0
        self.text = "00:00:00 | App Name (CLI) v0.0.0 | 0 lines"
        self.control = FormattedTextControl(self.get_text, focusable=False)

    def get_text(self):
        siren = self.siren_patterns[self.siren_index]
        return [("class:title", f"{siren} {self.text} {siren}")]

    def update_lines(self, num_lines):
        clock = datetime.now().strftime("%H:%M:%S")
        self.text = f"{clock} | {settings.app_name} (CLI) v{settings.version} | {num_lines} lines "

    def tick_siren(self):
        self.siren_index = (self.siren_index + 1) % len(self.siren_patterns)


# Instantiate the title bar and window
title_bar = TitleBar()
title_bar_widget = Window(height=1, content=title_bar.control, style="reverse", align=WindowAlign.CENTER)

# Separator under title
title_separator = Window(height=1, char="-", style="class:line")

# ----------------------------
# Layout
# ----------------------------
root_container = HSplit([
    title_bar_widget,  # dynamic title
    title_separator,
    output_field,      # scrollable output
    Window(height=1, char="-"),  # line between output and input
    input_field,       # input area
])

layout = Layout(root_container, focused_element=input_field)

# ----------------------------
# Log updater + title animation
# ----------------------------
async def ui_updater(app, state):
    """
    Updates the output_field with new logs and animates the title bar.
    Ensures mouse scrolling works freely while still auto-scrolling when needed.
    """
    last_line = None
    
    siren_interval = 0.5
    last_siren_tick = time.monotonic()

    while True:
        now = time.monotonic()
        lines = log_buffer.lines
        new_text = "\n".join(lines)

        buf = output_field.buffer

        # Determine if the cursor is already at the bottom
        lines_from_bottom = buf.document.line_count - buf.document.cursor_position_row - 1
        at_bottom = lines_from_bottom <= 2

        # Update output_field only if last line changed
        if lines and lines[-1] != last_line:
            # Decide cursor position: move to end only if force_scroll or already at bottom
            if state.get("force_scroll", False) or at_bottom:
                cursor_pos = len(new_text)
                state["force_scroll"] = False
                
            else:
                cursor_pos = buf.document.cursor_position  # preserve cursor for user scrolling

            # Update the buffer
            buf.set_document(
                buf.document.__class__(new_text, cursor_position=cursor_pos),
                bypass_readonly=True
            )

            last_line = lines[-1]

        # Update title bar animation and line count
        if now - last_siren_tick >= siren_interval:
            title_bar.tick_siren()
            last_siren_tick = now
            title_bar.update_lines(len(lines))

        # Force redraw of UI so title updates even without user input
        app.invalidate()

        await asyncio.sleep(0.2)

