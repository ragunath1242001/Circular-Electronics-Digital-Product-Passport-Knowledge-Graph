from app.core.config import Settings


def test_settings_read_environment(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("APP_NAME", "Test Passport")
    monkeypatch.setenv("APP_DEBUG", "true")

    settings = Settings(_env_file=None)

    assert settings.app_name == "Test Passport"
    assert settings.app_debug is True

