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

async def cmd_rank(args, ctx: RuntimeContext=None):
    async def _run():
        if not args:
            logger.warning("Please provide ranking arguments")
            return

        query = parse_query(args)
        logger.debug(f"query: {query}")

        if not query.get("group"):
            logger.warning("rank requires --group")
            return
        
        logger.info(f"Ranking events (stored)...")
        events = load_events()

        if not events:
            logger.warning("No events saved, run 'refresh' first")
            return

        result = query_events(
            events=events,
            text=query["text"],
            fields=query["fields"],
            filters=query["filters"],
            group_by=query["group"],
            sort=query["sort"],
            limit=query["limit"],
            strict=query["strict"]
        )

        if not result: 
            logger.info("No ranking results")
            return

        for row in result[::-1]:
            log_buffer.write(f"RANK: {row['group']} (count={row['count']} / avg_score={row['avg_score']})")

        logger.info(f"Returned {len(result)} ranked groups")

    await _run()
