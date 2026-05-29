from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from logwise.analysis.analyzer import Analysis, EndpointStat


def render_console(analysis: Analysis, console: Console | None = None) -> None:
    console = console or Console()

    # ---- health header ----
    health = (
        f"[bold]Total lines:[/] {analysis.total_lines:,}    "
        f"[green]parsed:[/] {analysis.parsed:,}    "
        f"[yellow]malformed:[/] {analysis.malformed:,} ({analysis.malformed_pct:.1f}%)    "
        f"[dim]blank:[/] {analysis.blank:,}"
    )
    if analysis.time_min:
        health += f"\n[dim]window:[/] {analysis.time_min}  →  {analysis.time_max}"
    console.print(Panel(health, title="logwise — health", border_style="cyan"))

    # ---- format breakdown (anomaly surface) ----
    if analysis.format_counts:
        fmt_table = Table(title="Line formats seen", show_edge=False)
        fmt_table.add_column("format")
        fmt_table.add_column("count", justify="right")
        for k, v in sorted(analysis.format_counts.items(), key=lambda x: -x[1]):
            style = "red" if k == "malformed" else ("yellow" if k == "salvaged" else "")
            fmt_table.add_row(f"[{style}]{k}[/{style}]" if style else k, f"{v:,}")
        console.print(fmt_table)

    # ---- status classes + error rate ----
    sc = analysis.status_classes
    status_line = "  ".join(f"{k}: {v:,}" for k, v in sc.items() if v)
    err_style = "red" if analysis.error_rate_pct >= 5 else "green"
    console.print(
        f"\n[bold]Status:[/] {status_line}    "
        f"[bold]error rate:[/] [{err_style}]{analysis.error_rate_pct:.1f}%[/{err_style}]\n"
    )

    _endpoint_table(console, "Slowest endpoints (by p95)", analysis.slowest, show_latency=True)
    _endpoint_table(console, "Top error endpoints", analysis.top_errors, show_errors=True)
    _endpoint_table(console, "Busiest endpoints", analysis.busiest)

    if analysis.top_ips:
        ip_table = Table(title="Top client IPs")
        ip_table.add_column("ip")
        ip_table.add_column("requests", justify="right")
        for ip, n in analysis.top_ips:
            ip_table.add_row(ip, f"{n:,}")
        console.print(ip_table)

    # ---- malformed samples (never hide failures) ----
    if analysis.sample_malformed:
        console.print("\n[yellow]Sample malformed lines (first few):[/]")
        for ln, raw in analysis.sample_malformed:
            console.print(f"  [dim]L{ln}:[/] {raw}")


def _fmt_ms(v: float | None) -> str:
    return f"{v:.0f}ms" if v is not None else "—"


def _endpoint_table(console, title, stats: list[EndpointStat],
                    show_latency=False, show_errors=False) -> None:
    if not stats:
        return
    table = Table(title=title)
    table.add_column("path", overflow="fold")
    table.add_column("count", justify="right")
    if show_latency:
        table.add_column("avg", justify="right")
        table.add_column("p95", justify="right")
        table.add_column("max", justify="right")
    if show_errors:
        table.add_column("4xx+", justify="right")
        table.add_column("5xx", justify="right")
    for s in stats:
        row = [s.path, f"{s.count:,}"]
        if show_latency:
            row += [_fmt_ms(s.avg_ms), _fmt_ms(s.p95_ms), _fmt_ms(s.max_ms)]
        if show_errors:
            row += [str(s.error_count), f"[red]{s.server_error_count}[/red]"]
        table.add_row(*row)
    console.print(table)
