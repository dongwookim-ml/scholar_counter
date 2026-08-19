from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from scholar_counter import db
from scholar_counter.config import PROJECT_ROOT, Settings

REAL_DATA_DIR = PROJECT_ROOT / "data" / "snapshots"


@pytest.fixture
def settings(tmp_path) -> Settings:
    # data_dir must be redirected too, or tests would read the repo's real
    # snapshots and rebuild the fixture database from them.
    return Settings(
        database=tmp_path / "test.db",
        data_dir=tmp_path / "snapshots",
        auto_update=False,
    )


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


@pytest.fixture(autouse=True)
def _protect_real_snapshots():
    """Fail loudly if a test writes into the repository's real snapshots.

    A Settings default pointing at the live data directory once let the update
    tests append fabricated snapshots to the committed history.
    """
    before = {p.name for p in REAL_DATA_DIR.glob("*.json")} if REAL_DATA_DIR.is_dir() else set()
    yield
    after = {p.name for p in REAL_DATA_DIR.glob("*.json")} if REAL_DATA_DIR.is_dir() else set()
    assert after == before, f"test modified real snapshots: {after ^ before}"
