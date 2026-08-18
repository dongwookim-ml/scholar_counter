"""SQLite persistence for citation snapshots.

The historical data model was one pickle file per snapshot plus one CSV per
change, which meant every API request re-read the entire history from disk.
Everything now lives in a single database and aggregation happens in SQL.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshot (
    id          INTEGER PRIMARY KEY,
    captured_at TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS citation (
    snapshot_id INTEGER NOT NULL REFERENCES snapshot(id) ON DELETE CASCADE,
    title       TEXT    NOT NULL,
    citations   INTEGER NOT NULL,
    PRIMARY KEY (snapshot_id, title)
);

CREATE INDEX IF NOT EXISTS citation_title_idx ON citation(title);
"""

# Per-snapshot totals, reused by most of the analytics queries.
_TOTALS_CTE = """
WITH totals AS (
    SELECT s.id            AS id,
           s.captured_at   AS captured_at,
           COALESCE(SUM(c.citations), 0) AS total,
           COUNT(c.title)  AS papers
    FROM snapshot s
    LEFT JOIN citation c ON c.snapshot_id = s.id
    GROUP BY s.id
)
"""


def connect(database: Path) -> sqlite3.Connection:
    """Open ``database``, creating the file and schema if needed."""
    database.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(database, detect_types=0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(SCHEMA)
    return conn


@contextmanager
def session(database: Path) -> Iterator[sqlite3.Connection]:
    conn = connect(database)
    try:
        yield conn
    finally:
        conn.close()


def save_snapshot(
    conn: sqlite3.Connection, captured_at: datetime, counts: Mapping[str, int]
) -> int:
    """Store one snapshot and return its row id."""
    stamp = captured_at.replace(microsecond=0).isoformat(sep=" ")
    with conn:
        cursor = conn.execute("INSERT OR REPLACE INTO snapshot (captured_at) VALUES (?)", (stamp,))
        snapshot_id = int(cursor.lastrowid)
        conn.executemany(
            "INSERT OR REPLACE INTO citation (snapshot_id, title, citations) VALUES (?, ?, ?)",
            [(snapshot_id, title, int(count)) for title, count in counts.items()],
        )
    return snapshot_id


def snapshot_count(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) FROM snapshot").fetchone()[0])


def latest_snapshot(conn: sqlite3.Connection) -> sqlite3.Row | None:
    """Most recent snapshot with its total and paper count, or None if empty."""
    return conn.execute(
        _TOTALS_CTE + "SELECT * FROM totals ORDER BY captured_at DESC LIMIT 1"
    ).fetchone()


def latest_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """``{title: citations}`` for the newest snapshot."""
    rows = conn.execute(
        """
        SELECT c.title, c.citations
        FROM citation c
        WHERE c.snapshot_id = (SELECT id FROM snapshot ORDER BY captured_at DESC LIMIT 1)
        """
    ).fetchall()
    return {row["title"]: row["citations"] for row in rows}


def totals_series(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Every snapshot as (captured_at, total, papers), oldest first."""
    return conn.execute(
        _TOTALS_CTE + "SELECT captured_at, total, papers FROM totals ORDER BY captured_at"
    ).fetchall()


def change_series(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Citation deltas between consecutive snapshots, skipping flat periods.

    This replaces the old ``difference/*.csv`` files, which stored the same
    information but could not round-trip any title containing a comma.
    """
    return conn.execute(
        _TOTALS_CTE
        + """
        SELECT captured_at, total - LAG(total) OVER (ORDER BY captured_at) AS change
        FROM totals
        ORDER BY captured_at
        """
    ).fetchall()


# strftime patterns that collapse snapshots into calendar buckets.
GRANULARITIES = {
    "daily": "%Y-%m-%d",
    "monthly": "%Y-%m",
    "yearly": "%Y",
}


def bucketed_totals(conn: sqlite3.Connection, granularity: str) -> list[sqlite3.Row]:
    """Totals collapsed to one point per calendar bucket, oldest first.

    Snapshots are irregular, so each bucket is represented by its *last*
    snapshot and the change is the movement since the previous bucket.
    """
    try:
        fmt = GRANULARITIES[granularity]
    except KeyError:
        raise ValueError(
            f"Unknown granularity {granularity!r}; expected one of {sorted(GRANULARITIES)}"
        ) from None

    return conn.execute(
        _TOTALS_CTE
        + """
        , ranked AS (
            SELECT strftime(:fmt, captured_at) AS bucket,
                   captured_at,
                   total,
                   papers,
                   ROW_NUMBER() OVER (
                       PARTITION BY strftime(:fmt, captured_at)
                       ORDER BY captured_at DESC
                   ) AS rank_in_bucket
            FROM totals
        )
        SELECT bucket,
               captured_at,
               total,
               papers,
               total - LAG(total) OVER (ORDER BY bucket) AS change
        FROM ranked
        WHERE rank_in_bucket = 1
        ORDER BY bucket
        """,
        {"fmt": fmt},
    ).fetchall()


def paper_trend(conn: sqlite3.Connection, title: str) -> list[sqlite3.Row]:
    """Citation history for one paper, oldest first."""
    return conn.execute(
        """
        SELECT s.captured_at, c.citations
        FROM citation c
        JOIN snapshot s ON s.id = c.snapshot_id
        WHERE c.title = ?
        ORDER BY s.captured_at
        """,
        (title,),
    ).fetchall()


def all_trends(conn: sqlite3.Connection) -> dict[str, list[sqlite3.Row]]:
    """Citation history for every paper, in one query."""
    rows = conn.execute(
        """
        SELECT c.title, s.captured_at, c.citations
        FROM citation c
        JOIN snapshot s ON s.id = c.snapshot_id
        ORDER BY c.title, s.captured_at
        """
    ).fetchall()

    trends: dict[str, list[sqlite3.Row]] = {}
    for row in rows:
        trends.setdefault(row["title"], []).append(row)
    return trends
