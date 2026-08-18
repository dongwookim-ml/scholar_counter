"""Crawl Google Scholar and persist a snapshot.

Shared by the HTTP endpoint, the scheduler and the CLI. A non-blocking lock
guarantees a scheduled run and a button press can never overlap.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from . import db
from .config import Settings
from .scraper import ScrapeError, fetch_citations

logger = logging.getLogger(__name__)

_lock = threading.Lock()


@dataclass(frozen=True, slots=True)
class UpdateResult:
    success: bool
    message: str
    total_citations: int | None = None
    papers_count: int | None = None
    changed: bool = False
    finished_at: datetime = field(default_factory=datetime.now)

    def as_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "message": self.message,
            "total_citations": self.total_citations,
            "papers_count": self.papers_count,
            "changed": self.changed,
            "finished_at": self.finished_at.replace(microsecond=0).isoformat(sep=" "),
        }


def is_running() -> bool:
    return _lock.locked()


def run_update(settings: Settings) -> UpdateResult:
    """Fetch the profile and store a snapshot, unless one is already in flight."""
    if not _lock.acquire(blocking=False):
        logger.info("Update already in progress; skipping this request.")
        return UpdateResult(success=False, message="An update is already in progress.")

    try:
        logger.info("Fetching Google Scholar profile %s", settings.scholar_user_id)
        counts = fetch_citations(settings)

        with db.session(settings.database) as conn:
            previous = db.latest_snapshot(conn)
            previous_total = previous["total"] if previous is not None else None
            db.save_snapshot(conn, datetime.now(), counts)

        total = sum(counts.values())
        changed = previous_total is not None and total != previous_total
        delta = "" if previous_total is None else f" ({total - previous_total:+d})"
        message = f"{total:,} citations across {len(counts)} papers{delta}"
        logger.info("Update complete: %s", message)

        return UpdateResult(
            success=True,
            message=message,
            total_citations=total,
            papers_count=len(counts),
            changed=changed,
        )

    except ScrapeError as exc:
        logger.warning("Update failed: %s", exc)
        return UpdateResult(success=False, message=str(exc))
    except Exception as exc:  # surfaced to the UI, never crashes the server
        logger.exception("Unexpected error during update")
        return UpdateResult(success=False, message=f"Unexpected error: {exc}")
    finally:
        _lock.release()
