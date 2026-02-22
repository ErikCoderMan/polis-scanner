import asyncio
import json
from src.services.fetcher import refresh_events, load_events
from src.api.polis import PolisAPIError
from src.core.logger import get_logger
from src.ui.log_buffer import log_buffer
from src.utils.query import query_events, parse_query

logger = get_logger(__name__)

state = {
    "refresh_task": None,
    "load_task": None,
    "more_task": None,
    "find_task": None,
    "search_task": None,
    "rank_task": None,
    "force_scroll": False
}


async def _run_command_task(task_key, coro):
    """Unified task runner"""

    if state.get(task_key) and not state[task_key].done():
        logger.warning("Already running command")
        return

    task = asyncio.create_task(coro())
    state[task_key] = task

    try:
        await task
    finally:
        state["force_scroll"] = True
        state[task_key] = None


# -------------------------
# Command implementations
# -------------------------

async def cmd_help(args=None):
    logger.info("""Showing help...
Commands:
    refresh
        Fetch the latest events from the API.
    load
        Display stored events from local storage.
    more <id>
        Show full details for a specific event by its ID.
    find <text>
        Quick search for events containing the given text.
        Results are displayed in reverse order; the best matches appear at the bottom.
    search [options]
        Advanced search with filters, sorting, and limits.
        Results are displayed in reverse order; top match appears last.
    rank --group <field> [options]
        Show grouped statistics (counts) for a specified field.
        Filters (--text, --fields, --filters) are applied before grouping.
        Ranked groups are displayed in reverse order; group with highest count appears at the bottom.

Search options:
    --text <text>
        Search for specific words in event fields (default behavior).
    --fields <field1 field2 ...>
        Specify which event fields to search in (default: name, summary, type, location.name).
    --filters <field1 value1 field2 value2 ...>
        Filter events by exact matches for specified fields.
    --sort <value>
        score      - sort by relevance score (default)
        -datetime  - sort by datetime, newest first
    --limit <n>
        Limit the number of results returned.

Rank options:
    --group <field>
        Specify the field to group by for statistics.
    --sort <value>
        -count     - sort groups by count (default)
        <field>    - sort groups alphabetically by field value
    --text <text>
        Filter events by text before grouping.
    --fields <field1 field2 ...>
        Specify which fields to search in for filtering before grouping.
    --filters <field1 value1 ...>
        Filter events by exact matches before grouping.
    --limit <n>
        Limit the number of ranked groups returned.

Other:
    help
        Display this help message.
    exit
        Quit the program.
    """)


async def cmd_refresh(args=None):
    async def _run():
        logger.info("Refreshing events (fetching)...")

        events = await refresh_events()

        if not events:
            logger.info("No new events")
            return

        for event in events:
            logger.info(
                f"NEW: {event['id']} - {event['name']} - {event['summary']}"
            )

        logger.info(f"Returned {len(events)} events")

    await _run()


async def cmd_load(args=None):
    async def _run():
        logger.info("Loading events...")
        events = load_events()

        if not events:
            logger.warning("No events saved, run 'refresh' instead")
            return

        for event in events:
            logger.info(
                f"LOAD: {event['id']} - {event['name']} - {event['summary']}"
            )

        logger.info(f"Returned {len(events)} events")

    await _run()


async def cmd_more(args):
    async def _run():
        if not args:
            logger.warning("Please specify event id")
            return

        target = args[0]

        logger.info("Getting more info about event...")
        events = load_events()

        if not events:
            logger.warning("No events saved, run 'refresh' first")
            return

        event = [e for e in events if str(e.get("id")) == target]

        if not event:
            logger.warning("Target event id does not exist")
            return

        for k, v in event[0].items():
            logger.info(f"{k}: {v}")

    await _run()


async def cmd_find(args):
    async def _run():
        if not args:
            logger.warning("Please enter text to find")
            return

        text = " ".join(args)

        logger.info(f"Finding events (stored)...")

        events = load_events()

        if not events:
            logger.warning("No events saved, run 'refresh' first")
            return

        result = query_events(events=events, text=text)

        for event in result[::-1]:
            logger.info(f"FIND: {event['id']} - {event['name']} - {event['summary']}")

        logger.info(f"Returned {len(result)} events")

    await _run()


async def cmd_search(args):
    async def _run():
        if not args:
            logger.warning("Please enter search argument")
            return

        query = parse_query(args)

        logger.info(f"query: {query}")

        events = load_events()

        if not events:
            logger.warning("No events saved")
            return

        result = query_events(
            events=events,
            text=query["text"],
            fields=query["fields"],
            filters=query["filters"],
            group_by=None,
            limit=query["limit"]
        )

        for event in result[::-1]:
            logger.info(f"SEAR: {event['id']} - {event['name']} - {event['summary']}")

        logger.info(f"Returned {len(result)} events")

    await _run()


async def cmd_rank(args):
    async def _run():
        if not args:
            logger.warning("Please provide ranking arguments")
            return

        query = parse_query(args)

        if not query.get("group"):
            logger.warning("rank requires --group")
            return

        events = load_events()

        if not events:
            logger.warning("No events saved")
            return

        result = query_events(
            events=events,
            text=query["text"],
            fields=query["fields"],
            filters=query["filters"],
            group_by=query["group"],
            sort=query["sort"],
            limit=query["limit"]
        )

        if not result:
            logger.info("No ranking results")
            return

        for value, count in result[::-1]:
            logger.info(f"RANK: {value} ({count})")

        logger.info(f"Returned {len(result)} ranked groups")

    await _run()


async def handle_command(text, app):
    parts = text.strip().lower().split(" ", 1)

    cmd = parts[0]
    args = parts[1].split() if len(parts) > 1 else []

    if not cmd:
        return

    if cmd in ("exit", "quit"):
        app.exit()
        return

    command_map = {
        "refresh": cmd_refresh,
        "load": cmd_load,
        "more": cmd_more,
        "help": cmd_help,
        "find": cmd_find,
        "search": cmd_search,
        "rank": cmd_rank,
    }

    handler = command_map.get(cmd)

    if handler:
        await handler(args)
        state["force_scroll"] = True
    else:
        logger.warning("Unknown command")
        
        
