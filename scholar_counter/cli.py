"""Command line entry points."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime

from . import db, store
from .app import create_app
from .config import Settings
from .migrate import migrate
from .updater import run_update


def _configure_logging(debug: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _serve(settings: Settings) -> int:
    from werkzeug.serving import is_running_from_reloader

    # The debug reloader runs this module twice; only the child should schedule.
    start_scheduler = not (settings.debug and not is_running_from_reloader())
    app = create_app(settings, start_scheduler=start_scheduler)

    scheduler = app.config.get("SCHEDULER")
    print(f"Dashboard:  http://{settings.host}:{settings.port}")
    print(f"Database:   {settings.database}")
    if scheduler is not None:
        print(
            f"Auto-update: daily at {settings.update_hour:02d}:{settings.update_minute:02d} "
            f"(next {scheduler.next_run_at:%Y-%m-%d %H:%M})"
        )
    else:
        print("Auto-update: disabled (set SCHOLAR_AUTO_UPDATE=1 to enable)")

    app.run(host=settings.host, port=settings.port, debug=settings.debug)
    return 0


def _latest_age_hours(settings: Settings) -> float | None:
    """Hours since the newest snapshot, or None when there is no data."""
    store.sync_database(settings.data_dir, settings.database)
    with db.session(settings.database) as conn:
        latest = db.latest_snapshot(conn)
    if latest is None:
        return None
    delta = datetime.now() - datetime.fromisoformat(latest["captured_at"])
    return delta.total_seconds() / 3600


def _update(settings: Settings, args: argparse.Namespace) -> int:
    if args.skip_if_fresh_hours is not None:
        age = _latest_age_hours(settings)
        if age is not None and age < args.skip_if_fresh_hours:
            print(f"Latest snapshot is {age:.1f}h old; nothing to do.")
            return 0

    result = run_update(settings)
    print(result.message)
    return 0 if result.success else 1


def _check(settings: Settings, args: argparse.Namespace) -> int:
    """Exit non-zero when the data has gone stale, for CI to alarm on."""
    age = _latest_age_hours(settings)
    if age is None:
        print("No data recorded at all.")
        return 1
    if age > args.max_age_hours:
        print(f"Stale: newest snapshot is {age:.1f}h old (limit {args.max_age_hours}h).")
        return 1
    print(f"Fresh: newest snapshot is {age:.1f}h old.")
    return 0


def _migrate(settings: Settings) -> int:
    imported, skipped = migrate(settings)
    print(f"Imported {imported} snapshot(s), skipped {skipped}.")
    with db.session(settings.database) as conn:
        print(f"Database now holds {db.snapshot_count(conn)} snapshot(s) at {settings.database}.")
    return 0


def _export(settings: Settings) -> int:
    written = store.export_database(settings.data_dir, settings.database)
    print(f"Wrote {written} JSON snapshot(s) to {settings.data_dir}.")
    return 0


def _sync(settings: Settings) -> int:
    loaded = store.sync_database(settings.data_dir, settings.database, force=True)
    print(f"Rebuilt {settings.database.name} from {loaded} JSON snapshot(s).")
    return 0


def _build(settings: Settings) -> int:
    from .build import build_site

    store.sync_database(settings.data_dir, settings.database)
    output = build_site(settings)
    print(f"Static site written to {output}")
    return 0


def _status(settings: Settings) -> int:
    store.sync_database(settings.data_dir, settings.database)
    with db.session(settings.database) as conn:
        latest = db.latest_snapshot(conn)
        total = db.snapshot_count(conn)

    if latest is None:
        print("No data yet. Run 'scholar-counter update' to collect the first snapshot.")
        return 1

    print(f"Snapshots:  {total}")
    print(f"Latest:     {latest['captured_at']}")
    print(f"Citations:  {latest['total']:,} across {latest['papers']} papers")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="scholar-counter", description=__doc__)
    parser.add_argument("--debug", action="store_true", help="verbose logging")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("serve", help="run the dashboard web server (default)")

    update = sub.add_parser("update", help="fetch the profile once and store a snapshot")
    update.add_argument(
        "--skip-if-fresh-hours",
        type=float,
        default=None,
        metavar="H",
        help="do nothing if the newest snapshot is younger than H hours",
    )

    check = sub.add_parser("check", help="exit non-zero if the data has gone stale")
    check.add_argument("--max-age-hours", type=float, default=48.0, metavar="H")
    sub.add_parser("migrate", help="import legacy history/*.pkl files into SQLite")
    sub.add_parser("status", help="print what is currently stored")
    sub.add_parser("export", help="write the database out as JSON snapshots")
    sub.add_parser("sync", help="rebuild the database cache from JSON snapshots")
    sub.add_parser("build", help="generate the static site")

    args = parser.parse_args(argv)
    settings = Settings.from_env()
    _configure_logging(args.debug or settings.debug)

    # These two need the parsed arguments; the rest only need settings.
    if args.command == "update":
        return _update(settings, args)
    if args.command == "check":
        return _check(settings, args)

    handlers = {
        "serve": _serve,
        "migrate": _migrate,
        "status": _status,
        "export": _export,
        "sync": _sync,
        "build": _build,
    }
    return handlers[args.command or "serve"](settings)


if __name__ == "__main__":
    sys.exit(main())
