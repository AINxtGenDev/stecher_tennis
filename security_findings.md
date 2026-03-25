# Code Review Summary — `docker` branch

**Date:** 2026-03-23
**Updated:** 2026-03-25 (verified all critical fixes)
**Scope:** Full `docker` branch diff vs `main` (Docker infra, app.py, templates, tests)

---

## 🔴 Critical (Must Fix) — ALL FIXED ✅

### 1. ~~DB export streams live WAL-mode file, risking corruption~~ ✅ Fixed
- **File:** `app.py` — `export_database()`
- **Fix applied:** Uses `conn.backup(dst_conn)` to produce a consistent snapshot to a temp file (`app.py:2545`)

### 2. ~~DB import replaces file while other connections may be open~~ ✅ Fixed
- **File:** `app.py` — `import_database()`
- **Fix applied:** Added `PRAGMA wal_checkpoint(TRUNCATE)` before overwrite, `_db_import_lock` for serialization, stale WAL/SHM cleanup (`app.py:2602`)

### 3. ~~No upload size limit on DB import~~ ✅ Fixed
- **File:** `app.py`
- **Fix applied:** `app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024` (50 MB) (`app.py:131`)

### 4. ~~Stored XSS via unescaped player names in JavaScript~~ ✅ Fixed
- **Files:** `index.html`, `db_settings.html`
- **Fix applied:** Added `escapeHtml()` helper in both templates, wrapped all user-supplied text in JS template literals (13+ call sites)

### 5. ~~No security headers in Caddyfile~~ ✅ Fixed
- **File:** `Caddyfile`
- **Fix applied:** Added HSTS, X-Frame-Options DENY, X-Content-Type-Options nosniff, Referrer-Policy, Permissions-Policy (`Caddyfile:18-24`)

### 6. ~~HTTPS port mismatch between docker-compose.yml and .env.example~~ ✅ Fixed
- **Files:** `docker-compose.yml:17`
- **Fix applied:** Changed to `"${HTTPS_PORT:-443}:443"` for parameterized port mapping

---

## 🟡 Suggestions (Should Consider)

### 7. ~~No schema validation on imported database~~ ✅ Fixed
- **File:** `app.py` — `import_database()`
- **Fix applied:** Added schema validation after integrity check — verifies required columns in both `players` and `challenges` tables (`app.py:2593-2598`)

### 8. No container hardening in docker-compose.yml
- **File:** `docker-compose.yml`
- **Why:** Missing `security_opt: ["no-new-privileges:true"]`, `mem_limit`, `pids_limit`. Important on resource-constrained RPi.
- **Fix:** Add hardening options to both services.

### 9. Caddy receives all env vars including SECRET_KEY
- **File:** `docker-compose.yml`
- **Why:** `env_file: .env` gives Caddy access to `SECRET_KEY`, `FLASK_DEBUG`, etc. Violates least privilege.
- **Fix:** Use explicit `environment:` entries; Caddy only needs `DUCKDNS_*`, `ACME_*`, `HTTPS_PORT`.

### 10. ~~No log rotation configured~~ ✅ Fixed
- **File:** `docker-compose.yml`
- **Fix applied:** Added `logging: { driver: json-file, options: { max-size: "10m", max-file: "3" } }` to both app and caddy services

### 11. ~~Volume removal uses greedy grep in deploy.sh~~ ✅ Fixed
- **File:** `deploy.sh:176`
- **Fix applied:** Replaced greedy `grep caddy_data` with exact volume name `stecher_tennis_caddy_data`

### 12. ~~CDN resources without SRI hashes~~ ✅ Fixed
- **Files:** All templates (`index.html`, `admin.html`, `db_settings.html`)
- **Fix applied:** Added `integrity` (SHA-512) and `crossorigin="anonymous"` attributes to all CDN resources (Bootstrap CSS/JS, jQuery, Socket.IO)

### 13. Entrypoint doesn't validate critical env vars
- **File:** `entrypoint.sh`
- **Why:** App starts silently with default `SECRET_KEY` placeholder in production.
- **Fix:** Check `SECRET_KEY` is set and not the placeholder; refuse to start otherwise.

### 14. Inconsistent nav bar privilege guard
- **Files:** `index.html`, `admin.html`, `db_settings.html`
- **Why:** Admin link shown to all users in some templates, gated by `{% if current_user.privilege_level in ['admin', 'superadmin'] %}` in others.
- **Fix:** Apply consistent privilege check across all templates.

---

## 🟢 Nits (Optional)

### 15. ~~Email mismatch in footer~~ ✅ Fixed
- **File:** `index.html:420`
- **Fix applied:** Changed `mailto:` href from `hpe.com` to `gmx.at` to match visible text

### 16. ~~Caddy log level set to ERROR only~~ ✅ Fixed
- **File:** `Caddyfile:15`
- **Fix applied:** Changed log level from `ERROR` to `WARN` to catch TLS renewal warnings

### 17. ~~Version regex only captures 2 components~~ ✅ Fixed
- **File:** `build-and-push.sh:22`
- **Fix applied:** Regex now captures optional third component: `[0-9]+\.[0-9]+(\.[0-9]+)?`

### 18. `0.20rem` font-size on mobile pyramid
- **File:** `index.html:146,217`
- **Detail:** ~3.2px, effectively unreadable. Consider hiding names and using tap tooltips.

### 19. ~~New buttons use inline styles instead of CSS variables~~ ✅ Fixed
- **File:** `db_settings.html`
- **Fix applied:** Added `--action-color` CSS variable, `.btn-action` and `.action-border` classes; replaced all inline `#0d6efd` styles

### 20. Health test tests 405, not CSRF exemption
- **File:** `tests/test_health.py`
- **Detail:** `POST /health` returns 405 (method not allowed), not a CSRF rejection. Test passes but doesn't test what it claims.

---

## ✅ What's Good

- **Multi-stage Dockerfile** — build tools stay in builder stage, runtime image is clean and small
- **Non-root container user** (`appuser` UID 1000) correctly configured
- **`exec` in entrypoint.sh** — PID 1 signal handling done right
- **App port not exposed to host** — all traffic forced through Caddy
- **`depends_on: condition: service_healthy`** — Caddy waits for Flask readiness
- **CSRF protection thorough** — all forms include tokens, `$.ajaxSetup` attaches headers globally
- **Jinja2 auto-escaping** used correctly for all server-rendered content (XSS issue is JS-side only)
- **Multi-arch builds** (amd64+arm64) correctly target both dev and RPi
- **Health endpoint** correctly CSRF-exempt and unauthenticated
- **`DB_PATH` env var** with auto-mkdir and fallback is well-designed
- **Idempotent operations** throughout (init_db, buildx, systemd stops)
- **DB import has good defensive patterns** — temp file with `finally` cleanup, integrity check, confirmation dialog
- **Login page** has proper `autocomplete` attributes for password managers
