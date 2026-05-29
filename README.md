![ci](https://github.com/M-Talha-Farooqi/logwise-cli/actions/workflows/ci.yml/badge.svg)

# logwise

A resilient server-log analyzer for on-call engineers. Point it at any web-service log
file (or pipe one in) and get a triage report: what's broken, what's slow, what's weird —
even when the log is messy, mixed-format, or partially corrupted.

## Requirements

- Python 3.11+
- (optional) Docker, if you prefer the container path

## Install & run (single command after clone)

```bash
pip install . && logwise analyze path/to/your.log
```

Or without installing:

```bash
pip install -e ".[dev]"        # dev install
python -m logwise analyze path/to/your.log
```

Or via Docker (no local Python needed):

```bash
docker build -t logwise . && docker run --rm -v "$PWD":/data logwise analyze /data/your.log
```

## Generate a sample log (no data shipped — make your own)

```bash
python scripts/generate_logs.py --lines 5000 --seed 42 --out sample.log
logwise analyze sample.log
```

The generator emits ~90% canonical lines and ~10% deviations across all six categories
(alternate timestamp formats, alternate latency units, missing/`-` status, extra quoted
fields, fully malformed lines, and JSON-format lines).

## Usage

```bash
logwise analyze FILE            # full report  (FILE or '-' for stdin)
logwise slowest FILE --top 20   # slowest endpoints by p95
logwise errors  FILE            # error breakdown
logwise analyze FILE --format json | jq   # machine-readable output
cat app.log | logwise analyze -            # read from stdin
```

### Options

- `--format {table,json,csv}` (default `table`)
- `--top N` (default 10)

### Exit codes

- `0` clean run
- `1` ran fine but found 5xx errors or a >20% malformed rate (useful in cron/CI alerts)
- `2` usage error (no input / file not found)

## How it handles messy logs

Every line lands in exactly one bucket — parsed, salvaged, malformed, or blank — and the
report shows the counts. Bad lines are skipped with a visible count and sample, never
silently dropped, and a single bad line can never crash the run.

## Tests

```bash
pytest -q
```
