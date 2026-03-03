from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.runtime import RuntimeContext

import asyncio

from src.core.logger import get_logger
from src.ui.log_buffer import log_buffer
from src.services.fetcher import load_events
from src.core.registry import command

logger = get_logger(__name__)

@command(
    name="more",
    usage="more <id>",
    description="Show full details for a specific event by its ID.",
    category="data"
)
async def cmd_more(args, ctx: RuntimeContext=None):
    if not args:
        logger.warning("Please specify event id")
        return

    target = args[0]

    logger.info("Getting more info about event...")
    events = load_events()

    if not events:
        logger.warning("No events saved, run 'refresh' first")
        return

    event = [e for e in events if str(e.get("id")) == target]

    if not event:
        logger.warning("Target event id does not exist")
        return

    for k, v in event[0].items():
        log_buffer.write(f"{k}: {v}")

