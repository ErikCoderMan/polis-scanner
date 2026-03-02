from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.runtime import RuntimeContext

import asyncio

from src.core.logger import get_logger
from src.ui.log_buffer import log_buffer
from src.services.fetcher import refresh_events

logger = get_logger(__name__)

async def cmd_refresh(args=None, ctx: RuntimeContext=None):
    async def _run():
        logger.info("Refreshing events (fetching)...")
        events = await refresh_events()

        if not events:
            logger.info("No new events")
            return

        for event in events[::-1]:
            log_buffer.write(
                f"REFRESH: {event['id']} - {event['name']} - {event['summary']}"
            )

        logger.info(f"Returned {len(events)} events")

    await _run()
