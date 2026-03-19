import os
import pytest

# Set DB_PATH to a temp file BEFORE importing app (app reads env at import time)
# Each test that needs a custom DB_PATH should use monkeypatch instead
from app import app as flask_app


@pytest.fixture
def app():
    """Create application for testing."""
    flask_app.config["TESTING"] = True
    yield flask_app


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()
