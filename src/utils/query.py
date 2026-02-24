from collections import Counter
from typing import Any
import re

from src.core.logger import get_logger
from src.core.config import settings

logger = get_logger(__name__)

# ----------------------------
# parse
# ----------------------------

# f.e used by poll cmd
def parse_interval(args: list[str] | str) -> dict:
    args = " ".join([arg for arg in args]) if isinstance(args, list) else args
    args = args.lower().strip()
    
    multipliers = {
        "s": 1,
        "m": 60,
        "h": 3600,
        "d": 86400,
    }
    
    # ---- dict to return ----
    result = {
        "toggle": None,
        "interval_s": None,
        "interval_str": None
    }
    
    # ---- parse toggle ----
    
    if any(a in args for a in ("start", "on")) and not any(a in args for a in ("stop", "off")):
        result['toggle'] = "start"
    
    elif any(a in args for a in ("stop", "off")) and not any(a in args for a in ("start", "on")):
        result["toggle"] = "stop"
        return result
    
    else:
        return result
    
    # ---- parse interval ----
    
    try:
        match_arg = re.search(r"(\d+)([smhd])", args)
        if match_arg:
            number = int(match_arg.group(1))
            unit = match_arg.group(2)
            logger.debug(f"Poll interval set from cmd argument (cmd arg overrides config settings)")
        
        else:
            interval_str = settings.poll_interval if settings.poll_interval else "5m" # extra fallback
            match_conf = re.search(r"(\d+)([smhd])", interval_str)
            if match_conf:
                number = int(match_conf.group(1))
                unit = match_conf.group(2)
                logger.debug(f"Poll interval set from config settings (can be overridden with cmd argument)")
    
    except ValueError:
        logger.error("Error while parsing interval value, probably caused by invalid value either from cmd arg or config")
        raise

    if unit not in multipliers:
        raise ValueError("Invalid interval format. Use s, m, h, or d.")
    
    seconds = number * multipliers[unit]
    result["interval_str"] = f"{number}{unit}" if number and unit else None
    result["interval_s"] = seconds
    
    logger.debug(f"Poll interval set to '{result['interval_str']}'")

    # ---- verify interval value ----

    if seconds <= 10:
        match = re.search(r"--force\s+(.*?)(?=\s+--\w+|$)", args)
        force = match.group(1).lower().strip() if match else None
        force = isinstance(force, str) and force.lower() == "true"
        
        if not force:
            raise ValueError("Polling interval too small, minimum is '10s' but recommended minimum is '60s' \n(however you can bypass minimum limit by adding '--force True' as argument altough it is not recommended)")
        
        else:
            logger.info(
                "Setting polling interval below the recommended minimum using --force. "
                "Use at your own risk; this may lead to rate limiting or blocking."
            )

    elif seconds < 60:
        logger.warning("Polling interval under 60 seconds works but is not recommended")
        
        
    return result


# f.e used by find, search and rank cmds
def parse_query(args: list[str] | str) -> dict:
    args = " ".join([arg for arg in args]) if isinstance(args, list) else args
    if not args:
        return
        
    text = ""
    fields =  []
    filters =  {}
    group_by = ""
    limit = 0
    sort = ""
    
    match = re.search(r"--text\s+(.*?)(?=\s+--\w+|$)", args)
    text = match.group(1) if match else None
    
    match = re.search(r"--fields\s+(.*?)(?=\s+--\w+|$)", args)
    fields = match.group(1).split() if match else None
    
    match = re.search(r"--filters\s+(.*?)(?=\s+--\w+|$)", args)
    filters = match.group(1).split() if match else None
    filters = dict(zip(filters[::2], filters[1::2])) if filters else None
    
    match = re.search(r"--group\s+(.*?)(?=\s+--\w+|$)", args)
    group_by = match.group(1) if match else None
    
    match = re.search(r"--limit\s+(.*?)(?=\s+--\w+|$)", args)
    limit = match.group(1) if match else None
    
    match = re.search(r"--sort\s+(.*?)(?=\s+--\w+|$)", args)
    sort = match.group(1) if match else None
    
    
    if limit:
        try:
            limit = int(limit)
    
        except ValueError:
            logger.error("limit has to be integer")
            raise
    
    result = {
        "text": text,
        "fields": fields if fields else "all",
        "filters": filters,
        "group": group_by,
        "limit": limit,
        "sort": sort
    }
    
    return result


# ----------------------------
# helpers
# ----------------------------

def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).lower().strip()


def get_field(event: dict, field: str):
    """
    Supports dot notation: location.name
    """
    parts = field.split(".")
    value = event

    for part in parts:
        if not isinstance(value, dict):
            return None
        value = value.get(part)

    return value


def event_text_blob(event: dict, fields: list[str]) -> str:
    values = []
    for f in fields:
        v = get_field(event, f)
        if v is not None:
            values.append(normalize_text(v))
    return " ".join(values)


def score_query_event(event, query, fields):
    score = 0

    # Text scoring
    if query.get("text"):
        blob = event_text_blob(event, fields)
        words = normalize_text(query["text"]).split()

        for w in words:
            if w in blob:
                score += 1

    # Filter soft bonus scoring (optional)
    if query.get("filters"):
        for f, val in query["filters"].items():
            field_value = normalize_text(get_field(event, f))

            if normalize_text(val) in field_value:
                score += 1

    return score


# ----------------------------
# query engine
# ----------------------------

def query_events(
    events: list[dict],
    *,
    text: str | None = None,
    fields: list[str] | None = None,
    filters: dict[str, str] | None = None,
    group_by: str | None = None,
    sort: str | None = None,
    limit: int | None = None,
) -> list:

    if all(v is None for v in (text, filters, group_by, sort)):
        logger.error("no search parameters provided")
        return []

    if not fields or fields == "all":
        fields = ["name", "summary", "type", "location.name"]

    # ----------------------------
    # Candidate filtering stage (hard filter)
    # ----------------------------

    filtered = []

    for e in events:
        ok = True

        if filters:
            for f, val in filters.items():
                field_value = normalize_text(get_field(e, f))

                if normalize_text(val) not in field_value:
                    ok = False
                    break

        if ok:
            filtered.append(e)

    events = filtered
    
    # ----------------------------
    # Text candidate filtering (hard constraint)
    # ----------------------------

    if text:
        words = normalize_text(text).split()
        filtered = []

        for e in events:
            blob = event_text_blob(e, fields)

            if all(w in blob for w in words):
                filtered.append(e)

        events = filtered
    
    # ----------------------------
    # Group stage (rank mode)
    # ----------------------------

    if group_by:
        groups = {}

        for e in events:
            key = normalize_text(get_field(e, group_by))
            if not key:
                continue

            if key not in groups:
                groups[key] = {
                    "count": 0,
                    "score_sum": 0
                }

            # Beräkna score om text finns
            query_obj = {
                "text": text,
                "filters": filters or {}
            }

            score = score_query_event(e, query_obj, fields)

            groups[key]["count"] += 1
            groups[key]["score_sum"] += score

        result = []

        for k, v in groups.items():
            avg_score = v["score_sum"] / v["count"] if v["count"] > 0 else 0

            result.append({
                "group": k,
                "count": v["count"],
                "avg_score": round(avg_score, 3)
            })

        # ----------------------------
        # Sorting (rank mode)
        # ----------------------------

        if sort == "count" or not sort:
            result.sort(key=lambda x: x["count"], reverse=True)

        elif sort == "score":
            result.sort(key=lambda x: x["avg_score"], reverse=True)

        elif sort == "group":
            result.sort(key=lambda x: x["group"])

        if limit:
            result = result[:limit]

        return result

    # ----------------------------
    # Unified scoring stage
    # ----------------------------

    scored_events = []

    query_obj = {
        "text": text,
        "filters": filters or {}
    }

    for e in events:
        score = score_query_event(e, query_obj, fields)

        if score > 0:
            event_copy = dict(e)
            event_copy["score"] = score
            scored_events.append(event_copy)

    # Sort by score (primary ranking signal)
    scored_events.sort(key=lambda x: x["score"], reverse=True)

    events = scored_events
    

    # ----------------------------
    # Sorting stage (non-group)
    # ----------------------------

    if sort == "datetime":
        events.sort(
            key=lambda e: normalize_text(get_field(e, "datetime")),
            reverse=True
        )

    # ----------------------------
    # Limit stage
    # ----------------------------

    if limit:
        events = events[:limit]

    return events
