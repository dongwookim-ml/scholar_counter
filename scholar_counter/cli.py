"""Command line entry points."""

from __future__ import annotations

import argparse
import logging
import sys

from . import db
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


def _update(settings: Settings) -> int:
    result = run_update(settings)
    print(result.message)
    return 0 if result.success else 1


def _migrate(settings: Settings) -> int:
    imported, skipped = migrate(settings)
    print(f"Imported {imported} snapshot(s), skipped {skipped}.")
    with db.session(settings.database) as conn:
        print(f"Database now holds {db.snapshot_count(conn)} snapshot(s) at {settings.database}.")
    return 0


def _status(settings: Settings) -> int:
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
    sub.add_parser("update", help="fetch the profile once and store a snapshot")
    sub.add_parser("migrate", help="import legacy history/*.pkl files into SQLite")
    sub.add_parser("status", help="print what is currently stored")

    args = parser.parse_args(argv)
    settings = Settings.from_env()
    _configure_logging(args.debug or settings.debug)

    handlers = {
        "serve": _serve,
        "update": _update,
        "migrate": _migrate,
        "status": _status,
    }
    return handlers[args.command or "serve"](settings)


if __name__ == "__main__":
    sys.exit(main())
