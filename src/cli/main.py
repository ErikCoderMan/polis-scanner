import asyncio
from prompt_toolkit.application import Application
from .ui import layout, ui_updater
from .commands import state
from .keybindings import kb
from src.core.logger import get_logger
from src.core.config import settings

logger = get_logger(__name__)

async def run_cli():
    logger.info("Starting CLI")
    logger.info(f"Data dir: {settings.data_dir}")
    logger.info("Type 'help'")

    app = Application(
        layout=layout,
        key_bindings=kb,
        mouse_support=True,
        full_screen=True
    )

    asyncio.create_task(ui_updater(app, state))
    await app.run_async()

    # wait background job before exit
    task = state.get("refresh_task")
    if task and not task.done():
        logger.info("Waiting for running refresh to finish...")
        await task

    return 0
