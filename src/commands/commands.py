from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.runtime import RuntimeContext

import asyncio
import json
from src.core.config import settings
from src.services.fetcher import refresh_events, load_events
from src.api.polis import PolisAPIError
from src.core.logger import get_logger
from src.ui.log_buffer import log_buffer
from src.utils.query import query_events, parse_query, parse_interval, parse_command
from src.core.lifecycle import graceful_shutdown
from src.core.scheduler import WorkerAlreadyRunningError

logger = get_logger(__name__)


# -------------------------
# Command implementations
# -------------------------

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


async def cmd_refresh(args=None, ctx: RuntimeContext=None):
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


async def cmd_load(args=None, ctx: RuntimeContext=None):
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


async def cmd_more(args, ctx: RuntimeContext=None):
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


async def cmd_clear(args=None, ctx: RuntimeContext=None):
    async def _run():
        logger.info("Clearing screen...") # still being written to file log
        log_buffer.clear()

    await _run()


async def cmd_poll(args, ctx: RuntimeContext = None):
    # -----------------------------
    # Resolve interval
    # -----------------------------
    
    seconds = None

    # 1. Try args
    if args:
        try:
            seconds = parse_interval(args)
        except ValueError:
            logger.warning("Invalid interval format from arguments")

    # 2. Try config
    if not seconds:
        if settings.poll_interval:
            try:
                seconds = parse_interval(settings.poll_interval)
                logger.info(f"Interval set to config value {settings.poll_interval}")
            except ValueError:
                logger.error("Invalid interval format from config")

    # 3. Fallback
    if not seconds:
        logger.warning("Using fallback interval 5m")
        seconds = 5 * 60

    # -----------------------------
    # Policy validation
    # -----------------------------

    if seconds < settings.poll_interval_lowest_allowed_s:
        if "--force" not in (args or []):
            logger.error(
                f"Minimum allowed interval is "
                f"{settings.poll_interval_lowest_allowed_s}s. "
                f"Use --force to override."
            )
            return

        logger.warning("Running below allowed minimum with --force")

    elif seconds < settings.poll_interval_lowest_recomended_s:
        logger.warning("Interval is below recommended minimum")

    # -----------------------------
    # Poll loop
    # -----------------------------

    logger.info(f"Poll started, interval={seconds}s")

    try:
        while True:
            new_events = await refresh_events()

            if new_events:
                for event in new_events:
                    log_buffer.write(
                        f"POLL: {event['id']} - "
                        f"{event['name']} - "
                        f"{event['summary']}"
                    )

            await asyncio.sleep(seconds)

    except asyncio.CancelledError:
        logger.info("Poll cancelled")
        raise


async def cmd_kill(args, ctx: RuntimeContext=None):
    if not args:
        logger.warning("Please specify command to kill")
        return

    name = args[0]

    if not ctx.scheduler.has_worker(name):
        logger.warning(f"No running task named '{name}'")
        return

    logger.info(f"Killing '{name}'...")
    await ctx.scheduler.stop_and_wait(name)
    logger.info(f"'{name}' stopped")


async def cmd_tasks(args=None, ctx: RuntimeContext = None):
    if not ctx or not ctx.scheduler:
        logger.error("Scheduler not available")
        return

    workers = ctx.scheduler.list_workers()
    result = workers
    
    if "tasks" in [name for name in result.keys()]:
        result.pop("tasks")

    if not result:
        logger.info("No tasks registered")
        return
    
    logger.info("Listing tasks...")
    for name, task in result.items():
        status = (
            "running"
            if not task.done()
            else "cancelled"
            if task.cancelled()
            else "done"
        )

        log_buffer.write(
            f"TASK: {name} | status={status}"
        )

    logger.info(f"Total tasks (excluding self): {len(result)}")

# --------------------
# command handler
# --------------------

async def handle_command(text, ctx: RuntimeContext=None):
    cmd, args = parse_command(text)

    if not cmd:
        return

    if cmd in ("exit", "quit"):
        if "now" in args:
            await graceful_shutdown(ctx=ctx, force=True)
        
        else:
            await graceful_shutdown(ctx=ctx, force=False)
        
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
        "poll": cmd_poll,
        "kill": cmd_kill,
        "tasks": cmd_tasks
    }
    
    try:
        handler = command_map.get(cmd)

        if not handler:
            logger.warning("Unknown command")
            ctx.state["force_scroll"] = True
            return

        logger.info(f"cmd='{cmd}', args='{' '.join(args)}'")

        try:
            ctx.scheduler.spawn(
                cmd,
                lambda: handler(args=args, ctx=ctx)
            )

        except WorkerAlreadyRunningError:
            logger.warning(f"Command '{cmd}' is already running")
            
    finally:
        ctx.state["force_scroll"] = True

