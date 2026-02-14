import asyncio
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.widgets import TextArea
from src.ui.log_buffer import log_buffer

# ----------------------------
# UI widgets
# ----------------------------
output_field = TextArea(
    text="",
    scrollbar=True,
    focusable=True,
    wrap_lines=False,
    read_only=True
)

input_field = TextArea(
    height=1,
    prompt="> ",
    multiline=False
)

# ----------------------------
# Layout
# ----------------------------
root_container = HSplit([
    output_field,
    Window(height=1, char="-"),
    input_field,
])

layout = Layout(root_container, focused_element=input_field)


# ----------------------------
# Log updater task
# ----------------------------
async def ui_updater():
    from .commands import state
    last_line = None
    while True:
        lines = log_buffer.lines
        new_text = "\n".join(lines)

        if lines and lines[-1] != last_line:
            buf = output_field.buffer
            at_bottom = buf.document.cursor_position == len(buf.document.text)
            if state.get("force_scroll", False):
                cursor_pos = len(new_text)
                state["force_scroll"] = False
            else:
                cursor_pos = len(new_text) if at_bottom else buf.document.cursor_position

            buf.set_document(
                buf.document.__class__(new_text, cursor_position=cursor_pos),
                bypass_readonly=True
            )
            last_line = lines[-1]

        await asyncio.sleep(0.1)
