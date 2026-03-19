---
phase: 01-app-container
plan: 01
subsystem: infra
tags: [docker, gunicorn, eventlet, flask, sqlite, python312]

# Dependency graph
requires: []
provides:
  - Multi-stage Dockerfile (python:3.12-slim builder + runtime stages)
  - docker-requirements.txt with 19 pinned production dependencies
  - .dockerignore excluding dev/test/doc artifacts
  - entrypoint.sh initializing DB then exec-ing gunicorn with single eventlet worker
  - app.py DB_PATH env var support with fallback to project root
  - app.py /health endpoint (CSRF-exempt, no auth required)
  - backup_tennis_db.sh respecting DB_PATH env var
affects: [02-compose, 03-caddy, 04-registry]

# Tech tracking
tech-stack:
  added: [gunicorn==23.0.0, eventlet==0.40.1, docker multi-stage build]
  patterns:
    - Non-root container user (appuser UID/GID 1000)
    - exec-based entrypoint for proper PID 1 signal handling
    - DB_PATH env var with fallback for Docker/non-Docker compatibility
    - CSRF-exempt health route for infrastructure tooling

key-files:
  created:
    - docker-requirements.txt
    - .dockerignore
    - Dockerfile
    - entrypoint.sh
  modified:
    - app.py
    - backup_tennis_db.sh

key-decisions:
  - "Do NOT use --preload with gunicorn: known incompatibility with eventlet worker class"
  - "Named volumes (not bind mounts) for SQLite: avoids host UID/GID permission mismatch"
  - "entrypoint.sh calls init_db() before gunicorn: init_db() only runs under __main__ normally, not under gunicorn import"
  - "DB_PATH fallback preserves original behavior: unset = tennis.db in project root"
  - "/health has no DB connectivity check: simple and fast, suitable for Docker HEALTHCHECK"

patterns-established:
  - "Entrypoint pattern: shell init script + exec to transfer PID 1 to app process"
  - "Multi-stage build: builder stage for C extension compilation, runtime stage copies only /venv"
  - "Environment-driven config: all paths/secrets via env vars, .env excluded from image"

requirements-completed: [CONT-01, CONT-02, CONT-03, CONT-04, OPS-01, OPS-02, OPS-03]

# Metrics
duration: 2min
completed: 2026-03-19
---

# Phase 1 Plan 01: Docker Infrastructure Summary

**Multi-stage Dockerfile with python:3.12-slim, non-root appuser, DB_PATH env var migration, and CSRF-exempt /health endpoint for single-eventlet-worker gunicorn deployment**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-19T06:43:11Z
- **Completed:** 2026-03-19T06:45:31Z
- **Tasks:** 2
- **Files modified:** 6 (4 created, 2 modified)

## Accomplishments

- Complete Docker infrastructure: Dockerfile, docker-requirements.txt, .dockerignore, entrypoint.sh
- app.py modified to read DB_PATH env var with automatic parent directory creation and backward-compatible fallback
- /health endpoint added (CSRF-exempt, no authentication) returning {"status": "ok"} HTTP 200
- backup_tennis_db.sh updated to use ${DB_PATH:-/home/stecher/stecher_tennis/tennis.db} fallback

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Docker infrastructure files** - `7d43a1a` (feat)
2. **Task 2: Add /health endpoint, DB_PATH env var to app.py, update backup script** - `9832feb` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `Dockerfile` - Multi-stage build: builder stage installs C extensions into /venv; runtime stage copies venv, creates non-root appuser (UID 1000), sets DB_PATH=/app/data/tennis.db, HEALTHCHECK via urllib
- `docker-requirements.txt` - 19 pinned production dependencies (Flask 3.1.1 through requests 2.32.3), no ML/AI libraries
- `.dockerignore` - Excludes .git, __pycache__, *.db, .env, .planning/, documentation/, tests/, with !CLAUDE.md negation
- `entrypoint.sh` - set -euo pipefail; Python init_db(); exec /venv/bin/gunicorn --workers 1 --worker-class eventlet --timeout 120
- `app.py` - DB_PATH env var block (lines 91-100), /health route with @csrf.exempt (lines 116-120)
- `backup_tennis_db.sh` - SOURCE_DB now uses ${DB_PATH:-...} parameter expansion

## Decisions Made

- No `--preload` flag in gunicorn command: known incompatibility with eventlet causes worker startup failures
- entrypoint.sh triggers init_db() explicitly before gunicorn starts because gunicorn imports app:app and never reaches the `if __name__ == "__main__":` block where init_db() is called
- /health has no database connectivity check: keeps health check fast and avoids circular dependency issues at startup

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. Docker build/run requires env vars (SECRET_KEY, CORS_ALLOWED_ORIGINS) injected at runtime via `docker run -e` or docker-compose.yml — documented as Phase 2 scope.

## Next Phase Readiness

- All Docker infrastructure files complete and verified (app imports cleanly, all acceptance criteria pass)
- Plan 02 (docker build + smoke test) can proceed: `docker build -t tennis-app .` and `docker run` with health check verification
- Remaining STATE.md blocker resolved: DB_PATH code change location identified and implemented

---
*Phase: 01-app-container*
*Completed: 2026-03-19*
