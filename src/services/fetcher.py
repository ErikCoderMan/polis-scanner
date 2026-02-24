from typing import List, Dict
from pathlib import Path
import json

from src.api.polis import fetch_events, PolisAPIError
from src.core.config import settings
from src.core.logger import get_logger

logger = get_logger(__name__)

STATE_FILE = settings.cache_dir / "last_event.json"
DATA_FILE = settings.data_dir / "events.json"


def load_events(data_file: Path = DATA_FILE) -> List[Dict]:
    """Load all saved events from data_file, safely handling missing/empty/invalid JSON"""

    if not data_file.exists() or data_file.stat().st_size == 0:
        return []

    try:
        with data_file.open("r", encoding="utf-8") as f:
            events = json.load(f)
            if not isinstance(events, list):
                return []

            logger.debug(f"Loaded {len(events)} events from {data_file}")
            return events

    except json.JSONDecodeError:
        logger.warning(f"{data_file} is empty or corrupt, starting fresh")
        return []


def save_events(old_events: List[Dict], new_events: List[Dict], data_file: Path = DATA_FILE) -> None:
    """Merge old and new events (unique by id) and save to data_file"""

    seen_ids = {e.get("id") for e in old_events if "id" in e}
    unique_new = [e for e in new_events if e.get("id") not in seen_ids]

    merged_events = old_events + unique_new
    merged_events = sorted(merged_events, key=lambda e: e["id"], reverse=True)

    data_file.parent.mkdir(parents=True, exist_ok=True)
    with data_file.open("w", encoding="utf-8") as f:
        json.dump(merged_events, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved {len(unique_new)} new and {len(merged_events)} total events to {data_file}")


def update_last_event(newest_event: Dict, state_file: Path = STATE_FILE) -> bool:
    """Return True if newest_event is different than last saved, and update state_file"""

    last_event = None
    if state_file.exists() and state_file.stat().st_size > 0:
        try:
            with state_file.open("r", encoding="utf-8") as f:
                last_event = json.load(f)

        except json.JSONDecodeError:
            logger.warning(f"{state_file} empty or corrupt, overwriting")

    if last_event and newest_event["id"] == last_event.get("id"):
        logger.debug(f"No new events, last id: {newest_event['id']}")
        return False

    state_file.parent.mkdir(parents=True, exist_ok=True)
    with state_file.open("w", encoding="utf-8") as f:
        json.dump(newest_event, f, indent=2, ensure_ascii=False)

    return True


# -----------------------------
# Refresh events
# -----------------------------
async def refresh_events(
    data_file: Path = DATA_FILE,
    state_file: Path = STATE_FILE
) -> List[Dict]:
    """Fetch, compare, and save new events. Returns list of new events."""

    try:
        events = await fetch_events()

    except PolisAPIError:
        logger.exception("Failed to refresh events from Polis API")
        raise

    if not events:
        return []

    events = sorted(events, key=lambda e: e["id"], reverse=True)
    newest_event = events[0]

    if not update_last_event(newest_event, state_file):
        return []

    old_events = load_events(data_file)
    seen_ids = {e.get("id") for e in old_events if "id" in e}
    new_events = [e for e in events if e.get("id") not in seen_ids]
    new_events = sorted(new_events, key=lambda e: e['id'], reverse=True)

    for e in new_events:
        logger.debug(
            f"New event: {e}"
        )

    if new_events:
        save_events(old_events, new_events, data_file)

    return new_events
