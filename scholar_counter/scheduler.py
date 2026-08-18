"""Background thread that refreshes the profile once a day."""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta

from . import db
from .config import Settings
from .updater import UpdateResult, run_update

logger = logging.getLogger(__name__)

# Poll rather than sleeping until the target time: a laptop that suspends
# through the scheduled hour would otherwise wake up and wait a further day.
CHECK_INTERVAL_SECONDS = 60


class DailyUpdater:
    """Runs :func:`run_update` every day at the configured local time."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._next_run_at = self._following(datetime.now())
        self._last_result: UpdateResult | None = None

    @property
    def next_run_at(self) -> datetime:
        return self._next_run_at

    @property
    def last_result(self) -> UpdateResult | None:
        return self._last_result

    def _following(self, now: datetime) -> datetime:
        target = now.replace(
            hour=self._settings.update_hour,
            minute=self._settings.update_minute,
            second=0,
            microsecond=0,
        )
        return target if target > now else target + timedelta(days=1)

    def _is_stale(self) -> bool:
        """True when the newest snapshot predates the staleness window."""
        with db.session(self._settings.database) as conn:
            latest = db.latest_snapshot(conn)

        if latest is None:
            return True
        age = datetime.now() - datetime.fromisoformat(latest["captured_at"])
        return age > timedelta(hours=self._settings.stale_after_hours)

    def _run(self) -> None:
        result = run_update(self._settings)
        self._last_result = result
        now = datetime.now()

        if result.success:
            self._next_run_at = self._following(now)
        else:
            # Scholar rate-limits routinely; waiting a full day would leave a
            # visible hole in the history for a failure that clears in minutes.
            self._next_run_at = now + timedelta(minutes=self._settings.retry_after_minutes)
            logger.warning("Update failed (%s); retrying sooner.", result.message)
        logger.info(
            "Next scheduled update: %s",
            self._next_run_at.isoformat(sep=" ", timespec="minutes"),
        )

    def _loop(self) -> None:
        # Catch up first: the machine may have been asleep at the scheduled time.
        if self._is_stale():
            logger.info("Latest snapshot is stale; updating now.")
            self._run()
        else:
            logger.info(
                "Next scheduled update: %s",
                self._next_run_at.isoformat(sep=" ", timespec="minutes"),
            )

        while not self._stop.wait(CHECK_INTERVAL_SECONDS):
            if datetime.now() >= self._next_run_at:
                self._run()

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._loop, name="scholar-daily", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None
