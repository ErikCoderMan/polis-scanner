import time

from src.core.config import settings
from src.core.logger import get_logger
from src.services.fetcher import refresh_events

logger = get_logger(__name__)

def run_cli():
    logger.info("Starting CLI")
    logger.info(f"Data dir: {settings.data_dir}")
    
    try:
        logger.info("Refreshing events")
        events = refresh_events()
        
        if not events:
            logger.info("No new events")
            return
        
        for event in events:
            logger.info(f"{event['id']} - {event['datetime']} - {event['name']} - {event['summary']}")
    
    except KeyboardInterrupt:
        logger.info("Shutting down...")
