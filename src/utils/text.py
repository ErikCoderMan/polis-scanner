from collections.abc import Mapping, Iterable

def extract_strings(obj):
    if isinstance(obj, str):
        yield obj

    elif isinstance(obj, Mapping):  # dict
        for value in obj.values():
            yield from extract_strings(value)

    elif isinstance(obj, Iterable) and not isinstance(obj, (str, bytes)):
        for item in obj:
            yield from extract_strings(item)
