from __future__ import annotations

from datetime import datetime, timedelta

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
    assert [point["change"] for point in trends["daily_trend"]] == [4]


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
