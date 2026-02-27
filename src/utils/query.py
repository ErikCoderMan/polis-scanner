from typing import Any
import re

from src.core.logger import get_logger
from src.core.config import settings

logger = get_logger(__name__)


# ==========================================================
# PARSE
# ==========================================================

def parse_interval(args: list[str] | str) -> dict:
    args = " ".join(args) if isinstance(args, list) else args
    args = args.lower().strip()

    multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}

    result = {
        "toggle": None,
        "interval_s": None,
        "interval_str": None,
    }

    if any(a in args for a in ("start", "on")) and not any(a in args for a in ("stop", "off")):
        result["toggle"] = "start"
        
    elif any(a in args for a in ("stop", "off")) and not any(a in args for a in ("start", "on")):
        result["toggle"] = "stop"
        return result
        
    else:
        return result

    match = re.search(r"(\d+)([smhd])", args)

    if not match:
        interval_str = settings.poll_interval or "5m"
        match = re.search(r"(\d+)([smhd])", interval_str)

    if not match:
        raise ValueError("Invalid interval format")

    number = int(match.group(1))
    unit = match.group(2)

    seconds = number * multipliers[unit]
    
    # if seconds is lower then recomended limit
    if settings.poll_interval_lowest_allowed_s < seconds < settings.poll_interval_lowest_recomended_s:
        logger.warning(f"Interval is lower then {settings.poll_interval_lowest_recomended_s}s, it works but is not recomended for very long periods")
    
    # if seconds is lower then allowed limit
    elif seconds < settings.poll_interval_lowest_allowed_s:
        if not "--force" in args:
            logger.error(f"Can not set interval value below allowed minimum value of '{settings.poll_interval_lowest_allowed_s}s', if you are sure, bypass with '--force' altough it is not recomended")
            return # early return to prevent poll start
        
        # runs only with '--force'
        else:
            logger.warning(f"Interval set to {seconds}s with '--force', it is below minimum allowed value of '{settings.poll_interval_lowest_allowed_s}s' it is not adviced to poll this frequently")

    result["interval_str"] = f"{number}{unit}"
    result["interval_s"] = seconds

    return result


def parse_query(args: list[str] | str) -> dict:
    args = " ".join(args) if isinstance(args, list) else args
    if not args:
        return {}

    def extract(flag):
        match = re.search(rf"{flag}\s+(.*?)(?=\s+--\w+|$)", args)
        return match.group(1).lower().strip() if match else None

    text = extract("--text")
    fields = extract("--fields")
    filters = extract("--filters")
    group_by = extract("--group")
    limit = extract("--limit")
    sort = extract("--sort")
    strict = extract("--strict")

    fields = fields.split() if fields else None

    if filters:
        parts = filters.split()
        filters = dict(zip(parts[::2], parts[1::2]))
        
    else:
        filters = None

    sort = sort.split() if sort else None

    if limit:
        limit = int(limit)

    if strict and strict == "true":
        strict = True
    
    elif strict and strict == "false":
        strict = False
    
    else:
        strict = True # default strict

    return {
        "text": text,
        "fields": fields or "all",
        "filters": filters,
        "group": group_by,
        "limit": limit,
        "sort": sort,
        "strict": strict
    }


# ==========================================================
# HELPERS
# ==========================================================

def normalize_text(value: Any) -> str:
    if value is None:
        return ""
        
    return str(value).lower().strip()


def get_field(event: dict, field: str):
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


def score_query_event(event, text, filters, fields):
    score = 0

    if text:
        blob = event_text_blob(event, fields)
        words = normalize_text(text).split()
        
        for w in words:
            if w in blob:
                score += 1

    if filters:
        for f, val in filters.items():
            field_value = normalize_text(get_field(event, f))
            
            if normalize_text(val) in field_value:
                score += 1

    return score


# ==========================================================
# QUERY ENGINE
# ==========================================================

def query_events(
    events: list[dict],
    *,
    text: str | None = None,
    fields: list[str] | None = None,
    filters: dict[str, str] | None = None,
    group_by: str | None = None,
    sort: list[str] | None = None,
    limit: int | None = None,
    strict: bool = True,
) -> list:

    if not fields or fields == "all":
        fields = ["name", "summary", "type", "location.name"]

    # ------------------------------------------------------
    # HARD FILTERING
    # ------------------------------------------------------
    if strict:
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

        if text:
            words = normalize_text(text).split()
            filtered = []

            for e in events:
                blob = event_text_blob(e, fields)
                
                if all(w in blob for w in words):
                    filtered.append(e)

            events = filtered

    # ------------------------------------------------------
    # GROUP MODE
    # ------------------------------------------------------

    if group_by:
        groups = {}

        for e in events:
            key = normalize_text(get_field(e, group_by))
            if not key:
                continue

            if key not in groups:
                groups[key] = {"count": 0, "score_sum": 0}

            score = score_query_event(e, text, filters, fields)

            groups[key]["count"] += 1
            groups[key]["score_sum"] += score

        result = []

        for k, v in groups.items():
            avg_score = v["score_sum"] / v["count"] if v["count"] else 0
            result.append({
                "group": k,
                "count": v["count"],
                "avg_score": round(avg_score, 3),
            })

        if sort:
            def group_sort_key(row):
                values = []
                
                for field in sort:
                    values.append(row.get(field))
                    
                return tuple(values)

            result.sort(key=group_sort_key, reverse=True)
            
        else:
            
            result.sort(key=lambda x: (-x["avg_score"], -x["count"], x["group"]))

        return result[:limit] if limit else result

    # ------------------------------------------------------
    # EVENT MODE
    # ------------------------------------------------------

    if not strict:
        scored = []
        for e in events:
            score = score_query_event(e, text, filters, fields)
            if not score:
                continue # ignore events without any match score
                
            event_copy = dict(e)
            event_copy["score"] = score
            scored.append(event_copy)
            
        events = scored
        
    else:
        non_scored = []
        for e in events:
            event_copy = dict(e)
            event_copy["score"] = 0
            non_scored.append(event_copy)
            
        events = non_scored

    if sort:
        def event_sort_key(event):
            values = []
            for field in sort:
                if field == "score":
                    values.append(event.get("score", 0))
                    
                else:
                    values.append(get_field(event, field))
                    
            return tuple(values)

        events.sort(key=event_sort_key, reverse=True)
        
    else:
        events.sort(key=lambda e: (e.get("score", 0), get_field(e, "datetime")), reverse=True)

    return events[:limit] if limit else events
    
    
