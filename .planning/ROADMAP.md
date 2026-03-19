# Roadmap: Stecher Tennis — Docker Deployment

## Overview

Four sequential phases containerize an existing working Flask-SocketIO application into a Docker Compose stack deployable on any Linux server with a single command. The Dockerfile is built first because every subsequent phase depends on a correctly configured image. The Compose stack is wired on x86 without TLS complexity. HTTPS is added in isolation to protect Let's Encrypt rate limits. Multi-arch build comes last when everything else is verified.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: App Container** - Working Docker image for the Flask app with correct gunicorn, permissions, and volume path
- [x] **Phase 2: Compose Stack** - Full two-container stack running locally via docker compose up, data persisted across restarts
- [x] **Phase 3: HTTPS via Caddy** - Automatic TLS working end-to-end via DuckDNS DNS-01 challenge (completed 2026-03-19)
- [ ] **Phase 4: Multi-Arch & RPi Deploy** - Image builds for ARM64 + AMD64; verified deployment on Raspberry Pi

## Phase Details

### Phase 1: App Container
**Goal**: A Docker image that runs the Flask-SocketIO app correctly — single eventlet worker, non-root user, configurable DB path, health endpoint, minimal size
**Depends on**: Nothing (first phase)
**Requirements**: CONT-01, CONT-02, CONT-03, CONT-04, OPS-01, OPS-02, OPS-03
**Success Criteria** (what must be TRUE):
  1. `docker build` completes without error and produces an image under 200MB
  2. `docker run` starts the container and `curl localhost:5000/health` returns HTTP 200
  3. Container process runs as a non-root user (verify with `docker exec ... whoami`)
  4. Setting `DB_PATH=/app/data/tennis.db` in the environment causes the app to read/write SQLite at that path
  5. Gunicorn starts with exactly 1 worker and eventlet worker class (visible in container startup logs)
**Plans:** 2/2 plans executed

Plans:
- [x] 01-01-PLAN.md — Create Docker infrastructure (Dockerfile, entrypoint.sh, docker-requirements.txt, .dockerignore) and modify app.py (DB_PATH + /health endpoint)
- [x] 01-02-PLAN.md — Create test infrastructure (pytest + unit tests) and validate Docker image with smoke tests

### Phase 2: Compose Stack
**Goal**: Both app and Caddy containers start together, app is reachable through Caddy on the local machine, and SQLite data survives docker compose down/up cycles
**Depends on**: Phase 1
**Requirements**: COMP-01, COMP-02, COMP-03, COMP-04
**Success Criteria** (what must be TRUE):
  1. `docker compose up -d` starts both services without error
  2. HTTP request to the Caddy port reaches the Flask app (WebSocket connect also succeeds)
  3. Creating data in the app, running `docker compose down && docker compose up -d`, and verifying data still exists confirms volume persistence
  4. App container port 5000 is not reachable directly from the host (only through Caddy)
**Plans:** 2/2 plans executed

Plans:
- [x] 02-01-PLAN.md — Create docker-compose.yml (two services, internal network, named volumes) and Caddyfile (HTTP reverse proxy to app:5000 with WebSocket headers)
- [x] 02-02-PLAN.md — Create .env.example documenting all env vars; validate full Compose stack with smoke tests (COMP-01 through COMP-04)

### Phase 3: HTTPS via Caddy
**Goal**: The app is reachable over HTTPS at the DuckDNS domain with a valid Let's Encrypt certificate obtained via DNS-01 challenge
**Depends on**: Phase 2
**Requirements**: HTTP-01, HTTP-02, HTTP-03, HTTP-04
**Success Criteria** (what must be TRUE):
  1. Browser navigates to `https://<domain>.duckdns.org` and receives a valid TLS certificate (no browser warning)
  2. WebSocket connections to the HTTPS domain connect and receive real-time updates
  3. HTTP requests to port 80 redirect automatically to HTTPS
  4. Setting `ACME_CA_URL` env var switches between Let's Encrypt staging and production endpoints without Caddyfile edits
**Plans:** 2/2 plans complete

Plans:
- [x] 03-01-PLAN.md — Create Dockerfile.caddy (xcaddy + caddy-dns/duckdns), rewrite Caddyfile for HTTPS with DNS-01 ACME, update docker-compose.yml and .env.example
- [x] 03-02-PLAN.md — Build custom Caddy image, validate duckdns module, smoke test full HTTPS stack with staging certificate

### Phase 4: Multi-Arch & RPi Deploy
**Goal**: A single `docker compose pull && docker compose up -d` on the Raspberry Pi brings up the full working stack using a multi-architecture image
**Depends on**: Phase 3
**Requirements**: CONT-05
**Success Criteria** (what must be TRUE):
  1. `docker buildx build --platform linux/amd64,linux/arm64` completes without error for both platforms
  2. The app runs correctly on the Raspberry Pi after pulling the published image (HTTPS works, data persists, WebSocket connects)
  3. A reboot of the Raspberry Pi causes both containers to restart automatically without manual intervention
**Plans**: TBD

Plans:
- [ ] 04-01: Set up docker buildx, resolve ARM64 gcc dependencies, publish multi-arch image to registry, deploy and verify on RPi

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. App Container | 2/2 | Complete | 2026-03-19 |
| 2. Compose Stack | 2/2 | Complete | 2026-03-19 |
| 3. HTTPS via Caddy | 2/2 | Complete   | 2026-03-19 |
| 4. Multi-Arch & RPi Deploy | 0/1 | Not started | - |
