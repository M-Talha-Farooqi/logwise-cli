from logwise.analysis.analyzer import analyze
from logwise.parsing.parser import parse_lines


def _report(n_ok=10):
    lines = [f"2024-03-15T14:23:0{i%10}Z 10.0.0.7 GET /api/x 200 {10*i}ms" for i in range(n_ok)]
    lines += ["2024-03-15T14:23:09Z 10.0.0.7 GET /api/x 500 50ms"]
    return parse_lines(lines)


def test_error_rate_and_slowest():
    a = analyze(_report(), top=5)
    assert a.status_classes["5xx"] == 1
    assert a.error_rate_pct > 0
    assert a.slowest and a.slowest[0].p95_ms is not None


def test_empty_input_does_not_crash():
    a = analyze(parse_lines([]), top=5)
    assert a.total_lines == 0 and a.error_rate_pct == 0.0
