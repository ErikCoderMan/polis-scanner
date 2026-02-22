from collections import Counter
from typing import Any
import re

from src.core.logger import get_logger

logger = get_logger(__name__)

# ----------------------------
# parse
# ----------------------------

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

        if sort == "-count" or not sort:
            result.sort(key=lambda x: x["count"], reverse=True)

        elif sort == "-score":
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

    if sort == "-datetime":
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
