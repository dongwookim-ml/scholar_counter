from __future__ import annotations

import pytest

from scholar_counter.config import Settings


def test_defaults_are_safe():
    settings = Settings()
    assert settings.host == "127.0.0.1", "must not bind every interface by default"
    assert settings.debug is False, "the Werkzeug debugger must be opt-in"


def test_profile_url_uses_the_configured_id():
    assert "user=ABC123" in Settings(scholar_user_id="ABC123").profile_url


def test_environment_overrides(monkeypatch):
    monkeypatch.setenv("SCHOLAR_USER_ID", "XYZ")
    monkeypatch.setenv("SCHOLAR_PORT", "9000")
    monkeypatch.setenv("SCHOLAR_DEBUG", "true")
    monkeypatch.setenv("SCHOLAR_UPDATE_HOUR", "5")

    settings = Settings.from_env()

    assert settings.scholar_user_id == "XYZ"
    assert settings.port == 9000
    assert settings.debug is True
    assert settings.update_hour == 5


@pytest.mark.parametrize(
    "value,expected",
    [("1", True), ("yes", True), ("0", False), ("no", False)],
)
def test_boolean_parsing(monkeypatch, value, expected):
    monkeypatch.setenv("SCHOLAR_AUTO_UPDATE", value)
    assert Settings.from_env().auto_update is expected


def test_rejects_out_of_range_hour(monkeypatch):
    monkeypatch.setenv("SCHOLAR_UPDATE_HOUR", "24")
    with pytest.raises(ValueError, match="must be 0-23"):
        Settings.from_env()


def test_rejects_non_numeric_port(monkeypatch):
    monkeypatch.setenv("SCHOLAR_PORT", "eighty-eighty")
    with pytest.raises(ValueError, match="must be an integer"):
        Settings.from_env()
