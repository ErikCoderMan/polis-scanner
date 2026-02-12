import time

from src.core.config import settings
from src.core.logger import get_logger
from src.services.fetcher import refresh_events
from src.api.polis import PolisAPIError

logger = get_logger(__name__)

def run_cli():
    logger.info("Starting CLI")
    logger.info(f"Data dir: {settings.data_dir}")

    try:
        logger.info("Refreshing events")
        events = refresh_events()

        if not events:
            logger.info("No new events")
            return 0

        for event in events:
            logger.info(f"{event['id']} - {event['datetime']} - {event['name']} - {event['summary']}")

        return 0

    except PolisAPIError:
        logger.error("Could not update events (API failure)")
        return 1

    except KeyboardInterrupt:
        logger.info("Shutting down...")
        return 130

