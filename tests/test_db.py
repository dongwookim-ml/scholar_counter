from __future__ import annotations

from datetime import datetime, timedelta

from scholar_counter import db


def test_empty_database_has_no_latest(conn):
    assert db.latest_snapshot(conn) is None
    assert db.snapshot_count(conn) == 0
    assert db.latest_counts(conn) == {}


def test_snapshot_totals(seeded):
    latest = db.latest_snapshot(seeded)
    assert latest["total"] == 20
    assert latest["papers"] == 2
    assert db.snapshot_count(seeded) == 3


def test_latest_counts_returns_newest_only(seeded):
    assert db.latest_counts(seeded) == {"Alpha": 12, "Beta": 8}


def test_change_series_is_null_then_deltas(seeded):
    changes = [row["change"] for row in db.change_series(seeded)]
    assert changes == [None, 2, 8]


def test_change_series_reflects_removed_papers(conn):
    """A paper leaving the profile must lower the total, not be ignored.

    The pre-SQLite code summed per-paper increases only, so a removed paper
    silently inflated reported growth.
    """
    base = datetime(2025, 3, 1)
    db.save_snapshot(conn, base, {"Kept": 10, "Removed": 30})
    db.save_snapshot(conn, base + timedelta(days=1), {"Kept": 12})

    assert [row["change"] for row in db.change_series(conn)] == [None, -28]


def test_totals_series_is_chronological(seeded):
    stamps = [row["captured_at"] for row in db.totals_series(seeded)]
    assert stamps == sorted(stamps)
    assert [row["total"] for row in db.totals_series(seeded)] == [10, 12, 20]


def test_paper_trend(seeded):
    assert [row["citations"] for row in db.paper_trend(seeded, "Alpha")] == [6, 7, 12]
    assert db.paper_trend(seeded, "Nonexistent") == []


def test_all_trends_groups_by_title(seeded):
    trends = db.all_trends(seeded)
    assert set(trends) == {"Alpha", "Beta"}
    assert [row["citations"] for row in trends["Beta"]] == [4, 5, 8]


def test_resaving_same_timestamp_replaces_rather_than_duplicates(conn):
    stamp = datetime(2025, 5, 1, 12, 0)
    db.save_snapshot(conn, stamp, {"Alpha": 1, "Beta": 2})
    db.save_snapshot(conn, stamp, {"Alpha": 5})

    assert db.snapshot_count(conn) == 1
    assert db.latest_counts(conn) == {"Alpha": 5}, "stale rows must be cascaded away"


def test_titles_with_commas_and_quotes_round_trip(conn):
    """The old CSV format could not represent either."""
    awkward = 'Learning, Fast and Slow: A "Practical" Guide'
    db.save_snapshot(conn, datetime(2025, 6, 1), {awkward: 4})
    assert db.latest_counts(conn) == {awkward: 4}
