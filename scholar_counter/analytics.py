"""Read-only aggregations over the citation database."""

from __future__ import annotations

import sqlite3
import statistics
from datetime import datetime, timedelta
from typing import Any

TOP_PAPERS = 5


def _date(stamp: str) -> str:
    """'2025-01-02 09:30:00' -> '2025-01-02'."""
    return stamp.split(" ", 1)[0]


def _recent_total(changes: list[sqlite3.Row], days: int) -> int:
    cutoff = datetime.now() - timedelta(days=days)
    total = 0
    for row in changes:
        if row["change"] is None:
            continue
        if datetime.fromisoformat(row["captured_at"]) >= cutoff:
            total += row["change"]
    return total


def summary(conn: sqlite3.Connection) -> dict[str, Any] | None:
    from . import db

    latest = db.latest_snapshot(conn)
    if latest is None:
        return None

    totals = db.totals_series(conn)
    changes = db.change_series(conn)

    current_total = latest["total"]
    previous_total = totals[-2]["total"] if len(totals) > 1 else current_total

    counts = db.latest_counts(conn)
    top = sorted(counts.items(), key=lambda item: item[1], reverse=True)[:TOP_PAPERS]

    return {
        "current_total": current_total,
        "daily_change": current_total - previous_total,
        "weekly_change": _recent_total(changes, 7),
        "monthly_change": _recent_total(changes, 30),
        "total_papers": latest["papers"],
        "top_papers": [{"title": title, "citations": count} for title, count in top],
        "last_updated": latest["captured_at"],
    }


def trends(conn: sqlite3.Connection, granularity: str = "daily") -> dict[str, Any]:
    """Citation totals and movement, collapsed to calendar buckets."""
    from . import db

    rows = db.bucketed_totals(conn, granularity)
    return {
        "granularity": granularity,
        "overall_trend": [
            {"timestamp": row["bucket"], "total_citations": row["total"], "papers": row["papers"]}
            for row in rows
        ],
        # The first bucket has no predecessor, and flat buckets are not worth a bar.
        "change_trend": [
            {"timestamp": row["bucket"], "change": row["change"]} for row in rows if row["change"]
        ],
    }


def papers(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    from . import db

    counts = db.latest_counts(conn)
    trends_by_title = db.all_trends(conn)

    result = []
    for title, citations in counts.items():
        history = trends_by_title.get(title, [])
        recent_change = 0
        if len(history) > 1:
            recent_change = history[-1]["citations"] - history[-2]["citations"]
        result.append(
            {
                "title": title,
                "current_citations": citations,
                "recent_change": recent_change,
                "trend": [
                    {"timestamp": _date(row["captured_at"]), "citations": row["citations"]}
                    for row in history
                ],
            }
        )

    result.sort(key=lambda paper: paper["current_citations"], reverse=True)
    return result


def paper_detail(conn: sqlite3.Connection, title: str) -> dict[str, Any] | None:
    from . import db

    history = db.paper_trend(conn, title)
    if not history:
        return None

    citations = [row["citations"] for row in history]
    total_growth = citations[-1] - citations[0]
    span_days = 0.0
    if len(history) > 1:
        span = datetime.fromisoformat(history[-1]["captured_at"]) - datetime.fromisoformat(
            history[0]["captured_at"]
        )
        span_days = span.total_seconds() / 86400

    return {
        "title": title,
        "current_citations": citations[-1],
        "total_growth": total_growth,
        # Growth per calendar day, not per snapshot: snapshots are irregular.
        "avg_daily_growth": round(total_growth / span_days, 3) if span_days else 0.0,
        "trend": [
            {"timestamp": _date(row["captured_at"]), "citations": row["citations"]}
            for row in history
        ],
    }


def overview(conn: sqlite3.Connection) -> dict[str, Any] | None:
    """Advanced metrics for the analytics panel."""
    from . import db

    totals = db.totals_series(conn)
    if not totals:
        return None

    changes = [row["change"] for row in db.change_series(conn) if row["change"] is not None]
    counts = db.latest_counts(conn)

    total_growth = totals[-1]["total"] - totals[0]["total"]
    span_days = 0.0
    if len(totals) > 1:
        span = datetime.fromisoformat(totals[-1]["captured_at"]) - datetime.fromisoformat(
            totals[0]["captured_at"]
        )
        span_days = span.total_seconds() / 86400

    values = list(counts.values())
    most_cited = max(counts.items(), key=lambda item: item[1], default=("", 0))
    least_cited = min(counts.items(), key=lambda item: item[1], default=("", 0))

    return {
        "total_growth": total_growth,
        "avg_daily_growth": round(total_growth / span_days, 2) if span_days else 0.0,
        "best_day": max(changes, default=0),
        "worst_day": min(changes, default=0),
        "avg_change": round(statistics.mean(changes), 2) if changes else 0.0,
        "most_cited_paper": {"title": most_cited[0], "citations": most_cited[1]},
        "least_cited_paper": {"title": least_cited[0], "citations": least_cited[1]},
        "avg_citations_per_paper": round(statistics.mean(values), 2) if values else 0.0,
        "median_citations": round(statistics.median(values), 2) if values else 0.0,
        "recent_growth_30_days": _recent_total(db.change_series(conn), 30),
        "total_papers": len(counts),
        "data_points": len(totals),
        "tracking_since": _date(totals[0]["captured_at"]),
    }
