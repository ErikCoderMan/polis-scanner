from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.runtime import RuntimeContext

import asyncio
import time
from datetime import datetime

from prompt_toolkit.layout import Layout, WindowAlign
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.document import Document
from prompt_toolkit.application import Application

from src.ui.log_buffer import log_buffer
from src.core.config import settings

from .keybindings import build_keybindings

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


class CLIApp:
    def __init__(self, ctx: RuntimeContext):
        ctx.ui = self
        self.ctx = ctx

        # Widgets
        self.output_field = TextArea(
            text="",
            scrollbar=True,
            focusable=True,
            wrap_lines=True,
            read_only=True,
            multiline=True
        )

        self.history = InMemoryHistory()

        self.input_field = TextArea(
            height=1,
            prompt="> ",
            multiline=False,
            history=self.history
        )

        # Title bar
        self.title_bar = TitleBar()
        self.title_bar_widget = Window(
            height=1,
            content=self.title_bar.control,
            style="reverse",
            align=WindowAlign.CENTER
        )

        self.title_separator = Window(height=1, char="-", style="class:line")

        self.layout = Layout(
            HSplit([
                self.title_bar_widget,
                self.title_separator,
                self.output_field,
                Window(height=1, char="-"),
                self.input_field,
            ]),
            focused_element=self.input_field
        )

        # UI state
        self.last_snapshot = ""
        
        # Application
        kb = build_keybindings(ctx.ui)
        self.app = Application(
            layout=self.layout,
            key_bindings=kb,
            mouse_support=True,
            full_screen=True
        )
    
    
    async def shutdown(self):
        self.app.exit()

    # --------------------------------------------------
    # UI Update Loop
    # --------------------------------------------------

    async def update_ui(self, title_sleep=0.5, main_sleep=0.5):
        last_snapshot = ""
        title_timer = time.monotonic()

        while True:
            snapshot = log_buffer.get_text()
            now = time.monotonic()

            # Title animation
            if now - title_timer >= title_sleep:
                self.title_bar.tick_siren()
                self.title_bar.update_lines(len(snapshot.splitlines()))
                title_timer = now

            if snapshot != last_snapshot:
                buf = self.output_field.buffer
                doc = buf.document

                at_bottom = doc.cursor_position >= max(len(doc.text) - 5, 0)

                if self.ctx.state.get("force_scroll", False) or at_bottom:
                    cursor = len(snapshot)
                    self.ctx.state["force_scroll"] = False
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

            self.app.invalidate()
            await asyncio.sleep(main_sleep)
