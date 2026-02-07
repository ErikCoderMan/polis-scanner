import requests
import time
from src.core.config import settings
from src.core.logger import get_logger

logger = get_logger(__name__)

def fetch_instant(query: str) -> dict:
    url = settings.duck_instant_url
    params = {
        "q": query,
        "format": "json",
        "no_html": 1,
        "skip_disambig": 1,
    }

    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    logger.info(f"Fetched {len(data)} elements")
    
    
    
    return data
