from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from scholar_counter import analytics, db


def test_summary_on_empty_database(conn):
    assert analytics.summary(conn) is None


def test_summary_reports_latest_and_delta(seeded):
    result = analytics.summary(seeded)
    assert result["current_total"] == 20
    assert result["daily_change"] == 8
    assert result["total_papers"] == 2


def test_summary_top_papers_are_ranked(seeded):
    top = analytics.summary(seeded)["top_papers"]
    assert [paper["title"] for paper in top] == ["Alpha", "Beta"]
    assert top[0]["citations"] == 12


def test_weekly_change_only_counts_the_recent_window(conn):
    now = datetime.now()
    db.save_snapshot(conn, now - timedelta(days=60), {"Alpha": 10})
    db.save_snapshot(conn, now - timedelta(days=40), {"Alpha": 30})  # outside 7 days
    db.save_snapshot(conn, now - timedelta(days=1), {"Alpha": 35})  # inside 7 days

    assert analytics.summary(conn)["weekly_change"] == 5


def test_trends_skips_flat_intervals(conn):
    base = datetime(2025, 1, 1)
    db.save_snapshot(conn, base, {"Alpha": 5})
    db.save_snapshot(conn, base + timedelta(days=1), {"Alpha": 5})  # no movement
    db.save_snapshot(conn, base + timedelta(days=2), {"Alpha": 9})

    trends = analytics.trends(conn)
    assert len(trends["overall_trend"]) == 3
    assert [point["change"] for point in trends["change_trend"]] == [4]


def test_papers_sorted_by_citations_with_recent_change(seeded):
    papers = analytics.papers(seeded)
    assert [paper["title"] for paper in papers] == ["Alpha", "Beta"]
    assert papers[0]["recent_change"] == 5
    assert len(papers[0]["trend"]) == 3


def test_paper_detail_growth_is_per_calendar_day(conn):
    """Snapshots are irregular, so growth must divide by elapsed days."""
    base = datetime(2025, 1, 1)
    db.save_snapshot(conn, base, {"Alpha": 0})
    db.save_snapshot(conn, base + timedelta(days=1), {"Alpha": 1})
    db.save_snapshot(conn, base + timedelta(days=10), {"Alpha": 20})

    detail = analytics.paper_detail(conn, "Alpha")
    assert detail["total_growth"] == 20
    assert detail["avg_daily_growth"] == 2.0  # 20 over 10 days, not 20/3 snapshots


def test_paper_detail_missing_title(seeded):
    assert analytics.paper_detail(seeded, "Nope") is None


def test_overview_metrics(seeded):
    result = analytics.overview(seeded)
    assert result["total_growth"] == 10
    assert result["best_day"] == 8
    assert result["most_cited_paper"] == {"title": "Alpha", "citations": 12}
    assert result["data_points"] == 3
    assert result["tracking_since"] == "2025-01-01"


def test_overview_on_empty_database(conn):
    assert analytics.overview(conn) is None


def test_trends_default_granularity_is_daily(seeded):
    assert analytics.trends(seeded)["granularity"] == "daily"


def test_daily_granularity_collapses_same_day_snapshots(conn):
    """Two scrapes on one day are one point, taking the later total."""
    db.save_snapshot(conn, datetime(2025, 1, 1, 9, 0), {"Alpha": 5})
    db.save_snapshot(conn, datetime(2025, 1, 1, 18, 0), {"Alpha": 8})
    db.save_snapshot(conn, datetime(2025, 1, 2, 9, 0), {"Alpha": 11})

    points = analytics.trends(conn, "daily")["overall_trend"]

    assert [p["timestamp"] for p in points] == ["2025-01-01", "2025-01-02"]
    assert [p["total_citations"] for p in points] == [8, 11]


def test_monthly_granularity_uses_the_last_snapshot_of_each_month(conn):
    db.save_snapshot(conn, datetime(2025, 1, 3), {"Alpha": 5})
    db.save_snapshot(conn, datetime(2025, 1, 28), {"Alpha": 9})
    db.save_snapshot(conn, datetime(2025, 2, 14), {"Alpha": 20})

    result = analytics.trends(conn, "monthly")

    assert [p["timestamp"] for p in result["overall_trend"]] == ["2025-01", "2025-02"]
    assert [p["total_citations"] for p in result["overall_trend"]] == [9, 20]
    assert result["change_trend"] == [{"timestamp": "2025-02", "change": 11}]


def test_yearly_granularity(conn):
    db.save_snapshot(conn, datetime(2024, 6, 1), {"Alpha": 10})
    db.save_snapshot(conn, datetime(2024, 12, 31), {"Alpha": 40})
    db.save_snapshot(conn, datetime(2025, 7, 1), {"Alpha": 100})

    result = analytics.trends(conn, "yearly")

    assert [p["timestamp"] for p in result["overall_trend"]] == ["2024", "2025"]
    assert [p["total_citations"] for p in result["overall_trend"]] == [40, 100]
    assert result["change_trend"] == [{"timestamp": "2025", "change": 60}]


def test_coarser_buckets_never_lose_the_final_total(seeded):
    """Whatever the bucket size, the newest point must match the latest total."""
    latest = analytics.summary(seeded)["current_total"]
    for granularity in ("daily", "monthly", "yearly"):
        points = analytics.trends(seeded, granularity)["overall_trend"]
        assert points[-1]["total_citations"] == latest


def test_change_across_a_gap_is_attributed_to_the_later_bucket(conn):
    """A month with no snapshots is absent, not zero."""
    db.save_snapshot(conn, datetime(2025, 1, 15), {"Alpha": 10})
    db.save_snapshot(conn, datetime(2025, 4, 15), {"Alpha": 30})

    result = analytics.trends(conn, "monthly")

    assert [p["timestamp"] for p in result["overall_trend"]] == ["2025-01", "2025-04"]
    assert result["change_trend"] == [{"timestamp": "2025-04", "change": 20}]


def test_unknown_granularity_is_rejected(seeded):
    with pytest.raises(ValueError, match="Unknown granularity"):
        analytics.trends(seeded, "hourly")
