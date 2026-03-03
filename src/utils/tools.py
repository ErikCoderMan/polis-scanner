def flatten_dict(data, parent_key="", sep="."):
    """
    Utility functions for transforming and traversing nested data structures.
    Includes helpers for flattening deeply nested dictionaries
    into dot-notation key paths.
    """
    
    flat = {}

    if isinstance(data, dict):
        for key, value in data.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else str(key)
            flat.update(flatten_dict(value, new_key, sep))

    elif isinstance(data, list):
        for index, value in enumerate(data):
            new_key = f"{parent_key}{sep}{index}" if parent_key else str(index)
            flat.update(flatten_dict(value, new_key, sep))

    else:
        if parent_key:
            flat[parent_key] = data

    return flat
