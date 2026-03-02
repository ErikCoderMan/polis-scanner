from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.runtime import RuntimeContext

import asyncio

from src.core.logger import get_logger
from src.ui.log_buffer import log_buffer
from src.services.fetcher import load_events
from src.utils.query import query_events, parse_query

logger = get_logger(__name__)

async def cmd_find(args, ctx: RuntimeContext=None):
    async def _run():
        if not args:
            logger.warning("Please enter text to find")
            return

        text = " ".join(args)
        logger.debug(f"query text: {text}")

        logger.info(f"Finding events (stored)...")
        events = load_events()

        if not events:
            logger.warning("No events saved, run 'refresh' first")
            return

        result = query_events(events=events, text=text)

        for event in result[::-1]:
            log_buffer.write(f"FIND{f' (score={event['score']})' if event['score'] else ''}: {event['id']} - {event['name']} - {event['summary']}")

        logger.info(f"Returned {len(result)} events")

    await _run()
