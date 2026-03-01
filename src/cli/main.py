from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.runtime import RuntimeContext

import asyncio

from src.core.logger import get_logger
from src.core.config import settings

from .ui import CLIApp

logger = get_logger(__name__)

async def run_cli(ctx: RuntimeContext):
    logger.info("Starting CLI")
    logger.info(f"Data dir: {settings.data_dir}")
    logger.info("For GUI interface, add argument '--gui' when running program.")
    logger.info("Type 'help' to show full help text.")

    cli = CLIApp(ctx)

    # start UI updater worker
    ctx.scheduler.spawn("cli_ui", cli.update_ui())

    await cli.app.run_async()
    return 0
