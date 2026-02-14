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


async def cmd_help():
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

    state["force_scroll"] = True


async def cmd_refresh():
    if state["refresh_task"] and not state["refresh_task"].done():
        logger.warning("Already refreshing events!")
        return

    async def _run():
        try:
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
        
        except PolisAPIError:
            logger.error("Could not update events (API failure)")
            raise
        
        finally:
            state['refresh_task'] = None

    state["refresh_task"] = asyncio.create_task(_run())
    state["force_scroll"] = True


async def cmd_load():
    if state["load_task"] and not state["load_task"].done():
        logger.warning("Already loading events")
        return
    
    async def _run():
        try:
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
                
        except (FileNotFoundError, json.JSONDecodeError):
            logger.error("No events saved or file corrupt, run 'refresh' instead")
            raise
        
        finally:
            state['load_task'] = None
    
    state['load_task'] = asyncio.create_task(_run())
    state['force_scroll'] = True


async def cmd_more(args):
    if state['more_task'] and not state['more_task'].done():
        logger.warning("Already running more command")
        return
    
    async def _run():
        try:
            if not args:
                logger.warning("Please specify event id as argument, for example: more 123456")
                return
            
            target_event = args[0] if len(args) > 0 else None
            
            logger.info("Getting more info about event...")
            events = load_events()
            
            if not events:
                logger.warning("No events saved, run 'refresh' first")
                return
            
            event = [e for e in events if str(e.get("id", None)) == target_event] 
            
            if not event:
                logger.warning("Target event id does not exist in stored events")
                return
            
            for k, v in event[0].items():
                logger.info(f"{k}: {v}")
        
        except (FileNotFoundError, json.JSONDecodeError):
            logger.error("No events saved or file corrupt, run 'refresh' first")
            raise
        
        finally:
            state['more_task'] = None
    
    state['more_task'] = asyncio.create_task(_run())
    state['force_scroll'] = True


async def cmd_find(args):
    if state['find_task'] and not state['find_task'].done():
        logger.warning("Already running filter command")
        return
        
    async def _run():
        try:
            if not args:
                logger.warning("Please enter text to find as argument")
                return
            
            text = " ".join([arg for arg in args])
            logger.info(f"text: {text}")
                    
            logger.info("Finding events (stored)...")
            events = load_events()
            
            if not events:
                logger.warning("No events saved, run 'refresh' first")
                return
            
            result = query_events(events=events, text=text)
            
            for event in result[::-1]:
                logger.info(f"FIND: {event['id']} - {event['name']} - {event['summary']}")
            
            logger.info(f"Returned {len(result)} events")
        
        except (FileNotFoundError, json.JSONDecodeError):
            logger.error("No events saved or file corrupt, run 'refresh' first")
            raise
        
        finally:
            state['find_task'] = None
    
    state['find_task'] = asyncio.create_task(_run())
    state['force_scroll'] = True


async def cmd_search(args):
    if state['search_task'] and not state['search_task'].done():
        logger.warning("Already running search command")
        return
        
    async def _run():
        try:
            if not args:
                logger.warning("Please enter atleast one search argument")
                return
            
            query = parse_query(args)
            logger.info(f"query: {query}")
            
            logger.info("Searching for events (stored)...")
            events = load_events()
            
            if not events:
                logger.warning("No events saved, run 'refresh' first")
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
        
        except (FileNotFoundError, json.JSONDecodeError):
            logger.error("No events saved or file corrupt, run 'refresh' first")
            raise
        
        finally:
            state['search_task'] = None
    
    state['search_task'] = asyncio.create_task(_run())
    state['force_scroll'] = True
    
    
async def cmd_rank(args):
    if state['rank_task'] and not state['rank_task'].done():
        logger.warning("Already running rank command")
        return
        
    async def _run():
        try:
            if not args:
                logger.warning("Please provide ranking arguments (ex: --group type)")
                return
            
            query = parse_query(args)
            logger.info(f"query: {query}")
            
            if not query.get("group"):
                logger.warning("rank requires --group")
                return
            
            logger.info("Ranking events (stored)...")
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

            # result = list[tuple[str, int]]
            for value, count in result[::-1]:
                logger.info(f"RANK: {value} ({count})")
            
            logger.info(f"Returned {len(result)} ranked groups")
        
        except (FileNotFoundError, json.JSONDecodeError):
            logger.error("No events saved or file corrupt, run 'refresh' first")
            raise
        
        finally:
            state['rank_task'] = None
    
    state['rank_task'] = asyncio.create_task(_run())
    state['force_scroll'] = True


async def handle_command(text, app):
    parts = text.strip().lower().split(" ", 1)
    cmd = parts[0]
    args = parts[1] if len(parts) > 1 else None
    
    logger.debug(f"parts: cmd={cmd}, args={args if args else None}")
    
    if args:
        args = [a.strip() for a in args.split(" ")]
    
    if not cmd:
        return

    if cmd in ("exit", "quit"):
        app.exit()
        return

    if cmd == "refresh":
        await cmd_refresh()
        return
    
    if cmd == "load":
        await cmd_load()
        return
        
    if cmd == "more":
        await cmd_more(args)
        return

    if cmd == "help":
        await cmd_help()
        return
    
    if cmd == "find":
        await cmd_find(args)
        return
    
    if cmd == "search":
        await cmd_search(args)
        return
    
    if cmd == "rank":
        await cmd_rank(args)
        return

    logger.warning("Unknown command")


