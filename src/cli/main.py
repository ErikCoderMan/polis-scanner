from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.runtime import RuntimeContext

import asyncio
from prompt_toolkit.application import Application

from src.core.logger import get_logger
from src.core.config import settings

from .ui import layout, ui_updater
from .keybindings import build_keybindings

logger = get_logger(__name__)

async def run_cli(ctx: RuntimeContext):
    logger.info("Starting CLI")
    logger.info(f"Data dir: {settings.data_dir}")
    logger.info("For GUI interface, add argument '--gui' when running program.")
    logger.info("Type 'help' to show full help text.")
    
    loop = asyncio.get_running_loop()
    kb = build_keybindings(ctx=ctx)
    
    app = Application(
        layout=layout,
        key_bindings=kb,
        mouse_support=True,
        full_screen=True
    )
    
    ctx.app_cli = app

    asyncio.create_task(ui_updater(ctx))
    await app.run_async()

    return 0
