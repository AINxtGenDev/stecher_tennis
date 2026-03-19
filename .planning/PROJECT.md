# Stecher Tennis — Docker Deployment

## What This Is

Dockerization of an existing Flask-based tennis ranking web application. The app manages player rankings, challenges, and real-time updates via WebSocket. The goal is to containerize it with Docker Compose so it can be deployed on any server (Raspberry Pi or x86) with a single `docker compose up` command, including automatic HTTPS via Caddy reverse proxy.

## Core Value

One-command deployment: `docker compose up -d` brings up the entire stack (app + reverse proxy + HTTPS) on any Linux server, ARM or x86.

## Requirements

### Validated

<!-- Existing capabilities inferred from codebase -->

- ✓ Flask web application with eventlet async — existing
- ✓ Real-time updates via Flask-SocketIO — existing
- ✓ SQLite database with WAL mode — existing
- ✓ Authentication with bcrypt + Flask-Login — existing
- ✓ CSRF protection via Flask-WTF — existing
- ✓ Gunicorn production server support — existing
- ✓ Caddy reverse proxy configuration (manual) — existing (documented in 99_rpi.txt)
- ✓ Multi-stage Dockerfile for Python 3.12 + eventlet — Validated in Phase 1: App Container
- ✓ Health check endpoint for container orchestration — Validated in Phase 1: App Container
- ✓ Production-ready gunicorn configuration — Validated in Phase 1: App Container
- ✓ Docker best practices (non-root user, minimal image, .dockerignore) — Validated in Phase 1: App Container
- ✓ Docker Compose with app + Caddy services — Validated in Phase 2: Compose Stack
- ✓ SQLite database persisted via Docker volume mount — Validated in Phase 2: Compose Stack
- ✓ Environment configuration via .env file — Validated in Phase 2: Compose Stack
- ✓ Automatic HTTPS via Caddy with DuckDNS domain — Validated in Phase 3: HTTPS via Caddy

### Active

- [ ] Multi-architecture support (ARM64 + AMD64)

### Out of Scope

- Database migration to PostgreSQL — SQLite is sufficient for this use case
- CI/CD pipeline — manual deployment is fine for now
- Kubernetes/Swarm orchestration — single-host Docker Compose is enough
- Monitoring stack (Prometheus/Grafana) — not needed for a club app

## Context

- App currently runs on a Raspberry Pi with manual systemd + Caddy setup (see `documentation/99_rpi.txt`)
- Single-worker gunicorn is required (Flask-SocketIO with eventlet needs exactly 1 worker)
- SQLite database must survive container rebuilds — volume mount is essential
- DuckDNS is used for dynamic DNS + free SSL certificates via Caddy
- App binds to 0.0.0.0:5000 internally, Caddy handles external HTTPS on 443

## Constraints

- **Single worker**: Gunicorn must run with `--workers 1 --worker-class eventlet` (Socket.IO requirement)
- **Multi-arch**: Docker image must build for both `linux/amd64` and `linux/arm64`
- **SQLite file locking**: WAL mode + volume mount needs proper file permissions
- **DuckDNS**: Caddy needs a DuckDNS API token for automatic HTTPS certificate provisioning

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Volume mount for SQLite | Data must survive container rebuilds | ✓ Done (Phase 2) |
| Caddy in Docker Compose | Consistent deployment, no manual proxy config | ✓ Done (Phase 2) |
| Multi-stage Dockerfile | Smaller image, separate build and runtime dependencies | ✓ Done (Phase 1) |
| DuckDNS for HTTPS | Free dynamic DNS + automatic SSL, already in use | ✓ Done (Phase 3) |
| Non-root container user | Security best practice for production containers | ✓ Done (Phase 1) |

---
## Current State

Phases 1–3 complete. App containerized (Phase 1), Compose stack with Caddy reverse proxy and SQLite volume (Phase 2), HTTPS via custom Caddy build with DuckDNS DNS-01 ACME (Phase 3). Staging TLS certs validated. Next: Phase 4 (Multi-Arch & RPi Deploy).

*Last updated: 2026-03-19 after Phase 3 completion*
