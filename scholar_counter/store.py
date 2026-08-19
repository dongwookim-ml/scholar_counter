"""Snapshot storage as one JSON file per scrape.

GitHub Actions runners are ephemeral, so the repository itself holds the
history. JSON keeps each day a small, readable addition that git can diff;
the SQLite database is a derived cache rebuilt from these files and is never
committed.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator, Mapping
from datetime import datetime
from pathlib import Path

from . import db
from .config import PROJECT_ROOT

logger = logging.getLogger(__name__)

DATA_DIR = PROJECT_ROOT / "data" / "snapshots"
FILENAME_FORMAT = "%Y%m%dT%H%M%S"


def snapshot_path(directory: Path, captured_at: datetime) -> Path:
    return directory / f"{captured_at.strftime(FILENAME_FORMAT)}.json"


def write_snapshot(directory: Path, captured_at: datetime, counts: Mapping[str, int]) -> Path:
    """Write one snapshot. Keys are sorted so diffs stay minimal and stable."""
    directory.mkdir(parents=True, exist_ok=True)
    path = snapshot_path(directory, captured_at)
    payload = {
        "captured_at": captured_at.replace(microsecond=0).isoformat(),
        "citations": dict(sorted(counts.items())),
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def read_snapshot(path: Path) -> tuple[datetime, dict[str, int]] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        captured_at = datetime.fromisoformat(payload["captured_at"])
        citations = {str(k): int(v) for k, v in payload["citations"].items()}
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        logger.warning("Skipping %s: %s", path.name, exc)
        return None
    return captured_at, citations


def iter_snapshots(directory: Path) -> Iterator[tuple[datetime, dict[str, int]]]:
    for path in sorted(directory.glob("*.json")):
        snapshot = read_snapshot(path)
        if snapshot is not None:
            yield snapshot


def export_database(directory: Path, database: Path) -> int:
    """Write every snapshot currently in the database out as JSON."""
    written = 0
    with db.session(database) as conn:
        for row in db.totals_series(conn):
            captured_at = datetime.fromisoformat(row["captured_at"])
            counts = {
                r["title"]: r["citations"]
                for r in conn.execute(
                    """
                    SELECT c.title, c.citations
                    FROM citation c
                    JOIN snapshot s ON s.id = c.snapshot_id
                    WHERE s.captured_at = ?
                    """,
                    (row["captured_at"],),
                )
            }
            write_snapshot(directory, captured_at, counts)
            written += 1
    return written


def _is_in_sync(directory: Path, database: Path) -> bool:
    if not database.exists():
        return False

    paths = sorted(directory.glob("*.json"))
    with db.session(database) as conn:
        if db.snapshot_count(conn) != len(paths):
            return False
        latest = db.latest_snapshot(conn)

    if not paths:
        return latest is None
    if latest is None:
        return False

    newest = read_snapshot(paths[-1])
    if newest is None:
        return False
    return newest[0].isoformat(sep=" ") == latest["captured_at"]


def sync_database(directory: Path, database: Path, *, force: bool = False) -> int:
    """Rebuild the SQLite cache from JSON when the two disagree.

    Returns the number of snapshots loaded, or -1 when already in sync.
    """
    paths = sorted(directory.glob("*.json")) if directory.is_dir() else []
    if not paths:
        # Rebuilding from nothing would destroy a database that is the only
        # remaining copy of the history. Leave it alone and say so.
        logger.debug("No JSON snapshots under %s; leaving %s untouched.", directory, database.name)
        return -1

    if not force and _is_in_sync(directory, database):
        return -1

    database.unlink(missing_ok=True)
    loaded = 0
    with db.session(database) as conn:
        for captured_at, counts in iter_snapshots(directory):
            db.save_snapshot(conn, captured_at, counts)
            loaded += 1

    logger.info("Rebuilt %s from %d JSON snapshot(s)", database.name, loaded)
    return loaded
