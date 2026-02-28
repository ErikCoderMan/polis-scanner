from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.runtime import RuntimeContext

import asyncio
from prompt_toolkit.key_binding import KeyBindings
from src.commands.commands import handle_command
from .ui import output_field, input_field

def build_keybindings(ctx: RuntimeContext = None):
    kb = KeyBindings()
    
    @kb.add("enter")
    def _(event):
        
        buffer = event.app.current_buffer

        text = buffer.text.strip()
        if not text:
            buffer.reset()
            return

        buffer.validate_and_handle()

        asyncio.create_task(handle_command(text=text, ctx=ctx))

    @kb.add("pageup")
    def _(event):
        event.app.layout.focus(output_field)
        event.app.current_buffer.cursor_up(count=20)
        event.app.layout.focus(input_field)


    @kb.add("pagedown")
    def _(event):
        event.app.layout.focus(output_field)
        event.app.current_buffer.cursor_down(count=20)
        event.app.layout.focus(input_field)

    @kb.add("c-c")
    def _(event):
        event.app.exit(result=130)
    
    return kb
