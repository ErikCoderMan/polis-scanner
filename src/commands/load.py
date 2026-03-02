from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.runtime import RuntimeContext

import asyncio

from src.core.logger import get_logger
from src.ui.log_buffer import log_buffer
from src.services.fetcher import load_events

logger = get_logger(__name__)

async def cmd_load(args=None, ctx: RuntimeContext=None):
    async def _run():
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

    await _run()
