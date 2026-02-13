from prompt_toolkit.key_binding import KeyBindings
from .ui import output_field, input_field
from .commands import handle_command

kb = KeyBindings()

@kb.add("enter")
def _(event):
    text = input_field.text
    input_field.buffer.reset()
    import asyncio
    asyncio.create_task(handle_command(text, event.app))

@kb.add("pageup")
def _(event):
    output_field.buffer.cursor_up(count=20)

@kb.add("pagedown")
def _(event):
    output_field.buffer.cursor_down(count=20)

@kb.add("c-c")
def _(event):
    event.app.exit(result=130)
