# External Integrations

**Analysis Date:** 2026-03-18

## APIs & External Services

**LLM/Generative AI (Installed but Status Unknown):**
- Google Generative AI (Gemini)
  - SDK/Client: `google-generativeai` v0.8.5
  - Auth: Likely via environment variable (not found in `.env`)
  - Status: Installed but no usage found in codebase

- OpenAI
  - SDK/Client: `openai` v1.75.0
  - Auth: Likely via `OPENAI_API_KEY` environment variable (not found in `.env`)
  - Status: Installed but no usage found in codebase

- LiteLLM (LLM Abstraction)
  - SDK/Client: `litellm` v1.68.1
  - Purpose: Unified interface for multiple LLMs
  - Status: Installed but no usage found in codebase

**Analytics (Installed but Status Unknown):**
- PostHog
  - SDK/Client: `posthog` v4.0.1
  - Auth: Likely via environment variable
  - Status: Installed but no usage found in codebase

- Mixpanel
  - SDK/Client: `mixpanel` v4.10.1
  - Status: Installed but no usage found in codebase

## Data Storage

**Databases:**
- SQLite 3
  - Type: File-based relational database
  - Location: `tennis.db` in project root
  - Connection: Python `sqlite3` standard library
  - Client: None (direct SQL via sqlite3 module)
  - Config: Database path set in `app.py` line 91: `app.config["DATABASE"] = os.path.join(app.root_path, "tennis.db")`
  - Schema: `schema.sql` - Two tables (`players`, `challenges`) and one view (`completed_challenges_view`)

**File Storage:**
- Local filesystem only
- Static assets: `static/` directory (PNG images)
- Templates: `templates/` directory (Jinja2 HTML templates)

**Caching:**
- Custom in-memory cache: `DataCache` class in `app.py` (line 228-256)
  - TTL-based (Time-To-Live): 10 seconds default
  - Thread-safe with lock mechanism
  - Used to cache player and challenge data for real-time updates

## Authentication & Identity

**Auth Provider:**
- Custom implementation (no external provider)
- Implementation: `app.py` with Flask-Login integration
  - User model: `User` class in `app.py` (line 132-136)
  - User loader: `load_user()` in `app.py` (line 140-152)
  - Login route: `/login` in `app.py`
  - User data stored in `players` table with `username` and `password_hash` columns
  - Password hashing: bcrypt via `bcrypt` package

**Privilege Levels:**
- Three levels stored in database: `player`, `admin`, `superadmin`
- Protected routes use decorators: `@admin_required` and `@superadmin_required` in `app.py` (lines 156-181)

**Session Management:**
- Flask-Login for session handling
- Login view: `login_tennis.html` template
- Session timeout/CSRF: Protected via Flask-WTF

## Monitoring & Observability

**Logging:**
- Python standard `logging` module configured in `app.py` (line 70)
- Logger instance: `logger = logging.getLogger(__name__)`
- Output: Console/stdout logging with INFO level
- Socket.IO logging: Enabled in debug mode via `engineio_logger` parameter

**Error Tracking:**
- No external error tracking service configured
- Default Flask error pages: `error.html` template
- Socket.IO error handler: `default_error_handler()` in `app.py` (line 2548-2549)

**Performance Monitoring:**
- No APM service detected

## CI/CD & Deployment

**Hosting:**
- Not detected - self-hosted application
- Application designed to run on standard Python runtime
- Can be deployed on any Linux/Windows/macOS with Python 3.12

**CI Pipeline:**
- Not detected - no GitHub Actions, GitLab CI, or other CI configuration found

**Web Server:**
- Production: gunicorn (WSGI server)
  - Package: `gunicorn` included in requirements
  - Recommended worker class: `eventlet` for async support

- Development: Built-in Flask development server via `socketio.run()`

**Reverse Proxy:**
- Not required but recommended for production
- Application includes `ProxyFix` middleware in `app.py` (line 80) for proxy awareness
- ProxyFix configuration: `x_for=1, x_proto=1, x_host=1` to handle X-Forwarded headers

## Environment Configuration

**Required Environment Variables:**
- `SECRET_KEY` - Flask session encryption (has default but warns if not set)
- `FLASK_DEBUG` - Debug mode toggle ("true"/"false", default: "false")
- `FLASK_HOST` - Server bind address (default: "0.0.0.0")
- `FLASK_PORT` - Server bind port (default: 5000)

**Optional Environment Variables:**
- `CORS_ALLOWED_ORIGINS` - Comma-separated list of allowed origins for CORS (required for production)
- `TEST_DATE` - Override current date for testing purposes

**Current Configuration (.env file exists):**
```
SECRET_KEY=8376579c-7d1d-486e-9eb6-0f6b42f531cd
CORS_ALLOWED_ORIGINS=http://192.168.1.8:5000
FLASK_DEBUG=true
```

**Secrets Location:**
- `.env` file (git-ignored) in project root
- Should never be committed to version control

## WebSockets & Real-Time Communication

**Implementation:**
- Socket.IO (WebSocket protocol) via Flask-SocketIO
- Async mode: eventlet
- Server configuration in `app.py` (lines 205-216)

**CORS Configuration:**
- Dynamic CORS setup based on `CORS_ALLOWED_ORIGINS` environment variable
- Fallback to "*" (allow all) if not in production and no origins configured
- Security warning logged if CORS permits all origins

**Socket.IO Events:**
- Implemented in `app.py` with `@socketio.on()` decorators
- Key events:
  - `connect` - Client connection (line 2501-2518)
  - `disconnect` - Client disconnection (line 2528-2530)
  - `request_full_update` - Client requests full data refresh (line 2534-2538)
  - `ping` - Heartbeat check (line 2543-2545)

**Real-Time Data Push:**
- Server emits updates to all connected clients via `emit_data_update()` function
- Triggered on: challenge creation, result submission, availability changes, ranking updates

## Security Features

**CSRF Protection:**
- Enabled via Flask-WTF (`CSRFProtect` in `app.py` line 115)
- Configuration for production:
  - `WTF_CSRF_SSL_STRICT = False` - Disables strict SSL referrer checking (proxy-friendly)
  - `WTF_CSRF_TRUSTED_ORIGINS` - Whitelist of trusted origins from environment

**Password Security:**
- bcrypt hashing with adaptive cost factor
- User creation/login routes enforce password hashing

**Rate Limiting:**
- Login rate limiting implemented: `MAX_LOGIN_ATTEMPTS = 5`, `LOGIN_LOCKOUT_TIME = 5 minutes`
- Enforcement in login route with thread-safe `login_attempts_lock`

**Session Security:**
- `SECRET_KEY` required for session encryption
- Session configuration defaults to secure settings
- ProxyFix middleware for proxy-aware header parsing

---

*Integration audit: 2026-03-18*
