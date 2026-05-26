from __future__ import annotations

import csv
import io

from logwise.analysis.analyzer import Analysis


def render_csv(analysis: Analysis) -> str:
    """Emit the slowest-endpoints table as CSV (the most spreadsheet-useful view)."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["path", "count", "avg_ms", "p95_ms", "max_ms", "errors_4xx_plus", "errors_5xx"])
    for s in analysis.slowest:
        writer.writerow([
            s.path, s.count,
            f"{s.avg_ms:.0f}" if s.avg_ms is not None else "",
            f"{s.p95_ms:.0f}" if s.p95_ms is not None else "",
            f"{s.max_ms:.0f}" if s.max_ms is not None else "",
            s.error_count, s.server_error_count,
        ])
    return buf.getvalue()
