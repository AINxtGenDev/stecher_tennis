# Coding Conventions

**Analysis Date:** 2026-03-18

## Naming Patterns

**Files:**
- Single main application file: `app.py` (2,559 lines)
- Templates use descriptive names with HTML extension: `admin.html`, `login_tennis.html`, `index.html`
- Database file: `tennis.db` (SQLite)
- Configuration: `schema.sql` for database schema, `initial_players.json` for seed data

**Functions:**
- snake_case for all function names (e.g., `get_active_challenges()`, `serialize_player()`, `eligible_opponents_for()`)
- Descriptive verb-noun pattern: `get_*`, `set_*`, `create_*`, `resolve_*`, `serialize_*`, `emit_*`, `handle_*`
- Event handlers prefixed with `handle_`: `handle_connect()`, `handle_disconnect()`, `handle_request_full_update()`
- Route handler functions match route names: `/index` → `index()`, `/admin` → `admin()`

**Variables:**
- snake_case for all variable names
- Descriptive names: `challenger_id`, `opponent_id`, `deadline`, `timestamp`, `player_record`, `login_attempts`
- Database cursors: `cur`, `cursor` (not always prefixed)
- Collections: `players`, `challenges`, `opponents_list`, `pyramid`
- Boolean flags: `is_available`, `available`, `login_successful`, `opponent_blocked`, `debug_mode`
- Datetime variables: `now_dt`, `timestamp`, `deadline`, `dt` (context-specific conversions)

**Types & Classes:**
- PascalCase for classes: `User`, `DataCache`, `CustomJSONEncoder`, `CustomJSONProvider`
- Constants in UPPER_SNAKE_CASE: `APP_VERSION`, `MAX_LOGIN_ATTEMPTS`, `LOGIN_LOCKOUT_TIME`
- Private/protected convention: Not explicitly used; underscore not used for module internals

## Code Style

**Formatting:**
- black is available in requirements.txt for code formatting
- 79-character implicit line limit (Flask convention, not strictly enforced)
- UTF-8 encoding declaration at file start: `# -*- coding: utf-8 -*-`
- 4-space indentation throughout

**Linting:**
- flake8 available in requirements.txt for code linting
- No .flake8 or setup.cfg configuration file present; uses default rules
- Code uses standard Python conventions (PEP 8 mostly)

**Line Length & Wrapping:**
- Long imports wrapped in parentheses:
  ```python
  from flask_socketio import (
      SocketIO,
      emit,
      join_room,
      leave_room,
  )
  ```
- Long parameter lists broken across lines:
  ```python
  db.execute(
      "SELECT c.*, p1.name as challenger_name FROM challenges c "
      "JOIN players p1 ON c.challenger_id = p1.id "
      "WHERE c.resolved = 0 AND c.deadline > ?",
      (now_str,),
  )
  ```

## Import Organization

**Order:**
1. Standard library imports (`re`, `os`, `sqlite3`, `json`, `logging`, `time`, `datetime`)
2. Third-party framework imports (`flask`, `flask_login`, `flask_socketio`, `werkzeug`)
3. Security imports (`bcrypt`, `functools`)
4. Project-specific imports (via `dotenv`)

**Path Aliases:**
- Not used. All imports are absolute
- Database, templates, and static files accessed via `app.root_path` and `app.config["DATABASE"]`

**Import Style:**
- Individual imports: `from flask import Flask, g, request, jsonify, render_template`
- Multi-line imports with trailing comma (PEP 8):
  ```python
  from flask_login import (
      LoginManager,
      UserMixin,
      login_user,
  )
  ```

## Error Handling

**Exception Hierarchy:**
- sqlite3.Error for database errors
- sqlite3.IntegrityError for constraint violations (UNIQUE, FOREIGN KEY)
- ValueError, TypeError for parsing failures (datetime strings)
- Exception (catch-all) for unexpected errors

**Pattern - Try/Except Blocks:**
```python
try:
    # Operation
    cur = db.execute("SELECT ...")
    result = cur.fetchone()
except sqlite3.IntegrityError as e:
    error_string = str(e).lower()
    if "unique constraint failed" in error_string:
        # Handle uniqueness violation
        logger.warning(f"...")
        return jsonify({"error": "..."}), 400
    else:
        # Handle other integrity errors
        logger.exception(f"...")
        return jsonify({"error": "..."}), 500
except sqlite3.Error as e:
    logger.exception(f"SQLite error: {e}")
    return jsonify({"error": "..."}), 500
except Exception as e:
    logger.exception(f"Unexpected error: {e}")
    return jsonify({"error": "..."}), 500
```

**Error Responses:**
- Return JSON with error key: `jsonify({"error": "message"})`
- Include appropriate HTTP status codes (400, 404, 500)
- Never expose internal exceptions to client in production
- All error responses include logging via `logger.exception()` or `logger.error()`

## Logging

**Framework:** Python's built-in `logging` module

**Setup:**
```python
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
```

**Patterns:**
- INFO: Application startup, configuration, successful operations
  ```python
  logger.info(f"Starting Tennis App version: {APP_VERSION}")
  logger.info(f"New player '{newplayer_name}' inserted with temporary ID {newplayer_id}")
  ```
- WARNING: Security warnings, deprecated operations, recovery from issues
  ```python
  logger.warning("SECURITY WARNING: Using default secret key...")
  logger.warning(f"IntegrityError (UNIQUE constraint) for new player '{newplayer_name}'")
  ```
- ERROR: Significant failures that require attention
  ```python
  logger.error("Failed to retrieve data for index page rendering.")
  logger.error(f"New player '{newplayer_name}' was unexpectedly deleted during re-ranking")
  ```
- EXCEPTION: Caught exceptions with full traceback
  ```python
  logger.exception("Database connection failed.")
  logger.exception("Error in api_realtime_data")
  ```

**Log Messages:**
- Include relevant context: player names, IDs, user information
- Use f-strings for variable interpolation
- Multi-parameter logging with `%s` format for structured info:
  ```python
  logger.info(
      "New player challenge successfully processed: %s (ID: %s, Rank: %s) vs %s (ID: %s, Rank: %s)",
      newplayer_name, newplayer_id, new_player_current_rank,
      opponent_name, opponent_id, opponent_new_rank,
  )
  ```

## Comments

**When to Comment:**
- Section headers using `--- COMMENT ---` format (uppercase, surrounded by dashes):
  ```python
  # --- NEW: Imports for Authentication and Security ---
  # --- MODIFIED: Keep ProxyFix for general proxy awareness ---
  # --- Socket.IO and CORS Configuration ---
  # --- ROUTES ---
  # --- SocketIO Event Handlers ---
  ```
- Significant algorithmic changes or business logic
- Security and configuration decisions:
  ```python
  # This is the definitive fix for the "referrer does not match host" error.
  app.config["WTF_CSRF_SSL_STRICT"] = False
  ```
- Inline comments for non-obvious logic (rare)

**JSDoc/TSDoc:**
- Only one docstring observed at line 980:
  ```python
  def generate_username(full_name, db):
      """Generates a unique username based on the player's full name."""
  ```
- Generally minimal use of docstrings; rely on function names and comments

**Comment Markers:**
- NEW: Indicates newly added functionality
- MODIFIED: Indicates changed existing functionality
- CRITICAL: Indicates important configuration/security fix
- Most comments use forward-slash pattern `---` for section headers

## Function Design

**Size Guidelines:**
- Ranges from 5 lines (simple getters) to 200+ lines (complex business logic)
- Average route handler: 50-150 lines (validates input, executes queries, handles errors, returns response)
- Serialization functions: 20-50 lines (datetime conversion and formatting)
- Complex operations like `newplayer_challenge()` can exceed 200 lines with full error handling

**Parameters:**
- Typically 1-3 parameters per function
- Database queries use positional arguments with `?` placeholders (parameterized queries)
- Flask request data accessed via global `request` object, not passed as parameters
- Optional parameters with defaults:
  ```python
  def DataCache.__init__(self, ttl=10):
      self.ttl = ttl

  def get_completed_challenges(limit=50):
      # Implementation
  ```

**Return Values:**
- Database read functions: Return raw cursor rows or dicts
- Serialization functions: Return modified dicts with formatted timestamps
- Route handlers: Return `render_template()`, `redirect()`, or `jsonify()` responses
- API endpoints return JSON: `jsonify({"success": True, "data": {...}})` or `jsonify({"error": "..."}), status_code`
- SocketIO handlers: Use `emit()` to send responses

## Module Design

**Single File Architecture:**
- Entire backend in `app.py` (~2,500 lines)
- No module separation or packages
- All imports at file top, followed by initialization and configuration
- Classes and functions defined in logical order:
  1. Setup and configuration
  2. Authentication (User class, decorators, login manager)
  3. Data structures (DataCache)
  4. Serialization functions
  5. Helper/utility functions
  6. Route handlers
  7. WebSocket handlers
  8. Main execution

**Exports:**
- No explicit `__all__` definition
- Flask app (`app`) and Socket.IO instance (`socketio`) are module-level globals used for decorators

**Approach:**
- Route decorators stacked directly above handler functions:
  ```python
  @app.route("/login", methods=["GET", "POST"])
  @login_required
  def login():
      # Implementation
  ```
- Utility functions defined before use
- Ordered for readability: setup → logic → routes → handlers

## Database Access

**Pattern:**
- Global function `get_db()` returns SQLite connection from Flask `g` object (request-scoped)
- All queries use parameterized statements with `?` placeholders to prevent SQL injection
- Row factory set to `sqlite3.Row` for dict-like access:
  ```python
  g.db.row_factory = sqlite3.Row
  # Then: player = dict(row)
  ```
- Pragma settings for safety:
  - `PRAGMA journal_mode=WAL` (Write-Ahead Logging)
  - `PRAGMA foreign_keys = ON` (Enable foreign key constraints)

**Transaction Style:**
- Context manager usage: `with db:` for automatic commit/rollback
- Manual `db.commit()` after execute operations
- `db.rollback()` on exception

## Decorator Usage

**Route Decorators:**
- Authentication: `@login_required` from flask-login
- Custom authorization: `@admin_required`, `@superadmin_required` (custom decorators defined at lines 156-181)
- SocketIO events: `@socketio.on("event_name")`
- Flask hooks: `@app.teardown_appcontext`, `@login_manager.user_loader`

**Custom Decorator Pattern:**
```python
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.privilege_level not in [...]:
            flash("Message", "danger")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated_function
```

## Code Organization

**Global State:**
- `app`: Flask application instance
- `logger`: Logger instance configured at module level
- `socketio`: Socket.IO instance with eventlet async mode
- `csrf`: CSRF protection instance
- `login_manager`: Flask-Login manager instance
- `data_cache`: DataCache instance for 10-second caching
- `login_attempts`, `login_attempts_lock`: Thread-safe rate limiting dict

**Thread Safety:**
- Lock objects used for race-condition safety: `login_attempts_lock`, `DataCache.lock`
- Lock acquired with context manager: `with lock:`
- SQLite accessed via connection pooling (Flask `g` object is per-request)

---

*Convention analysis: 2026-03-18*
