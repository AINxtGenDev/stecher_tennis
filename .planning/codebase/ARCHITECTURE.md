# Architecture

**Analysis Date:** 2026-03-18

## Pattern Overview

**Overall:** Monolithic Flask application with real-time WebSocket updates

**Key Characteristics:**
- Single file application (`app.py`, 2559 lines)
- Request-response with real-time broadcast layer via Socket.IO
- Event-driven updates to connected clients
- Complex business logic for ranking and challenge eligibility co-located with routes
- Thread-safe caching layer for frequently accessed data

## Layers

**Presentation Layer:**
- Purpose: HTML rendering and user interface
- Location: `templates/` directory
- Contains: Jinja2 templates (index.html, admin.html, db_settings.html, login_tennis.html, error.html, stecher_start.html)
- Depends on: Flask route responses, Socket.IO client library
- Used by: Web browsers via HTTP requests and WebSocket connections

**API Layer:**
- Purpose: HTTP endpoints for data retrieval and state mutation
- Location: `app.py` (routes starting at line 1024)
- Contains: Flask routes with `@app.route()` decorators
- Depends on: Database access layer, business logic layer
- Used by: Frontend JavaScript, form submissions

**Business Logic Layer:**
- Purpose: Implement tennis ranking system rules and algorithms
- Location: `app.py` (core functions at lines 443-867)
- Contains: Functions like `eligible_opponents_for()`, `rerank_players()`, `resolve_expired_challenges()`, `create_pyramid()`
- Depends on: Database access layer, utility functions
- Used by: Route handlers, WebSocket event handlers

**Data Access Layer:**
- Purpose: Database connection and query execution
- Location: `app.py` (lines 368-441)
- Contains: `get_db()`, `close_db()`, `init_db()` functions using SQLite3
- Depends on: SQLite database file at `tennis.db`
- Used by: All business logic and route handlers

**Real-Time Communication Layer:**
- Purpose: Broadcast ranking/challenge updates to connected clients
- Location: `app.py` (lines 949-977, 2502-2544)
- Contains: Socket.IO event emitters (`emit_to_room()`, `emit_data_update()`) and handlers
- Depends on: SocketIO library, Flask application context
- Used by: Route handlers after state mutations

**Security Layer:**
- Purpose: Authentication, authorization, and CSRF protection
- Location: `app.py` (lines 83-181)
- Contains: Flask-Login user loader, decorators (`admin_required`, `superadmin_required`), rate limiting
- Depends on: bcrypt password hashing, Flask-WTF CSRF protection
- Used by: Route handlers via `@login_required`, `@admin_required` decorators

**Serialization & Formatting Layer:**
- Purpose: Convert database rows and Python objects to JSON-safe formats
- Location: `app.py` (lines 228-352)
- Contains: `DataCache` class, `serialize_player()`, `serialize_challenge()` functions
- Depends on: datetime parsing, JSON encoding
- Used by: Route handlers before returning responses

## Data Flow

**Challenge Creation Flow:**

1. User submits challenge via POST to `/challenge` route (line 1365)
2. Route validates: player availability, eligibility rules, active challenge status
3. If valid, `INSERT` into `challenges` table with `deadline = now + 10 days`
4. `emit_data_update("general")` broadcasts new challenge to all connected clients
5. Frontend receives Socket.IO event and re-renders pyramid/challenge lists
6. WebSocket connected clients in room `"tennis_updates"` receive the update

**Challenge Resolution Flow:**

1. User submits result via POST to `/submit_result` route (line 1580)
2. Route validates match details (winner, loser, score)
3. Updates `challenges` table: set `result`, `resolved=1`, `resolved_at=now`
4. Calls `rerank_players()` to update ranking: winner moves up, loser moves down (line 765)
5. May set blocking periods: `block_opponent_until` (7 days) for both players
6. If new player won, updates `is_new=0` flag
7. Calls `resolve_expired_challenges()` to clean up any timeouts
8. Broadcasts `emit_data_update("general")` to all clients
9. Frontend updates pyramid and active challenges display

**Real-Time Data Fetch:**

1. Client connects via WebSocket (handler `handle_connect()` at line 2502)
2. Client emits `"request_full_update"` event
3. Server calls `get_realtime_data_cached()` (line 937)
4. Returns pyramid, active challenges, player list, current user info
5. Emits back to client via Socket.IO response

**State Management:**

- **Ranking State**: `players.rank` column — single source of truth
- **Challenge State**: `challenges` table with `resolved` flag and `result` field
- **Availability State**: `players.available` flag, `unavailable_since` timestamp
- **Blocking State**: `block_challenger_until`, `block_opponent_until` timestamps
- **Cache State**: In-memory 10-second TTL cache for `get_realtime_data()` (class `DataCache` at line 228)

## Key Abstractions

**Player Ranking Pyramid:**
- Purpose: Visual representation of current standings (1-45 players)
- Examples: Rendered via `create_pyramid()` function (line 443), displayed in `templates/index.html`
- Pattern: 2D array where row sizes follow sequence [1,2,3,4,5,6,7,8,9] to form triangle

**Challenge Lifecycle:**
- Purpose: Encapsulate a single match from proposal to resolution
- Examples: Database row in `challenges` table
- States: Active (resolved=0), Resolved (resolved=1), Expired (deadline passed)
- Pattern: Timestamp-based expiration checked by `resolve_expired_challenges()` (line 793)

**User Privilege Levels:**
- Purpose: Control access to admin and superadmin features
- Examples: `players.privilege_level` column (values: "player", "admin", "superadmin")
- Pattern: Checked via `@admin_required` (line 156) and `@superadmin_required` (line 170) decorators

**Eligibility Calculator:**
- Purpose: Determine which opponents a challenger can face based on rank rules
- Examples: `eligible_opponents_for()` function (line 667)
- Pattern: Rank-based distance rules vary by tier; unavailable players extend the searchable range

## Entry Points

**Web Application Entry:**
- Location: `app.py` (lines 76-216)
- Triggers: `python app.py` or via gunicorn in production
- Responsibilities: Initialize Flask app, configure CSRF/auth, initialize database if needed, start SocketIO server

**Login Route:**
- Location: `/login` route at line 1029
- Triggers: GET/POST requests to `/login` URL
- Responsibilities: Validate credentials, rate limit failed attempts, establish Flask-Login session

**Index/Dashboard Route:**
- Location: `/index` route at line 1132
- Triggers: GET requests after authentication
- Responsibilities: Render main pyramid view with current user context

**Admin Panel:**
- Location: `/admin` route at line 1168
- Triggers: GET requests from admin/superadmin users only
- Responsibilities: Show player management and challenge administration UI

**API Endpoints:**
- Location: Lines 1116-2174
- Triggers: AJAX/JSON requests from frontend
- Responsibilities: Return JSON data for dynamic UI updates without page reload

**WebSocket Event Handlers:**
- Location: Lines 2502-2544
- Triggers: Socket.IO `connect`, `disconnect`, `request_full_update`, `ping` events
- Responsibilities: Send full game state to newly connected clients, maintain presence

## Error Handling

**Strategy:** Try-catch at database layer, validation at route layer, user feedback via flash messages and JSON error responses

**Patterns:**

- **Database Errors** (`sqlite3.Error`): Logged via logger.exception(), transactions rolled back, 500-level response or flash message
  - Examples: Lines 378, 437, 513, 788

- **Validation Errors**: Return 400 status with JSON `{"error": "message"}` or redirect with flash message
  - Examples: Lines 1371-1481 (challenge validation), 1080-1099 (login validation)

- **Authentication Errors**: Flask-Login's `@login_required` redirects to login page; `@admin_required`/`@superadmin_required` flash and redirect to index/admin
  - Examples: Lines 156-181

- **Time/Parse Errors**: Try-except with fallback to None or default value; logged as warnings
  - Examples: Lines 269-277 (datetime parsing in serialize_player)

## Cross-Cutting Concerns

**Logging:**
- Tool: Python `logging` module configured at line 70
- Approach: Logger initialized as `logger = logging.getLogger(__name__)` at line 71
- Key log points: App startup (line 74), DB operations (378, 437), eligibility rules (689), challenge resolution (800+)

**Validation:**
- Approach: Each route validates inputs before database modification
- Examples: Challenger/opponent existence (lines 1374-1379), availability flags (1383-1409), eligibility rules (1450)
- Pattern: Return early with error response if validation fails

**Authentication:**
- Approach: Flask-Login session-based via `current_user` context variable
- User model: `User` class at line 132 (id, username, privilege_level)
- User loader: Line 140, queries `players` table by id
- Session storage: Flask session cookie with `SECRET_KEY` (line 83)

**Time Management:**
- Approach: Centralized `get_current_time()` function (line 355) allows test date override via `TEST_DATE` env var
- Used for: Challenge deadlines, blocking period expiration, active challenge filtering
- Pattern: All time-based queries use `get_current_time()` instead of `datetime.now()`

---

*Architecture analysis: 2026-03-18*
