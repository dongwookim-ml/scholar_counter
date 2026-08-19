"""Generate a self-contained static copy of the dashboard.

Every JSON file is produced by calling the real API through Flask's test
client, so the static site cannot drift from the live endpoints.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from flask import render_template

from . import db
from .app import create_app
from .config import PROJECT_ROOT, Settings

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT = PROJECT_ROOT / "site"

# API routes captured verbatim, mapped to their path in the generated site.
ENDPOINTS = {
    "/api/summary": "api/summary.json",
    "/api/papers": "api/papers.json",
    "/api/analytics": "api/analytics.json",
    "/api/status": "api/status.json",
    "/api/export/citations.csv": "api/export/citations.csv",
    "/api/export/papers.csv": "api/export/papers.csv",
}


def build_site(settings: Settings, output: Path = DEFAULT_OUTPUT) -> Path:
    app = create_app(settings, start_scheduler=False)
    client = app.test_client()

    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    def write(relative: str, payload: bytes) -> None:
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)

    for route, relative in ENDPOINTS.items():
        response = client.get(route)
        if response.status_code != 200:
            logger.warning("%s returned %d; writing it anyway", route, response.status_code)
        write(relative, response.data)

    for granularity in sorted(db.GRANULARITIES):
        response = client.get("/api/trends", query_string={"granularity": granularity})
        write(f"api/trends/{granularity}.json", response.data)

    # Relative URLs so the site works from a project-pages subpath.
    with app.app_context():
        html = render_template(
            "dashboard.html",
            static_site=True,
            api_base="api",
            css_url="static/css/style.css",
            js_url="static/js/dashboard.js",
        )
    write("index.html", html.encode("utf-8"))

    shutil.copytree(Path(app.static_folder), output / "static")
    # Tell Pages not to run the output through Jekyll.
    write(".nojekyll", b"")

    logger.info("Static site written to %s", output)
    return output
