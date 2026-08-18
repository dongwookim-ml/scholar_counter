"""Flask application factory and JSON API."""

from __future__ import annotations

import csv
import io
import logging
from typing import Any

from flask import Flask, Response, jsonify, render_template, request

from . import analytics, db
from .config import Settings
from .scheduler import DailyUpdater
from .updater import is_running, run_update

logger = logging.getLogger(__name__)

NO_DATA = ({"error": "No data available. Run an update to collect the first snapshot."}, 404)


def _csv_response(rows: list[list[Any]], filename: str) -> Response:
    buffer = io.StringIO()
    csv.writer(buffer).writerows(rows)
    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


def create_app(settings: Settings | None = None, *, start_scheduler: bool = True) -> Flask:
    settings = settings or Settings.from_env()
    app = Flask(__name__)
    app.config["SETTINGS"] = settings

    scheduler: DailyUpdater | None = None
    if start_scheduler and settings.auto_update:
        scheduler = DailyUpdater(settings)
        scheduler.start()
    app.config["SCHEDULER"] = scheduler

    def connection():
        return db.session(settings.database)

    @app.get("/")
    def dashboard() -> str:
        return render_template("dashboard.html")

    @app.get("/api/summary")
    def api_summary():
        with connection() as conn:
            data = analytics.summary(conn)
        return jsonify(data) if data else NO_DATA

    @app.get("/api/trends")
    def api_trends():
        granularity = request.args.get("granularity", "daily")
        if granularity not in db.GRANULARITIES:
            return {
                "error": f"Unknown granularity {granularity!r}.",
                "allowed": sorted(db.GRANULARITIES),
            }, 400

        with connection() as conn:
            return jsonify(analytics.trends(conn, granularity))

    @app.get("/api/papers")
    def api_papers():
        with connection() as conn:
            return jsonify({"papers": analytics.papers(conn)})

    @app.get("/api/paper")
    def api_paper_detail():
        # A query parameter, not a path segment: titles may contain slashes.
        title = request.args.get("title", "").strip()
        if not title:
            return {"error": "Missing 'title' query parameter."}, 400

        with connection() as conn:
            detail = analytics.paper_detail(conn, title)
        return jsonify(detail) if detail else ({"error": "Paper not found."}, 404)

    @app.get("/api/analytics")
    def api_analytics():
        with connection() as conn:
            data = analytics.overview(conn)
        return jsonify(data) if data else NO_DATA

    @app.get("/api/export/citations.csv")
    def api_export_citations():
        with connection() as conn:
            totals = db.totals_series(conn)
            changes = {row["captured_at"]: row["change"] for row in db.change_series(conn)}

        rows: list[list[Any]] = [["Timestamp", "Total Citations", "Change", "Papers"]]
        rows.extend(
            [row["captured_at"], row["total"], changes.get(row["captured_at"]) or 0, row["papers"]]
            for row in totals
        )
        return _csv_response(rows, "citation_history.csv")

    @app.get("/api/export/papers.csv")
    def api_export_papers():
        with connection() as conn:
            totals = db.totals_series(conn)
            trends = db.all_trends(conn)

        stamps = [row["captured_at"] for row in totals]
        rows: list[list[Any]] = [["Paper Title", *stamps]]
        for title in sorted(trends):
            by_stamp = {row["captured_at"]: row["citations"] for row in trends[title]}
            rows.append([title, *(by_stamp.get(stamp, "") for stamp in stamps)])
        return _csv_response(rows, "papers_history.csv")

    @app.post("/api/update")
    def api_update():
        result = run_update(settings)
        return jsonify(result.as_dict()), (200 if result.success else 503)

    @app.get("/api/status")
    def api_status():
        with connection() as conn:
            latest = db.latest_snapshot(conn)
            snapshots = db.snapshot_count(conn)

        payload: dict[str, Any] = {
            "has_data": latest is not None,
            "updating": is_running(),
            "snapshots": snapshots,
            "last_update": latest["captured_at"] if latest is not None else None,
            "total_citations": latest["total"] if latest is not None else 0,
            "papers_count": latest["papers"] if latest is not None else 0,
            "auto_update": settings.auto_update,
            "next_update": None,
        }
        if scheduler is not None:
            payload["next_update"] = scheduler.next_run_at.isoformat(sep=" ", timespec="minutes")
        return jsonify(payload)

    return app
