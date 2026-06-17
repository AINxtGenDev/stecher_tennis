# Session Checkpoint

**Date:** 2026-06-17
**Branch:** docker
**Version:** 3.60
**Latest commit:** `d89e03c` chore: bump version to 3.61 • 17. Juni 2026
**Git Status:** pushed to origin/docker; untracked: `REVIEW.md`, `REVIEW-TEMPLATES.md` (not committed)
**Production:** **v3.61 live on RPi** (deployed 2026-06-17; container hardening active since 2026-04-08)

## Current Session (2026-06-17)

### Fixed 3 Critical findings + WR-03 (from REVIEW.md)

Acted on the review findings deferred last session. Each fix is an atomic commit;
all 9 tests pass (7 existing + 2 new smoke tests).

- **CR-02** (`11bb39c`) — Operator-precedence/casing bug in the UNIQUE-constraint
  check of `add_player` (`app.py:2064`) and `update_player` (`app.py:2159`). The
  `A or B and C` parse plus an uppercase `"UNIQUE"` literal searched in a
  `.lower()`'d string made branch A dead. Replaced both with the proven pattern
  from `newplayer_challenge`.
- **CR-03** (`1abf88e`) — In `resolve_expired_challenges`, moved `emit_data_update`
  outside the `with db:` block so it broadcasts only after the commit (was
  publishing uncommitted state).
- **CR-01** (`6ad71d8`) — `resolve_expired_challenges()` was dead code (never
  called). Added a throttled `@app.before_request` hook (runs at most once/min)
  that invokes it. Chose `before_request` over an eventlet background task because
  it runs identically under `python app.py` and gunicorn and doesn't depend on
  monkey-patching. Trade-off: cleanup only fires on traffic — fine for a 10-day rule.
- **WR-03** (`2dab8d0`) — Added `eventlet.monkey_patch()` at the very top of
  `app.py` (before `logging`, to avoid the lock deadlock). Restores dev/prod parity
  (gunicorn eventlet workers already patch). Added `tests/test_eventlet_patch.py`.
  Key correction to the review: `monkey_patch()` does NOT fix `sqlite3`/`bcrypt`
  blocking — those are C extensions; only `eventlet.tpool` would, which is a larger
  future change (deliberately out of scope).

### Version bump + deploy
- Bumped to **v3.61 • 17. Juni 2026** (`d89e03c`): `APP_VERSION` in app.py + footer in index.html.
- Built multi-arch (amd64 + arm64) via `build-and-push.sh`, pushed to GHCR:
  - app `:v3.61`/`:latest` → manifest `sha256:84aaec99…d3916`
  - caddy `:v3.61`/`:latest` → manifest `sha256:97391864…0724d`
  - GHCR_TOKEN was sourced from the stored docker `~/.docker/config.json` `ghcr.io` auth (no token in shell history).
- Deployed to RPi (`~/stecher_tennis`, `docker compose pull && up -d`). Verified:
  running container image digests match the pushed manifests, `APP_VERSION = "3.61"`,
  footer `Version: 3.61 • 17. Juni 2026`, app container `healthy`.
- External LAN HTTPS check (`:10443`) not confirmable — known NAT-hairpin router limitation.

### Still open (deferred)
- REVIEW.md: WR-01, WR-02, WR-04, WR-05, WR-06, WR-07 + 5 Info
- REVIEW-TEMPLATES.md: all 13 findings (6 Warning, 7 Info)

## Prior Session (2026-04-17)

### Code Review Pass (no code changes)
Spawned `gsd-code-reviewer` agents against `app.py` and all 5 templates. Produced two artifacts (not committed):

- `REVIEW.md` — app.py: 3 Critical, 7 Warning, 5 Info (15 total)
- `REVIEW-TEMPLATES.md` — templates: 0 Critical, 6 Warning, 7 Info (13 total)

### Top Findings (combined priority)

**Critical (app.py):**
1. **CR-01** — `resolve_expired_challenges()` at `app.py:743-814` is defined but **never called anywhere**. No `before_request` hook, no background task. Business rule "10-day auto-resolve" is silently broken; `is_new` flags on expired new-player challengers never clear.
2. **CR-02** — Operator-precedence bug in `add_player` (`app.py:2064-2069`) and `update_player` (`app.py:2159-2164`). `A or (B and C)` parsing plus an uppercase `"UNIQUE"` literal searched inside a `.lower()`'d haystack makes the first branch dead. Correct pattern already exists at `app.py:1868-1871` in `newplayer_challenge` — copy it.
3. **CR-03** — In `resolve_expired_challenges` (`app.py:766-805`), `emit_data_update` fires **inside** `with db:` despite a comment claiming "after commit". Broadcasts uncommitted state; if commit fails, clients hold rolled-back data.

**Warning (app.py):**
- WR-01 `emit_data_update("new_player_added")` labels player ID as `challenge_id` (`app.py:1839-1846`). `cursor.lastrowid` at that point refers to the player INSERT, not the challenge INSERT.
- WR-02 `@login_required` on Socket.IO handlers is ineffective (`app.py:2592-2604`). Follow the manual `current_user.is_authenticated` pattern from `handle_connect`.
- WR-03 No `eventlet.monkey_patch()` — `bcrypt`/`sqlite3`/`shutil.copy2` block the event loop.
- WR-04 `import_database` uses `shutil.copy2` on WAL-mode DB (`app.py:2480-2494`) — corruption risk; use sqlite3 backup API (already used for export).
- WR-05 `login_attempts` / `login_attempts_by_ip` dicts grow unbounded.
- WR-06 `reset_completed_challenges_display` uses `datetime.now()` instead of `get_current_time()` (`app.py:2378`) — breaks `TEST_DATE`.
- WR-07 `submit_result` has no result allowlist before DB writes.

**Warning (templates):**
- WR-01 Reflected XSS risk in `index.html:428, 443, 457` — three `.html(response.message)` calls inject server strings as raw HTML.
- WR-02 **Inconsistent nav privilege guards** — `admin.html:70-75` gates the admin link, but `index.html:243` and `db_settings.html:73` show it to everyone. (Already tracked as #14 in Remaining Items.)
- WR-03 `admin.html` Socket.IO `data_update` wipes in-progress result forms via `$challengesContainer.html(newContent)` (`admin.html:211`). Needs dirty-form guard.
- WR-04/05 `/eligible_opponents` XHR has no `.fail()` handler; array-vs-error shape detection is conflated (`index.html:429`).
- WR-06 `data-valid-play-dates='${JSON.stringify(...)}'` uses single-quoted attr with JSON; `JSON.stringify` doesn't escape `'` (latent; dates only today).

### What's Solid
- CSRF wiring (meta tag + `$.ajaxSetup beforeSend` + hidden form inputs) correct throughout
- `escapeHtml()` consistently applied for player-name insertions in index.html core
- Jinja auto-escaping covers all server-rendered output
- SRI hashes on all CDN resources
- `error.html` and `stecher_start.html` clean
- Recent fixes (parse_datetime helper, delta Socket.IO, SECRET_KEY enforcement, DB indexes) are solid

### No Code Changes This Session
User reviewed findings but deferred fixes. REVIEW.md and REVIEW-TEMPLATES.md remain untracked for a future fix session.

## Prior Session (2026-04-08)

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
