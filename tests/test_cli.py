from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from scholar_counter import db, store
from scholar_counter.cli import main


@pytest.fixture
def env(monkeypatch, settings):
    monkeypatch.setenv("SCHOLAR_DATABASE", str(settings.database))
    monkeypatch.setenv("SCHOLAR_DATA_DIR", str(settings.data_dir))
    return settings


def seed(settings, age_hours: float) -> None:
    stamp = datetime.now() - timedelta(hours=age_hours)
    store.write_snapshot(settings.data_dir, stamp, {"Alpha": 5})
    store.sync_database(settings.data_dir, settings.database)


def test_check_passes_on_fresh_data(env, capsys):
    seed(env, age_hours=2)
    assert main(["check", "--max-age-hours", "48"]) == 0
    assert "Fresh" in capsys.readouterr().out


def test_check_fails_on_stale_data(env, capsys):
    seed(env, age_hours=72)
    assert main(["check", "--max-age-hours", "48"]) == 1
    assert "Stale" in capsys.readouterr().out


def test_check_fails_when_there_is_no_data_at_all(env, capsys):
    assert main(["check"]) == 1
    assert "No data" in capsys.readouterr().out


def test_update_skips_when_a_recent_snapshot_exists(env, monkeypatch, capsys):
    """Later runs in the same day must not scrape again."""
    seed(env, age_hours=2)
    called = []
    monkeypatch.setattr(
        "scholar_counter.updater.fetch_citations",
        lambda *a, **k: called.append(1) or {"Alpha": 9},
    )

    assert main(["update", "--skip-if-fresh-hours", "20"]) == 0
    assert called == [], "a fresh snapshot must prevent a second scrape"
    assert "nothing to do" in capsys.readouterr().out


def test_update_runs_when_the_snapshot_is_old(env, monkeypatch):
    seed(env, age_hours=30)
    monkeypatch.setattr("scholar_counter.updater.fetch_citations", lambda *a, **k: {"Alpha": 9})

    assert main(["update", "--skip-if-fresh-hours", "20"]) == 0
    with db.session(env.database) as conn:
        assert db.latest_counts(conn) == {"Alpha": 9}


def test_update_runs_when_there_is_no_data(env, monkeypatch):
    monkeypatch.setattr("scholar_counter.updater.fetch_citations", lambda *a, **k: {"Alpha": 1})
    assert main(["update", "--skip-if-fresh-hours", "20"]) == 0


def test_update_reports_failure_with_nonzero_exit(env, monkeypatch):
    from scholar_counter.scraper import RateLimited

    def blocked(*args, **kwargs):
        raise RateLimited("403")

    monkeypatch.setattr("scholar_counter.updater.fetch_citations", blocked)
    assert main(["update"]) == 1


def test_future_snapshot_does_not_count_as_fresh(env, monkeypatch, capsys):
    """A negative age means the writer and reader disagree about the timezone.
    Treating it as freshness would silently suppress every future scrape."""
    seed(env, age_hours=-6)
    scraped = []
    monkeypatch.setattr(
        "scholar_counter.updater.fetch_citations",
        lambda *a, **k: scraped.append(1) or {"Alpha": 9},
    )

    assert main(["update", "--skip-if-fresh-hours", "20"]) == 0
    assert scraped == [1], "skew must not be mistaken for a recent snapshot"
    assert "in the future" in capsys.readouterr().err


def test_check_fails_on_clock_skew(env, capsys):
    seed(env, age_hours=-6)
    assert main(["check", "--max-age-hours", "48"]) == 1
    assert "Clock skew" in capsys.readouterr().out
