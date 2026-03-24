---
phase: quick
plan: 260324-ay8
subsystem: security
tags: [security, xss, db-safety, headers, docker]
dependency_graph:
  requires: []
  provides: [safe-db-export, safe-db-import, upload-limit, xss-protection, security-headers, parameterized-https-port]
  affects: [app.py, templates/index.html, templates/db_settings.html, Caddyfile, docker-compose.yml]
tech_stack:
  added: []
  patterns: [sqlite3-backup-api, escapeHtml-helper, after_this_request-cleanup]
key_files:
  created: []
  modified: [app.py, templates/index.html, templates/db_settings.html, Caddyfile, docker-compose.yml]
decisions:
  - Used sqlite3 backup() API for export snapshots instead of file copy
  - Used .text() instead of .html() for showAlert to prevent XSS
  - Did not add CSP header (app uses inline scripts and CDN resources)
metrics:
  duration: 219s
  completed: 2026-03-24T06:59:54Z
  tasks_completed: 3
  tasks_total: 3
---

# Quick Task 260324-ay8: Fix All 6 Critical Security Findings Summary

Safe DB export via sqlite3 backup API, WAL-checkpointed import with lock, 50MB upload cap, escapeHtml on all user text in JS templates, Caddy security headers, parameterized HTTPS port.

## Tasks Completed

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | Fix DB export, import, and upload size limit | 006a5c0 | app.py |
| 2 | Fix stored XSS in JS template literals | 45313bd | templates/index.html, templates/db_settings.html |
| 3 | Add Caddy security headers and fix docker-compose port | 5113122 | Caddyfile, docker-compose.yml |

## Findings Addressed

1. **DB export corruption** - Replaced `send_file(db_path)` with `sqlite3.backup()` to temp file + `after_this_request` cleanup
2. **DB import race condition** - Added `_db_import_lock`, WAL checkpoint (TRUNCATE), and stale WAL/SHM removal before overwrite
3. **Missing upload size limit** - `MAX_CONTENT_LENGTH = 50MB`
4. **Stored XSS via player names** - Added `escapeHtml()` helper, wrapped all user-supplied text (names, scores, reasons) in both templates, changed `showAlert` from `.html()` to `.text()`
5. **Missing security headers** - Added HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy to Caddyfile
6. **HTTPS port mismatch** - Changed `"443:443"` to `"${HTTPS_PORT:-443}:443"` in docker-compose.yml

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None.
