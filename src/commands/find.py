from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.runtime import RuntimeContext

import asyncio

from src.core.logger import get_logger
from src.ui.log_buffer import log_buffer
from src.services.fetcher import load_events
from src.utils.query import query_events, parse_query
from src.core.registry import command

logger = get_logger(__name__)

@command(
    name="find",
    usage="find <text>",
    description=(
        "Quick search using strict filtering (default behavior).\n"
        "Only events matching all words are returned.\n"
        "Example:\n"
        "    find brand stockholm"
    ),
    category="data"
)
async def cmd_find(args, ctx: RuntimeContext=None):
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

