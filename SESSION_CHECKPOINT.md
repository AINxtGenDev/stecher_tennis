# Session Checkpoint — 2026-03-20

## What Was Done

### 1. CLAUDE.md Created
- Project-level guidance file for Claude Code created at repo root

### 2. Codebase Mapped (GSD)
- `.planning/codebase/` created with 7 documents (STACK, ARCHITECTURE, STRUCTURE, CONVENTIONS, TESTING, INTEGRATIONS, CONCERNS)
- Committed: `1515b41`

### 3. Reset Completed Challenges Button
- **New feature:** Blue button in `db_settings.html` above Danger Zone that resets the "Durchgeführte Herausforderungen" display to 0 without deleting data
- **How it works:** `app_settings` table stores a `completed_challenges_hidden_before` timestamp. `get_completed_challenges()` filters out challenges resolved before that cutoff. All data remains in the database.
- **Files changed:** `app.py`, `schema.sql`, `templates/db_settings.html`
- **New route:** `POST /reset_completed_challenges_display` (superadmin only)
- **Tested:** via Chrome DevTools MCP — confirmed count goes from 50 → 0

### 4. Version Bumped
- `templates/index.html`: Version 3.45 → **3.46 • 18. März 2026**
- Committed + pushed: `9ed62eb` (on `main`)

### 5. Docker Branch Created
- Branch `docker` created and pushed to `origin/docker`
- All Docker work happens on this branch

### 6. GSD Project Initialized for Docker Deployment
- **PROJECT.md:** Dockerize the tennis app for one-command deployment
- **Research:** 4 parallel researchers completed (Stack, Features, Architecture, Pitfalls) → `.planning/research/`
- **REQUIREMENTS.md:** 16 v1 requirements across 4 categories (Containerization, Compose, HTTPS, Operations)
- **ROADMAP.md:** 4 phases defined and approved
- Committed: `4f8a59c`

### 7. Phase 1 Context Gathered (discuss-phase)
- Discussed 3 gray areas: Production dependencies, Health endpoint design, DB_PATH migration strategy
- **Key decisions:**
  - New `docker-requirements.txt` with pinned versions (keep `prod-requirements.txt` as-is)
  - Core Flask/SocketIO/bcrypt stack + requests + pydantic; exclude AI libs, numpy, scipy, Pillow
  - `GET /health` → `{"status": "ok"}`, public, CSRF-exempt
  - `DB_PATH` env var with fallback to `tennis.db` in project root
  - Auto-create parent dirs, auto-seed on first run
  - Update `backup_tennis_db.sh` to respect `DB_PATH`
- Committed: `11714de`

### 8. Phase 1 Planned (plan-phase)
- **Research:** Researcher agent investigated Docker best practices, verified all 19 runtime dependencies with exact versions from conda env
- **Critical finding:** `init_db()` only runs under `__main__` — gunicorn won't trigger it. Entrypoint script needed to call `init_db()` before exec-ing gunicorn
- **Validation strategy:** Created `01-VALIDATION.md` with Nyquist sampling (pytest + Docker smoke tests)
- **Plans created:** 2 plans in 2 waves
  - **Wave 1 — Plan 01-01:** Docker infrastructure (Dockerfile, docker-requirements.txt, .dockerignore, entrypoint.sh) + app.py modifications (DB_PATH, /health endpoint, backup script update)
  - **Wave 2 — Plan 01-02:** Test suite (pytest: test_health.py, test_db_path.py, conftest.py) + Docker smoke test checkpoint
- **Verification:** Plan checker passed all 9 dimensions, 7/7 requirements covered
- Committed: `9bad83f`

### 9. Phase 1 Executed (execute-phase) ✓
- **Wave 1 — Plan 01-01:** Docker infrastructure built
  - `Dockerfile` — multi-stage build (python:3.12-slim), non-root `appuser`, HEALTHCHECK via urllib
  - `docker-requirements.txt` — 19 pinned production dependencies
  - `.dockerignore` — excludes .git, __pycache__, *.db, .env, .planning/
  - `entrypoint.sh` — calls `init_db()` before exec-ing gunicorn (1 worker, eventlet)
  - `app.py` — DB_PATH env var with `os.makedirs` + fallback; `/health` endpoint (CSRF-exempt, public)
  - `backup_tennis_db.sh` — respects `DB_PATH` env var
  - Commits: `7d43a1a`, `9832feb`
- **Wave 2 — Plan 01-02:** Test suite + Docker smoke tests
  - `pytest.ini`, `tests/conftest.py`, `tests/test_health.py`, `tests/test_db_path.py` — 7 unit tests, all passing
  - Docker smoke test: image builds (154MB), /health returns ok, non-root user confirmed, single eventlet worker, DB_PATH respected, logs to stdout
  - All 7 requirement proofs verified (CONT-01–04, OPS-01–03)
  - Commit: `133b909`
- **Verification:** Passed — 7/7 must-haves confirmed against actual codebase
- **Phase completion committed:** `75cfb30`, `db2480c`

### 10. Phase 2 Context Gathered (discuss-phase)
- Discussed 3 gray areas: Caddy image strategy, Host port mapping, Environment config
- **Key decisions:**
  - Official `caddy:2-alpine` image for Phase 2 (custom xcaddy build deferred to Phase 3)
  - Caddyfile: HTTP-only on `:80`, WebSocket header_up directives included from the start
  - Caddy exposes port 80 to host; app port 5000 internal only (COMP-02)
  - Caddy waits for app HEALTHCHECK via `depends_on: condition: service_healthy`
  - Named volumes: `tennis_data` at `/app/data`, `caddy_data` for Caddy state
  - Restart policy: `unless-stopped` for both services
  - `env_file: .env` in docker-compose.yml; `.env` git-ignored, `.env.example` tracked
  - Phase 2 vars only in `.env.example` — no Phase 3 placeholders
  - CORS: `http://192.168.1.8:5000` (dev) / `https://nechvatal.duckdns.org:10443/` (prod)
- **Domain correction:** DuckDNS domain is `nechvatal.duckdns.org` (not `tc-breakpoint-forderung`)
- Committed: `44d6ee4`

### 11. Phase 2 Planned (plan-phase)
- **Research:** Researcher agent investigated docker-compose patterns, Caddy reverse proxy config, volume strategies
- **Key finding:** Caddy 2 handles WebSocket upgrades automatically — `header_up` directives in CONTEXT.md are for Flask's `ProxyFix`, not WebSocket. COMP-02 (port isolation) requires simply omitting `ports:` on app service.
- **Validation strategy:** Created `02-VALIDATION.md` — all 4 COMP requirements are smoke/integration tests (manual, not pytest)
- **Plans created:** 2 plans in 2 waves
  - **Wave 1 — Plan 02-01:** docker-compose.yml (two services, internal network, named volumes, restart policy, depends_on healthcheck, env_file) + Caddyfile (reverse proxy to app:5000, WebSocket headers)
  - **Wave 2 — Plan 02-02:** .env.example (SECRET_KEY, CORS_ALLOWED_ORIGINS, FLASK_DEBUG, TEST_DATE) + full stack smoke tests (COMP-01 through COMP-04)
- **Verification:** Plan checker passed all 9 dimensions, 4/4 requirements covered
- Commits: `e90a9a7`, `246dd8b`, `b0a422b`

### 12. Phase 2 Executed (execute-phase) ✓
- **Wave 1 — Plan 02-01:** Docker Compose + Caddyfile
  - `docker-compose.yml` — two services (app + caddy) on `tennis_net` bridge network, named volumes (`tennis_data`, `caddy_data`), app port 5000 internal only, Caddy on 80:80, `depends_on: condition: service_healthy`, `restart: unless-stopped`, `env_file: .env`
  - `Caddyfile` — `:80` plain HTTP reverse proxy to `app:5000` with four `header_up` directives (Host, X-Real-IP, X-Forwarded-For, X-Forwarded-Proto), no TLS (Phase 3)
  - Commits: `17c5866`, `a4df9fc`
- **Wave 2 — Plan 02-02:** .env.example + full stack smoke tests
  - `.env.example` — SECRET_KEY, CORS_ALLOWED_ORIGINS, FLASK_DEBUG, TEST_DATE with safe defaults and usage instructions
  - Smoke test: all 4 COMP requirements verified live (port 80 temporarily freed from `midvale-frontend`)
    - COMP-01: Both services started and healthy
    - COMP-02: `curl localhost/health` → 200 via Caddy; `curl localhost:5000/health` → connection refused
    - COMP-03: Data persisted across `docker compose down && up -d` cycle
    - COMP-04: All env vars documented in `.env.example`
  - Commits: `9b8de60`, `a98a658`
- **Verification:** Passed — 10/10 must-haves (8 automated, 2 human-verified)
- **Phase completion committed:** `f863cb8`

### 13. Phase 3 Context Gathered (discuss-phase)
- Discussed 3 gray areas: DuckDNS credentials & domain, Port & redirect strategy, ACME staging workflow
- **Key decisions:**
  - All config via env vars: `DUCKDNS_DOMAIN`, `DUCKDNS_TOKEN`, `ACME_EMAIL`, `ACME_CA`, `HTTPS_PORT`
  - Caddyfile uses `{$DUCKDNS_DOMAIN}.duckdns.org` — domain not hardcoded
  - Single shared `.env` file for both app and Caddy services (no separate caddy.env)
  - DuckDNS IP updates stay external (RPi cron) — Docker only uses token for DNS-01 ACME
  - Caddy listens directly on 10443 (HTTPS) + 80 (HTTP redirect) — no FritzBox port translation
  - `HTTPS_PORT` env var for configurability
  - HTTP→HTTPS redirect targets `https://domain:10443`
  - CORS_ALLOWED_ORIGINS updated to `https://nechvatal.duckdns.org:10443`
  - `.env.example` defaults to Let's Encrypt staging URL (safe)
  - Clear `caddy_data` volume when switching staging→production certs
  - Phase 3 smoke tests on NUC8 with staging certs; production cert on RPi in Phase 4
- Committed: `cb88900`

### 14. Phase 3 Planned (plan-phase)
- **Research:** Researcher agent investigated xcaddy builds, Caddy DNS-01 ACME, DuckDNS module, non-standard port redirect
- **Key findings:**
  - Custom Caddy build via `caddy:2-builder-alpine` + `xcaddy build --with github.com/caddy-dns/duckdns`
  - Empty `ACME_CA` env var causes Caddy parse error — must always be set (staging or production URL)
  - Caddy auto-redirect does NOT include non-standard port — manual `:80` redirect block required
  - Caddy v2 handles WebSocket upgrade automatically — no special directives needed
  - `caddy_config` volume not needed for Caddyfile setups
- **Validation strategy:** Created `03-VALIDATION.md` — all HTTP requirements are smoke/integration tests (Docker build + HTTPS connectivity)
- **Plans created:** 2 plans in 2 waves
  - **Wave 1 — Plan 03-01:** Dockerfile.caddy (xcaddy + duckdns module), Caddyfile (HTTPS + DNS-01 + HTTP redirect), docker-compose.yml (build context, port 10443+80, env_file), .env.example (DUCKDNS_DOMAIN, DUCKDNS_TOKEN, ACME_EMAIL, ACME_CA, HTTPS_PORT, updated CORS)
  - **Wave 2 — Plan 03-02:** Build verification (caddy list-modules | grep duckdns) + full HTTPS smoke test with staging certificate (checkpoint:human-verify)
- **Design decision:** `ACME_CA` always required (Option B from research) — staging URL or production URL `https://acme-v02.api.letsencrypt.org/directory`, never empty
- **Verification:** Plan checker passed all 9 dimensions, 4/4 requirements covered
- Commits: `bc0baa0`, `dc2b23e`, `8aba1d3`

### 15. Phase 3 Executed (execute-phase) ✓
- **Wave 1 — Plan 03-01:** HTTPS infrastructure files
  - `Dockerfile.caddy` — multi-stage build: `caddy:2-builder-alpine` + `xcaddy build --with github.com/caddy-dns/duckdns`, copies custom binary to `caddy:2-alpine`
  - `Caddyfile` — rewritten for HTTPS: global `acme_ca`/`email` block, HTTPS site block `{$DUCKDNS_DOMAIN}.duckdns.org:{$HTTPS_PORT}` with `dns duckdns` TLS, reverse proxy to `app:5000` with 4 `header_up` directives, `:80` block with permanent redirect to HTTPS (includes non-standard port)
  - `docker-compose.yml` — caddy service updated: `build: { dockerfile: Dockerfile.caddy }` replaces `image: caddy:2-alpine`, ports `10443+80`, `env_file: .env` added
  - `.env.example` — added DUCKDNS_DOMAIN, DUCKDNS_TOKEN, ACME_EMAIL, ACME_CA (staging default), HTTPS_PORT; CORS updated to `https://nechvatal.duckdns.org:10443`; switchover procedure documented
  - Commits: `69b9bd0`, `9ebe3ae`, `6582fba`, `8221b41`
- **Wave 2 — Plan 03-02:** Build verification + HTTPS smoke test
  - Custom Caddy image built, `caddy list-modules | grep duckdns` → `dns.providers.duckdns`
  - All 7 existing pytest tests pass (no regressions)
  - **Deviation:** Added `dns: [8.8.8.8, 8.8.4.4]` to caddy service in `docker-compose.yml` — Docker inherits host's `127.0.0.53` (systemd-resolved), unreachable from container network namespace
  - Smoke test results (all passed):
    - HTTP-01: duckdns module present in custom build
    - HTTP-02: staging TLS cert obtained (`(STAGING) Puzzling Parsnip E7`), HTTP/2 200, TLSv1.3
    - HTTP-03: Socket.IO polling works via HTTPS, websocket upgrade available
    - HTTP-04: `ACME_CA` env var shows staging URL
    - HTTP redirect: 301 → `https://nechvatal.duckdns.org:10443/health`
  - `midvale-frontend` stopped to free port 80 (restart with `docker start midvale-frontend`)
  - Commits: `5e75a28`, `16d4786`
- **Verification:** Passed (human_needed → approved) — 6/6 config truths verified, 4/4 runtime behaviors confirmed via smoke test
- **Phase completion committed:** `8bde4d9`, `edea9e3`

### 16. Phase 4 Context Gathered (discuss-phase)
- Discussed 4 gray areas: Container registry, Build strategy, RPi deployment procedure, Image tagging
- **Key decisions:**
  - Push to GHCR (public): `ghcr.io/ainxtgendev/stecher-tennis-app` + `ghcr.io/ainxtgendev/stecher-tennis-caddy`
  - docker-compose.yml uses GHCR `image:` refs; separate `docker-compose.build.yml` override for local NUC8 builds
  - QEMU cross-compile on NUC8 via `docker buildx` (both linux/amd64 + linux/arm64)
  - `build-and-push.sh` script: creates buildx builder, builds both images, pushes to GHCR; auth via `GHCR_TOKEN` env var
  - Expect Dockerfiles work as-is on ARM64 — verify during smoke test
  - Git clone repo on RPi; updates via `git pull && docker compose pull && docker compose up -d`
  - Full cutover script via SSH (`stecher` alias → `192.168.1.213`): stops old systemd+Caddy, starts Docker stack, verifies health
  - Staging→production Let's Encrypt cert switch included in Phase 4
  - Tag images with app version (e.g., `v3.46`) + `:latest`; both images share same tag
  - docker-compose.yml uses `:latest`; version tags in GHCR for rollback
- Committed: `f91f5ce`

### 17. Phase 4 Planned (plan-phase)
- **Research:** Researcher agent investigated docker buildx multi-platform builds, GHCR publishing, ARM64 wheel availability, RPi deployment patterns
- **Key findings:**
  - Both `python:3.12-slim` and `caddy:2-builder-alpine`/`caddy:2-alpine` have verified ARM64 variants
  - bcrypt 4.3.0 and greenlet 3.1.1 ship pre-built `manylinux_2017_aarch64` wheels — no source compilation needed under QEMU
  - NUC8 has Docker 29.3.0 + buildx v0.31.1 but needs QEMU binfmt registration and a docker-container driver builder
  - SSH alias `stecher` connects to RPi at `192.168.1.213:10115` with key auth
  - Old services: `stecher-tennis.service` (systemd) + `caddy.service` (apt-installed)
- **Validation strategy:** Created `04-VALIDATION.md` — all CONT-05 sub-behaviors are smoke/manual tests (build verification, RPi SSH checks, HTTPS cert, reboot resilience)
- **Plans created:** 2 plans in 2 waves
  - **Wave 1 — Plan 04-01:** `build-and-push.sh` (QEMU setup, buildx builder, version extraction, dual-image multi-platform build+push to GHCR), `docker-compose.yml` updated to GHCR `image:` refs, `docker-compose.build.yml` local build override
  - **Wave 2 — Plan 04-02:** `deploy.sh` RPi cutover script (stop old systemd+Caddy, enable Docker, clone/pull repo, pull GHCR images, start stack, health check, staging→production ACME switch), human verification checkpoint (HTTPS, WebSocket, data persistence, reboot resilience)
- **Verification:** Plan checker passed all 9 dimensions, 1/1 requirement (CONT-05) covered
- Commits: `9c23b2b`, `d520b98`, `aedf7c3`

### 18. Roadmap — 4 Phases

| # | Phase | Goal | Requirements | Status |
|---|-------|------|--------------|--------|
| 1 | App Container | Dockerfile, non-root user, health endpoint, gunicorn config | CONT-01–04, OPS-01–03 | ✓ Complete |
| 2 | Compose Stack | docker-compose.yml with app + Caddy, SQLite volume, .env | COMP-01–04 | ✓ Complete |
| 3 | HTTPS via Caddy | Custom Caddy build with DuckDNS, DNS-01 ACME, WebSocket | HTTP-01–04 | ✓ Complete |
| 4 | Multi-Arch & RPi | buildx for ARM64+AMD64, deploy on Raspberry Pi | CONT-05 | ✓ Complete |

### 19. Phase 4 Executed (execute-phase) ✓
- **Wave 1 — Plan 04-01:** Multi-arch build infrastructure
  - `build-and-push.sh` — QEMU binfmt + buildx builder, builds app + caddy for linux/amd64,linux/arm64, pushes to GHCR with version tag + :latest
  - `docker-compose.yml` — switched from local `build:` to GHCR `image:` refs
  - `docker-compose.build.yml` — local build override for NUC8 development
  - Commits: `4475f22`, `ba58ec4`, `5ffaa8d`
- **Wave 2 — Plan 04-02:** RPi deployment + live verification
  - `deploy.sh` — automated RPi cutover script (SSH pre-flight, stop old systemd services, clone repo, pull GHCR images, start Docker stack, health check, staging→production cert switch)
  - Live deployment fixes applied during execution:
    - Repo URL casing fixed (AINxtGenDev/stecher_tennis)
    - Clone logic handles existing non-git directory (backup + fresh clone)
    - Health check uses `docker compose exec` (curl not in slim image)
    - Caddyfile + docker-compose.yml: port 443 internally (FritzBox maps ext 10443 → int 443)
  - GHCR packages made public, RPi authenticated with GHCR
  - .env configured on RPi: SECRET_KEY, DUCKDNS_TOKEN, ACME_EMAIL set to real values
  - Commits: `6043602`, `6f3962e`, `6892e19`
- **Human verification passed:**
  - Production Let's Encrypt cert (issuer: Let's Encrypt E7, TLSv1.3)
  - WebSocket / real-time updates working
  - Containers survive RPi reboot (restart: unless-stopped)
- **Verification:** Passed — 7/7 must-haves, CONT-05 satisfied
- **Phase completion commits:** `555c0fd`, `b53a914`

### 20. README Updated
- Docker deployment section with step-by-step RPi clean install guide
- Updated project structure with Docker files
- Docker troubleshooting section
- Commit: `d016717`

### 21. Milestone v1.0 Complete 🎉
- All 4 phases, 8 plans, 16 requirements delivered
- App running on RPi as Docker Compose stack with production HTTPS

### 22. Local Dev Fixes (2026-03-19)
- **CORS fix:** Added `http://192.168.1.8:5000` to `CORS_ALLOWED_ORIGINS` in `.env` — Socket.IO was failing with 400 because only the production origin was allowed
- **Killed stale processes:** 3 `python3 app.py` instances were competing for port 5000; force-killed the suspended ones
- **UI tweak:** Shortened date/time dropdown placeholders in `index.html` — "Datum wählen..." → "Datum", "Zeit wählen..." → "Uhrzeit" for better readability
- **Nav button consistency:** Changed "Herausforderungen" and "DB-Einstellungen" from `btn-outline-secondary` (gray) to `btn-outline-primary` (blue) across all 3 templates — now matches "Rangliste" style. "Abmelden" stays red outlined.
- **Version bumped:** 3.46 → 3.47 • 19. März 2026
- Commits: `1038eeb`, `1c11b20`

### 23. RPi Health Check (2026-03-19)
- Verified RPi deployment is fully operational:
  - Both containers up and healthy (`app` + `caddy`)
  - `/health` returns `200 {"status":"ok"}` internally and externally
  - Production Let's Encrypt cert (issuer: E8), TLSv1.3, HTTP/2
  - HTTP→HTTPS redirect working (308)
  - App logs clean — only health checks and normal requests

### 24. v3.47 Deployed to Production RPi (2026-03-19)
- Built multi-arch images (amd64+arm64) via `build-and-push.sh`
- Pushed to GHCR: `stecher-tennis-app:v3.47` + `stecher-tennis-caddy:v3.47`
- Deployed: `git pull && docker compose pull && docker compose up -d`
- Verified: both containers healthy, `/health` returns 200 via HTTPS
- **Rollback:** v3.46 images still available on GHCR
- Commit: `0a5f7f6`

### 25. RPi Database Backup Automation (2026-03-19)
- **`backup_tennis_db.sh`** — adapted for Docker: uses `sudo sqlite3 .backup` on volume path, zips to `~/stecher_tennis/backup/`, 7-day retention, logs to `backup.log`
- **`check_db.sh`** — adapted for Docker: integrity check, foreign keys, schema & row counts via `sudo sqlite3`
- **Cron:** every 3h (`0 */3 * * *`), logs to `~/stecher_tennis/backup/cron.log`
- **Verified:** backup produces valid 12K zip with 41 players + 119 challenges matching live DB

### 26. Database Import/Export Feature (2026-03-20)
- **New feature:** "Datenbank Import / Export" card in `db_settings.html` above the "Herausforderungen" card
- **Export:** Download button triggers `GET /api/settings/db/export` — streams the SQLite file as `db_backup_<ISO-timestamp>.db` without page reload
- **Import:** File input (`.db` only) + confirmation button with dialog ("Achtung: Die bestehende Datenbank wird überschrieben.") → `POST /api/settings/db/import` validates SQLite integrity before replacing DB
- **Error handling:** Inline error/success messages for wrong file type, corrupt file, upload failures
- **Auth:** Both endpoints require superadmin
- **Files changed:** `app.py`, `templates/db_settings.html`
- Commits: `b401a40`, `75ede20`, `dca6d8f`

### 27. Backend Routes Fixed for DB Import/Export (2026-03-20)
- **Bug fix:** The executor had created the frontend card and JS but never added the backend routes to `app.py`
- Added `GET /api/settings/db/export` and `POST /api/settings/db/import` routes (superadmin only)
- Export uses `send_file` with `app.config["DATABASE"]` — works in both Docker (`DB_PATH`) and local dev mode
- Import validates SQLite integrity via `PRAGMA integrity_check` before replacing DB
- Also created missing `app_settings` table in local dev DB (existed in `schema.sql` but not in pre-existing DB)

### 28. Version Bumped (2026-03-20)
- `templates/index.html`: Version 3.47 → **3.48 • 20. März 2026**

## Current State
- **Branch:** `docker` (tracking `origin/docker`)
- **GSD status:** Milestone v1.0 complete. All 4 phases executed and verified.
- **RPi status:** Running Docker stack, production HTTPS, auto-restart on reboot, verified healthy 2026-03-19
- **GHCR images:** `ghcr.io/ainxtgendev/stecher-tennis-app:v3.47` + `ghcr.io/ainxtgendev/stecher-tennis-caddy:v3.47` (public)
- **RPi housekeeping:** `~/stecher_tennis` clean (git-tracked files only), `~/stecher_tennis.bak` kept (500MB, old bare-metal install)

## Key Info
- **Conda env:** `stecher_tennis`
- **Run app locally:** `conda activate stecher_tennis && python3 app.py`
- **Superadmin login:** MStecher / SuperSecretDevPassword!
- **DB in Docker:** `/var/lib/docker/volumes/stecher_tennis_tennis_data/_data/tennis.db` (NOT `~/stecher_tennis/tennis.db`)
- **DB restore:** `docker compose stop app && sudo cp backup.db /var/lib/docker/volumes/stecher_tennis_tennis_data/_data/tennis.db && sudo chown 1000:1000 ... && docker compose start app`
- **Remote:** `https://github.com/AINxtGenDev/stecher_tennis` (public)
- **RPi access:** `ssh stecher` (192.168.1.213:10115)
- **RPi app URL:** `https://nechvatal.duckdns.org:10443`
- **Update RPi:** `ssh stecher 'cd ~/stecher_tennis && docker compose pull && docker compose up -d'`
- **Build + push images:** `export GHCR_TOKEN=... && ./build-and-push.sh`
- **FritzBox port mapping:** ext 10443 → int 443, ext 80 → int 80
- **DuckDNS domain:** nechvatal.duckdns.org
- **ACME email:** otto.kuegerl@gmail.com
