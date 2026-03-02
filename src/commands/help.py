from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.runtime import RuntimeContext

import asyncio

from src.core.logger import get_logger
from src.ui.log_buffer import log_buffer

logger = get_logger(__name__)

async def cmd_help(args=None, ctx: RuntimeContext=None):
    logger.info("Showing help...")
    log_buffer.write("""
Data:
    refresh
        Fetch the latest events from the API.

    load
        Display events stored in local storage.

    more <id>
        Show full details for a specific event by its ID.

    find <text>
        Quick search using strict filtering (default behavior).
        Only events matching all words are returned.

    search [options]
        Advanced search with filtering, sorting and limit.

    rank --group <field> [options]
        Group events by a field and display statistics.

Tasks:
    poll [interval]
        Repeatedly refresh events at a fixed interval.

        Interval format: <int>[s|m|h|d]
        (seconds, minutes, hours, days).
        Examples: 30s, 5m, 1h, 2d.

    tasks
        List running background tasks.

    kill <name>
        Stop a running task.

Search options:
    --text <text>
        Match all words in the specified fields.

    --fields <field1 field2 ...>
        Fields used for text matching.
        (Default all): name, summary, type, location.name.

    --filters <field1 value1 field2 value2 ...>
        Exact field-value filtering.

    --sort <field1 field2 ...>
        Sort events by specified event fields.
        Examples:
            score
            datetime
            name
            type
            location.name

        Multiple fields can be provided in priority order.

    --limit <n>
        Limit the number of returned results.

    --strict <true|false>
        true  (default)  → hard filtering only
        false            → enable relevance scoring and ranking

Rank options:
    --group <field>
        Field used for grouping.

    --text <text>
        Apply text filtering before grouping.

    --fields <field1 field2 ...>
        Fields used for text filtering.

    --filters <field1 value1 ...>
        Exact field-value filters before grouping.

    --sort <field1 field2 ...>
        Sort grouped results.
        Available fields:
            count
            avg_score
            group

        Multiple fields can be provided in priority order.

    --limit <n>
        Limit number of groups returned.
    
    --strict <true|false>
        true  (default)  → hard filtering only
        false            → enable relevance scoring and ranking
        
Other:
    help
        Display this help message.

    clear
        Clear the output screen.

    exit / quit [now]
        Quit the program.
        
        Options:
            now            → Do not wait for background tasks, quit imediately
            (no arguments) → Program will make a clean exit, properly wait and close tasks

Examples:
    search --text polis --filters type brand location.name stockholm --limit 3
    find brand stockholm
    rank --group location.name --filters type brand
    """)
