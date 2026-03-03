from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.runtime import RuntimeContext

import asyncio
from src.core.registry import command
from src.core.logger import get_logger
from src.ui.log_buffer import log_buffer

logger = get_logger(__name__)

@command(
    name="tasks",
    usage="tasks",
    description="List running background tasks.",
    category="tasks"
)
async def cmd_tasks(args=None, ctx: RuntimeContext = None):
    if not ctx or not ctx.scheduler:
        logger.error("Scheduler not available")
        return

    workers = ctx.scheduler.list_workers()
    result = workers
    
    if "tasks" in [name for name in result.keys()]:
        result.pop("tasks")

    if not result:
        logger.info("No tasks registered")
        return
    
    logger.info("Listing tasks...")
    for name, task in result.items():
        status = (
            "running"
            if not task.done()
            else "cancelled"
            if task.cancelled()
            else "done"
        )

        log_buffer.write(
            f"TASK: {name} - status={status}"
        )

    logger.info(f"Total tasks: {len(result)}")
