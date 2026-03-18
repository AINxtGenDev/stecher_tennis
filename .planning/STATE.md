# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-18)

**Core value:** One-command deployment — `docker compose up -d` brings up the full stack (app + HTTPS) on any Linux server, ARM or x86
**Current focus:** Phase 1 — App Container

## Current Position

Phase: 1 of 4 (App Container)
Plan: 0 of 2 in current phase
Status: Ready to plan
Last activity: 2026-03-18 — Roadmap created; requirements mapped to 4 phases

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: -
- Trend: -

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Setup]: Single worker constraint — gunicorn must use `--workers 1 --worker-class eventlet`; hard-coded in Dockerfile CMD with comment
- [Setup]: Named volumes (not bind mounts) for SQLite to avoid host UID/GID permission mismatch
- [Setup]: ACME staging endpoint for all Phase 3 iteration; switch to production only after DNS-01 confirmed working

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 1] Eventlet version pinning: `prod-requirements.txt` must be audited for Python 3.12 compatibility; resolve via smoke test inside built container
- [Phase 1] `DB_PATH` code change: app currently hardcodes `tennis.db`; exact change location in `app.py` not yet identified
- [Phase 1] `init_db()` idempotency: must use `CREATE TABLE IF NOT EXISTS` to be safe on container restart against existing volume
- [Phase 4] Registry choice: Docker Hub vs GHCR vs local registry not yet decided; must resolve before Phase 4

## Session Continuity

Last session: 2026-03-18
Stopped at: Roadmap created; ready to plan Phase 1
Resume file: None
