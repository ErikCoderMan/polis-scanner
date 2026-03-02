from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.runtime import RuntimeContext

import asyncio

from src.core.logger import get_logger

logger = get_logger(__name__)

async def cmd_kill(args, ctx: RuntimeContext=None):
    if not args:
        logger.warning("Please specify command to kill")
        return

    name = args[0]

    if not ctx.scheduler.has_worker(name):
        logger.warning(f"No running task named '{name}'")
        return

    logger.info(f"Killing '{name}'...")
    await ctx.scheduler.stop_and_wait(name)
    logger.info(f"'{name}' stopped")
