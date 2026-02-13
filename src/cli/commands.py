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
                    f"{event['id']} - {event['name']} - {event['summary']}"
                )
        
        except PolisAPIError:
            logger.error("Could not update events (API failure)")
            raise

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
                logger.info("No events saved, run 'refresh' instead")
                return
            
            for event in events:
                logger.info(
                    f"{event['id']} - {event['name']} - {event['summary']}"
                )
                
        except (FileNotFoundError, json.JSONDecodeError):
            logger.error("No events saved or file corrupt, run 'refresh' instead")
            raise
    
    state['load_task'] = asyncio.create_task(_run())
    state['force_scroll'] = True


async def cmd_help():
    logger.debug("Showing help...")
    logger.info("Commands: refresh, load, help, exit")
    state["force_scroll"] = True


async def handle_command(text, app):
    cmd = text.strip().lower()
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

    if cmd == "help":
        await cmd_help()
        return

    logger.warning("Unknown command")
