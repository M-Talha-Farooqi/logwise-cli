from __future__ import annotations

import re
from datetime import datetime, timezone

# Ordered list of (regex anchored at start, strptime format). Most specific first.
# Each pattern captures the timestamp text in group 1 so the parser can also know how
# many characters to consume from the front of the line.
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # 2024-03-15T14:23:01Z  or  2024-03-15T14:23:01+00:00  (ISO-8601)
    (re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)"), "ISO"),
    # 2024/03/15 14:23:01
    (re.compile(r"^(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})"), "%Y/%m/%d %H:%M:%S"),
    # 15-Mar-2024 14:23:01
    (re.compile(r"^(\d{2}-[A-Za-z]{3}-\d{4} \d{2}:\d{2}:\d{2})"), "%d-%b-%Y %H:%M:%S"),
    # bare unix epoch (10 digits = seconds, 13 = millis), as the leading token
    (re.compile(r"^(\d{10,13})\b"), "EPOCH"),
]


def match_leading_timestamp(line: str) -> tuple[datetime | None, str]:
    """Try to read a timestamp off the FRONT of a line.

    Returns (parsed_dt_or_None, remainder_of_line_after_the_timestamp).
    If nothing matches, returns (None, original_line).

    We match at the front (not anywhere) because a timestamp may itself contain a space
    (e.g. '2024/03/15 14:23:01'), which would break naive whitespace splitting. By
    consuming the timestamp first, the rest of the line splits cleanly.
    """
    for pattern, kind in _PATTERNS:
        m = pattern.match(line)
        if not m:
            continue
        text = m.group(1)
        dt = _to_utc(text, kind)
        if dt is not None:
            return dt, line[m.end():].lstrip()
    return None, line


def parse_timestamp(text: str) -> datetime | None:
    """Parse a standalone timestamp string (used by the JSON strategy)."""
    text = text.strip()
    for pattern, kind in _PATTERNS:
        if pattern.match(text):
            dt = _to_utc(text, kind)
            if dt is not None:
                return dt
    return None


def _to_utc(text: str, kind: str) -> datetime | None:
    try:
        if kind == "ISO":
            # datetime.fromisoformat handles offsets; normalize trailing 'Z'.
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        elif kind == "EPOCH":
            num = int(text)
            if len(text) == 13:      # milliseconds
                num /= 1000
            dt = datetime.fromtimestamp(num, tz=timezone.utc)
        else:
            dt = datetime.strptime(text, kind)
    except (ValueError, OverflowError, OSError):
        return None
    # If no tzinfo (naive), assume UTC so comparisons are safe.
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
