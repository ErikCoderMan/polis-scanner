import asyncio
from prompt_toolkit.application import Application

from src.core.logger import get_logger
from src.core.config import settings
from src.commands.commands import state

from .ui import layout, ui_updater
from .keybindings import kb

logger = get_logger(__name__)

async def run_cli():
    logger.info("Starting CLI")
    logger.info(f"Data dir: {settings.data_dir}")
    logger.info("Type 'help' to show help text")

    app = Application(
        layout=layout,
        key_bindings=kb,
        mouse_support=True,
        full_screen=True
    )

    asyncio.create_task(ui_updater(app, state))
    await app.run_async()

    return 0
