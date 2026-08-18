from __future__ import annotations

import pytest
import requests

from scholar_counter.config import Settings
from scholar_counter.scraper import (
    PAGE_SIZE,
    RateLimited,
    ScrapeError,
    fetch_citations,
    parse_page,
)


def row(title: str, citations: str) -> str:
    return (
        '<tr class="gsc_a_tr">'
        f'<td class="gsc_a_t"><a class="gsc_a_at">{title}</a></td>'
        f'<td class="gsc_a_c"><a class="gsc_a_ac">{citations}</a></td>'
        "</tr>"
    )


def page(*rows: str) -> str:
    return f"<table><tbody>{''.join(rows)}</tbody></table>"


def test_parses_titles_and_counts():
    assert parse_page(page(row("Deep Nets", "42"), row("Wide Nets", "7"))) == {
        "Deep Nets": 42,
        "Wide Nets": 7,
    }


def test_blank_citation_cell_counts_as_zero():
    assert parse_page(page(row("Brand New Paper", ""))) == {"Brand New Paper": 0}


def test_row_without_citation_link_counts_as_zero():
    html = page('<tr class="gsc_a_tr"><td><a class="gsc_a_at">Untracked</a></td></tr>')
    assert parse_page(html) == {"Untracked": 0}


def test_ignores_rows_with_no_title():
    assert parse_page(page('<tr class="gsc_a_tr"><td>filler</td></tr>')) == {}


def test_empty_document_yields_nothing():
    assert parse_page("<html><body></body></html>") == {}


class FakeResponse:
    PROFILE_URL = "https://scholar.google.com/citations"

    def __init__(self, body: str, status_code: int = 200, url: str = PROFILE_URL) -> None:
        self.content = body.encode()
        self.status_code = status_code
        self.url = url

    def raise_for_status(self) -> None:
        return None


class FakeSession:
    """Serves a queue of page bodies and records the params it was called with."""

    def __init__(self, bodies: list[str]) -> None:
        self._bodies = bodies
        self.calls: list[dict] = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append(params or {})
        return FakeResponse(self._bodies.pop(0) if self._bodies else page())

    def close(self) -> None:
        return None


def test_stops_on_short_page():
    session = FakeSession([page(row("Only Paper", "3"))])
    result = fetch_citations(Settings(), session=session)

    assert result == {"Only Paper": 3}
    assert len(session.calls) == 1, "a partial page means there is nothing more to fetch"


def test_follows_pagination_until_exhausted():
    full = page(*(row(f"Paper {i}", str(i)) for i in range(PAGE_SIZE)))
    session = FakeSession([full, page(row("Last", "1"))])

    result = fetch_citations(Settings(), session=session)

    assert len(result) == PAGE_SIZE + 1
    assert [call["cstart"] for call in session.calls] == [0, PAGE_SIZE]


def test_empty_profile_raises():
    with pytest.raises(ScrapeError, match="No papers found"):
        fetch_citations(Settings(), session=FakeSession([page()]))


def test_network_failure_raises_scrape_error():
    class BrokenSession(FakeSession):
        def get(self, *args, **kwargs):
            raise requests.ConnectionError("no route to host")

    with pytest.raises(ScrapeError, match="Failed to fetch"):
        fetch_citations(Settings(), session=BrokenSession([]))


def test_bot_check_redirect_is_reported_as_rate_limiting():
    """Google answers 429 and redirects to /sorry/ rather than the profile."""

    class BlockedSession(FakeSession):
        def get(self, *args, **kwargs):
            return FakeResponse("<html>captcha</html>", 429, "https://www.google.com/sorry/index")

    with pytest.raises(RateLimited, match="rate-limiting"):
        fetch_citations(Settings(), session=BlockedSession([]))


def test_rate_limiting_is_a_scrape_error():
    assert issubclass(RateLimited, ScrapeError)
