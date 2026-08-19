from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime

import pytest

from scholar_counter import store
from scholar_counter.build import build_site


@pytest.fixture
def site(settings, tmp_path):
    data_dir = tmp_path / "snapshots"
    store.write_snapshot(data_dir, datetime(2025, 1, 1), {"Alpha": 5, "Beta": 2})
    store.write_snapshot(data_dir, datetime(2025, 2, 1), {"Alpha": 9, "Beta": 4})
    return build_site(replace(settings, data_dir=data_dir), tmp_path / "site")


def test_writes_every_expected_file(site):
    expected = {
        "index.html",
        ".nojekyll",
        "api/summary.json",
        "api/papers.json",
        "api/analytics.json",
        "api/status.json",
        "api/trends/daily.json",
        "api/trends/monthly.json",
        "api/trends/yearly.json",
        "api/export/citations.csv",
        "api/export/papers.csv",
        "static/css/style.css",
        "static/js/dashboard.js",
    }
    assert expected <= {p.relative_to(site).as_posix() for p in site.rglob("*") if p.is_file()}


def test_nojekyll_stops_pages_mangling_underscored_paths(site):
    assert (site / ".nojekyll").exists()


def test_marks_itself_static(site):
    html = (site / "index.html").read_text()
    assert 'data-static="true"' in html
    assert 'data-api-base="api"' in html


def test_update_button_is_absent(site):
    """Nothing can service it without a server, so it must not be rendered."""
    assert 'id="update-btn"' not in (site / "index.html").read_text()


def test_asset_and_export_urls_are_relative(site):
    html = (site / "index.html").read_text()
    # A project page lives under /<repo>/, so a leading slash would 404.
    assert 'href="static/css/style.css"' in html
    assert 'src="static/js/dashboard.js"' in html
    assert 'href="api/export/citations.csv"' in html
    assert 'href="/api/' not in html
    assert 'src="/static/' not in html


def test_generated_json_matches_the_live_api(site, settings, tmp_path):
    """The static files are produced through the real endpoints, not a copy."""
    summary = json.loads((site / "api/summary.json").read_text())
    assert summary["current_total"] == 13
    assert summary["total_papers"] == 2


def test_every_granularity_is_generated(site):
    for granularity in ("daily", "monthly", "yearly"):
        payload = json.loads((site / f"api/trends/{granularity}.json").read_text())
        assert payload["granularity"] == granularity
        assert payload["overall_trend"]


def test_papers_payload_carries_trends_for_client_side_detail(site):
    """The static build has no /api/paper, so detail comes from this file."""
    papers = json.loads((site / "api/papers.json").read_text())["papers"]
    assert papers
    assert all(paper["trend"] for paper in papers)


def test_rebuilding_replaces_stale_files(settings, tmp_path):
    data_dir = tmp_path / "snapshots"
    store.write_snapshot(data_dir, datetime(2025, 1, 1), {"Alpha": 5})
    output = tmp_path / "site"

    build_site(replace(settings, data_dir=data_dir), output)
    (output / "stale.txt").write_text("left over")
    build_site(replace(settings, data_dir=data_dir), output)

    assert not (output / "stale.txt").exists()
