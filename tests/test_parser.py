from logwise.models import LineFormat
from logwise.parsing.parser import parse_lines


def test_clean_line(clean_line):
    rep = parse_lines([clean_line])
    assert rep.parsed_count == 1
    e = rep.entries[0]
    assert e.method == "GET" and e.status == 200 and e.response_ms == 142.0
    assert e.fmt is LineFormat.STANDARD


def test_json_line():
    line = '{"timestamp":"2024-03-15T14:23:01Z","ip":"10.0.0.7","method":"post","path":"/api/login","status":401,"latency":"89ms"}'
    rep = parse_lines([line])
    e = rep.entries[0]
    assert e.fmt is LineFormat.JSON
    assert e.method == "POST" and e.status == 401 and e.response_ms == 89.0


def test_extra_quoted_fields_do_not_break_core():
    line = '2024-03-15T14:23:01Z 10.0.0.7 GET /api/users 200 142ms "Mozilla/5.0 with spaces" "https://x.com/a b"'
    e = parse_lines([line]).entries[0]
    assert e.status == 200 and e.response_ms == 142.0       # core fields still correct
    assert any("extra fields" in n for n in e.notes)


def test_missing_status_is_salvaged_not_dropped():
    line = "2024-03-15T14:23:01Z 10.0.0.7 GET /api/users - 142ms"
    e = parse_lines([line]).entries[0]
    assert e.status is None
    assert "status" in e.missing_fields


def test_malformed_lines_are_counted_not_crashing():
    lines = [
        "Traceback (most recent call last):",
        '  File "app.py", line 42, in handler',
        "###%%% garbage %%%###",
    ]
    rep = parse_lines(lines)
    assert rep.malformed_count == 3
    assert rep.parsed_count == 0                            # no crash, all counted


def test_conservation_invariant():
    """THE key test: every line is accounted for. Nothing is silently dropped."""
    lines = [
        "2024-03-15T14:23:01Z 10.0.0.7 GET /api/users 200 142ms",   # clean
        "",                                                          # blank
        "garbage line",                                             # malformed
        '{"timestamp":"2024-03-15T14:23:01Z","status":500}',        # json (partial)
        "2024/03/15 14:23:01 10.0.0.7 GET / - 0.142s",              # alt fmt + missing status
    ]
    rep = parse_lines(lines)
    assert rep.parsed_count + rep.malformed_count + rep.blank_lines == rep.total_lines


def test_never_crashes_on_adversarial_input():
    import random
    random.seed(1)
    adversarial = ["".join(chr(random.randint(0, 1000)) for _ in range(random.randint(0, 50)))
                   for _ in range(500)]
    rep = parse_lines(adversarial)                          # must not raise
    assert rep.total_lines == 500
