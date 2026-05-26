#!/usr/bin/env python3
"""Generate a representative server log, including the deviations logwise must survive.

Usage:
    python scripts/generate_logs.py --lines 5000 --out sample.log --seed 42
    python scripts/generate_logs.py --lines 200            # prints to stdout
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime, timedelta, timezone

IPS = ["192.168.1.42", "10.0.0.7", "172.16.0.3", "192.168.1.99", "10.0.0.250"]
METHODS = ["GET", "GET", "GET", "POST", "PUT", "DELETE", "PATCH"]  # GET-weighted
PATHS = ["/api/users", "/api/users/12", "/api/login", "/api/orders",
         "/api/orders/8841", "/health", "/api/search", "/static/app.js"]
# status weighted toward success, with a realistic error tail
STATUSES = [200] * 70 + [201] * 5 + [301, 302] + [400, 401, 403, 404] * 3 + [500, 502, 503]
USER_AGENTS = [
    '"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"',
    '"curl/8.4.0"',
    '"PostmanRuntime/7.36.0 some agent with spaces"',
]
REFERRERS = ['"https://example.com/search?q=a b c"', '"-"']


def _clean(ts: datetime) -> str:
    iso = ts.strftime("%Y-%m-%dT%H:%M:%SZ")
    ip = random.choice(IPS)
    method = random.choice(METHODS)
    path = random.choice(PATHS)
    status = random.choice(STATUSES)
    rt = random.randint(5, 800)
    return f"{iso} {ip} {method} {path} {status} {rt}ms"


def _alt_timestamp(ts: datetime) -> str:
    style = random.choice(["slash", "dmy", "epoch"])
    ip, method, path = random.choice(IPS), random.choice(METHODS), random.choice(PATHS)
    rest = f"{ip} {method} {path} {random.choice(STATUSES)} {random.randint(5, 800)}ms"
    if style == "slash":
        return f"{ts.strftime('%Y/%m/%d %H:%M:%S')} {rest}"
    if style == "dmy":
        return f"{ts.strftime('%d-%b-%Y %H:%M:%S')} {rest}"
    return f"{int(ts.timestamp())} {rest}"


def _alt_units(ts: datetime) -> str:
    iso = ts.strftime("%Y-%m-%dT%H:%M:%SZ")
    base = f"{iso} {random.choice(IPS)} {random.choice(METHODS)} {random.choice(PATHS)} {random.choice(STATUSES)}"
    style = random.choice(["seconds", "bare"])
    if style == "seconds":
        return f"{base} {random.randint(5, 800)/1000:.3f}s"
    return f"{base} {random.randint(5, 800)}"


def _missing_status(ts: datetime) -> str:
    iso = ts.strftime("%Y-%m-%dT%H:%M:%SZ")
    status = random.choice(["-", ""])  # '-' or omitted
    return f"{iso} {random.choice(IPS)} {random.choice(METHODS)} {random.choice(PATHS)} {status} {random.randint(5,800)}ms".replace("  ", " ")


def _extra_fields(ts: datetime) -> str:
    iso = ts.strftime("%Y-%m-%dT%H:%M:%SZ")
    return (f"{iso} {random.choice(IPS)} {random.choice(METHODS)} {random.choice(PATHS)} "
            f"{random.choice(STATUSES)} {random.randint(5,800)}ms "
            f"{random.choice(USER_AGENTS)} {random.choice(REFERRERS)}")


def _json_line(ts: datetime) -> str:
    return json.dumps({
        "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ip": random.choice(IPS),
        "method": random.choice(METHODS),
        "path": random.choice(PATHS),
        "status": random.choice(STATUSES),
        "latency": f"{random.randint(5,800)}ms",
    })


def _malformed(ts: datetime) -> str:
    kind = random.choice(["partial", "trace", "blank", "garbage"])
    if kind == "partial":
        return f"{ts.strftime('%Y-%m-%dT%H:%M:%SZ')} {random.choice(IPS)} GE"  # cut off
    if kind == "trace":
        return random.choice([
            "Traceback (most recent call last):",
            '  File "app.py", line 42, in handler',
            "ValueError: bad things happened",
        ])
    if kind == "blank":
        return ""
    return "###%%% not a log line at all %%%###"


DEVIATIONS = [_alt_timestamp, _alt_units, _missing_status, _extra_fields, _json_line, _malformed]


def generate(lines: int, seed: int | None) -> list[str]:
    if seed is not None:
        random.seed(seed)
    out = []
    ts = datetime(2024, 3, 15, 14, 0, 0, tzinfo=timezone.utc)
    for _ in range(lines):
        ts += timedelta(seconds=random.randint(0, 3))
        if random.random() < 0.10:                 # ~10% deviate
            out.append(random.choice(DEVIATIONS)(ts))
        else:
            out.append(_clean(ts))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate a representative log file.")
    ap.add_argument("--lines", type=int, default=1000)
    ap.add_argument("--out", type=str, default=None, help="Output file (default: stdout).")
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()

    rows = generate(args.lines, args.seed)
    text = "\n".join(rows) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"Wrote {args.lines} lines to {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
