"""Small, framework-independent helpers for responsive table column sizing."""

import unicodedata


def text_width_units(value):
    """Approximate rendered text width without depending on a browser or font engine."""
    text = "" if value is None else str(value)
    units = 0
    for char in text:
        if unicodedata.category(char).startswith("M"):
            continue
        units += 2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1
    return units


def estimate_column_width(
    header,
    values=(),
    *,
    min_width=88,
    max_width=280,
    pixels_per_unit=8,
    padding=32,
):
    """Estimate a bounded pixel width from the header and displayed cell values."""
    if min_width <= 0 or max_width < min_width:
        raise ValueError("column width bounds must satisfy 0 < min_width <= max_width")

    candidates = [header, *values]
    widest_units = max((text_width_units(value) for value in candidates), default=0)
    estimated = int(round(widest_units * pixels_per_unit + padding))
    return max(min_width, min(max_width, estimated))
