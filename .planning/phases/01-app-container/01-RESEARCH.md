# Phase 1: App Container - Research

**Researched:** 2026-03-18
**Domain:** Docker containerization of Flask-SocketIO/eventlet application with SQLite
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Production dependencies**
- Create a new `docker-requirements.txt` (do NOT overwrite `prod-requirements.txt`)
- Core stack: Flask, Flask-SocketIO, Flask-Login, Flask-WTF, flask-cors, gunicorn, eventlet, greenlet, python-engineio, python-socketio, bcrypt, Werkzeug, itsdangerous, Jinja2, click, python-dotenv
- Also include: requests, pydantic (used at runtime)
- Exclude: google-generativeai, openai, numpy, scipy, Pillow, beautifulsoup4, litellm, posthog, mixpanel
- Pin exact versions (generate from current conda env)

**Health endpoint**
- `GET /health` returns `{"status": "ok"}` with HTTP 200
- Publicly accessible (no authentication required)
- CSRF-exempt so curl and Docker HEALTHCHECK work without tokens
- No database connectivity check — simple and fast

**DB_PATH migration**
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

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CONT-01 | App runs in Docker container using `python:3.12-slim` multi-stage build | Multi-stage pattern documented below; `python:3.12-slim` verified as correct base |
| CONT-02 | Container runs as non-root user with correct file permissions | Non-root user pattern with UID/GID 1000 documented below |
| CONT-03 | `.dockerignore` excludes `.git`, `__pycache__`, `documentation/`, `*.db`, dev files | Standard .dockerignore patterns documented below |
| CONT-04 | Database path is configurable via `DB_PATH` env var (default: `data/tennis.db`) | Exact code location in app.py identified (line 91); migration path clear |
| OPS-01 | `/health` endpoint returns app status for Docker health check | CSRF-exempt route pattern documented; Flask-WTF `csrf.exempt` decorator identified |
| OPS-02 | Gunicorn configured with `--workers 1 --worker-class eventlet --timeout 120` | Verified from production systemd config; eventlet constraint documented |
| OPS-03 | Application logs to stdout for `docker logs` collection | Already configured: `logging.basicConfig(level=logging.INFO)` outputs to stdout by default |
</phase_requirements>

---

## Summary

This phase containerizes an existing Flask-SocketIO application (v3.44) using Python 3.12 and eventlet async mode. The application already logs to stdout, uses environment variables for secrets, and follows standard Flask patterns — Docker adaptation is primarily mechanical (Dockerfile, non-root user, health endpoint, DB path env var).

The most critical technical constraint is the single-worker requirement. Flask-SocketIO with eventlet maintains in-process state for WebSocket connections. Multiple gunicorn workers would give each worker its own Socket.IO state, causing "invalid session" errors. This is a hard architectural constraint, not a preference. The production systemd service already enforces `--workers 1 --worker-class eventlet`.

A non-obvious implementation gap exists: `init_db()` is only called inside `if __name__ == "__main__":` (line 2612). When gunicorn imports `app:app`, this block never executes. The database initialization logic must be triggered another way in the containerized setup — the recommended approach is a gunicorn `--preload` flag combined with an application-level startup hook, or a dedicated entrypoint script that initializes the DB before starting gunicorn.

**Primary recommendation:** Multi-stage Dockerfile with `python:3.12-slim`, non-root user (UID 1000), entrypoint script that calls `flask init-db` or equivalent before exec-ing gunicorn, and DB_PATH wired into app.config on line 91.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| python:3.12-slim | Docker base image | Minimal Python 3.12 on Debian Bookworm | Matches dev environment; slim reduces attack surface vs full image |
| gunicorn | 23.0.0 | WSGI production server | Standard Flask production server; verified in prod systemd config |
| eventlet | 0.40.1 | Async worker for gunicorn | Required by Flask-SocketIO; cannot use gevent or sync workers |
| Flask | 3.1.1 | Web framework | Core app framework |
| Flask-SocketIO | 5.5.1 | WebSocket support | Core feature |
| Flask-Login | 0.6.3 | Authentication | Core feature |
| Flask-WTF | 1.2.2 | CSRF protection | Core security feature |
| flask-cors | 6.0.1 | CORS headers | Used with Socket.IO origins |
| bcrypt | 4.3.0 | Password hashing | Core security |
| Werkzeug | 3.1.3 | WSGI utilities | Flask dependency |
| itsdangerous | 2.2.0 | Signing utilities | Flask dependency |
| Jinja2 | 3.1.6 | Template engine | Flask dependency |
| click | 8.2.1 | CLI | Flask dependency |
| python-dotenv | 1.1.0 | `.env` loading | Already used in app.py |
| greenlet | 3.1.1 | Coroutine support | eventlet dependency |
| python-engineio | 4.11.2 | Socket.IO engine | Flask-SocketIO dependency |
| python-socketio | 5.12.1 | Socket.IO protocol | Flask-SocketIO dependency |
| pydantic | 2.11.4 | Data validation | Used at runtime |
| requests | 2.32.3 | HTTP client | Used at runtime |

**Versions above are confirmed from the running conda environment (`stecher_tennis`). These are the exact versions to pin in `docker-requirements.txt`.**

### Supporting (excluded per locked decisions)
The following packages from `prod-requirements.txt` are excluded from `docker-requirements.txt`:
- google-generativeai, openai, numpy, scipy, Pillow, beautifulsoup4, litellm, posthog, mixpanel

### docker-requirements.txt (exact content to generate):
```
Flask==3.1.1
Flask-SocketIO==5.5.1
Flask-Login==0.6.3
Flask-WTF==1.2.2
flask-cors==6.0.1
gunicorn==23.0.0
eventlet==0.40.1
greenlet==3.1.1
python-engineio==4.11.2
python-socketio==5.12.1
bcrypt==4.3.0
Werkzeug==3.1.3
itsdangerous==2.2.0
Jinja2==3.1.6
click==8.2.1
python-dotenv==1.1.0
pydantic==2.11.4
pydantic_core==2.33.2
requests==2.32.3
```

Note: `pydantic_core` is a required binary dependency of `pydantic` v2; must be included or pip will install it automatically at correct version.

---

## Architecture Patterns

### Recommended Project Structure (new files this phase)
```
project-root/
├── Dockerfile              # Multi-stage builder + runtime
├── .dockerignore           # Excludes dev/test/doc artifacts
├── docker-requirements.txt # Pinned production-only deps
├── entrypoint.sh           # DB init + exec gunicorn
├── app.py                  # Modified: DB_PATH env var + /health route
└── backup_tennis_db.sh     # Modified: respects DB_PATH env var
```

### Pattern 1: Multi-Stage Dockerfile

**What:** Builder stage installs dependencies into a virtualenv; runtime stage copies only the venv into a clean image.
**When to use:** Always for Python apps — eliminates build tools (gcc, pip build cache) from the final image.

```dockerfile
# Stage 1: Builder — installs dependencies
FROM python:3.12-slim AS builder

WORKDIR /build

# Install system build deps needed for C extensions (bcrypt, greenlet)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY docker-requirements.txt .
RUN python -m venv /venv && \
    /venv/bin/pip install --no-cache-dir --upgrade pip && \
    /venv/bin/pip install --no-cache-dir -r docker-requirements.txt

# Stage 2: Runtime — clean image, no build tools
FROM python:3.12-slim AS runtime

# Non-root user (UID/GID 1000 is convention; avoids conflicts with host)
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid 1000 --no-create-home --shell /sbin/nologin appuser

WORKDIR /app

# Copy venv from builder
COPY --from=builder /venv /venv

# Copy application files
COPY --chown=appuser:appgroup app.py schema.sql initial_players.json ./
COPY --chown=appuser:appgroup templates/ templates/
COPY --chown=appuser:appgroup static/ static/
COPY --chown=appuser:appgroup entrypoint.sh ./

# Create data directory with correct permissions
RUN mkdir -p /app/data && chown appuser:appgroup /app/data

USER appuser

ENV PATH="/venv/bin:$PATH"
ENV DB_PATH=/app/data/tennis.db

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

ENTRYPOINT ["./entrypoint.sh"]
```

### Pattern 2: Entrypoint Script for DB Initialization

**What:** A shell script that runs before gunicorn starts. It initializes the database (if needed) then exec-replaces itself with gunicorn so signals pass through correctly.
**When to use:** Any time app startup logic (like DB init) must run before the WSGI server, but is hidden behind `if __name__ == "__main__":`.

**Critical context:** `app.py` calls `init_db()` only inside `if __name__ == "__main__":` (line 2612). Gunicorn imports `app:app` — this block never runs. Without an entrypoint that triggers initialization, a fresh container will fail at first DB access with `sqlite3.OperationalError: no such table`.

```bash
#!/bin/bash
set -euo pipefail

# Initialize database if needed (safe — init_db() checks for existing tables)
echo "Initializing database at ${DB_PATH:-/app/data/tennis.db}..."
python -c "
from app import app, init_db
with app.app_context():
    init_db()
"

# exec replaces this shell with gunicorn so PID 1 is gunicorn (signal handling)
exec /venv/bin/gunicorn \
    --workers 1 \
    --worker-class eventlet \
    --bind 0.0.0.0:5000 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    app:app
```

### Pattern 3: DB_PATH env var in app.py

**What:** Override `app.config["DATABASE"]` from an env var, with fallback to current default.
**Change location:** `app.py` line 91 (currently `app.config["DATABASE"] = os.path.join(app.root_path, "tennis.db")`)

```python
# app.py — replace line 91
_db_path = os.environ.get("DB_PATH")
if _db_path:
    # Docker mode: use configured path, auto-create parent dirs
    _db_dir = os.path.dirname(_db_path)
    if _db_dir:
        os.makedirs(_db_dir, exist_ok=True)
    app.config["DATABASE"] = _db_path
else:
    # Non-Docker mode: keep current behavior (project root)
    app.config["DATABASE"] = os.path.join(app.root_path, "tennis.db")
```

### Pattern 4: /health Endpoint (CSRF-exempt)

**What:** Simple health route that returns 200 without authentication or CSRF token.
**CSRF exemption:** Flask-WTF's `csrf.exempt()` decorator or `@csrf.exempt` on the route.

```python
# app.py — add after csrf = CSRFProtect(app) setup (around line 115)
@app.route("/health")
@csrf.exempt
def health():
    return jsonify({"status": "ok"}), 200
```

Note: Because this route has no `@login_required`, Flask-Login will not redirect to login page. The `@csrf.exempt` ensures no CSRF token is required for GET requests (Flask-WTF normally exempts GET, but being explicit is correct here for Docker HEALTHCHECK compatibility).

### Pattern 5: .dockerignore

```
# Version control
.git
.gitignore

# Python artifacts
__pycache__/
*.py[cod]
*.pyo
*.pyd
.Python
*.egg-info/
dist/
build/
.eggs/

# Development dependencies
requirements.txt
environment.yml

# Database files (never bake into image)
*.db
*.sqlite
*.sqlite3

# Documentation
documentation/
*.html
*.md
!CLAUDE.md

# Dev tools and config
.env
.env.*
.planning/
.claude/

# Backup artifacts
backup/

# Tests
test/
tests/
pytest.ini
setup.cfg
pyproject.toml

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS artifacts
.DS_Store
Thumbs.db
```

### Anti-Patterns to Avoid

- **Multiple gunicorn workers:** `--workers 2+` with eventlet causes Socket.IO session routing to random workers, breaking WebSocket connections. The single-worker constraint is hard and documented in production (systemd config line: `--workers 1 --worker-class eventlet`).
- **Running as root:** Container escapes are harder when PID 1 is non-root. Always `USER appuser` after setup.
- **Copying .env into image:** Never `COPY .env .` — secrets belong in runtime env vars, not image layers.
- **Baking the database into the image:** `*.db` in .dockerignore. A DB in the image would be lost on container restart and shared across all instances.
- **Using Alpine:** Explicitly ruled out in REQUIREMENTS.md (breaks bcrypt/greenlet C extensions, especially on ARM64).
- **`pip install` without pinned versions:** Unpinned installs in Dockerfile produce non-reproducible images. Always use `docker-requirements.txt` with exact version pins.
- **Not using exec in entrypoint:** If entrypoint.sh doesn't `exec` gunicorn, gunicorn runs as a subprocess of bash. Docker signals (SIGTERM for graceful shutdown) go to bash, not gunicorn.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| DB atomic backup | Custom file copy | `sqlite3 .backup` command | WAL mode requires online backup API; plain file copy can capture partial state |
| CSRF exemption | Manual token bypass | `@csrf.exempt` from Flask-WTF | Built-in, audited, reversible |
| Non-root user | Complex user setup | Standard `useradd`/`groupadd` pattern | Well-understood; UID 1000 is the conventional first non-root user |
| Signal forwarding | Custom signal handler | `exec` in entrypoint.sh | `exec` replaces shell with gunicorn, so signals reach gunicorn directly |
| Health check | Custom monitoring script | Simple `urllib.request.urlopen` or `curl` | No extra dependencies; fast startup |

**Key insight:** The eventlet single-worker constraint makes container setup simpler than multi-process apps — no shared memory, no session affinity needed at the container level. Complexity is pushed to Phase 2 (compose/networking).

---

## Common Pitfalls

### Pitfall 1: init_db() Never Called Under Gunicorn

**What goes wrong:** Fresh container starts successfully, first request hits a route that calls `get_db()`, SQLite opens a new (empty) file, query fails with `OperationalError: no such table: players`.

**Why it happens:** `init_db()` is only inside `if __name__ == "__main__":` (line 2612). Gunicorn's `app:app` import never reaches that block.

**How to avoid:** Entrypoint script explicitly calls `init_db()` via `python -c "from app import app, init_db; ..."` before starting gunicorn. The `init_db()` function itself is already idempotent — it checks for table existence before running schema.sql (lines 396-401).

**Warning signs:** Container starts but returns 500 on any authenticated route; logs show `OperationalError`.

### Pitfall 2: schema.sql Uses DROP TABLE at Top

**What goes wrong:** If `init_db()` is somehow called on a container that already has data (e.g., against a pre-populated volume), it will DROP all tables and reseed with `initial_players.json`, destroying real player data.

**Why it happens:** `schema.sql` lines 1-4 use `DROP TABLE IF EXISTS` followed by `CREATE TABLE`. This was designed for development resets, not production restarts.

**How to avoid:** The existing guard in `init_db()` (checks `sqlite_master` for `players` table before executing schema) already prevents this — as long as `init_db()` is the only caller of `schema.sql`. Never call `db.executescript(schema.sql)` directly. The `/reset_database` superadmin route does its own explicit DROP before calling `init_db()`, which is correct and intentional.

**Warning signs:** Production data disappears after container restart. This does NOT happen with current code, but would happen if schema.sql were called directly without the guard.

### Pitfall 3: DB File Permissions with Non-Root User

**What goes wrong:** Container starts as `appuser` (UID 1000). If the Docker volume is mounted from a host directory owned by root (UID 0), `appuser` cannot create the SQLite file. Fails with `PermissionError` at `init_db()`.

**Why it happens:** Named Docker volumes default to root ownership when first created. Bind mounts inherit the host directory's ownership.

**How to avoid:**
- Use named Docker volumes (not bind mounts) — Docker named volumes are created with the first container's UID ownership when the volume is empty and the container creates files there. This generally works.
- In the Dockerfile, `RUN mkdir -p /app/data && chown appuser:appgroup /app/data` sets ownership before switching to USER appuser.
- STATE.md already documents: "Named volumes (not bind mounts) for SQLite to avoid host UID/GID permission mismatch."

**Warning signs:** `PermissionError: [Errno 13] Permission denied: '/app/data/tennis.db'` in container logs.

### Pitfall 4: Gunicorn Does Not Load .env File

**What goes wrong:** In development, `load_dotenv()` reads `.env` from the project directory. In Docker, `.env` is excluded by .dockerignore. Gunicorn starts, `load_dotenv()` finds no file, env vars are empty, `SECRET_KEY` falls back to dev default, and a warning is logged.

**Why it happens:** `.env` is intentionally excluded from the image (correct security practice). Environment variables must be injected at runtime via `docker run -e` or `docker-compose.yml` `environment:` block.

**How to avoid:** In Phase 2, all required env vars go into `docker-compose.yml` or a `.env.example` file. For Phase 1 testing, pass env vars explicitly: `docker run -e SECRET_KEY=... -e CORS_ALLOWED_ORIGINS=...`.

**Warning signs:** Log line `SECURITY WARNING: Using default secret key.` — app works but is insecure.

### Pitfall 5: Gunicorn Logging Not Going to stdout

**What goes wrong:** `docker logs` shows nothing from gunicorn access/error logs because gunicorn defaults to writing to `--error-logfile -` only if explicitly specified; otherwise it writes to stderr of the supervisor process.

**Why it happens:** Gunicorn default logging behavior vs Docker's stdout/stderr capture.

**How to avoid:** Explicitly pass `--access-logfile - --error-logfile -` in the gunicorn command. The `-` means stdout/stderr. The Flask app's own `logging.basicConfig(level=logging.INFO)` already goes to stdout.

### Pitfall 6: HEALTHCHECK start-period Too Short

**What goes wrong:** Docker marks container unhealthy before the app has finished starting. With eventlet worker initialization and DB check at startup, the first health check may fire before the app is listening.

**How to avoid:** Use `--start-period=15s` (the app takes < 5 seconds in practice, but 15s provides buffer for slow ARM64 start on RPi). Retries: 3. This means the container needs 15s + 3x10s = 45s worst case before being marked unhealthy.

---

## Code Examples

### Verified: Current app.py database config (line 91)
```python
# Source: app.py line 91 (current)
app.config["DATABASE"] = os.path.join(app.root_path, "tennis.db")
```

### Verified: Current app.py startup (lines 2609-2616)
```python
# Source: app.py lines 2609-2616
if __name__ == "__main__":
    with app.app_context():
        init_db()
    logger.info("Starting Flask-SocketIO server with eventlet...")
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", 5000))
    socketio.run(app, host=host, port=port, debug=debug_mode, use_reloader=debug_mode)
```

### Verified: Production gunicorn command (from documentation/99_rpi.txt)
```bash
# Source: documentation/99_rpi.txt (systemd ExecStart)
gunicorn --workers 1 --worker-class eventlet --bind 127.0.0.1:8000 --timeout 120 app:app
```

### Verified: init_db() idempotency guard (lines 396-401)
```python
# Source: app.py lines 396-401
cur = db.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name='players';"
)
table_exists = cur.fetchone()
if not table_exists:
    # ... runs schema.sql and seeds initial_players.json
```

### Verified: CSRF instance (line 115)
```python
# Source: app.py line 115
csrf = CSRFProtect(app)
# Therefore: @csrf.exempt decorator is available on routes
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Alpine base image | python:3.12-slim | Alpine breaks bcrypt/greenlet C extensions on ARM64; slim uses Debian Bookworm with glibc |
| `pip install -r requirements.txt` in single stage | Multi-stage: builder installs deps, runtime copies venv | Final image excludes gcc, build-essential — reduces image size by ~200-300MB |
| Run app as root | Non-root user (UID 1000) | Defense-in-depth; required best practice |
| `.env` file in repo | Runtime env vars only | Secrets never baked into image layers |

**Note on image size target:** The phase success criteria specifies < 200MB. `python:3.12-slim` base is approximately 130MB. Adding the pinned runtime dependencies (no numpy/scipy/pillow/ML libs) should keep the final image under 200MB. This has not been verified empirically — the actual build will confirm.

---

## Open Questions

1. **Does `pydantic_core` need to be explicitly pinned in `docker-requirements.txt`?**
   - What we know: `pydantic==2.11.4` depends on `pydantic_core==2.33.2`. pip will install it automatically.
   - What's unclear: Whether a future pip resolve might pick a different `pydantic_core` patch version.
   - Recommendation: Include `pydantic_core==2.33.2` explicitly in `docker-requirements.txt` for reproducibility.

2. **Does `backup_tennis_db.sh` need to work inside the container?**
   - What we know: The script hardcodes `SOURCE_DB="/home/stecher/stecher_tennis/tennis.db"`. In Docker, DB is at `DB_PATH` (default `/app/data/tennis.db`).
   - What's unclear: Whether the backup script will ever be invoked from inside the container (vs. from the host via `docker exec`) or not at all in Phase 1.
   - Recommendation: Update `SOURCE_DB` to use `${DB_PATH:-/app/data/tennis.db}` as the locked decision specifies. Scope this change to Plan 01-02.

3. **Simple-websocket vs eventlet for Socket.IO transport**
   - What we know: `socketio = SocketIO(app, async_mode="eventlet", ...)` is hardcoded. eventlet patches stdlib, which has implications for gunicorn worker startup order.
   - What's unclear: Whether gunicorn's eventlet worker class and Flask-SocketIO's eventlet mode interact correctly without `--preload` flag.
   - Recommendation: Do NOT use `--preload` with eventlet (known incompatibility). The standard approach — gunicorn eventlet worker + Flask-SocketIO eventlet — is the established production pattern, verified by the working systemd config.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (installed in conda env; no test files exist yet) |
| Config file | None — Wave 0 creates `pytest.ini` |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CONT-01 | `docker build` completes, image < 200MB | smoke | `docker build -t tennis-test . && docker image inspect tennis-test --format='{{.Size}}'` | ❌ Wave 0 |
| CONT-02 | Container process runs as non-root | smoke | `docker run --rm tennis-test whoami` | ❌ Wave 0 |
| CONT-03 | `.dockerignore` excludes specified patterns | unit | `pytest tests/test_dockerignore.py` | ❌ Wave 0 |
| CONT-04 | `DB_PATH` env var routes SQLite to correct path | smoke | `docker run --rm -e DB_PATH=/tmp/test.db tennis-test python -c "from app import app; print(app.config['DATABASE'])"` | ❌ Wave 0 |
| OPS-01 | `GET /health` returns 200 | unit | `pytest tests/test_health.py -x -q` | ❌ Wave 0 |
| OPS-02 | Gunicorn starts with 1 eventlet worker | smoke | `docker run -d tennis-test && docker logs ... \| grep "Using worker: eventlet"` | ❌ Wave 0 |
| OPS-03 | Logs go to stdout | smoke | `docker logs <container>` captures app logs | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_health.py tests/test_db_path.py -x -q` (unit tests, fast)
- **Per wave merge:** `pytest tests/ -v` (all unit tests)
- **Phase gate:** Full unit suite green + smoke tests (`docker build`, `curl localhost:5000/health`, `docker exec whoami`) before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_health.py` — covers OPS-01: `/health` returns 200, no auth required, no CSRF
- [ ] `tests/test_db_path.py` — covers CONT-04: `DB_PATH` env var sets `app.config["DATABASE"]`, parent dir auto-created
- [ ] `tests/conftest.py` — Flask test client fixture, temporary DB fixture
- [ ] `pytest.ini` — test discovery config
- [ ] Framework install: already in conda env; `docker-requirements.txt` does not need pytest (dev-only)

---

## Sources

### Primary (HIGH confidence)
- `app.py` direct inspection — DB config (line 91), SocketIO init (line 216), init_db (lines 393-441), startup (lines 2609-2616), CSRF setup (line 115)
- `documentation/99_rpi.txt` — Production gunicorn command, systemd service config (verified working in production as of 2025-07-11 per log timestamps)
- `schema.sql` — DROP TABLE behavior, init_db safety analysis
- `requirements.txt` + conda env — Exact package versions confirmed via `conda run pip show`

### Secondary (MEDIUM confidence)
- `.planning/STATE.md` — Architectural decisions (named volumes for SQLite, single-worker constraint)
- `.planning/REQUIREMENTS.md` — Out-of-scope items (Alpine, multiple workers)
- `CLAUDE.md` — Tech stack and deployment target

### Tertiary (LOW confidence — not needed, decisions already locked)
- Docker multi-stage build best practices (standard industry practice, not verified against a specific doc)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — exact versions from running conda env
- Architecture: HIGH — patterns derived from existing production systemd config + direct app.py inspection
- Pitfalls: HIGH — identified from direct code inspection (init_db location, schema.sql DROP TABLE, non-root permissions)
- Validation: MEDIUM — test structure designed but no existing test infrastructure to verify against

**Research date:** 2026-03-18
**Valid until:** 2026-04-18 (stable stack; Python/Flask ecosystem moves slowly)
