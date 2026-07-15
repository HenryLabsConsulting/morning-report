"""Tests for the mock vendor API date window (mock_sources/app.py::_window)."""

import app as mock_app


def test_window_since_until_same_day_returns_only_that_day():
    """since == until == D must return exactly the records dated on day D.

    Regression test for B49: comparing a raw ISO timestamp against a bare
    since/until date lexicographically drops every record on the until day.
    """
    rows = [
        {"scheduled_at": "2026-06-14T23:59:00Z"},  # day before -> excluded
        {"scheduled_at": "2026-06-15T00:00:00Z"},  # on the day -> included
        {"scheduled_at": "2026-06-15T09:30:00Z"},  # on the day -> included
        {"scheduled_at": "2026-06-15T23:59:59Z"},  # on the day -> included
        {"scheduled_at": "2026-06-16T00:00:00Z"},  # day after -> excluded
    ]
    with mock_app.app.test_request_context("/?since=2026-06-15&until=2026-06-15"):
        result = mock_app._window(rows, "scheduled_at")

    assert len(result) == 3
    assert all(row["scheduled_at"].startswith("2026-06-15") for row in result)


def test_window_multi_day_range_is_inclusive_on_both_ends():
    rows = [
        {"scheduled_at": "2026-06-14T23:59:59Z"},  # before window -> excluded
        {"scheduled_at": "2026-06-15T00:00:00Z"},  # start boundary -> included
        {"scheduled_at": "2026-06-16T12:00:00Z"},  # middle -> included
        {"scheduled_at": "2026-06-17T23:59:59Z"},  # end boundary -> included
        {"scheduled_at": "2026-06-18T00:00:00Z"},  # after window -> excluded
    ]
    with mock_app.app.test_request_context("/?since=2026-06-15&until=2026-06-17"):
        result = mock_app._window(rows, "scheduled_at")

    dates = {row["scheduled_at"][:10] for row in result}
    assert dates == {"2026-06-15", "2026-06-16", "2026-06-17"}


def test_window_no_bounds_returns_all_rows():
    rows = [{"scheduled_at": "2026-06-15T09:30:00Z"}, {"scheduled_at": "2026-01-01T00:00:00Z"}]
    with mock_app.app.test_request_context("/"):
        result = mock_app._window(rows, "scheduled_at")
    assert result == rows
