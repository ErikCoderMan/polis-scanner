import asyncio
import json
from src.services.fetcher import refresh_events, load_events
from src.api.polis import PolisAPIError
from src.core.logger import get_logger
from src.ui.log_buffer import log_buffer
from src.utils.query import query_events, parse_query, parse_interval

logger = get_logger(__name__)

state = {
    "refresh_task": None,
    "load_task": None,
    "more_task": None,
    "find_task": None,
    "search_task": None,
    "rank_task": None,
    "poll_task": None,
    "poll_stop": None,
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

    poll [interval]
        Starts repeated execution of the refresh command to fetch new events
        automatically while pausing between requests.

        interval is formatted as <int>[s|m|h|d]
        (seconds, minutes, hours, days).
        Example values: 30s, 5m, 1h, 2d.
        
        Recomended minimum interval value: 60s.
        Minimum allowed interval: 10s (however this can be bypassed by adding 
        '--force True' to arguments even though it is not recommended
        to fetch so often and you can expect to get blocked fast).

    load
        Display events stored in local storage.

    more <id>
        Show full details for a specific event by its ID.

    find <text>
        Quick search for events containing the given text.
        Results are ranked by relevance; best matches are shown last.

    search [options]
        Advanced search supporting filters, sorting, and result limits.

        Results are ranked by relevance score by default.

    rank --group <field> [options]
        Show grouped statistics (counts) for a specified field.

        Filters (--text, --fields, --filters) are applied before grouping.

        Groups are sorted in reverse order by default, with the
        highest-count group appearing last.

Search options:
    --text <text>
        Search for specific words in event fields (default behavior).

    --fields <field1 field2 ...>
        Specify event fields to search in.
        Default: name, summary, type, location.name.

    --filters <field1 value1 field2 value2 ...>
        Filter events by exact field-value matches.

    --sort <value>
        score      - sort by relevance score (default)
        datetime   - sort by datetime, newest events first

    --limit <n>
        Limit the number of returned results.

Rank options:
    --group <field>
        Field used for grouping statistics.

    --sort <value>
        count     - sort groups by count (default)
        <field>    - sort groups alphabetically by field value

    --text <text>
        Filter events by text before grouping.

    --fields <field1 field2 ...>
        Fields used when filtering by text.

    --filters <field1 value1 ...>
        Exact field-value filters applied before grouping.

    --limit <n>
        Limit the number of ranked groups returned.

Other:
    help
        Display this help message.

    clear
        Clears the output screen.

    exit
        Quit the program.
    """)


async def cmd_refresh(args=None, interactive=True):
    async def _run():
        logger.info("Refreshing events (fetching)...")
        events = await refresh_events()

        if not events:
            logger.info("No new events")
            return

        for event in events:
            log_buffer.write(
                f"NEW: {event['id']} - {event['name']} - {event['summary']}"
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

        for event in events:
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
            log_buffer.write(f"FIND: {event['id']} - {event['name']} - {event['summary']}")

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
            limit=query["limit"]
        )

        for event in result[::-1]:
            log_buffer.write(f"SEAR: {event['id']} - {event['name']} - {event['summary']}")

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
            limit=query["limit"]
        )

        if not result: 
            logger.info("No ranking results")
            return

        for row in result[::-1]:
            log_buffer.write(f"RANK: {row['group']} (count={row['count']})")

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
                    await refresh_events() # can be replaced with refresh_events function for less output if prefered
                    
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
                logger.info("Poll loop exited")
        
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

async def handle_command(text, app, interactive=True):
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
        
        
