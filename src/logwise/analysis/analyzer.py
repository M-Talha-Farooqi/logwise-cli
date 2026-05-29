from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field

from logwise.models import ParseReport


@dataclass(slots=True)
class EndpointStat:
    path: str
    count: int
    avg_ms: float | None
    p95_ms: float | None
    max_ms: float | None
    error_count: int
    server_error_count: int


@dataclass(slots=True)
class Analysis:
    # health
    total_lines: int
    parsed: int
    malformed: int
    malformed_pct: float
    blank: int
    format_counts: dict[str, int]
    # request stats
    status_classes: dict[str, int]          # '2xx','3xx','4xx','5xx','unknown'
    error_rate_pct: float
    time_min: str | None
    time_max: str | None
    slowest: list[EndpointStat] = field(default_factory=list)
    top_errors: list[EndpointStat] = field(default_factory=list)
    busiest: list[EndpointStat] = field(default_factory=list)
    top_ips: list[tuple[str, int]] = field(default_factory=list)
    # the honesty layer
    sample_malformed: list[tuple[int, str]] = field(default_factory=list)


def _percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    s = sorted(values)
    k = max(0, min(len(s) - 1, int(round((pct / 100.0) * (len(s) - 1)))))
    return s[k]


def analyze(report: ParseReport, top: int = 10) -> Analysis:
    entries = report.entries

    # ---- status classes + error rate ----
    classes = {"2xx": 0, "3xx": 0, "4xx": 0, "5xx": 0, "unknown": 0}
    counted = 0
    errors = 0
    for e in entries:
        if e.status is None:
            classes["unknown"] += 1
            continue
        counted += 1
        bucket = f"{e.status // 100}xx"
        if bucket in classes:
            classes[bucket] += 1
        else:
            classes["unknown"] += 1
        if e.status >= 400:
            errors += 1
    error_rate = (100.0 * errors / counted) if counted else 0.0

    # ---- per-endpoint aggregation ----
    by_path_times: dict[str, list[float]] = defaultdict(list)
    by_path_count: Counter[str] = Counter()
    by_path_err: Counter[str] = Counter()
    by_path_5xx: Counter[str] = Counter()
    ip_counter: Counter[str] = Counter()
    timestamps = []

    for e in entries:
        key = e.path or "<no-path>"
        by_path_count[key] += 1
        if e.response_ms is not None:
            by_path_times[key].append(e.response_ms)
        if e.is_error:
            by_path_err[key] += 1
        if e.is_server_error:
            by_path_5xx[key] += 1
        if e.ip:
            ip_counter[e.ip] += 1
        if e.timestamp:
            timestamps.append(e.timestamp)

    def build_stat(path: str) -> EndpointStat:
        times = by_path_times.get(path, [])
        return EndpointStat(
            path=path,
            count=by_path_count[path],
            avg_ms=(sum(times) / len(times)) if times else None,
            p95_ms=_percentile(times, 95),
            max_ms=max(times) if times else None,
            error_count=by_path_err.get(path, 0),
            server_error_count=by_path_5xx.get(path, 0),
        )

    # slowest = by p95 (fall back to avg), only endpoints that have timing data
    timed_paths = [p for p in by_path_count if by_path_times.get(p)]
    slowest = sorted(
        (build_stat(p) for p in timed_paths),
        key=lambda s: (s.p95_ms or s.avg_ms or 0.0),
        reverse=True,
    )[:top]

    top_errors = sorted(
        (build_stat(p) for p in by_path_err),
        key=lambda s: (s.server_error_count, s.error_count),
        reverse=True,
    )[:top]

    busiest = sorted(
        (build_stat(p) for p in by_path_count),
        key=lambda s: s.count, reverse=True,
    )[:top]

    return Analysis(
        total_lines=report.total_lines,
        parsed=report.parsed_count,
        malformed=report.malformed_count,
        malformed_pct=report.malformed_pct,
        blank=report.blank_lines,
        format_counts=dict(report.format_counts),
        status_classes=classes,
        error_rate_pct=error_rate,
        time_min=min(timestamps).isoformat() if timestamps else None,
        time_max=max(timestamps).isoformat() if timestamps else None,
        slowest=slowest,
        top_errors=top_errors,
        busiest=busiest,
        top_ips=ip_counter.most_common(top),
        sample_malformed=[(m.line_no, m.raw[:120]) for m in report.malformed[:5]],
    )
