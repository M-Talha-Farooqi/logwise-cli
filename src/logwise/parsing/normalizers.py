from __future__ import annotations

import re

_RT_PATTERN = re.compile(r"^([0-9]*\.?[0-9]+)\s*(ms|s)?$", re.IGNORECASE)


def normalize_response_time(token: str | None) -> float | None:
    """Normalize a response-time token to milliseconds.

    '142ms'  -> 142.0
    '0.142s' -> 142.0
    '142'    -> 142.0   (bare number assumed to be ms, the dominant convention here)
    '-' / '' / junk -> None
    """
    if token is None:
        return None
    token = token.strip()
    if token in ("", "-"):
        return None
    m = _RT_PATTERN.match(token)
    if not m:
        return None
    value = float(m.group(1))
    unit = (m.group(2) or "ms").lower()
    return value * 1000.0 if unit == "s" else value


def normalize_status(token: str | None) -> int | None:
    """Normalize an HTTP status token to an int, or None if missing/'-'/invalid.

    Accepts only plausible HTTP codes (100-599). Anything else -> None, so a stray field
    never masquerades as a status.
    """
    if token is None:
        return None
    token = token.strip()
    if token in ("", "-"):
        return None
    if not token.isdigit():
        return None
    code = int(token)
    return code if 100 <= code <= 599 else None
