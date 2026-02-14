from collections import Counter
from typing import Any


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


def score_event(event: dict, words: list[str], fields: list[str]) -> int:
    blob = event_text_blob(event, fields)
    score = 0

    for w in words:
        if w in blob:
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

    if fields is None:
        fields = ["name", "summary", "type", "location.name"]

    # ---- filter stage ----
    if filters:
        filtered = []
        for e in events:
            ok = True
            for f, val in filters.items():
                field_value = normalize_text(get_field(e, f))
                if normalize_text(val) not in field_value:
                    ok = False
                    break

            if ok:
                filtered.append(e)
        events = filtered

    # ---- text search stage ----
    if text:
        words = [normalize_text(w) for w in text.split()]
        scored = []

        for e in events:
            s = score_event(e, words, fields)
            if s > 0:
                scored.append((s, e))

        scored.sort(key=lambda x: x[0], reverse=True)
        events = [e for _, e in scored]

    # ---- group stage (rank) ----
    if group_by:
        counter = Counter()

        for e in events:
            val = normalize_text(get_field(e, group_by))
            if val:
                counter[val] += 1

        result = list(counter.items())

        if sort == "-count" or sort is None:
            result.sort(key=lambda x: x[1], reverse=True)
        else:
            result.sort(key=lambda x: x[0])

        if limit:
            result = result[:limit]

        return result

    # ---- sorting (non-group results) ----
    if sort == "score":
        pass  # already sorted by score
    elif sort == "-datetime":
        events.sort(key=lambda e: normalize_text(get_field(e, "datetime")), reverse=True)

    # ---- limit ----
    if limit:
        events = events[:limit]

    return events
