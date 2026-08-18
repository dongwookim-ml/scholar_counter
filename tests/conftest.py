from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from scholar_counter import db
from scholar_counter.config import Settings


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(database=tmp_path / "test.db", auto_update=False)


@pytest.fixture
def conn(settings):
    connection = db.connect(settings.database)
    yield connection
    connection.close()


@pytest.fixture
def seeded(conn):
    """Three snapshots a day apart: 10 -> 12 -> 20 total citations."""
    base = datetime(2025, 1, 1, 9, 0)
    db.save_snapshot(conn, base, {"Alpha": 6, "Beta": 4})
    db.save_snapshot(conn, base + timedelta(days=1), {"Alpha": 7, "Beta": 5})
    db.save_snapshot(conn, base + timedelta(days=2), {"Alpha": 12, "Beta": 8})
    return conn
