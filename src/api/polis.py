from typing import List, Dict, Optional
import time
import requests

from src.core.config import settings
from src.core.logger import get_logger

logger = get_logger(__name__)

EVENT_URL = settings.polis_event_url


# -----------------------------
# Exceptions (domain errors)
# -----------------------------
class PolisAPIError(Exception):
    """Permanent API error (bad response, unexpected data)"""


class PolisAPITimeout(PolisAPIError):
    """Retryable: request took too long"""


class PolisAPIUnavailable(PolisAPIError):
    """Retryable: server/network/rate limit problem"""


# -----------------------------
# HTTP -> Domain translation
# -----------------------------
def _translate_http_error(resp: requests.Response, err: Exception) -> None:
    status = resp.status_code

    # Retryable
    if status == 403:
        raise PolisAPIUnavailable("Blocked / rate limited by Polis API") from err

    if status == 429:
        raise PolisAPIUnavailable("Too many requests") from err

    if 500 <= status < 600:
        raise PolisAPIUnavailable(f"Server error {status}") from err

    # Permanent
    raise PolisAPIError(f"Unexpected HTTP status {status}") from err


def _request(params: Optional[dict] = None) -> List[Dict]:
    try:
        resp = requests.get(
            EVENT_URL,
            params=params,
            timeout=settings.http_timeout_s,
            headers={
                "User-Agent": f"{settings.app_name}/{settings.version}",
                "Accept": "application/json",
            },
        )

        try:
            resp.raise_for_status()
        except requests.HTTPError as e:
            _translate_http_error(resp, e)

    except requests.Timeout as e:
        raise PolisAPITimeout("Polis API request timed out") from e

    except requests.RequestException as e:
        # DNS failure, connection reset, TLS, etc
        raise PolisAPIUnavailable(f"Network error: {e}") from e

    # -------- Response validation --------
    try:
        data = resp.json()
    except ValueError as e:
        raise PolisAPIError("Invalid JSON returned from API") from e

    if not isinstance(data, list):
        raise PolisAPIError("Unexpected API format (expected list)")

    return data


# -----------------------------
# Public API
# -----------------------------
def fetch_events(
    location: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: Optional[int] = None,
    retries: int = 3,
) -> List[Dict]:

    params = {}

    if location:
        params["locationname"] = location
    if event_type:
        params["type"] = event_type
    if limit:
        params["limit"] = limit

    attempt = 0
    backoff = 2

    while True:
        try:
            events = _request(params)
            logger.debug(f"Fetched {len(events)} events")
            return events

        except (PolisAPITimeout, PolisAPIUnavailable) as e:
            attempt += 1

            if attempt >= retries:
                raise PolisAPIUnavailable("Failed after multiple retries") from e

            logger.warning(
                f"API retry {attempt}/{retries}: {e} — sleeping {backoff}s"
            )
            time.sleep(backoff)
            backoff *= 2
