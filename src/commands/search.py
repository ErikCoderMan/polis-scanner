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

async def cmd_search(args, ctx: RuntimeContext=None):
    async def _run():
        if not args:
            logger.warning("Please enter search argument")
            return

        query = parse_query(args)
        logger.debug(f"query: {query}")
        
        logger.info(f"Searching in events (stored)...")
        events = load_events()

        if not events:
            logger.warning("No events saved, run 'refresh' first")
            return

        result = query_events(
            events=events,
            text=query["text"],
            fields=query["fields"],
            filters=query["filters"],
            group_by=None, # not used by this command
            sort=query["sort"],
            limit=query["limit"],
            strict=query["strict"]
        )

        for event in result[::-1]:
            log_buffer.write(f"SEARCH{f' (score={event['score']})' if not query['strict'] else ''}: {event['id']} - {event['name']} - {event['summary']}")

        logger.info(f"Returned {len(result)} events")

    await _run()
