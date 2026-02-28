from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.runtime import RuntimeContext

import asyncio
from src.core.logger import get_logger
from src.core.config import settings

logger = get_logger(__name__)

async def graceful_shutdown(state, ctx: RuntimeContext, force=False, grace_period=settings.shutdown_grace_period):
    """
    Graceful lifecycle shutdown manager.
    """
    
    
    if state.get("shutdown_in_progress", None):
            logger.error(f"shutdown already in progress, returning")
            return
    
    state["shutdown_in_progress"] = True
    logger.info("Shutdown initiated")
    running_tasks = []

    # --------------------------------------------------
    # Collect tasks + signal stop events
    # --------------------------------------------------

    for name, obj in state.items():
        if not (name.endswith("_task") and obj):
            continue

        if obj.done():
            continue

        running_tasks.append(obj)

        stop_name = name.replace("_task", "_stop")
        stop_event = state.get(stop_name)

        if stop_event:
            logger.info(f"Signalling stop event: {stop_name}")
            stop_event.set()
        else:
            logger.warning(f"No stop event registered for {name}")

    # --------------------------------------------------
    # Graceful wait phase
    # --------------------------------------------------

    if running_tasks and not force:
        try:
            logger.info(
                f"Waiting {grace_period}s for tasks to exit gracefully..."
            )

            await asyncio.wait_for(
                asyncio.gather(*running_tasks),
                timeout=grace_period
            )

        except asyncio.TimeoutError:
            logger.warning("Graceful shutdown timeout reached")

    # --------------------------------------------------
    # Force cancel remaining tasks
    # --------------------------------------------------
    await asyncio.sleep(0.5)
    running_tasks = [t for t in running_tasks if not t.done()]
    for task in running_tasks:
        if not task.done():
            logger.warning(f"Force cancelling task {task}")
            task.cancel()

    await asyncio.gather(*running_tasks, return_exceptions=True)

    # --------------------------------------------------
    # Stop event loop
    # --------------------------------------------------
    
    if ctx.mode == "gui" and ctx.loop:
        try:
            ctx.loop.call_soon_threadsafe(ctx.loop.stop)
            
        except Exception:
            logger.exception("Failed stopping event loop")

    # --------------------------------------------------
    # GUI cleanup hook
    # --------------------------------------------------

    if ctx.mode == "gui" and ctx.root:
        try:
            ctx.root.after(0, ctx.root.quit)
        except Exception:
            logger.exception("GUI shutdown failed")
    
    if ctx.mode == "cli" and ctx.interactive and ctx.app_cli:
        try:
            ctx.app_cli.exit()
        except Exception:
            logger.exception("CLI shutdown failed")

    logger.info("Shutdown completed")
