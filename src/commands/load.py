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
    name="load",
    usage="load",
    description="Display events stored in local storage.",
    category="data"
)
async def cmd_load(args=None, ctx: RuntimeContext=None):
    logger.info("Loading events (stored)...")
    events = load_events()

    if not events:
        logger.warning("No events saved, run 'refresh' instead")
        return

    for event in events[::-1]:
        log_buffer.write(
            f"LOAD: {event['id']} - {event['name']} - {event['summary']}"
        )

    logger.info(f"Returned {len(events)} events")

