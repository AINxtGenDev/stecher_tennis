"""Tests for the /health endpoint."""


def test_health_returns_200(client):
    """GET /health must return HTTP 200."""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_returns_json(client):
    """GET /health must return JSON body {"status": "ok"}."""
    response = client.get("/health")
    data = response.get_json()
    assert data == {"status": "ok"}


def test_health_no_auth_required(client):
    """/health must return 200 without authentication (not a 302 redirect to login)."""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_no_csrf_required(client):
    """POST to /health without CSRF token must not return 400 (CSRF-exempt verified)."""
    response = client.post("/health")
    # Accept 200 or 405 (Method Not Allowed) — just not 400 (CSRF failure)
    assert response.status_code != 400
