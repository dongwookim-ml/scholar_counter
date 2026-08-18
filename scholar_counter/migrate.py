"""One-time import of the legacy pickle/CSV history into SQLite.

The original ``history/*.pkl`` and ``difference/*.csv`` folders are only read,
never modified, so they remain a usable backup after migration.
"""

from __future__ import annotations

import logging
import pickle
from datetime import datetime
from pathlib import Path

from . import db
from .config import PROJECT_ROOT, Settings

logger = logging.getLogger(__name__)

LEGACY_HISTORY = PROJECT_ROOT / "history"
TIMESTAMP_FORMAT = "%Y%m%d%H%M"


def _parse_timestamp(path: Path) -> datetime | None:
    try:
        return datetime.strptime(path.stem, TIMESTAMP_FORMAT)
    except ValueError:
        logger.warning("Skipping %s: filename is not a %s timestamp", path.name, TIMESTAMP_FORMAT)
        return None


def _load_snapshot(path: Path) -> dict[str, int] | None:
    try:
        with path.open("rb") as handle:
            data = pickle.load(handle)
    except (OSError, pickle.UnpicklingError, EOFError, AttributeError) as exc:
        logger.warning("Skipping %s: %s", path.name, exc)
        return None

    if not isinstance(data, dict):
        logger.warning("Skipping %s: expected a dict, got %s", path.name, type(data).__name__)
        return None

    return {str(title): int(count) for title, count in data.items()}


def migrate(settings: Settings, history_dir: Path = LEGACY_HISTORY) -> tuple[int, int]:
    """Import every legacy snapshot. Returns (imported, skipped)."""
    if not history_dir.is_dir():
        logger.info("No legacy history at %s; nothing to migrate.", history_dir)
        return 0, 0

    imported = skipped = 0
    with db.session(settings.database) as conn:
        for path in sorted(history_dir.glob("*.pkl")):
            captured_at = _parse_timestamp(path)
            if captured_at is None:
                skipped += 1
                continue

            counts = _load_snapshot(path)
            if not counts:
                skipped += 1
                continue

            db.save_snapshot(conn, captured_at, counts)
            imported += 1

    return imported, skipped
