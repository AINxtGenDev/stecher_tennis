"""Tests for DB_PATH environment variable configuration."""
import os
import importlib


def test_db_path_env_var(tmp_path, monkeypatch):
    """When DB_PATH is set, app.config['DATABASE'] uses it."""
    test_db = str(tmp_path / "custom" / "test.db")
    monkeypatch.setenv("DB_PATH", test_db)
    # Must reimport app to pick up env var change (app reads env at import time)
    import app as app_module
    importlib.reload(app_module)
    try:
        assert app_module.app.config["DATABASE"] == test_db
    finally:
        # Restore original state
        monkeypatch.delenv("DB_PATH", raising=False)
        importlib.reload(app_module)


def test_db_path_creates_parent_dirs(tmp_path, monkeypatch):
    """When DB_PATH points to a non-existent directory, parent dirs are created."""
    test_db = str(tmp_path / "deep" / "nested" / "dir" / "test.db")
    monkeypatch.setenv("DB_PATH", test_db)
    import app as app_module
    importlib.reload(app_module)
    try:
        parent_dir = os.path.dirname(test_db)
        assert os.path.isdir(parent_dir)
    finally:
        monkeypatch.delenv("DB_PATH", raising=False)
        importlib.reload(app_module)


def test_db_path_fallback(monkeypatch):
    """When DB_PATH is not set, falls back to tennis.db in app root."""
    monkeypatch.delenv("DB_PATH", raising=False)
    import app as app_module
    importlib.reload(app_module)
    assert app_module.app.config["DATABASE"].endswith("tennis.db")
    assert os.path.dirname(app_module.app.config["DATABASE"]) == app_module.app.root_path
