from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class LineFormat(str, Enum):
    """Which strategy successfully parsed a line. Used for anomaly reporting."""
    STANDARD = "standard"          # the canonical space-delimited shape
    JSON = "json"                  # JSON-formatted line bolted on
    SALVAGED = "salvaged"          # partial parse: some fields recovered, some missing
    MALFORMED = "malformed"        # nothing usable


@dataclass(slots=True)
class LogEntry:
    """One successfully (or partially) parsed log line.

    Every field except `raw` and `line_no` is Optional, because the doc explicitly says
    fields go missing. A missing field is NEVER an error — it's recorded as None and the
    line still counts.
    """
    line_no: int
    raw: str
    fmt: LineFormat
    timestamp: datetime | None = None          # always normalized to UTC
    ip: str | None = None
    method: str | None = None
    path: str | None = None
    status: int | None = None
    response_ms: float | None = None           # ALWAYS normalized to milliseconds
    # which fields we could not recover, for the anomaly report
    missing_fields: list[str] = field(default_factory=list)
    # original tokens we couldn't classify (e.g., unexpected extra fields)
    notes: list[str] = field(default_factory=list)

    @property
    def is_error(self) -> bool:
        return self.status is not None and self.status >= 400

    @property
    def is_server_error(self) -> bool:
        return self.status is not None and 500 <= self.status < 600


@dataclass(slots=True)
class MalformedLine:
    """A line we could not parse at all. Kept (not dropped) so we can count and surface it."""
    line_no: int
    raw: str
    reason: str


@dataclass(slots=True)
class ParseReport:
    """Accounts for every input line. Returned by the parser to the analyzer."""
    entries: list[LogEntry] = field(default_factory=list)
    malformed: list[MalformedLine] = field(default_factory=list)
    total_lines: int = 0
    blank_lines: int = 0

    # counts of each format seen, for the "format anomaly" surface
    format_counts: dict[str, int] = field(default_factory=dict)

    def record_format(self, fmt: LineFormat) -> None:
        self.format_counts[fmt.value] = self.format_counts.get(fmt.value, 0) + 1

    @property
    def parsed_count(self) -> int:
        return len(self.entries)

    @property
    def malformed_count(self) -> int:
        return len(self.malformed)

    @property
    def malformed_pct(self) -> float:
        if self.total_lines == 0:
            return 0.0
        return 100.0 * self.malformed_count / self.total_lines
