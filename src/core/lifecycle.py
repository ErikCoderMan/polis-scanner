from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.runtime import RuntimeContext

import asyncio
from src.core.logger import get_logger
from src.core.config import settings

logger = get_logger(__name__)


async def graceful_shutdown(
    ctx: RuntimeContext,
    force: bool = False,
    grace_period: int = settings.shutdown_grace_period
):
    """
    Graceful lifecycle shutdown manager.
    """

    if ctx.state.get("shutdown_in_progress"):
        logger.error("Shutdown already in progress")
        return

    ctx.state["shutdown_in_progress"] = True
    logger.info("Shutdown initiated")

    scheduler = ctx.scheduler

    # --------------------------------------------------
    # Cancel workers first (deterministic shutdown signal)
    # --------------------------------------------------

    running_tasks = scheduler.running_tasks() if scheduler else []

    if running_tasks:
        logger.info(f"Cancelling {len(running_tasks)} workers")

        for task in running_tasks:
            task.cancel()

    # --------------------------------------------------
    # Grace period wait
    # --------------------------------------------------

    if running_tasks and not force:
        try:
            await asyncio.wait_for(
                asyncio.gather(
                    *running_tasks,
                    return_exceptions=True
                ),
                timeout=grace_period
            )
        except asyncio.TimeoutError:
            logger.warning("Graceful shutdown timeout reached")

    else:
        # Even if force=True, ensure tasks are drained
        if running_tasks:
            await asyncio.gather(
                *running_tasks,
                return_exceptions=True
            )

    # --------------------------------------------------
    # Stop event loop (GUI path)
    # --------------------------------------------------

    if ctx.is_gui() and ctx.loop:
        try:
            ctx.loop.call_soon_threadsafe(ctx.loop.stop)
        except Exception:
            logger.exception("Failed stopping event loop")

    # --------------------------------------------------
    # GUI cleanup hook
    # --------------------------------------------------

    if ctx.is_gui() and ctx.root:
        try:
            ctx.root.after(0, ctx.root.quit)
        except Exception:
            logger.exception("GUI shutdown failed")

    # --------------------------------------------------
    # CLI cleanup hook
    # --------------------------------------------------

    if ctx.is_cli() and ctx.interactive and ctx.app_cli:
        try:
            ctx.app_cli.exit()
        except Exception:
            logger.exception("CLI shutdown failed")

    logger.info("Shutdown completed")
