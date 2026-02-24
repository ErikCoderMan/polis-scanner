import asyncio
import time
from datetime import datetime
from prompt_toolkit.layout import Layout, WindowAlign
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.application.current import get_app
from prompt_toolkit.document import Document

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
    read_only=True,
    multiline=True
)

history = InMemoryHistory()
input_field = TextArea(
    height=1,
    prompt="> ",
    multiline=False,
    history=history
)

# ----------------------------
# Self-contained dynamic title bar
# ----------------------------
class TitleBar:
    def __init__(self):
        self.siren_patterns = ["*-*-*-", "-*-*-*"]
        self.siren_index = 0
        self.text = "00:00:00 | app v0.0.0 (CLI) | 0 lines"
        self.control = FormattedTextControl(self.get_text, focusable=False)

    def get_text(self):
        siren = self.siren_patterns[self.siren_index]
        return [("class:title", f"{siren} {self.text} {siren}")]

    def update_lines(self, num_lines):
        clock = datetime.now().strftime("%H:%M:%S")
        self.text = f"{clock} | {settings.app_name} v{settings.version} (CLI) | {num_lines} lines "

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

async def ui_updater(app, state, title_sleep=0.5, main_sleep=0.5):
    last_snapshot = ""
    title_timer = time.monotonic()

    while True:
        snapshot = log_buffer.get_text()
        now = time.monotonic()
        
        # Title animation
        if now - title_timer >= title_sleep:
            title_bar.tick_siren()
            title_bar.update_lines(len(snapshot.splitlines()))
            title_timer = now
        
        if snapshot != last_snapshot:

            buf = output_field.buffer
            doc = buf.document

            # Tail follow only if user is already near bottom
            at_bottom = doc.cursor_position >= max(len(doc.text) - 5, 0)

            if state.get("force_scroll", False) or at_bottom:
                cursor = len(snapshot)
                state["force_scroll"] = False
            else:
                cursor = doc.cursor_position

            buf.set_document(
                Document(
                    snapshot,
                    cursor_position=min(cursor, len(snapshot))
                ),
                bypass_readonly=True
            )

            last_snapshot = snapshot
            
        app.invalidate()
        await asyncio.sleep(0.5)

