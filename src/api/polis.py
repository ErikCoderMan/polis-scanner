from typing import List, Dict, Optional
import time
import requests

from src.core.config import settings
from src.core.logger import get_logger

logger = get_logger(__name__)

EVENT_URL = settings.polis_event_url


# -----------------------------
# Exceptions
# -----------------------------
class PolisAPIError(Exception):
    """Base error for API problems"""


class PolisAPITimeout(PolisAPIError):
    pass


class PolisAPIUnavailable(PolisAPIError):
    pass


# -----------------------------
# Internal request helper
# -----------------------------
def _request(params: Optional[dict] = None) -> List[Dict]:
    try:
        resp = requests.get(
            EVENT_URL,
            params=params,
            timeout=settings.http_timeout_s,
            headers={
                # Important: looks more like a real browser
                "User-Agent": f"{settings.app_name}/{settings.version}",
                "Accept": "application/json",
            },
        )

    except requests.exceptions.Timeout as e:
        raise PolisAPITimeout("Polis API request timed out") from e

    except requests.exceptions.RequestException as e:
        raise PolisAPIUnavailable(f"Network error: {e}") from e

    if resp.status_code == 403:
        raise PolisAPIUnavailable("Blocked by Cloudflare (rate limit)")

    if resp.status_code >= 500:
        raise PolisAPIUnavailable(f"Server error {resp.status_code}")

    if resp.status_code != 200:
        raise PolisAPIError(f"Unexpected status {resp.status_code}")

    try:
        data = resp.json()
    except ValueError as e:
        raise PolisAPIError("Invalid JSON returned from API") from e

    if not isinstance(data, list):
        raise PolisAPIError("Unexpected API format (expected list)")

    return data


# -----------------------------
# Public functions
# -----------------------------
def fetch_events(
    location: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: Optional[int] = None,
    retries: int = 3,
) -> List[Dict]:
    """
    Fetch raw events from Polis API.

    Returns:
        list[dict] raw API objects
    """

    params = {}

    if location:
        params["locationname"] = location

    if event_type:
        params["type"] = event_type

    if limit:
        params["limit"] = limit

    attempt = 0
    backoff = 2

    while attempt < retries:
        try:
            events = _request(params)
            logger.debug(f"Fetched {len(events)} events")
            return events

        except PolisAPITimeout:
            logger.warning("API timeout, retrying...")

        except PolisAPIUnavailable as e:
            logger.warning(f"API unavailable: {e}, retrying...")

        attempt += 1
        time.sleep(backoff)
        backoff *= 2

    raise PolisAPIUnavailable("Failed after multiple retries")
