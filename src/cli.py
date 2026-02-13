import asyncio
import sys

from src.core.config import settings
from src.core.logger import get_logger
from src.services.fetcher import refresh_events
from src.api.polis import PolisAPIError

logger = get_logger(__name__)


# -------------------------------------------------
# Async input (non-blocking stdin)
# -------------------------------------------------
async def ainput(prompt: str = "") -> str:
    print(prompt, end="", flush=True)
    return await asyncio.to_thread(sys.stdin.readline)


# -------------------------------------------------
# Command handlers
# -------------------------------------------------
async def cmd_refresh(state):
    if state["refresh_task"] and not state["refresh_task"].done():
        logger.info("Refresh already running")
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
                    f"{event['id']} - {event['datetime']} - {event['name']} - {event['summary']}"
                )

        except PolisAPIError:
            logger.error("Could not update events (API failure)")

    state["refresh_task"] = asyncio.create_task(_run())


async def cmd_help(_state):
    print(
        """
Commands:
  refresh   Fetch latest events
  help      Show this help
  exit      Quit program
"""
    )


# -------------------------------------------------
# CLI loop
# -------------------------------------------------
async def run_cli():
    logger.info("Starting CLI")
    logger.info(f"Data dir: {settings.data_dir}")

    state = {
        "refresh_task": None,
    }

    commands = {
        "refresh": cmd_refresh,
        "help": cmd_help,
        "exit": None,
        "quit": None,
    }

    await cmd_help(state)

    try:
        while True:
            line = (await ainput("> ")).strip().lower()

            if not line:
                continue

            if line in ("exit", "quit"):
                logger.info("Shutting down...")
                break

            cmd = commands.get(line)

            if not cmd:
                logger.warning("Unknown command — type 'help'")
                continue

            await cmd(state)

    except asyncio.CancelledError:
        pass

    # wait for running background task before exiting
    task = state.get("refresh_task")
    if task and not task.done():
        logger.info("Waiting for running refresh to finish...")
        await task

    return 0
