# Phase 3: HTTPS via Caddy - Context

**Gathered:** 2026-03-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Automatic TLS working end-to-end via DuckDNS DNS-01 challenge. Replace the Phase 2 plain HTTP Caddy setup with a custom Caddy build (xcaddy + caddy-dns/duckdns module). App reachable over HTTPS at `nechvatal.duckdns.org:10443` with valid Let's Encrypt certificate. HTTP-to-HTTPS redirect on port 80. WebSocket connections work over HTTPS. Staging/production ACME toggle via env var.

</domain>

<decisions>
## Implementation Decisions

### DuckDNS credentials & domain
- Domain configured via `DUCKDNS_DOMAIN` env var in `.env` (value: `nechvatal`)
- Caddyfile uses `{$DUCKDNS_DOMAIN}.duckdns.org` — not hardcoded
- DuckDNS token passed via `DUCKDNS_TOKEN` env var in `.env`
- TLS email configurable via `ACME_EMAIL` env var (value: `otto.kuegerl@gmail.com`)
- DuckDNS IP updates handled externally by existing RPi cron — Docker does NOT update DuckDNS IP
- Token is only used for DNS-01 ACME challenge inside the Caddy container
- All env vars passed to Caddy service via single shared `.env` file (no separate caddy.env)

### Port & redirect strategy
- Caddy listens on port 10443 (HTTPS) and port 80 (HTTP redirect) inside Docker
- Docker maps `10443:10443` and `80:80` to host
- No FritzBox port translation needed — Caddy serves directly on the external-facing port
- HTTPS port configurable via `HTTPS_PORT` env var in `.env` (default: 10443)
- HTTP requests to port 80 redirect permanently to `https://{$DUCKDNS_DOMAIN}.duckdns.org:{$HTTPS_PORT}{uri}`
- CORS_ALLOWED_ORIGINS in `.env.example` updated to `https://nechvatal.duckdns.org:10443`

### ACME staging workflow
- ACME endpoint toggled via `ACME_CA` env var in `.env`
- `.env.example` ships with staging URL as default: `https://acme-staging-v02.api.letsencrypt.org/directory`
- For production: remove or empty the `ACME_CA` line (Caddy defaults to Let's Encrypt production)
- When switching staging → production: clear `caddy_data` volume (`docker volume rm`) for clean slate
- Documented switchover procedure: edit .env → docker compose down → docker volume rm caddy_data → docker compose up -d
- Phase 3 smoke tests run on NUC8 with staging certs; production cert verification deferred to Phase 4 on RPi

### Claude's Discretion
- xcaddy Dockerfile structure and base image choice
- Caddy global options block (if needed)
- Exact Caddyfile formatting and log configuration
- How to handle empty/unset ACME_CA in Caddyfile (conditional or default behavior)
- caddy_config volume addition (if needed alongside caddy_data)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Docker infrastructure (Phase 1-2 output)
- `Dockerfile` — App container, multi-stage build, non-root appuser, HEALTHCHECK
- `docker-compose.yml` — Two services (app + caddy), internal network, named volumes, env_file
- `Caddyfile` — Current Phase 2 plain HTTP reverse proxy on :80 (will be rewritten)
- `.env.example` — Current env vars (SECRET_KEY, CORS_ALLOWED_ORIGINS, FLASK_DEBUG, TEST_DATE)
- `entrypoint.sh` — App entrypoint (init_db + gunicorn)

### Existing production setup
- `documentation/99_rpi.txt` — Current RPi Caddyfile (tc-breakpoint-forderung.duckdns.org, tls email, WebSocket headers), FritzBox port forwarding (10443→443, 80→80), DuckDNS cron with tokens

### Prior phase context
- `.planning/phases/01-app-container/01-CONTEXT.md` — Phase 1 decisions (DB_PATH, health endpoint, named volumes)
- `.planning/phases/02-compose-stack/02-CONTEXT.md` — Phase 2 decisions (caddy:2-alpine → custom build in Phase 3, caddy_data volume, internal network, env_file pattern)

### Requirements
- `.planning/REQUIREMENTS.md` — HTTP-01 through HTTP-04 define Phase 3 acceptance criteria

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Caddyfile`: Phase 2 reverse_proxy block with header_up directives — keep the reverse_proxy section, add TLS config
- `docker-compose.yml`: caddy service already has caddy_data volume and depends_on — replace image with build, update ports, add environment vars
- `.env.example`: Extend with Phase 3 vars (DUCKDNS_DOMAIN, DUCKDNS_TOKEN, ACME_EMAIL, ACME_CA, HTTPS_PORT)

### Established Patterns
- Caddy reverse_proxy to `app:5000` with header_up (Host, X-Real-IP, X-Forwarded-For, X-Forwarded-Proto) — proven working in Phase 2
- `env_file: .env` pattern for passing config to containers — reuse for Caddy env vars
- ProxyFix middleware in app.py (x_for=1, x_proto=1, x_host=1) — already handles forwarded headers from Caddy

### Integration Points
- New file: `Dockerfile.caddy` (or `caddy/Dockerfile`) — xcaddy build with caddy-dns/duckdns
- Modified: `Caddyfile` — rewrite for HTTPS with DNS-01, HTTP redirect, env var substitution
- Modified: `docker-compose.yml` — caddy service gets build context, updated ports (10443+80), environment section
- Modified: `.env.example` — add DUCKDNS_DOMAIN, DUCKDNS_TOKEN, ACME_EMAIL, ACME_CA, HTTPS_PORT

</code_context>

<specifics>
## Specific Ideas

- Domain is `nechvatal.duckdns.org` — NOT `tc-breakpoint-forderung` (that's the old domain in 99_rpi.txt)
- External HTTPS port is 10443 (matching existing FritzBox rule, no router reconfiguration needed)
- DuckDNS token for `nechvatal` domain: `f5035eb4-6739-4f5e-b0e7-5ee827c7062d` (from 99_rpi.txt cron script)
- Staging certs first on NUC8 to validate the pipeline; production certs on RPi in Phase 4

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-https-via-caddy*
*Context gathered: 2026-03-19*
