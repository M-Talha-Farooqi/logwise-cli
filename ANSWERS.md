# ANSWERS.md

## 1. How to run

On a fresh machine with **Python 3.11+**:

```bash
git clone <YOUR_REPO_URL> && cd logwise
pip install .
logwise analyze path/to/log.file
```

To try it without your own data, generate a representative log first:

```bash
python scripts/generate_logs.py --lines 5000 --seed 42 --out sample.log
logwise analyze sample.log
```

Only dependency to install is the package itself (`pip install .` pulls `typer` and `rich`
from PyPI). No databases, no system libraries. Docker path is in the README if Python
isn't available.

## 2. Stack choice

I built a **CLI in Python** (Typer + Rich).

- **Why Python:** the task is fundamentally text parsing and date/number normalization, and
  Python's standard library (`re`, `datetime`, `json`, `shlex`, `statistics`) covers all of
  it with no third-party parsing dependency. I can write defensive, readable code fast,
  which matters when robustness is the grading axis.
- **Why a CLI:** logs live in terminals and pipelines. A CLI composes with `ssh`, `grep`,
  `cron`, and `jq` (via `--format json`), which is exactly how an on-call engineer works.
- **What would have been a worse choice:** a **web dashboard** (e.g., Flask/React). It would
  add a server, a port, and session state to a task that is "read a file, summarize it" —
  more moving parts to deploy and secure, with no benefit for the on-call workflow. A
  **GUI** would be worse still: wrong domain entirely, and not scriptable. I also avoided
  pulling in a heavy log-parsing framework because the spec's whole point is handling
  *unexpected* shapes, which a rigid schema-based parser handles poorly.

## 3. One real edge case

**Unix-epoch timestamps in milliseconds vs seconds.**
See `src/logwise/parsing/timestamps.py`, in `_to_utc`, the `EPOCH` branch (around
**line 59**):

```python
num = int(text)
if len(text) == 13:      # milliseconds
    num /= 1000
dt = datetime.fromtimestamp(num, tz=timezone.utc)
```

The log spec lists Unix epoch as one timestamp format, but doesn't say seconds or millis —
real systems emit both. Without the 13-digit check, a millisecond epoch like
`1710512581000` would be interpreted as seconds, placing the event roughly **52,000 years**
in the future. That single bad value would then dominate the report's time-range window
(`min`/`max`) and make the whole "window covered" summary nonsense — a silent data-quality
failure, not a crash, which is the worst kind. The length check normalizes both to the same
instant.

## 4. AI usage

- **Tool:** Claude (Anthropic) via an AI coding assistant.
- **What I asked:** guidance on structuring a fallback parser that tries JSON, then a
  positional format, then a salvage path, and how to handle the various timestamp formats.
- **What it gave me:** a strategy-chain skeleton, the idea to consume the timestamp off the
  front of the line before tokenizing, and templates for the normalizer functions.
- **What I changed and why:** the AI's initial version used a single regex for the whole
  line, which broke on quoted user-agent strings containing spaces. I replaced the trailing
  split with `shlex.split` (with a fallback to plain `split()` for unbalanced quotes) and a
  positional mapper so extra quoted fields are preserved as notes instead of corrupting the
  status/latency columns. I also added the 13-digit epoch check after the AI's version
  treated all epoch values as seconds.
- I used AI for boilerplate generation (test scaffolding, Dockerfile, CI workflow, README
  templates), type annotations, and docstring phrasing. All logic was reviewed and adapted.

## 5. Honest gap

The standard-line parser maps fields **positionally** after consuming the timestamp. That
works for the shapes in the spec, but it's brittle if a future format reorders columns or
inserts a field between, say, IP and method — it would misalign everything downstream
silently. With another day I'd replace the positional mapper with a small set of
**named-capture regex profiles** plus a confidence score per profile, so the parser picks
the best-matching profile per line and reports low-confidence parses as anomalies rather
than guessing. I'd also add a `--strict` mode that fails loudly when the malformed rate
crosses a configurable threshold, and property-based tests (Hypothesis) to fuzz the parser
harder than my current hand-written adversarial test does.
