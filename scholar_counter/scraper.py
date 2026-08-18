"""Fetch citation counts from a Google Scholar profile."""

from __future__ import annotations

import logging

import requests
from bs4 import BeautifulSoup

from .config import Settings

logger = logging.getLogger(__name__)

# Scholar accepts up to 100 rows per request; the default is 20.
PAGE_SIZE = 100
# Safety net so a markup change cannot turn pagination into an infinite loop.
MAX_PAGES = 20


class ScrapeError(RuntimeError):
    """Raised when the profile cannot be fetched or parsed."""


class RateLimited(ScrapeError):
    """Google served its bot-check page instead of the profile."""


def _is_bot_check(response: requests.Response) -> bool:
    """Google redirects blocked clients to /sorry/ and answers 429."""
    return response.status_code == 429 or "/sorry/" in response.url


def parse_page(html: str | bytes) -> dict[str, int]:
    """Extract ``{title: citation_count}`` from one profile page."""
    soup = BeautifulSoup(html, "html.parser")
    papers: dict[str, int] = {}

    for row in soup.select("tr.gsc_a_tr"):
        title_el = row.select_one("a.gsc_a_at")
        if title_el is None:
            continue
        title = title_el.get_text(strip=True)
        if not title:
            continue
        cite_el = row.select_one("a.gsc_a_ac")
        cite_text = cite_el.get_text(strip=True) if cite_el is not None else ""
        papers[title] = int(cite_text) if cite_text.isdigit() else 0

    return papers


def fetch_citations(settings: Settings, session: requests.Session | None = None) -> dict[str, int]:
    """Fetch every paper on the configured profile, following pagination."""
    owns_session = session is None
    session = session or requests.Session()
    results: dict[str, int] = {}

    try:
        for page in range(MAX_PAGES):
            params = {"cstart": page * PAGE_SIZE, "pagesize": PAGE_SIZE}
            try:
                response = session.get(
                    settings.profile_url,
                    params=params,
                    headers=settings.request_headers,
                    timeout=settings.request_timeout,
                )
                if _is_bot_check(response):
                    raise RateLimited(
                        "Google Scholar is rate-limiting this network and served a "
                        "bot check instead of the profile. Try again later."
                    )
                response.raise_for_status()
            except requests.RequestException as exc:
                raise ScrapeError(f"Failed to fetch Google Scholar profile: {exc}") from exc

            batch = parse_page(response.content)
            if not batch:
                break
            results.update(batch)
            if len(batch) < PAGE_SIZE:
                break
        else:
            logger.warning("Stopped after %d pages; profile may be truncated.", MAX_PAGES)
    finally:
        if owns_session:
            session.close()

    if not results:
        raise ScrapeError(
            "No papers found. Google Scholar may be rate-limiting this IP, "
            "or the profile ID may be wrong."
        )

    return results
