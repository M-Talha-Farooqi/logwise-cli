from __future__ import annotations

import sys
from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from logwise import __version__
from logwise.analysis.analyzer import analyze
from logwise.output.console import render_console
from logwise.output.csv_out import render_csv
from logwise.output.json_out import render_json
from logwise.parsing.parser import parse_lines, stream_file

app = typer.Typer(
    help="logwise — a resilient server-log analyzer for on-call engineers.",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()
err_console = Console(stderr=True)


class OutFormat(str, Enum):
    table = "table"
    json = "json"
    csv = "csv"


def _read_lines(path: Optional[str]):
    """Return an iterable of lines from a path or stdin.

    path is None or '-'  -> stdin
    otherwise            -> file (validated)
    """
    if path is None or path == "-":
        if sys.stdin.isatty():
            err_console.print("[red]No input.[/] Provide a file path or pipe a log via stdin.")
            raise typer.Exit(code=2)
        return sys.stdin
    p = Path(path)
    if not p.exists():
        err_console.print(f"[red]File not found:[/] {path}")
        raise typer.Exit(code=2)
    if not p.is_file():
        err_console.print(f"[red]Not a file:[/] {path}")
        raise typer.Exit(code=2)
    return stream_file(p)


def _emit(analysis, fmt: OutFormat) -> None:
    if fmt is OutFormat.json:
        console.print_json(render_json(analysis))
    elif fmt is OutFormat.csv:
        sys.stdout.write(render_csv(analysis))
    else:
        render_console(analysis, console)


@app.command("analyze")
def analyze_cmd(
    path: Optional[str] = typer.Argument(None, help="Path to log file, or '-' for stdin."),
    fmt: OutFormat = typer.Option(OutFormat.table, "--format", "-f", help="Output format."),
    top: int = typer.Option(10, "--top", "-n", min=1, help="How many rows in top-N tables."),
):
    """Full triage report: health, anomalies, errors, slowest + busiest endpoints."""
    report = parse_lines(_read_lines(path))
    result = analyze(report, top=top)
    _emit(result, fmt)
    # exit code 1 if there were server errors or a high malformed rate — script-friendly
    if result.status_classes.get("5xx", 0) > 0 or result.malformed_pct > 20:
        raise typer.Exit(code=1)


@app.command()
def slowest(
    path: Optional[str] = typer.Argument(None),
    top: int = typer.Option(10, "--top", "-n", min=1),
    fmt: OutFormat = typer.Option(OutFormat.table, "--format", "-f"),
):
    """Show only the slowest endpoints (by p95 latency)."""
    report = parse_lines(_read_lines(path))
    result = analyze(report, top=top)
    if fmt is OutFormat.table:
        from logwise.output.console import _endpoint_table
        _endpoint_table(console, "Slowest endpoints (by p95)", result.slowest, show_latency=True)
    else:
        _emit(result, fmt)


@app.command()
def errors(
    path: Optional[str] = typer.Argument(None),
    top: int = typer.Option(10, "--top", "-n", min=1),
    fmt: OutFormat = typer.Option(OutFormat.table, "--format", "-f"),
):
    """Show only the error breakdown and top error-producing endpoints."""
    report = parse_lines(_read_lines(path))
    result = analyze(report, top=top)
    if fmt is OutFormat.table:
        sc = result.status_classes
        console.print("Status: " + "  ".join(f"{k}: {v}" for k, v in sc.items() if v))
        console.print(f"Error rate: {result.error_rate_pct:.1f}%\n")
        from logwise.output.console import _endpoint_table
        _endpoint_table(console, "Top error endpoints", result.top_errors, show_errors=True)
    else:
        _emit(result, fmt)


@app.command()
def version():
    """Print the version."""
    console.print(f"logwise {__version__}")
