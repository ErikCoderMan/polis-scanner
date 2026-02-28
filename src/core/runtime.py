from dataclasses import dataclass
from typing import Literal
import asyncio
import tkinter as tk

@dataclass(slots=True)
class RuntimeContext:
    mode: Literal["gui", "cli"] | None = None
    interactive: bool = False
    loop: asyncio.AbstractEventLoop | None = None
    root: tk.Tk | None = None
    app_cli: object | None = None
    app_gui: object | None = None 

    def is_gui(self) -> bool:
        return self.mode.lower() == "gui"

    def is_cli(self) -> bool:
        return self.mode.lower() == "cli"
