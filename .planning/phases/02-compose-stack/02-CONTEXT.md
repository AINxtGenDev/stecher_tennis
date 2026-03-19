# Phase 2: Compose Stack - Context

**Gathered:** 2026-03-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Full two-container stack (app + Caddy) running locally via `docker compose up -d`. SQLite data persists across `docker compose down`/`up` cycles. App is only reachable through Caddy on an internal network. HTTPS is NOT part of this phase (Phase 3).

</domain>

<decisions>
## Implementation Decisions

### Caddy image strategy
- Use official `caddy:2-alpine` image in Phase 2 (plain HTTP reverse proxy)
- Phase 3 will replace it with a custom xcaddy build that includes `caddy-dns/duckdns`
- No Caddy build step needed in Phase 2

### Caddyfile configuration
- Listen on `:80` (HTTP only, no TLS)
- Include WebSocket header_up directives from the start (Host, X-Real-IP, X-Forwarded-For, X-Forwarded-Proto)
- Matches the existing RPi Caddyfile pattern from `documentation/99_rpi.txt`

### Host port mapping
- Caddy exposes port 80 to the host (`80:80`)
- App port 5000 is NOT exposed to the host — only reachable via Caddy on the internal Docker network
- Satisfies COMP-02 requirement

### Service dependency
- Caddy uses `depends_on` with `condition: service_healthy` to wait for app's HEALTHCHECK
- App's HEALTHCHECK is already defined in the Dockerfile (interval=30s, start-period=15s)

### Volume strategy
- Named Docker volumes for both SQLite data and Caddy state
- `tennis_data` volume mounted at `/app/data` (app's DB_PATH)
- `caddy_data` volume for Caddy certificates/state (needed for Phase 3)
- Data survives `docker compose down`; only `docker compose down -v` removes it
- Named volumes (not bind mounts) — decided in Phase 1

### Restart policy
- `restart: unless-stopped` for both services
- Containers restart on crash/reboot but stay stopped after manual `docker compose stop`

### Environment configuration
- `env_file: .env` in docker-compose.yml for the app service
- `.env` stays git-ignored (already in .gitignore)
- `.env.example` committed with safe placeholder values
- Phase 2 vars only — no Phase 3 placeholders (DuckDNS, ACME)

### CORS_ALLOWED_ORIGINS
- Development: `http://192.168.1.8:5000`
- Production: `https://nechvatal.duckdns.org:10443/`
- `.env.example` documents both values as examples

### Claude's Discretion
- Internal Docker network name
- Caddy log configuration
- Exact docker-compose.yml formatting and comments
- Smoke test approach for volume persistence verification

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Docker infrastructure (Phase 1 output)
- `Dockerfile` — Multi-stage build, non-root appuser, HEALTHCHECK, DB_PATH=/app/data/tennis.db
- `entrypoint.sh` — init_db() + exec gunicorn (1 worker, eventlet)
- `docker-requirements.txt` — 19 pinned production dependencies
- `.dockerignore` — Excludes .git, __pycache__, *.db, .env, .planning/

### Existing production setup
- `documentation/99_rpi.txt` — Current RPi Caddyfile (WebSocket headers, reverse_proxy), systemd service, DuckDNS cron, port forwarding (external 10443 → internal 443)

### Prior phase context
- `.planning/phases/01-app-container/01-CONTEXT.md` — Phase 1 decisions (DB_PATH, health endpoint, non-root user, named volumes)

### Requirements
- `.planning/REQUIREMENTS.md` — COMP-01 through COMP-04 define Phase 2 acceptance criteria

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Dockerfile`: Already sets `DB_PATH=/app/data/tennis.db`, creates `/app/data` dir, runs as appuser UID 1000
- `entrypoint.sh`: Handles init_db() + gunicorn startup — no changes needed for Compose
- HEALTHCHECK in Dockerfile: Used by `depends_on: condition: service_healthy`

### Established Patterns
- App binds to `0.0.0.0:5000` — accessible from other containers on same network
- ProxyFix middleware already configured in app.py (x_for=1, x_proto=1, x_host=1) — handles Caddy's forwarded headers
- CORS_ALLOWED_ORIGINS loaded from `.env` via `load_dotenv()` — env_file in compose passes it through

### Integration Points
- New files: `docker-compose.yml`, `Caddyfile`, `.env.example`
- Existing `.env` pattern: app already reads SECRET_KEY, CORS_ALLOWED_ORIGINS, FLASK_DEBUG from .env
- Dockerfile EXPOSE 5000: Used by Caddy's `reverse_proxy app:5000` (Docker DNS resolves service names)

</code_context>

<specifics>
## Specific Ideas

- DuckDNS domain is `nechvatal.duckdns.org` (not `tc-breakpoint-forderung` which is the old domain in 99_rpi.txt)
- Production external port is 10443 (FritzBox forwards 10443 → RPi 443)
- CORS must use `http://192.168.1.8:5000` for dev and `https://nechvatal.duckdns.org:10443/` for production

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-compose-stack*
*Context gathered: 2026-03-19*
