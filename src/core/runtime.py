from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import asyncio
    import tkinter as tk

from dataclasses import dataclass
from typing import Literal

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
