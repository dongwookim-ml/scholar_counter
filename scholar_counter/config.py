"""Application settings, resolved from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from exc


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime configuration. Every field is overridable via the environment."""

    scholar_user_id: str = "RkspD6IAAAAJ"
    host: str = "127.0.0.1"
    port: int = 8080
    debug: bool = False
    database: Path = PROJECT_ROOT / "scholar.db"
    request_timeout: float = 30.0
    user_agent: str = DEFAULT_USER_AGENT

    # Scheduled updates
    auto_update: bool = True
    update_hour: int = 3
    update_minute: int = 0
    # Run an update at startup if the newest snapshot is older than this.
    stale_after_hours: int = 24
    # Google Scholar rate-limits often; retry sooner than the next daily slot.
    retry_after_minutes: int = 60

    @property
    def profile_url(self) -> str:
        return f"https://scholar.google.com/citations?user={self.scholar_user_id}"

    @property
    def request_headers(self) -> dict[str, str]:
        return {"User-Agent": self.user_agent}

    @classmethod
    def from_env(cls) -> Settings:
        # `cls.field` is a slot descriptor under slots=True, so read defaults
        # off a default-constructed instance instead.
        d = cls()
        database = os.environ.get("SCHOLAR_DATABASE")
        settings = cls(
            scholar_user_id=os.environ.get("SCHOLAR_USER_ID", d.scholar_user_id),
            host=os.environ.get("SCHOLAR_HOST", d.host),
            port=_env_int("SCHOLAR_PORT", d.port),
            debug=_env_bool("SCHOLAR_DEBUG", d.debug),
            database=Path(database).expanduser() if database else d.database,
            request_timeout=float(os.environ.get("SCHOLAR_TIMEOUT", d.request_timeout)),
            user_agent=os.environ.get("SCHOLAR_USER_AGENT", d.user_agent),
            auto_update=_env_bool("SCHOLAR_AUTO_UPDATE", d.auto_update),
            update_hour=_env_int("SCHOLAR_UPDATE_HOUR", d.update_hour),
            update_minute=_env_int("SCHOLAR_UPDATE_MINUTE", d.update_minute),
            stale_after_hours=_env_int("SCHOLAR_STALE_AFTER_HOURS", d.stale_after_hours),
            retry_after_minutes=_env_int("SCHOLAR_RETRY_AFTER_MINUTES", d.retry_after_minutes),
        )
        if not 0 <= settings.update_hour <= 23:
            raise ValueError(f"SCHOLAR_UPDATE_HOUR must be 0-23, got {settings.update_hour}")
        if not 0 <= settings.update_minute <= 59:
            raise ValueError(f"SCHOLAR_UPDATE_MINUTE must be 0-59, got {settings.update_minute}")
        return settings
