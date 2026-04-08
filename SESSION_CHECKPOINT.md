# Session Checkpoint

**Date:** 2026-04-08
**Branch:** docker
**Version:** 3.60
**Latest commit:** `88f932a` fix: add NET_BIND_SERVICE cap for Caddy
**Git Status:** clean (all committed and pushed)
**Production:** v3.60 live on RPi (deployed 2026-04-08, container hardening active)

## Current Session (2026-04-08)

### Container Hardening
Added security directives to both Docker containers in docker-compose.yml:
- `read_only: true` — immutable root filesystem (volumes remain writable)
- `security_opt: [no-new-privileges:true]` — prevents privilege escalation
- `cap_drop: [ALL]` — drops all Linux capabilities
- `tmpfs: /tmp` on app container for eventlet
- `cap_add: [NET_BIND_SERVICE]` on Caddy (required for binding ports 80/443)

### Issue: Caddy crash after cap_drop ALL
- `cap_drop: ALL` removed `NET_BIND_SERVICE` which Caddy needs → `exec /usr/bin/caddy: operation not permitted`
- Fixed by adding `cap_add: NET_BIND_SERVICE` back for Caddy only

## Prior Session (2026-04-06 evening → 2026-04-07)

### Code Review & Fixes
Performed full code review (security, quality, performance, frontend) and fixed the top 5 findings:

1. **SECRET_KEY required** — App crashes on startup if SECRET_KEY env var is missing instead of using insecure default
2. **Database indexes** — 4 new indexes on foreign keys and frequently filtered columns (schema.sql + auto-created in init_db for existing DBs)
3. **Delta Socket.IO updates** — `emit_data_update()` now queries only needed data sections per update type. Client `updateUI` handles partial payloads.
4. **parse_datetime() helper** — Replaced 26+ duplicated strptime patterns with single helper. Added `_get_field()` for safe access on sqlite3.Row objects.
5. **Silent except:pass eliminated** — Replaced with logged warnings

### Bugs Found & Fixed During Testing
- **sqlite3.Row .get() crash** — Fixed with `_get_field()` helper
- **Pyramid disappearing on availability toggle** — Fixed by requiring both `players` AND `active_challenges` for pyramid rebuild
- **FLASK_DEBUG=false breaks local dev** — Reverted .env to true (set false only on production Pi)

### Additional Fixes
- Removed leading dash from "gesperrt bis" text in blocked players list
- Bumped version to 3.60 • 7. April 2026
- Updated README: correct API routes, LOC counts, SECRET_KEY docs
- Removed obsolete report HTML files

### Comprehensive Testing (56 tests, 0 failures)
Full automated test via Chrome DevTools MCP — see `result.md` for details.

### Deployment
- Built multi-arch images (AMD64 + ARM64) via `build-and-push.sh`
- Pushed to GHCR: `ghcr.io/ainxtgendev/stecher-tennis-app:v3.60`
- Deployed to RPi: `docker compose pull && docker compose up -d`
- Both containers healthy: app + caddy

### Deployment
- `git pull` + `docker compose up -d` on RPi (compose-only change, no image rebuild needed)
- Verified: `docker inspect` confirms `ReadonlyRootfs: true`

## Commits (this session)
- `88f932a` fix: add NET_BIND_SERVICE cap for Caddy to bind ports 80/443
- `461f6df` security: harden Docker containers with read-only fs, no-new-privileges, cap-drop

## Prior Sessions
- 2026-04-06 evening → 2026-04-07: Code review, v3.60, delta updates, deploy
- 2026-04-06 afternoon: Bootstrap modals replacing native dialogs
- 2026-04-06 morning: Tablet pyramid display fix
- 2026-04-05: Result submission fix, Docker deployment setup

## RPi Deployment Notes
- **Production traffic** goes through Docker containers, NOT systemd service
- Deploy (image changes): `build-and-push.sh` → `ssh stecher 'cd ~/stecher_tennis && docker compose pull && docker compose up -d'`
- Deploy (compose-only changes): `ssh stecher 'cd ~/stecher_tennis && git pull && docker compose up -d'`
- Caddy runs as Docker container for HTTPS via DuckDNS DNS-01 ACME
- External HTTPS check from LAN fails (NAT hairpin issue — router limitation)

## Next Steps
- Merge docker → main
- Deploy to second club (ts-breaking.duckdns.org)

## Remaining Items
### Security
- C2: Hardcoded default passwords returned to client
- ~~#8 No container hardening in docker-compose.yml~~ ✓ Fixed 2026-04-08
- #9 Caddy receives all env vars including SECRET_KEY
- #14 Inconsistent nav bar privilege guard

### Performance
- P3-P8: Redundant queries, unused server-side pyramid, payload bloat (partially addressed by delta updates)

### Other
- Test coverage low (7 unit tests, no business logic coverage)
- RPi: clean up unused systemd service + native Caddy
