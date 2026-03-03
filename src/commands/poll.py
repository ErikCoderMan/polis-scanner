from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.runtime import RuntimeContext

import asyncio

from src.core.config import settings
from src.core.logger import get_logger
from src.ui.log_buffer import log_buffer
from src.utils.query import parse_interval
from src.services.fetcher import refresh_events
from src.core.registry import command

logger = get_logger(__name__)

@command(
    name="poll",
    usage="poll [interval]",
    description=(
        "Repeatedly refresh events at a fixed interval.\n\n"
        "Interval format: <int>[s|m|h|d]\n"
        "(seconds, minutes, hours, days).\n"
        "Example interval values: 30s, 5m, 1h, 2d."
    ),
    category="tasks"
)
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
