from __future__ import annotations

import csv
import io
from datetime import datetime

import pytest

from scholar_counter import db
from scholar_counter.app import create_app
from scholar_counter.scraper import ScrapeError


@pytest.fixture
def client(settings):
    app = create_app(settings, start_scheduler=False)
    app.config.update(TESTING=True)
    return app.test_client()


@pytest.fixture
def populated(settings, seeded, client):
    return client


def test_dashboard_renders(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Scholar Citation Tracker" in response.data


def test_summary_404s_without_data(client):
    response = client.get("/api/summary")
    assert response.status_code == 404
    assert "error" in response.get_json()


def test_summary(populated):
    body = populated.get("/api/summary").get_json()
    assert body["current_total"] == 20
    assert body["total_papers"] == 2


def test_status_without_data(client):
    body = client.get("/api/status").get_json()
    assert body["has_data"] is False
    assert body["snapshots"] == 0
    assert body["updating"] is False


def test_status_reports_scheduler_state(settings, seeded):
    app = create_app(settings, start_scheduler=False)
    body = app.test_client().get("/api/status").get_json()
    assert body["has_data"] is True
    assert body["auto_update"] is False
    assert body["next_update"] is None


def test_papers_endpoint(populated):
    papers = populated.get("/api/papers").get_json()["papers"]
    assert [paper["title"] for paper in papers] == ["Alpha", "Beta"]


def test_paper_detail_requires_title(populated):
    assert populated.get("/api/paper").status_code == 400


def test_paper_detail_unknown_title(populated):
    assert populated.get("/api/paper", query_string={"title": "Ghost"}).status_code == 404


def test_paper_detail(populated):
    body = populated.get("/api/paper", query_string={"title": "Alpha"}).get_json()
    assert body["current_citations"] == 12


def test_paper_title_containing_a_slash(settings, conn):
    """The old /api/paper/<title> route 404'd on any title with a slash."""
    title = "A/B Testing at Scale"
    db.save_snapshot(conn, datetime(2025, 1, 1), {title: 9})

    client = create_app(settings, start_scheduler=False).test_client()
    response = client.get("/api/paper", query_string={"title": title})

    assert response.status_code == 200
    assert response.get_json()["current_citations"] == 9


def test_export_citations_csv(populated):
    response = populated.get("/api/export/citations.csv")
    assert response.status_code == 200
    assert "attachment" in response.headers["Content-Disposition"]

    rows = list(csv.reader(io.StringIO(response.get_data(as_text=True))))
    assert rows[0] == ["Timestamp", "Total Citations", "Change", "Papers"]
    assert len(rows) == 4  # header + three snapshots


def test_export_papers_csv_quotes_awkward_titles(settings, conn):
    title = 'Learning, Fast and Slow: A "Practical" Guide'
    db.save_snapshot(conn, datetime(2025, 1, 1), {title: 4})

    client = create_app(settings, start_scheduler=False).test_client()
    text = client.get("/api/export/papers.csv").get_data(as_text=True)

    rows = list(csv.reader(io.StringIO(text)))
    assert rows[1][0] == title, "csv module must quote the comma and escape the quotes"


def test_update_endpoint_reports_failure(client, monkeypatch):
    def boom(*args, **kwargs):
        raise ScrapeError("rate limited")

    monkeypatch.setattr("scholar_counter.updater.fetch_citations", boom)
    response = client.post("/api/update")

    assert response.status_code == 503
    assert response.get_json()["success"] is False
    assert "rate limited" in response.get_json()["message"]


def test_update_endpoint_stores_a_snapshot(client, settings, monkeypatch):
    monkeypatch.setattr(
        "scholar_counter.updater.fetch_citations", lambda *a, **k: {"Alpha": 3, "Beta": 4}
    )
    body = client.post("/api/update").get_json()

    assert body["success"] is True
    assert body["total_citations"] == 7
    with db.session(settings.database) as conn:
        assert db.latest_counts(conn) == {"Alpha": 3, "Beta": 4}
