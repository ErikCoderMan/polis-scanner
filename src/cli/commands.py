import asyncio
import json
from src.services.fetcher import refresh_events, load_events
from src.api.polis import PolisAPIError
from src.core.logger import get_logger
from src.ui.log_buffer import log_buffer

logger = get_logger(__name__)


state = {
    "refresh_task": None,
    "load_task": None,
    "more_task": None,
    "force_scroll": False
}


async def cmd_refresh():
    if state["refresh_task"] and not state["refresh_task"].done():
        logger.warning("Already refreshing events!")
        return

    async def _run():
        try:
            logger.info("Refreshing events...")
            events = await refresh_events()

            if not events:
                logger.info("No new events")
                return

            for event in events:
                logger.info(
                    f"NEW: {event['id']} - {event['name']} - {event['summary']}"
                )
        
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


async def cmd_help():
    logger.debug("Showing help...")
    logger.info("Commands: refresh, load, more [id], help, exit")
    state["force_scroll"] = True


async def handle_command(text, app):
    parts = text.strip().lower().split(" ", 1)
    cmd = parts[0]
    args = parts[1] if len(parts) > 1 else None
    
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

    logger.warning("Unknown command")
