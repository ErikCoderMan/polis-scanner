import time

from src.api.duck import fetch_instant
from src.core.logger import get_logger
from src.utils.text import extract_strings

logger = get_logger(__name__)

def lookup(events: list[dict]) -> list[dict]:
    result = []
    for event in events:
        logger.debug(f"looking up area of event: {event.get('id')}")
        ddg_instant = "".join(list(extract_strings(fetch_instant(f"{event['location']['name']}"))))
        
        info = {
            "event_id": event.get('id'),
            "ddg_instant": ddg_instant
        }
        
        result.append(info)
        time.sleep(1)
    
    return result
