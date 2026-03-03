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
    name="search",
    usage="search [options]",
    description=(
        "Advanced search with filtering, sorting and limit.\n\n"
        "Options:\n"
        "    --text <text>\n"
        "        Match all words in the specified fields.\n\n"
        "    --fields <field1 field2 ...>\n"
        "        Fields used for text matching.\n"
        "        (Default all): name, summary, type, location.name.\n\n"
        "    --filters <field1 value1 field2 value2 ...>\n"
        "        Exact field-value filtering.\n\n"
        "    --sort <field1 field2 ...>\n"
        "        Sort events by specified event fields.\n"
        "        Examples: score, datetime, name, type, location.name\n"
        "        Multiple fields can be provided in priority order.\n\n"
        "    --limit <n>\n"
        "        Limit the number of returned results.\n\n"
        "    --strict <true|false>\n"
        "        true  (default)  → hard filtering only\n"
        "        false            → enable relevance scoring and ranking\n"
        "Example:\n"
        "   search --text polis --filters type brand location.name stockholm --limit 3\n"
    ),
    category="data"
)
async def cmd_search(args, ctx: RuntimeContext=None):
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
