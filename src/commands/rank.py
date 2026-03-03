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
    name="rank",
    usage="rank --group <field> [options]",
    description=(
        "Group events by a field and display statistics.\n\n"
        "Options:\n"
        "    --group <field>\n"
        "        Field used for grouping.\n\n"
        "    --text <text>\n"
        "        Apply text filtering before grouping.\n\n"
        "    --fields <field1 field2 ...>\n"
        "        Fields used for text filtering.\n\n"
        "    --filters <field1 value1 ...>\n"
        "        Exact field-value filters before grouping.\n\n"
        "    --sort <field1 field2 ...>\n"
        "        Sort grouped results.\n"
        "        Available fields: count, avg_score, group\n"
        "        Multiple fields can be provided in priority order.\n\n"
        "    --limit <n>\n"
        "        Limit number of groups returned.\n\n"
        "    --strict <true|false>\n"
        "        true  (default)  → hard filtering only\n"
        "        false            → enable relevance scoring and ranking\n"
        "Example:\n"
        "   rank --group location.name --filters type brand"
    ),
    category="data"
)
async def cmd_rank(args, ctx: RuntimeContext=None):
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

