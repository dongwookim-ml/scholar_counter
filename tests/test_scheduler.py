from __future__ import annotations

import pickle
import threading
from dataclasses import replace
from datetime import datetime, timedelta

from scholar_counter import db, updater
from scholar_counter.migrate import migrate
from scholar_counter.scheduler import DailyUpdater


def test_next_run_is_later_today_when_the_hour_has_not_passed(settings):
    scheduler = DailyUpdater(replace(settings, update_hour=23, update_minute=59))
    assert scheduler.next_run_at > datetime.now()
    assert scheduler.next_run_at.hour == 23


def test_next_run_rolls_to_tomorrow_once_the_hour_has_passed(settings):
    now = datetime.now()
    scheduler = DailyUpdater(replace(settings, update_hour=0, update_minute=0))
    expected_day = (now + timedelta(days=1)).date() if now.hour or now.minute else now.date()
    assert scheduler.next_run_at.date() == expected_day


def test_empty_database_counts_as_stale(settings):
    assert DailyUpdater(settings)._is_stale() is True


def test_fresh_snapshot_is_not_stale(settings):
    with db.session(settings.database) as conn:
        db.save_snapshot(conn, datetime.now(), {"Alpha": 1})
    assert DailyUpdater(settings)._is_stale() is False


def test_old_snapshot_is_stale(settings):
    with db.session(settings.database) as conn:
        db.save_snapshot(conn, datetime.now() - timedelta(hours=30), {"Alpha": 1})
    assert DailyUpdater(replace(settings, stale_after_hours=24))._is_stale() is True


def test_startup_catch_up_runs_an_update(settings, monkeypatch):
    """A machine asleep at 03:00 must still refresh once it wakes."""
    monkeypatch.setattr("scholar_counter.updater.fetch_citations", lambda *a, **k: {"Alpha": 11})
    scheduler = DailyUpdater(settings)  # empty database => stale
    scheduler.start()
    try:
        deadline = datetime.now() + timedelta(seconds=5)
        while scheduler.last_result is None and datetime.now() < deadline:
            threading.Event().wait(0.05)
    finally:
        scheduler.stop()

    assert scheduler.last_result is not None
    assert scheduler.last_result.success is True
    with db.session(settings.database) as conn:
        assert db.latest_counts(conn) == {"Alpha": 11}


def test_fresh_database_skips_the_catch_up(settings, monkeypatch):
    calls: list[int] = []
    monkeypatch.setattr(
        "scholar_counter.updater.fetch_citations",
        lambda *a, **k: (calls.append(1), {"Alpha": 1})[1],
    )
    with db.session(settings.database) as conn:
        db.save_snapshot(conn, datetime.now(), {"Alpha": 1})

    scheduler = DailyUpdater(settings)
    scheduler.start()
    threading.Event().wait(0.3)
    scheduler.stop()

    assert calls == [], "a recent snapshot must not trigger an immediate scrape"


def test_concurrent_updates_are_serialised(settings, monkeypatch):
    """The scheduled run and the Update button must never scrape at once."""
    started = threading.Event()
    release = threading.Event()

    def slow_fetch(*args, **kwargs):
        started.set()
        release.wait(timeout=5)
        return {"Alpha": 1}

    monkeypatch.setattr("scholar_counter.updater.fetch_citations", slow_fetch)

    worker = threading.Thread(target=updater.run_update, args=(settings,))
    worker.start()
    started.wait(timeout=5)

    second = updater.run_update(settings)  # arrives while the first still holds the lock
    release.set()
    worker.join(timeout=5)

    assert second.success is False
    assert "already in progress" in second.message


def test_migrate_imports_legacy_pickles(settings, tmp_path):
    history = tmp_path / "history"
    history.mkdir()
    (history / "202401011200.pkl").write_bytes(pickle.dumps({"Alpha": 5}))
    (history / "202401021200.pkl").write_bytes(pickle.dumps({"Alpha": 9, "Beta": 2}))

    imported, skipped = migrate(settings, history_dir=history)

    assert (imported, skipped) == (2, 0)
    with db.session(settings.database) as conn:
        assert db.snapshot_count(conn) == 2
        assert db.latest_counts(conn) == {"Alpha": 9, "Beta": 2}


def test_migrate_skips_unreadable_and_misnamed_files(settings, tmp_path):
    history = tmp_path / "history"
    history.mkdir()
    (history / "202401011200.pkl").write_bytes(pickle.dumps({"Alpha": 5}))
    (history / "not-a-timestamp.pkl").write_bytes(pickle.dumps({"Beta": 1}))
    (history / "202401021200.pkl").write_bytes(b"this is not a pickle")

    imported, skipped = migrate(settings, history_dir=history)

    assert imported == 1
    assert skipped == 2


def test_migrate_is_idempotent(settings, tmp_path):
    history = tmp_path / "history"
    history.mkdir()
    (history / "202401011200.pkl").write_bytes(pickle.dumps({"Alpha": 5}))

    migrate(settings, history_dir=history)
    migrate(settings, history_dir=history)

    with db.session(settings.database) as conn:
        assert db.snapshot_count(conn) == 1


def test_migrate_with_no_legacy_folder(settings, tmp_path):
    assert migrate(settings, history_dir=tmp_path / "absent") == (0, 0)


def test_failed_update_retries_sooner_than_the_next_day(settings, monkeypatch):
    """A rate-limited scrape must not cost a whole day of history."""
    from scholar_counter.scraper import RateLimited

    def blocked(*args, **kwargs):
        raise RateLimited("bot check")

    monkeypatch.setattr("scholar_counter.updater.fetch_citations", blocked)
    scheduler = DailyUpdater(replace(settings, retry_after_minutes=30))
    scheduler._run()

    delay = scheduler.next_run_at - datetime.now()
    assert timedelta(minutes=25) < delay < timedelta(minutes=35)
    assert scheduler.last_result.success is False


def test_successful_update_returns_to_the_daily_slot(settings, monkeypatch):
    monkeypatch.setattr("scholar_counter.updater.fetch_citations", lambda *a, **k: {"Alpha": 1})
    scheduler = DailyUpdater(replace(settings, update_hour=3, retry_after_minutes=30))
    scheduler._run()

    assert scheduler.next_run_at.hour == 3
    assert scheduler.next_run_at - datetime.now() > timedelta(minutes=30)
