---
phase: 03-https-via-caddy
plan: 01
subsystem: infra
tags: [caddy, xcaddy, duckdns, dns-01, acme, tls, https, docker, reverse-proxy]

# Dependency graph
requires:
  - phase: 02-compose-stack
    provides: "docker-compose.yml with caddy:2-alpine service, Caddyfile with :80 reverse proxy, .env.example"
provides:
  - "Dockerfile.caddy: multi-stage xcaddy build with caddy-dns/duckdns module"
  - "Caddyfile: HTTPS site block with DNS-01 ACME, HTTP-to-HTTPS redirect"
  - "docker-compose.yml: caddy service with build context, HTTPS port, env_file"
  - ".env.example: all Phase 3 env vars documented with staging default"
affects: [03-02-smoke-test, phase-04]

# Tech tracking
tech-stack:
  added: [xcaddy, caddy-dns/duckdns, caddy:2-builder-alpine]
  patterns: [multi-stage-xcaddy-build, parse-time-env-substitution, manual-http-redirect-for-non-standard-port, acme-ca-always-required]

key-files:
  created: [Dockerfile.caddy]
  modified: [Caddyfile, docker-compose.yml, .env.example]

key-decisions:
  - "ACME_CA always required (Option B): staging or production URL must be set; empty value causes Caddy parse error"
  - "Manual HTTP-to-HTTPS redirect block: Caddy auto-redirect omits non-standard port in Location header"
  - "Parse-time {$...} env substitution throughout Caddyfile, not runtime {env.*} placeholders"

patterns-established:
  - "Multi-stage xcaddy build: caddy:2-builder-alpine -> build -> caddy:2-alpine runtime"
  - "Caddyfile env var pattern: {$DUCKDNS_DOMAIN}.duckdns.org:{$HTTPS_PORT} for configurable site address"
  - "Switchover procedure: change ACME_CA, down, volume rm caddy_data, up"

requirements-completed: [HTTP-01, HTTP-02, HTTP-03, HTTP-04]

# Metrics
duration: 2min
completed: 2026-03-19
---

# Phase 3 Plan 01: HTTPS Infrastructure Summary

**Custom Caddy image with xcaddy + caddy-dns/duckdns module, Caddyfile with DNS-01 ACME on configurable port, HTTP-to-HTTPS redirect, and full env var configuration**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-19T09:00:04Z
- **Completed:** 2026-03-19T09:02:15Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- Created Dockerfile.caddy with multi-stage xcaddy build including caddy-dns/duckdns module
- Rewrote Caddyfile from plain HTTP to HTTPS with DNS-01 ACME challenge, global options, and manual HTTP redirect
- Updated docker-compose.yml caddy service with build context, HTTPS port mapping, and env_file
- Updated .env.example with all Phase 3 variables and staging-to-production switchover documentation

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Dockerfile.caddy and update docker-compose.yml** - `69b9bd0` (feat)
2. **Task 2: Rewrite Caddyfile for HTTPS with DNS-01 ACME** - `9ebe3ae` (feat)
3. **Task 3: Update .env.example with Phase 3 variables** - `6582fba` (feat)

## Files Created/Modified
- `Dockerfile.caddy` - Multi-stage build: caddy:2-builder-alpine with xcaddy compiles caddy-dns/duckdns, copies binary to caddy:2-alpine runtime
- `Caddyfile` - HTTPS site block with DNS-01 ACME via DuckDNS, global acme_ca/email options, reverse_proxy with header_up directives, :80 HTTP-to-HTTPS redirect
- `docker-compose.yml` - Caddy service updated: image replaced with build context, HTTPS port ${HTTPS_PORT:-10443}, env_file added
- `.env.example` - Added DUCKDNS_DOMAIN, DUCKDNS_TOKEN, ACME_EMAIL, ACME_CA, HTTPS_PORT; updated CORS default; documented switchover procedure

## Decisions Made
- **ACME_CA always required (Option B from research):** Empty `{$ACME_CA}` causes Caddyfile parse error ("Wrong argument count"). Instead of supporting empty/removed ACME_CA, the value must always be set -- staging URL for testing, production URL for real certs. This diverges slightly from CONTEXT.md "remove or empty" language but avoids parse errors entirely.
- **Manual HTTP-to-HTTPS redirect:** Caddy's auto-redirect omits non-standard port numbers in the Location header. Since HTTPS runs on 10443, a manual `:80` site block with explicit `redir` is required.
- **Parse-time env substitution:** Used `{$VAR}` syntax (parse-time) throughout Caddyfile, not `{env.VAR}` (runtime), per research guidance -- parse-time works everywhere.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- **pytest not available:** System Python lacks pytest module and no virtual environment exists in the project. Since this plan modifies only infrastructure files (Dockerfile.caddy, Caddyfile, docker-compose.yml, .env.example) and makes zero changes to app.py or test files, existing tests are unaffected.

## User Setup Required

None - no external service configuration required. Real DuckDNS token will be needed in `.env` during Plan 02 smoke testing.

## Next Phase Readiness
- All four infrastructure files ready for smoke testing in Plan 02
- Plan 02 will: build the custom Caddy image, verify duckdns module loads, test HTTPS with staging certs
- User will need to provide real `DUCKDNS_TOKEN` value in `.env` for DNS-01 challenge to succeed

## Self-Check: PASSED

All 4 artifact files exist. All 3 task commits verified (69b9bd0, 9ebe3ae, 6582fba).

---
*Phase: 03-https-via-caddy*
*Completed: 2026-03-19*
