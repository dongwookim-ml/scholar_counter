from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime

import pytest

from scholar_counter import db, store


@pytest.fixture
def data_dir(tmp_path):
    return tmp_path / "snapshots"


def test_write_then_read_round_trip(data_dir):
    stamp = datetime(2025, 3, 4, 5, 6, 7)
    path = store.write_snapshot(data_dir, stamp, {"Alpha": 3})

    assert path.name == "20250304T050607.json"
    assert store.read_snapshot(path) == (stamp, {"Alpha": 3})


def test_keys_are_sorted_so_diffs_stay_minimal(data_dir):
    path = store.write_snapshot(data_dir, datetime(2025, 1, 1), {"Zeta": 1, "Alpha": 2})
    payload = json.loads(path.read_text())
    assert list(payload["citations"]) == ["Alpha", "Zeta"]


def test_unicode_titles_are_not_escaped(data_dir):
    title = "Un modèle bayésien 한국어"
    path = store.write_snapshot(data_dir, datetime(2025, 1, 1), {title: 7})

    assert title in path.read_text(encoding="utf-8")
    assert store.read_snapshot(path)[1] == {title: 7}


def test_titles_with_commas_and_quotes_survive(data_dir):
    title = 'Learning, Fast and Slow: A "Practical" Guide'
    path = store.write_snapshot(data_dir, datetime(2025, 1, 1), {title: 4})
    assert store.read_snapshot(path)[1] == {title: 4}


def test_read_snapshot_skips_corrupt_file(data_dir, caplog):
    data_dir.mkdir(parents=True)
    bad = data_dir / "20250101T000000.json"
    bad.write_text("{not json")
    assert store.read_snapshot(bad) is None


def test_iter_snapshots_is_chronological_and_skips_bad_files(data_dir):
    store.write_snapshot(data_dir, datetime(2025, 1, 2), {"Alpha": 2})
    store.write_snapshot(data_dir, datetime(2025, 1, 1), {"Alpha": 1})
    (data_dir / "20250103T000000.json").write_text("{broken")

    stamps = [captured_at for captured_at, _ in store.iter_snapshots(data_dir)]
    assert stamps == [datetime(2025, 1, 1), datetime(2025, 1, 2)]


def test_sync_builds_the_cache_from_json(settings, data_dir):
    store.write_snapshot(data_dir, datetime(2025, 1, 1), {"Alpha": 5})
    store.write_snapshot(data_dir, datetime(2025, 1, 2), {"Alpha": 9, "Beta": 1})

    loaded = store.sync_database(data_dir, settings.database)

    assert loaded == 2
    with db.session(settings.database) as conn:
        assert db.snapshot_count(conn) == 2
        assert db.latest_counts(conn) == {"Alpha": 9, "Beta": 1}


def test_sync_is_a_noop_when_already_current(settings, data_dir):
    store.write_snapshot(data_dir, datetime(2025, 1, 1), {"Alpha": 5})
    store.sync_database(data_dir, settings.database)

    assert store.sync_database(data_dir, settings.database) == -1


def test_sync_notices_a_new_snapshot_file(settings, data_dir):
    store.write_snapshot(data_dir, datetime(2025, 1, 1), {"Alpha": 5})
    store.sync_database(data_dir, settings.database)

    store.write_snapshot(data_dir, datetime(2025, 1, 2), {"Alpha": 8})
    assert store.sync_database(data_dir, settings.database) == 2


def test_sync_rebuilds_when_the_cache_is_missing(settings, data_dir):
    store.write_snapshot(data_dir, datetime(2025, 1, 1), {"Alpha": 5})
    store.sync_database(data_dir, settings.database)
    settings.database.unlink()

    assert store.sync_database(data_dir, settings.database) == 1


def test_export_then_sync_preserves_every_snapshot(settings, seeded, data_dir):
    """A full round trip through JSON must not lose or alter anything."""
    before = {row["captured_at"]: row["total"] for row in db.totals_series(seeded)}
    store.export_database(data_dir, settings.database)
    store.sync_database(data_dir, settings.database, force=True)

    with db.session(settings.database) as conn:
        after = {row["captured_at"]: row["total"] for row in db.totals_series(conn)}

    assert after == before


def test_update_writes_json_and_cache(settings, data_dir, monkeypatch):
    """The committed JSON is the source of truth, so an update must write it."""
    from scholar_counter import updater

    monkeypatch.setattr("scholar_counter.updater.fetch_citations", lambda *a, **k: {"Alpha": 12})
    result = updater.run_update(replace(settings, data_dir=data_dir))

    assert result.success is True
    assert len(list(data_dir.glob("*.json"))) == 1
    with db.session(settings.database) as conn:
        assert db.latest_counts(conn) == {"Alpha": 12}


def test_failed_update_writes_no_json(settings, data_dir, monkeypatch):
    from scholar_counter import updater
    from scholar_counter.scraper import ScrapeError

    def boom(*args, **kwargs):
        raise ScrapeError("blocked")

    monkeypatch.setattr("scholar_counter.updater.fetch_citations", boom)
    result = updater.run_update(replace(settings, data_dir=data_dir))

    assert result.success is False
    assert not data_dir.exists() or not list(data_dir.glob("*.json"))


def test_sync_never_wipes_the_cache_when_no_json_exists(settings, data_dir):
    """The database can be the only surviving copy; an empty data dir must
    not be treated as an instruction to delete it."""
    with db.session(settings.database) as conn:
        db.save_snapshot(conn, datetime(2025, 1, 1), {"Alpha": 42})

    assert store.sync_database(data_dir, settings.database) == -1

    with db.session(settings.database) as conn:
        assert db.latest_counts(conn) == {"Alpha": 42}


def test_sync_leaves_cache_alone_when_directory_is_missing(settings, tmp_path):
    with db.session(settings.database) as conn:
        db.save_snapshot(conn, datetime(2025, 1, 1), {"Alpha": 7})

    assert store.sync_database(tmp_path / "nope", settings.database) == -1

    with db.session(settings.database) as conn:
        assert db.latest_counts(conn) == {"Alpha": 7}
