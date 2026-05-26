from datetime import timezone

from logwise.parsing.timestamps import match_leading_timestamp, parse_timestamp


def test_iso():
    dt, rest = match_leading_timestamp("2024-03-15T14:23:01Z rest here")
    assert dt is not None and dt.tzinfo == timezone.utc
    assert rest == "rest here"


def test_slash_with_space():
    dt, rest = match_leading_timestamp("2024/03/15 14:23:01 10.0.0.7 GET / 200 5ms")
    assert dt is not None
    assert rest.startswith("10.0.0.7")        # timestamp's internal space didn't leak


def test_day_month():
    dt, _ = match_leading_timestamp("15-Mar-2024 14:23:01 x")
    assert dt is not None and dt.month == 3


def test_epoch_seconds_vs_millis():
    sec = parse_timestamp("1710512581")
    ms = parse_timestamp("1710512581000")
    assert sec is not None and ms is not None
    # both should land on the same instant, not 50,000 years apart
    assert abs((sec - ms).total_seconds()) < 1


def test_garbage_timestamp_returns_none():
    dt, rest = match_leading_timestamp("not-a-timestamp here")
    assert dt is None and rest == "not-a-timestamp here"
