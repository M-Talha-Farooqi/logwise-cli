from __future__ import annotations

import json
import shlex
from typing import Iterable, Iterator

from logwise.models import LineFormat, LogEntry, MalformedLine, ParseReport
from logwise.parsing.normalizers import normalize_response_time, normalize_status
from logwise.parsing.timestamps import match_leading_timestamp, parse_timestamp

_HTTP_METHODS = {
    "GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS", "TRACE", "CONNECT",
}
# common JSON key aliases -> canonical field
_JSON_KEYS = {
    "timestamp": "timestamp", "time": "timestamp", "ts": "timestamp", "@timestamp": "timestamp",
    "ip": "ip", "client_ip": "ip", "remote_addr": "ip", "src": "ip",
    "method": "method", "verb": "method",
    "path": "path", "url": "path", "uri": "path", "endpoint": "path",
    "status": "status", "status_code": "status", "code": "status",
    "response_time": "rt", "rt": "rt", "latency": "rt", "duration": "rt", "elapsed": "rt",
}


def parse_lines(lines: Iterable[str]) -> ParseReport:
    """Parse an iterable of raw lines into a ParseReport. Streams line-by-line so memory
    stays flat regardless of file size (handles 'a few hundred thousand lines')."""
    report = ParseReport()
    for i, raw in enumerate(lines, start=1):
        report.total_lines += 1
        line = raw.rstrip("\n")
        stripped = line.strip()

        # 1) blank line -> counted, not malformed, not dropped
        if stripped == "":
            report.blank_lines += 1
            continue

        try:
            entry = _parse_one(i, line)
        except Exception as exc:  # noqa: BLE001 — last-resort guard: a line must NEVER crash the run
            report.malformed.append(MalformedLine(i, line, f"unexpected: {exc!s}"))
            report.record_format(LineFormat.MALFORMED)
            continue

        if entry is None:
            report.malformed.append(MalformedLine(i, line, "no strategy matched"))
            report.record_format(LineFormat.MALFORMED)
        else:
            report.entries.append(entry)
            report.record_format(entry.fmt)
    return report


def _parse_one(line_no: int, line: str) -> LogEntry | None:
    stripped = line.strip()
    # 2) JSON strategy — a line clearly bolted on in a different format
    if stripped.startswith("{"):
        entry = _try_json(line_no, stripped)
        if entry is not None:
            return entry
        # fall through: a '{' that isn't valid JSON still gets a chance below
    # 3) standard / salvage strategy
    return _try_standard(line_no, line)


def _try_json(line_no: int, text: str) -> LogEntry | None:
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        return None

    fields: dict[str, object] = {}
    for k, v in obj.items():
        canon = _JSON_KEYS.get(str(k).lower())
        if canon:
            fields[canon] = v

    ts = parse_timestamp(str(fields["timestamp"])) if "timestamp" in fields else None
    status = normalize_status(str(fields["status"])) if "status" in fields else None
    rt = normalize_response_time(str(fields["rt"])) if "rt" in fields else None

    entry = LogEntry(
        line_no=line_no, raw=text, fmt=LineFormat.JSON,
        timestamp=ts,
        ip=str(fields["ip"]) if "ip" in fields else None,
        method=str(fields["method"]).upper() if "method" in fields else None,
        path=str(fields["path"]) if "path" in fields else None,
        status=status, response_ms=rt,
    )
    _record_missing(entry)
    return entry


def _try_standard(line_no: int, line: str) -> LogEntry | None:
    """Canonical shape:  <timestamp> <ip> <method> <path> <status> <rt> [extras...]

    Approach:
      a) consume the leading timestamp first (it may contain a space)
      b) tokenize the rest with shlex so quoted referrers/user-agents stay intact
      c) map tokens positionally, defending against missing/extra fields
    """
    ts, remainder = match_leading_timestamp(line)

    # tokenize quote-aware; if shlex chokes on unbalanced quotes, fall back to split()
    try:
        tokens = shlex.split(remainder)
    except ValueError:
        tokens = remainder.split()

    # If we have neither a timestamp nor enough tokens, it's not the standard shape.
    if ts is None and len(tokens) < 4:
        return None

    ip = method = path = None
    status = rt = None
    idx = 0

    # ip: first token that looks like an address (contains '.' or ':') — but if the next
    # token is an HTTP method we assume position 0 is the IP regardless.
    if tokens:
        ip = tokens[idx]; idx += 1
    # method
    if idx < len(tokens) and tokens[idx].upper() in _HTTP_METHODS:
        method = tokens[idx].upper(); idx += 1
    # path
    if idx < len(tokens):
        path = tokens[idx]; idx += 1
    # status
    if idx < len(tokens):
        status = normalize_status(tokens[idx]); idx += 1
    # response time
    if idx < len(tokens):
        rt = normalize_response_time(tokens[idx]); idx += 1
    # anything left over = extra appended fields (user agent, referrer). Keep as a note,
    # do NOT discard — but don't let it derail the core fields.
    extras = tokens[idx:]

    # Decide format: full standard vs salvaged (some core fields missing)
    fmt = LineFormat.STANDARD if (ts and method and status is not None) else LineFormat.SALVAGED

    # If literally nothing useful came out, treat as malformed (return None).
    core_present = [x for x in (ts, method, status) if x is not None]
    if not core_present and ip is None and path is None:
        return None

    entry = LogEntry(
        line_no=line_no, raw=line, fmt=fmt,
        timestamp=ts, ip=ip, method=method, path=path,
        status=status, response_ms=rt,
        notes=([f"extra fields: {' '.join(extras)}"] if extras else []),
    )
    _record_missing(entry)
    return entry


def _record_missing(entry: LogEntry) -> None:
    for name in ("timestamp", "ip", "method", "path", "status", "response_ms"):
        if getattr(entry, name) is None:
            entry.missing_fields.append(name)


def stream_file(path) -> Iterator[str]:
    """Yield lines from a file path, decoding leniently so a stray non-UTF-8 byte
    (partial write) doesn't kill the run."""
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        yield from fh
