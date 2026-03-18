# Phase 1: App Container - Context

**Gathered:** 2026-03-18
**Status:** Ready for planning

<domain>
## Phase Boundary

A Docker image that runs the Flask-SocketIO app correctly — single eventlet worker, non-root user, configurable DB path, health endpoint, minimal image size. Multi-stage Dockerfile with python:3.12-slim, .dockerignore, and gunicorn CMD.

</domain>

<decisions>
## Implementation Decisions

### Production dependencies
- Create a new `docker-requirements.txt` (do NOT overwrite `prod-requirements.txt`)
- Core stack: Flask, Flask-SocketIO, Flask-Login, Flask-WTF, flask-cors, gunicorn, eventlet, greenlet, python-engineio, python-socketio, bcrypt, Werkzeug, itsdangerous, Jinja2, click, python-dotenv
- Also include: requests, pydantic (used at runtime)
- Exclude: google-generativeai, openai, numpy, scipy, Pillow, beautifulsoup4, litellm, posthog, mixpanel
- Pin exact versions (generate from current conda env)

### Health endpoint
- `GET /health` returns `{"status": "ok"}` with HTTP 200
- Publicly accessible (no authentication required)
- CSRF-exempt so curl and Docker HEALTHCHECK work without tokens
- No database connectivity check — simple and fast

### DB_PATH migration
- Read `DB_PATH` env var; if unset, fall back to `tennis.db` in project root (preserves current non-Docker behavior)
- Auto-create parent directories (`os.makedirs(parent, exist_ok=True)`) on startup if they don't exist
- `init_db()` auto-populates with `initial_players.json` if the DB doesn't exist at the configured path (same as current behavior)
- Update `backup_tennis_db.sh` to respect `DB_PATH` env var

### Claude's Discretion
- Multi-stage Dockerfile structure (builder vs runtime stages)
- .dockerignore contents (follow CONT-03 requirement)
- Non-root user name and UID/GID choice
- Gunicorn timeout value and logging configuration
- Docker HEALTHCHECK interval/timeout/retries

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Deployment reference
- `documentation/99_rpi.txt` — Current production setup on RPi: systemd service config, Caddyfile, gunicorn flags, DuckDNS cron, environment file layout

### Dependency files
- `prod-requirements.txt` — Current production dependencies (reference for what exists; Docker gets its own file)
- `requirements.txt` — Full dev dependencies with pinned versions (source for version pins)
- `environment.yml` — Conda environment specification

### Application entry point
- `app.py` lines 2557-2560 — Application startup, Flask app initialization and socketio.run()
- `app.py` lines 36-107 — Configuration loading and Flask app setup
- `app.py` lines 368-390 — `get_db()` and database connection setup (where DB_PATH needs to be wired in)

### Database
- `schema.sql` — Database schema definition
- `initial_players.json` — Seed data loaded by init_db()

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `prod-requirements.txt`: Starting point for Docker deps list (trim and pin)
- `environment.yml`: Has pinned versions that can be used for `docker-requirements.txt`
- `documentation/99_rpi.txt`: Existing gunicorn command, systemd service, Caddyfile — all inform Docker config

### Established Patterns
- Database path currently hardcoded via `app.config["DATABASE"] = os.path.join(app.root_path, "tennis.db")` — needs `DB_PATH` env var override
- `get_db()` uses Flask `g` object for request-scoped connections
- `init_db()` creates schema from `schema.sql` and seeds from `initial_players.json`
- Logging uses Python's `logging` module with `basicConfig(level=INFO)` — already goes to stdout
- Environment loaded via `load_dotenv()` from `.env`

### Integration Points
- `app.py` database config section: Wire in `DB_PATH` env var with fallback
- `app.py` routes section: Add `/health` endpoint
- `backup_tennis_db.sh`: Update to use `DB_PATH` env var
- New files: `Dockerfile`, `.dockerignore`, `docker-requirements.txt`

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-app-container*
*Context gathered: 2026-03-18*
