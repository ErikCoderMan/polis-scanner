from prompt_toolkit.key_binding import KeyBindings
from .ui import output_field, input_field
from src.commands.commands import handle_command


kb = KeyBindings()

@kb.add("enter")
def _(event):
    buffer = event.app.current_buffer

    text = buffer.text.strip()
    if not text:
        buffer.reset()
        return

    buffer.validate_and_handle()

    import asyncio
    asyncio.create_task(handle_command(text, event.app))

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
