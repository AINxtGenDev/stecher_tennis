# Requirements: Stecher Tennis — Docker Deployment

**Defined:** 2026-03-18
**Core Value:** One-command deployment on any Linux server (ARM or x86) with automatic HTTPS

## v1 Requirements

Requirements for initial Docker deployment. Each maps to roadmap phases.

### Containerization

- [ ] **CONT-01**: App runs in a Docker container using `python:3.12-slim` multi-stage build
- [ ] **CONT-02**: Container runs as non-root user with correct file permissions
- [ ] **CONT-03**: `.dockerignore` excludes `.git`, `__pycache__`, `documentation/`, `*.db`, dev files
- [ ] **CONT-04**: Database path is configurable via `DB_PATH` env var (default: `data/tennis.db`)
- [ ] **CONT-05**: Docker image builds for both ARM64 and AMD64 via `docker buildx`

### Docker Compose

- [ ] **COMP-01**: `docker-compose.yml` defines two services: app and caddy
- [ ] **COMP-02**: App and Caddy communicate on an internal bridge network (app port not exposed to host)
- [ ] **COMP-03**: SQLite database persisted via named Docker volume mounted at `/app/data`
- [ ] **COMP-04**: `.env.example` documents all configurable environment variables

### HTTPS & Reverse Proxy

- [ ] **HTTP-01**: Custom Caddy image built with xcaddy + caddy-dns/duckdns module
- [ ] **HTTP-02**: Caddy serves HTTPS with automatic certificate via DuckDNS DNS-01 ACME challenge
- [ ] **HTTP-03**: WebSocket connections pass through Caddy to Flask-SocketIO
- [ ] **HTTP-04**: Toggle between Let's Encrypt staging and production ACME endpoints via env var

### Operations

- [ ] **OPS-01**: `/health` endpoint returns app status for Docker health check
- [ ] **OPS-02**: Gunicorn configured with `--workers 1 --worker-class eventlet --timeout 120`
- [ ] **OPS-03**: Application logs to stdout for `docker logs` collection

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### CI/CD

- **CICD-01**: GitHub Actions workflow to build and push multi-arch image on tag
- **CICD-02**: Automated deployment to Raspberry Pi via SSH on push

### Monitoring

- **MON-01**: Container metrics exposed for Prometheus scraping
- **MON-02**: Log aggregation via Loki or similar

## Out of Scope

| Feature | Reason |
|---------|--------|
| PostgreSQL migration | SQLite is sufficient for club-level traffic |
| Kubernetes/Swarm | Single-host Docker Compose meets all needs |
| Alpine base image | Breaks bcrypt/greenlet C extensions, especially on ARM64 |
| Multiple gunicorn workers | Flask-SocketIO requires exactly 1 worker with eventlet |
| Eventlet → gevent migration | Out of scope for Dockerization; separate milestone |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CONT-01 | — | Pending |
| CONT-02 | — | Pending |
| CONT-03 | — | Pending |
| CONT-04 | — | Pending |
| CONT-05 | — | Pending |
| COMP-01 | — | Pending |
| COMP-02 | — | Pending |
| COMP-03 | — | Pending |
| COMP-04 | — | Pending |
| HTTP-01 | — | Pending |
| HTTP-02 | — | Pending |
| HTTP-03 | — | Pending |
| HTTP-04 | — | Pending |
| OPS-01 | — | Pending |
| OPS-02 | — | Pending |
| OPS-03 | — | Pending |

**Coverage:**
- v1 requirements: 16 total
- Mapped to phases: 0
- Unmapped: 16 ⚠️

---
*Requirements defined: 2026-03-18*
*Last updated: 2026-03-18 after initial definition*
