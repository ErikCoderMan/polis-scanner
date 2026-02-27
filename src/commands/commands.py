import asyncio
import json
from src.services.fetcher import refresh_events, load_events
from src.api.polis import PolisAPIError
from src.core.logger import get_logger
from src.ui.log_buffer import log_buffer
from src.utils.query import query_events, parse_query, parse_interval

logger = get_logger(__name__)

state = {
    "poll_task": None,
    "poll_stop": None,
    "force_scroll": False
}


# -------------------------
# Command implementations
# -------------------------

async def cmd_help(args=None, interactive=True):
    logger.info("""Showing help...
Commands:
    refresh
        Fetch the latest events from the API.

    poll [start <interval> | stop]
        Repeatedly runs the refresh command at a fixed interval.

        Interval format: <int>[s|m|h|d]
        (seconds, minutes, hours, days).
        Examples: 30s, 5m, 1h, 2d.

        Recommended minimum interval: 60s.
        Minimum allowed interval: 10s.
        Use with care to avoid rate limiting.

    load
        Display events stored in local storage.

    more <id>
        Show full details for a specific event by its ID.

    find <text>
        Quick search using strict filtering (default behavior).
        Only events matching all words are returned.

    search [options]
        Advanced search with filtering, sorting and limit.

        Default mode: strict filtering (no relevance scoring).
        Only exact matches are returned unless --strict false is used.

        To enable relevance ranking:
            --strict false

    rank --group <field> [options]
        Group events by a field and display statistics.

        Filters (--text, --fields, --filters) are applied before grouping.

        Default sorting:
            If --text is used → avg_score, count, group
            Otherwise        → count, group

Search options:
    --text <text>
        Match all words in the specified fields.

    --fields <field1 field2 ...>
        Fields used for text matching.
        Default: name, summary, type, location.name.

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

    exit / quit
        Quit the program.
    """)


async def cmd_refresh(args=None, interactive=True):
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


async def cmd_load(args=None, interactive=True):
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


async def cmd_more(args, interactive=True):
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
            log_buffer.write(f"{k}: {v}")

    await _run()


async def cmd_find(args, interactive=True):
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


async def cmd_search(args, interactive=True):
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


async def cmd_rank(args, interactive=True):
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


async def cmd_clear(args=None, interactive=True):
    async def _run():
        logger.info("Clearing screen...") # still being written to file log
        log_buffer.clear()

    await _run()


async def cmd_poll(args, interactive=True):
    """ 
    command for automatic event fetching
    the command will run 'refresh' in a loop until stopped
    same command is used for both start and stop,
    parse_interval function will look for substring in args
    to decide if toggle is start or stop
    """
    
    # ---- STATUS ----
    
    if not args:
        logger.info("Getting poll status...")
        task = state.get("poll_task")
        
        if task and not task.done():
            logger.info("Poll is ON, use 'poll stop' to stop")
        
        else:
            logger.info("Poll is OFF, use 'poll start [INTERVAL]' to start")
            logger.info("INTERVAL Duration formatted as <int>[s|m|h|d]")
            
        return
    
    # ---- PARSE ARGS ----
    
    # parse intervall (taken from config if not specified)
    query = parse_interval(args)
    
    if not query:
        return
    
    # ---- STOP ----
    
    if query.get("toggle", None) == "stop":
        stop_event = state.get("poll_stop")
        task = state.get("poll_task")
        
        if not task or task.done():
            logger.warning("Poll is not running")
            return
        
        logger.info("Stopping poll loop...")
        stop_event.set()
        await task
        logger.info("Poll stopped")
        return
        
    
    # ---- START ----
    
    elif query.get("toggle", None) == "start":
        if state.get("poll_task") and not state["poll_task"].done():
            logger.warning("Poll already running")
            return
        
        logger.info("Starting poll loop...")
        
        stop_event = asyncio.Event()
        state["poll_stop"] = stop_event
        
        async def poll_loop():
            logger.info(f"Poll started, interval={query['interval_s']}s {f"({query['interval_str']})" if not 's' in query['interval_str'] else ''}")
            
            try:
                while True:
                    new_events = await refresh_events()
                    if new_events:
                        for event in new_events:
                            log_buffer.write(
                                f"POLL: {event['id']} - {event['name']} - {event['summary']}"
                            )
                    
                    try:
                        await asyncio.wait_for(stop_event.wait(), timeout=query['interval_s'])
                        
                        # If we get here then stop_event was set so we break infinity loop
                        break
                        
                    except asyncio.TimeoutError:
                        # Timeout = run next cycle
                        continue
            
            finally:
                state["poll_task"] = None
                state["poll_stop"] = None
                logger.debug("Poll loop exited")
        
        if interactive:
            task = asyncio.create_task(poll_loop())
            state["poll_task"] = task
        
        else:
            await poll_loop()
    
    else:
        logger.warning("Invalid/missing argument(s), expected either 'start [interval]' or 'stop' as command argument, type 'help' for more info")


# --------------------
# command handler
# --------------------

async def handle_command(text, app=None, interactive=True):
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
        "clear": cmd_clear,
        "poll": cmd_poll
    }

    handler = command_map.get(cmd)

    if handler:
        logger.info(f"cmd='{cmd}', args='{' '.join(args)}'")
        await handler(args=args, interactive=interactive)
        state["force_scroll"] = True
        
    else:
        logger.warning("Unknown command")
        
        
        
