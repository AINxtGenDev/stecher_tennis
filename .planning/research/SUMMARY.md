# Project Research Summary

**Project:** Stecher Tennis — Docker Deployment
**Domain:** Dockerizing a brownfield Flask+SocketIO+SQLite+Caddy app for Raspberry Pi (arm64) and x86
**Researched:** 2026-03-18
**Confidence:** HIGH (core infrastructure), MEDIUM (eventlet compatibility long-term)

## Executive Summary

This project is a single-host containerization of an existing, working Flask-SocketIO application onto Docker Compose running on a Raspberry Pi. The app manages tennis club rankings with real-time updates via Socket.IO and persists data in SQLite. The recommended approach is a two-container Docker Compose stack: a Python app container (gunicorn + eventlet) behind a custom Caddy container that provides TLS termination via DuckDNS DNS-01 ACME challenge. Because the app already works in production on the RPi, this milestone is purely an infrastructure change — no application logic modifications are needed beyond a configurable database path.

The single most important constraint in this entire deployment is that gunicorn must be configured with exactly one worker. Flask-SocketIO's in-process session state is fundamentally incompatible with multi-worker setups unless a message queue (Redis) is introduced. This is a hard requirement, not a preference, and must be enforced and documented so it is never "optimized away" later. The second most important infrastructure decision is to build a custom Caddy image using xcaddy to include the DuckDNS DNS provider module — the official caddy image does not include it and HTTP-01 challenge may fail at home/RPi network configurations where ISPs block inbound port 80.

The primary risks are: (1) SQLite volume permission failures when running as a non-root container user — mitigated by chowning the data directory before switching to the non-root user in the Dockerfile; (2) Let's Encrypt rate limit exhaustion during Caddy/DuckDNS configuration iteration — mitigated by using the ACME staging endpoint until DNS-01 challenge is confirmed working; and (3) eventlet's declining maintenance status under Python 3.12 — mitigated by pinning both eventlet and Flask-SocketIO to known-compatible versions and deferring async worker migration to a future milestone.

## Key Findings

### Recommended Stack

The recommended base image is `python:3.12-slim` (not Alpine, not full). Alpine uses musl libc which breaks prebuilt wheels for `bcrypt`, `cryptography`, and `greenlet` — all required by this app — causing slow and fragile ARM64 cross-compilation. The full image is unnecessary at ~350MB vs ~41MB for slim. Gunicorn 23.x (already in prod-requirements.txt) serves as the WSGI server. Eventlet is kept as the async worker class for this milestone since it already works in production; migration away from eventlet is an application code change that is explicitly out of scope.

Caddy is built as a custom two-stage image using xcaddy to include the `caddy-dns/duckdns` module. The existing Caddyfile from `documentation/99_rpi.txt` works as-is in Docker with two changes: the upstream changes from `localhost:8000` to `app:5000` (Docker service DNS), and the TLS block switches to DNS-01 challenge syntax. The Compose file uses no `version:` key (deprecated in Compose v2), named volumes for SQLite and Caddy certificates, `restart: unless-stopped` on both services, and `depends_on: condition: service_healthy` to prevent Caddy from starting before Flask is ready.

**Core technologies:**
- `python:3.12-slim`: App container base — Debian-based, multi-arch (amd64+arm64), prebuilt wheel support
- `gunicorn 23.x` + `eventlet`: WSGI server — single-worker requirement for Flask-SocketIO; already in prod-requirements.txt
- `caddy:2` (custom xcaddy build): Reverse proxy — automatic HTTPS via DuckDNS DNS-01 ACME, WebSocket-transparent
- `docker buildx`: Multi-arch build — covers RPi arm64 and x86 amd64 from a single build command
- Named Docker volumes: SQLite + TLS cert persistence — avoids host UID/GID mismatch of bind mounts

### Expected Features

**Must have (table stakes):**
- Multi-stage Dockerfile (builder + runtime stages) — keeps final image small and build tools absent from runtime
- `.dockerignore` excluding `.env`, `*.db`, `.git`, `__pycache__`, `venv` — prevents secrets and bloat in image
- Named volume for SQLite data at `/app/data` — data survives container rebuilds and image updates
- Non-root container user (appuser) with correct volume ownership — security baseline
- Gunicorn with `--workers 1 --worker-class eventlet` — hard constraint for Flask-SocketIO correctness
- Environment configuration via `.env` file — `SECRET_KEY`, `DUCKDNS_TOKEN`, `CORS_ALLOWED_ORIGINS`, `DB_PATH`
- Caddy reverse proxy with WebSocket header forwarding and DuckDNS TLS — replaces existing manual setup
- Named volumes for `caddy_data` and `caddy_config` — TLS certificates survive container restarts
- `restart: unless-stopped` on both services — survives RPi reboots without systemd
- Internal Docker network (`tennis_net`) — app port 5000 never exposed to host; only Caddy exposes 80/443
- Multi-arch image build (`linux/amd64,linux/arm64`) — same image deploys to dev machine and RPi

**Should have (operational quality):**
- `/health` endpoint in Flask + Docker `HEALTHCHECK` — enables `depends_on: condition: service_healthy`
- `depends_on: condition: service_healthy` in Compose — eliminates 502s during Caddy startup before Flask is ready
- Gunicorn `--timeout 120 --access-logfile -` — prevents WebSocket long-poll timeouts; logs to Docker stdout
- DB path configurable via `DB_PATH` env var — app currently hardcodes `tennis.db`; needed for volume mount at `/app/data/tennis.db`
- DuckDNS token validation step before Caddy config (`curl` test) — prevents wasted ACME attempts
- ACME staging endpoint during testing — preserves Let's Encrypt production rate limit quota

**Defer (out of scope for Docker milestone):**
- Eventlet-to-gevent or eventlet-to-threading migration — application code change, separate milestone
- CI/CD pipeline — manual `docker compose pull && docker compose up -d` is sufficient
- Monitoring (Prometheus/Grafana) — `docker compose logs` is adequate for a club app
- Redis message queue — only needed if multiple workers are ever added (they won't be)
- PostgreSQL migration — SQLite with WAL mode handles this load comfortably

### Architecture Approach

The architecture is a two-container Docker Compose stack on a single host. Caddy sits at the network edge, handles TLS termination and HTTP-to-HTTPS redirect, and reverse-proxies all traffic (including WebSocket upgrades, which Caddy v2 handles automatically) to the Flask app container on the internal `tennis_net` bridge network. The Flask app is reachable only via the internal network at `app:5000` — it does not expose any host port. SQLite data lives in a named volume mounted at `/app/data/` inside the app container. Caddy's TLS certificates live in a separate named volume (`caddy_data`). The app container runs gunicorn with a single eventlet worker, which handles all concurrent Socket.IO greenlet connections within one OS process.

**Major components:**
1. App container (`python:3.12-slim`, multi-stage) — runs Flask-SocketIO via gunicorn, serves all HTTP/WS traffic on internal port 5000, reads/writes SQLite at `/app/data/tennis.db`
2. Caddy container (custom xcaddy build with `caddy-dns/duckdns`) — TLS termination, HTTP redirect, reverse proxy with DuckDNS DNS-01 ACME certificate management
3. Named volumes — `tennis_data` for SQLite persistence, `caddy_data` + `caddy_config` for TLS state
4. `.env` file — injects `SECRET_KEY`, `DUCKDNS_TOKEN`, `CORS_ALLOWED_ORIGINS`, `DB_PATH` at runtime; never baked into images

### Critical Pitfalls

1. **SQLite volume owned by root (non-root user cannot write)** — Create and chown `/app/data` before the `USER` instruction in the Dockerfile: `RUN mkdir -p /app/data && chown -R appuser:appuser /app/data`; use named volumes (not bind mounts) to get automatic permission propagation from the image.

2. **Gunicorn multi-worker breaks Socket.IO silently** — Hard-code `--workers 1` in the Dockerfile CMD with an explanatory comment. Never use `--workers $(nproc)`. Symptoms are intermittent "invalid session" errors and stale real-time data visible only to some users.

3. **Let's Encrypt rate limit hit during Caddy/DuckDNS iteration** — Set `acme_ca https://acme-staging-v02.api.letsencrypt.org/directory` in the Caddyfile for all testing; switch to the production endpoint only after DNS-01 challenge is confirmed working. Verify the DuckDNS token with a direct API curl before touching Caddy.

4. **Eventlet Python 3.12 runtime incompatibility** — Pin both `eventlet` and `flask-socketio` to known-compatible versions in `prod-requirements.txt`. Add a smoke-test step (`python -c "import eventlet; eventlet.monkey_patch(); print('OK')"`) to the build or startup verification. When using `--worker-class eventlet`, gunicorn handles monkey-patching automatically — do not call `eventlet.monkey_patch()` manually in `app.py`.

5. **ARM64 build failure due to missing gcc in slim image** — In the builder stage of the multi-stage Dockerfile, install build dependencies before pip: `RUN apt-get update && apt-get install -y --no-install-recommends gcc python3-dev libffi-dev`. These are excluded from the runtime stage automatically by the multi-stage pattern.

## Implications for Roadmap

Based on research, this milestone decomposes into four tightly sequential phases. Each phase has clear deliverables and gates the next one. Phase ordering is driven by hard dependencies: you cannot test Caddy without a running app container, and you cannot multi-arch build without a working single-arch Dockerfile.

### Phase 1: App Container Foundation

**Rationale:** The Dockerfile is the foundation for everything else. Getting it right first (multi-stage, non-root user, correct gunicorn command, volume path, .dockerignore) prevents rework in all subsequent phases. All the highest-severity pitfalls cluster here.

**Delivers:** A working Docker image for the Flask app that runs correctly on the local architecture, with correct permissions, minimal size, and the single-worker gunicorn constraint enforced.

**Addresses:** Multi-stage Dockerfile, `.dockerignore`, non-root user, `prod-requirements.txt` in image, `--workers 1 --worker-class eventlet`, `DB_PATH` env var, `/health` endpoint, `HEALTHCHECK` instruction.

**Avoids:** Pitfalls 1 (volume permissions), 3 (multi-worker), 4 (eventlet monkey patch), 5 (Python 3.12 compat), 8 (ARM64 gcc), 10 (bloated requirements), 12 (SIGTERM), 14 (.dockerignore).

**Research flag:** Standard patterns — no additional research needed. All decisions are well-documented.

### Phase 2: Docker Compose Stack (Single-Arch)

**Rationale:** With the app image working, wire it into a Compose file with a minimal Caddy configuration. Validate the full stack end-to-end on the development machine (x86) before adding multi-arch complexity. Use HTTP-only or self-signed TLS at this stage to avoid ACME complications.

**Delivers:** A `docker-compose.yml` and `Caddyfile` that bring up both services on the development machine. App is reachable through Caddy. Internal network isolates the app. Named volumes persist SQLite data across `docker compose down / up` cycles. `depends_on: condition: service_healthy` works.

**Addresses:** Compose file structure, internal network, named volumes, `restart: unless-stopped`, env_file, `depends_on`, Caddy reverse proxy with WebSocket headers.

**Avoids:** Pitfalls 7 (WebSocket upgrade), 9 (secrets in Compose YAML), 11 (caddy_data not persisted).

**Research flag:** Standard patterns — Caddy v2 + Compose is well-documented.

### Phase 3: DuckDNS HTTPS via Caddy Custom Build

**Rationale:** TLS configuration is isolated to this phase to prevent Let's Encrypt rate limit consumption during Compose wiring. By the time this phase runs, the stack is already known-working without TLS complications.

**Delivers:** A custom Caddy image built with `xcaddy` + `caddy-dns/duckdns`, a Caddyfile with DNS-01 ACME configuration, and verified HTTPS access to the app via the DuckDNS domain.

**Addresses:** Custom Caddy Dockerfile (xcaddy build), DuckDNS env var injection, Caddyfile DNS-01 syntax, ACME staging endpoint for testing, production endpoint cutover.

**Avoids:** Pitfall 6 (rate limit) — use staging ACME throughout this phase; switch to production only at phase completion after staging confirms DNS-01 challenge succeeds.

**Research flag:** Standard patterns — xcaddy build pattern is official and well-documented; DuckDNS module is maintained.

### Phase 4: Multi-Architecture Build and RPi Deployment

**Rationale:** Multi-arch comes last because it adds build complexity (QEMU, registry push) that is irrelevant until the single-arch stack is fully working. This phase is also the most likely to surface ARM64-specific build issues (gcc missing in slim builder, slow QEMU compilation).

**Delivers:** Multi-arch images (`linux/amd64,linux/arm64`) pushed to a container registry, and a verified deployment on the Raspberry Pi via `docker compose pull && docker compose up -d`.

**Addresses:** `docker buildx` setup, builder stage gcc installation, registry choice (Docker Hub / GHCR / local), RPi deployment procedure documentation.

**Avoids:** Pitfall 8 (ARM64 gcc) — confirmed by explicit `--platform linux/arm64` test build before final push.

**Research flag:** Standard patterns — Docker buildx multi-platform is official and well-documented.

### Phase Ordering Rationale

- Phases 1 and 2 must be sequential; Phase 3 depends on Phase 2's running stack to validate TLS integration; Phase 4 depends on Phases 1-3 producing a known-working image.
- TLS is isolated to Phase 3 specifically to protect Let's Encrypt rate limit quota — the most irreversible failure mode in this project.
- Multi-arch build is deferred to Phase 4 because it requires a registry and adds build time; all validation that can happen on x86 should happen before cross-compiling.
- The `DB_PATH` env var change (making the database path configurable) must happen in Phase 1 because it affects the Dockerfile volume mount point — delay would require Dockerfile rework.

### Research Flags

Phases with standard patterns (no additional per-phase research needed):
- **Phase 1:** Multi-stage Dockerfile and gunicorn+eventlet patterns are extensively documented.
- **Phase 2:** Docker Compose v2 + Caddy reverse proxy patterns are well-documented officially.
- **Phase 3:** xcaddy build and DuckDNS module are official, maintained, and well-documented.
- **Phase 4:** Docker buildx multi-platform build is official Docker tooling with clear documentation.

Potential areas to watch (not blocking, but monitor):
- **Eventlet + Python 3.12 compatibility:** The eventlet project is in maintenance mode. If smoke testing in Phase 1 reveals incompatibilities, migration to `simple-websocket` + gthread mode (Flask-SocketIO maintainer's recommendation for low-traffic apps) may be needed before Phase 2. This is unlikely given the app already works on the RPi.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | `python:3.12-slim`, gunicorn, Caddy xcaddy pattern all verified against official docs and current sources (Feb-Mar 2026) |
| Features | HIGH | Feature set is derived from a working production config; all table-stakes features validated against official deployment docs |
| Architecture | HIGH | Two-container Compose pattern is well-established; single-worker constraint is authoritatively documented in Flask-SocketIO docs |
| Pitfalls | HIGH | Most pitfalls sourced from official issue trackers, SQLite docs, and Caddy community; rate-limit pitfall is particularly well-evidenced |

**Overall confidence:** HIGH

### Gaps to Address

- **Eventlet version pinning:** `prod-requirements.txt` must be audited to confirm eventlet and flask-socketio are pinned to Python 3.12-compatible versions. Exact compatible version range was not resolved in research. Resolve in Phase 1 by running the smoke test `python -c "import eventlet; eventlet.monkey_patch(); print('OK')"` inside the built container.

- **DB_PATH application code change:** The app currently hardcodes the SQLite path as `tennis.db`. The exact change needed in `app.py` (or wherever `get_db()` constructs the path) was not reviewed in research. Must be identified and made in Phase 1 before the volume mount can work correctly.

- **Registry for multi-arch push:** Research identified three options (Docker Hub, GHCR, local registry:2 container) but did not select one. Resolve before Phase 4 by deciding which registry is accessible from the build machine and the RPi.

- **`init_db()` idempotency:** Architecture research notes that `init_db()` must use `CREATE TABLE IF NOT EXISTS` to be safe on restart with an existing database. This should be verified in Phase 1 before it causes data loss on a fresh container restart against an existing volume.

## Sources

### Primary (HIGH confidence)
- [Flask-SocketIO Deployment Docs](https://flask-socketio.readthedocs.io/en/latest/deployment.html) — single worker constraint, eventlet worker class
- [Caddy Automatic HTTPS Docs](https://caddyserver.com/docs/automatic-https) — DNS-01 challenge, rate limits, staging endpoint
- [Caddy reverse_proxy directive](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy) — WebSocket header passthrough
- [caddy-dns/duckdns module](https://github.com/caddy-dns/duckdns) — xcaddy build pattern, env var parameter
- [Docker Multi-Platform Build Docs](https://docs.docker.com/build/building/multi-platform/) — buildx setup, push requirement
- [Docker Compose Networking](https://docs.docker.com/compose/how-tos/networking/) — service name DNS resolution
- [Python Docker Hub official image](https://hub.docker.com/_/python/) — multi-arch support, slim vs alpine
- Existing production config (`documentation/99_rpi.txt`) — validated working Caddyfile and systemd setup

### Secondary (MEDIUM confidence)
- [pythonspeed.com — Best Docker base image for Python (Feb 2026)](https://pythonspeed.com/articles/base-image-python-docker-images/) — slim vs alpine reasoning
- [Flask-SocketIO Discussion #2068 — eventlet status](https://github.com/miguelgrinberg/Flask-SocketIO/discussions/2068) — eventlet maintenance status, future migration path
- [OneUptime — SQLite in Docker (Feb 2026)](https://oneuptime.com/blog/post/2026-02-08-how-to-run-sqlite-in-docker-when-and-how/view) — WAL mode on local volumes confirmed safe
- [TestDriven.io — Docker Best Practices](https://testdriven.io/blog/docker-best-practices/) — non-root user, multi-stage, healthcheck patterns
- [Flask-SocketIO Issue #1385](https://github.com/miguelgrinberg/Flask-SocketIO/issues/1385) — Docker 60s hang with eventlet (import ordering)

### Tertiary (LOW confidence)
- [Security Boulevard — Environment Variables and Secrets in 2026](https://securityboulevard.com/2025/12/are-environment-variables-still-safe-for-secrets-in-2026/) — .env file security tradeoffs (consistent with official Docker guidance)

---
*Research completed: 2026-03-18*
*Ready for roadmap: yes*
