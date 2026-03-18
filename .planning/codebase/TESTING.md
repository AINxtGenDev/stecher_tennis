# Testing Patterns

**Analysis Date:** 2026-03-18

## Test Framework

**Status:** Testing infrastructure is configured but no test files currently exist in the codebase.

**Runner:**
- pytest (present in requirements.txt)
- Config: No `pytest.ini`, `setup.cfg`, or `pyproject.toml` configuration file found
- Uses pytest default configuration

**Assertion Library:**
- No assertion library explicitly imported (would use pytest's built-in `assert` statements)

**Additional Testing Packages:**
- Flask-Testing available (line 35 in requirements.txt)
- coverage available (line 20 in requirements.txt) for test coverage measurement

**Run Commands:**
```bash
pytest                          # Run all tests
pytest -v                       # Verbose output
pytest --cov=app               # Coverage report
pytest -x                       # Stop on first failure
pytest tests/                   # Run tests in tests/ directory
```

## Test File Organization

**Current State:**
- No test files exist in the codebase
- No tests/ directory structure

**Recommended Pattern (based on Flask best practices):**
- Co-located with application: `test_app.py` at project root
- Or separate directory: `tests/test_*.py`
- Test discovery via pytest's default pattern matching

**Structure:**
```
/home/nuc8/05_development/02_python/01_stecher_tennis/
├── app.py
├── test_app.py                # Or tests/test_app.py
├── tests/
│   ├── conftest.py           # Shared fixtures
│   ├── test_auth.py
│   ├── test_challenges.py
│   ├── test_players.py
│   └── test_socketio.py
```

## Test Structure Patterns (Best Practice for This Codebase)

**Flask Test Client Setup (recommended pattern):**
```python
import pytest
from app import app

@pytest.fixture
def client():
    """Create test client for Flask application."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            yield client

@pytest.fixture
def runner():
    """Create CLI runner for commands."""
    return app.test_cli_runner()
```

**Database Fixture (recommended pattern):**
```python
@pytest.fixture
def db():
    """Create and initialize test database."""
    app.config['DATABASE'] = ':memory:'  # Use in-memory SQLite
    with app.app_context():
        init_db()
        yield get_db()
        get_db().close()
```

**Authentication Fixture (recommended pattern):**
```python
@pytest.fixture
def auth_client(client, db):
    """Create authenticated test client."""
    # Create test user
    db.execute(
        "INSERT INTO players (name, username, password_hash, privilege_level) "
        "VALUES (?, ?, ?, ?)",
        ("Test User", "testuser", bcrypt.hashpw(b"password", bcrypt.gensalt()).decode(), "player")
    )
    db.commit()

    # Login
    client.post('/login', data={
        'username': 'testuser',
        'password': 'password'
    })
    return client
```

## Mocking

**Framework:** unittest.mock (standard library) or pytest-mock recommended

**Patterns for This Codebase:**

**1. Mock database operations:**
```python
from unittest.mock import patch, MagicMock

def test_get_active_challenges():
    with patch('app.get_db') as mock_db:
        mock_db.return_value.execute.return_value.fetchall.return_value = []
        result = get_active_challenges()
        assert result == []
```

**2. Mock datetime for time-dependent tests:**
```python
from unittest.mock import patch
from datetime import datetime

def test_expired_challenge_resolution():
    test_time = datetime(2025, 3, 20, 10, 0, 0)
    with patch('app.get_current_time') as mock_time:
        mock_time.return_value = test_time
        # Test behavior at specific time
```

**3. Mock environment variables:**
```python
from unittest.mock import patch
import os

def test_debug_mode():
    with patch.dict(os.environ, {"FLASK_DEBUG": "true"}):
        # Test with debug mode enabled
```

**What to Mock:**
- External API calls (none currently in this codebase)
- System time (for deadline/expiry testing)
- Database operations (for unit testing logic without DB)
- Environment variables (for config testing)
- Flask g object for request-scoped globals

**What NOT to Mock:**
- Database for integration tests (use in-memory SQLite instead)
- Flask request context (use test client instead)
- Authentication decorators (test them end-to-end)
- Core serialization functions (test with real data)

## Fixtures and Factories

**Test Data Pattern (recommended):**
```python
@pytest.fixture
def sample_player(db):
    """Create a test player."""
    db.execute(
        "INSERT INTO players (name, username, password_hash, privilege_level, rank, available, is_ranked_player) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("John Doe", "johndoe", bcrypt.hashpw(b"pass123", bcrypt.gensalt()).decode(),
         "player", 1, 1, 1)
    )
    db.commit()
    return db.execute("SELECT * FROM players WHERE username = 'johndoe'").fetchone()

@pytest.fixture
def sample_challenge(db, sample_player):
    """Create a test challenge."""
    db.execute(
        "INSERT INTO players (name, username, password_hash, rank, available, is_ranked_player) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("Jane Doe", "janedoe", bcrypt.hashpw(b"pass456", bcrypt.gensalt()).decode(),
         2, 1, 1)
    )
    db.commit()
    opponent = db.execute("SELECT * FROM players WHERE username = 'janedoe'").fetchone()

    from datetime import datetime, timedelta
    deadline = datetime.now() + timedelta(days=10)

    db.execute(
        "INSERT INTO challenges (challenger_id, opponent_id, timestamp, deadline, resolved) "
        "VALUES (?, ?, ?, ?, ?)",
        (sample_player['id'], opponent['id'], datetime.now(), deadline, 0)
    )
    db.commit()
    return db.execute("SELECT * FROM challenges ORDER BY id DESC LIMIT 1").fetchone()
```

**Location:**
- `tests/conftest.py` for shared fixtures
- Fixtures used across multiple test modules

## Coverage

**Requirements:** No explicit coverage requirements enforced (no .coveragerc file)

**View Coverage:**
```bash
pytest --cov=app --cov-report=html    # Generate HTML report
pytest --cov=app --cov-report=term    # Terminal report
```

**Coverage Report Location:**
- `htmlcov/index.html` when using `--cov-report=html`

**Target (Recommended):**
- Core business logic: >80% coverage
- Route handlers: >70% coverage
- Utility functions: >90% coverage
- Error handling: 100% coverage for different error paths

## Test Types

**Unit Tests (recommended scope):**
- Test individual functions in isolation
- Use mocks for database access, external dependencies
- Test serialization functions: `serialize_player()`, `serialize_challenge()`
- Test utility functions: `generate_username()`, `create_pyramid()`
- Test ranking logic: `rerank_players()` with mock DB
- Test cache: `DataCache` methods directly

**Example:**
```python
def test_generate_username_unique():
    """Username generation should produce unique values."""
    db = MagicMock()
    db.execute.return_value.fetchone.return_value = None  # No existing user

    username = generate_username("John Doe", db)
    assert username == "johndoe"

def test_generate_username_increments():
    """Username generation should append number if taken."""
    db = MagicMock()
    # First call: user exists, second call: doesn't exist
    db.execute.return_value.fetchone.side_effect = [("1",), None]

    username = generate_username("John Doe", db)
    assert username == "johndoe1"
```

**Integration Tests (recommended scope):**
- Test route handlers with test client
- Use in-memory SQLite database (`:memory:`)
- Test database operations with real schema
- Test authentication flows end-to-end
- Test challenge creation and result submission
- Test privilege level enforcement

**Example:**
```python
def test_login_success(client, db):
    """Successful login should set session."""
    db.execute(
        "INSERT INTO players (name, username, password_hash) "
        "VALUES (?, ?, ?)",
        ("Test", "testuser", bcrypt.hashpw(b"pass123", bcrypt.gensalt()).decode())
    )
    db.commit()

    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'pass123'
    }, follow_redirects=True)

    assert response.status_code == 200
    # Check that user is authenticated (can access protected page)

def test_login_failure(client):
    """Incorrect credentials should deny access."""
    response = client.post('/login', data={
        'username': 'nonexistent',
        'password': 'wrongpass'
    }, follow_redirects=True)

    assert b'Ung' in response.data  # German error message
```

**E2E Tests (if needed):**
- Not currently implemented
- Selenium for browser-based testing
- Test WebSocket connections and real-time updates
- Test full user workflow: login → challenge → result

## Common Patterns

**Async Testing (SocketIO):**
```python
import pytest
from flask_socketio import SocketIOTestClient

@pytest.fixture
def socketio_client(app):
    """Create SocketIO test client."""
    with app.test_client() as client:
        # Authenticate first
        client.post('/login', data={'username': 'testuser', 'password': 'pass'})

        socketio_client = client.socketio
        socketio_client.connect()
        yield socketio_client
        socketio_client.disconnect()

def test_websocket_connect(socketio_client):
    """Test WebSocket connection."""
    assert socketio_client.is_connected()

def test_emit_data_update(socketio_client):
    """Test data update emission."""
    socketio_client.emit('request_full_update')
    # Verify response
    data = socketio_client.get_received()
    assert len(data) > 0
```

**Database State Testing:**
```python
def test_challenge_creation(auth_client, db):
    """Test that challenge is created correctly."""
    # Get opponent ID
    opponent = db.execute(
        "SELECT id FROM players WHERE username = 'opponent'"
    ).fetchone()

    # Create challenge
    response = auth_client.post('/challenge', json={
        'opponent_id': opponent['id']
    })

    assert response.status_code == 200

    # Verify database state
    challenge = db.execute(
        "SELECT * FROM challenges ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert challenge is not None
    assert challenge['resolved'] == 0
```

**Error Testing:**
```python
def test_challenge_with_unavailable_opponent(auth_client, db):
    """Test challenging unavailable opponent returns error."""
    opponent = db.execute(
        "SELECT id FROM players WHERE username = 'opponent'"
    ).fetchone()

    # Mark opponent unavailable
    db.execute("UPDATE players SET available = 0 WHERE id = ?", (opponent['id'],))
    db.commit()

    response = auth_client.post('/challenge', json={
        'opponent_id': opponent['id']
    })

    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data

def test_invalid_datetime_parsing():
    """Test serialize_challenge handles invalid datetime."""
    challenge = {
        'deadline': 'invalid-date-format',
        'timestamp': '2025-03-18 10:00:00'
    }

    result = serialize_challenge(challenge)
    assert result['deadline_formatted'] == 'N/A'
```

**Rate Limiting Testing:**
```python
def test_login_rate_limiting(client):
    """Test login attempts are rate limited."""
    for i in range(5):
        response = client.post('/login', data={
            'username': 'testuser',
            'password': 'wrongpass'
        }, follow_redirects=True)
        assert response.status_code == 200

    # 6th attempt should be blocked
    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'wrongpass'
    }, follow_redirects=True)

    assert b'Zu viele' in response.data  # German rate limit message
    assert response.status_code == 200  # Redirected, not allowed to retry
```

## Test Configuration

**Environment Setup (conftest.py):**
```python
import os
import pytest
from app import app, get_db, init_db

@pytest.fixture
def app_config():
    """Configure app for testing."""
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
    app.config['DATABASE'] = ':memory:'  # In-memory SQLite
    return app

@pytest.fixture
def app_context(app_config):
    """Create app context for testing."""
    with app_config.app_context():
        yield app_config
```

**Conftest Location:** `tests/conftest.py`

---

*Testing analysis: 2026-03-18*
