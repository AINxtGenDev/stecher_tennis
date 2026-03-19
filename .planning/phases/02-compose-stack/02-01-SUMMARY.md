---
phase: 02-compose-stack
plan: 01
subsystem: infra
tags: [docker-compose, caddy, reverse-proxy, sqlite, named-volumes, networking]

# Dependency graph
requires:
  - phase: 01-app-container
    provides: Dockerfile with HEALTHCHECK, EXPOSE 5000, DB_PATH=/app/data/tennis.db, entrypoint.sh with gunicorn

provides:
  - docker-compose.yml defining two-service stack (app + caddy) on internal bridge network
  - Caddyfile with plain HTTP reverse proxy to app:5000 and ProxyFix-compatible headers
  - App port 5000 isolated from host (only Caddy port 80 exposed)
  - Named volumes: tennis_data for SQLite, caddy_data for Phase 3 TLS state

affects: [03-tls, 04-cicd]

# Tech tracking
tech-stack:
  added: [caddy:2-alpine]
  patterns:
    - Two-service internal bridge network — Caddy fronts app, app port hidden from host
    - depends_on condition: service_healthy — Caddy waits for Dockerfile HEALTHCHECK before starting
    - Named Docker volumes for non-root container user (avoids UID/GID bind-mount permission issues)

key-files:
  created:
    - docker-compose.yml
    - Caddyfile
  modified: []

key-decisions:
  - "No version: key in docker-compose.yml — deprecated in Compose v2, omitted to avoid warnings"
  - "Caddy :80 site address (not a domain) explicitly disables auto-HTTPS — Phase 3 will replace with DuckDNS ACME"
  - "caddy_data volume included now — Phase 3 TLS cert storage needs it pre-created"
  - "App build: and image: both specified — build provides fallback; image: names the result for later reference"

patterns-established:
  - "Reverse proxy isolation: app service has no ports block — only reachable via Caddy on tennis_net"
  - "Header forwarding: four header_up directives (Host, X-Real-IP, X-Forwarded-For, X-Forwarded-Proto) for Flask ProxyFix"
  - "Caddy WS: WebSocket upgrade handled automatically by Caddy 2 reverse_proxy — no explicit Connection/Upgrade headers needed"

requirements-completed: [COMP-01, COMP-02, COMP-03]

# Metrics
duration: 4min
completed: 2026-03-19
---

# Phase 2 Plan 01: Compose Stack Definition Summary

**docker-compose.yml and Caddyfile wiring caddy:2-alpine in front of tennis-app on an internal bridge network with port 5000 isolated from the host**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-19T07:46:07Z
- **Completed:** 2026-03-19T07:50:19Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created docker-compose.yml defining app and caddy services on the `tennis_net` custom bridge network — satisfies COMP-01
- App port 5000 has no `ports:` block; only Caddy publishes `80:80` to the host — satisfies COMP-02
- Named volume `tennis_data` mounted at `/app/data` provides SQLite persistence across `compose down/up` — satisfies COMP-03
- Caddyfile reverse proxies to `app:5000` via Docker DNS with all four ProxyFix-compatible `header_up` directives
- `depends_on: condition: service_healthy` ensures Caddy waits for the Dockerfile HEALTHCHECK before starting

## Task Commits

Each task was committed atomically:

1. **Task 1: Create docker-compose.yml** - `17c5866` (feat)
2. **Task 2: Create Caddyfile** - `a4df9fc` (feat)

## Files Created/Modified

- `docker-compose.yml` — Two-service Compose stack: app (build + image, tennis_net, tennis_data:/app/data, no ports) + caddy (caddy:2-alpine, 80:80, depends_on service_healthy, caddy_data:/data)
- `Caddyfile` — Plain HTTP reverse proxy: :80 listener, reverse_proxy app:5000, four header_up directives, log to stderr at ERROR level

## Decisions Made

- No `version:` key in docker-compose.yml — deprecated in Compose v2, causes warnings, safe to omit entirely
- Used `:80` as Caddyfile site address (not `localhost:80` or a domain name) — this is the Caddy 2 idiom that explicitly disables auto-HTTPS
- `caddy_data` volume included now even though Phase 2 uses plain HTTP — Phase 3 needs the volume pre-existing for TLS cert storage
- Both `build: .` and `image: tennis-app:latest` on app service — `build:` provides fallback on clean machines, `image:` names the resulting image for future CI/CD use

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- `pytest` binary not on PATH in shell environment. Resolved by discovering the project's conda environment at `/home/nuc8/miniconda3/envs/stecher_tennis/bin/pytest`. All 7 existing tests passed with no regression.

## User Setup Required

None — no external service configuration required for this plan. (COMP-04 `.env.example` is scoped to plan 02.)

## Next Phase Readiness

- docker-compose.yml and Caddyfile are complete and validate cleanly (`docker compose config --quiet` exits 0)
- Plan 02 (`.env.example`) is the only remaining plan in Phase 2
- Phase 3 (TLS/DuckDNS ACME) will replace the Caddyfile `:80` listener with a domain-based config — the `caddy_data` volume is already defined to hold certificates

---
*Phase: 02-compose-stack*
*Completed: 2026-03-19*
