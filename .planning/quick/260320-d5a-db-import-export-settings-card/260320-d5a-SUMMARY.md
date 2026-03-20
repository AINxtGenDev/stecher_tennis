---
phase: quick
plan: 260320-d5a
subsystem: database-management
tags: [superadmin, backup, restore, sqlite, settings-ui]
dependency_graph:
  requires: []
  provides: [db-export-api, db-import-api, db-import-export-card]
  affects: [app.py, templates/db_settings.html]
tech_stack:
  added: []
  patterns: [temp-file-copy-for-sqlite-export, integrity-check-before-import]
key_files:
  created: []
  modified:
    - app.py
    - templates/db_settings.html
decisions:
  - "Used shutil.copy2 for export/import to preserve SQLite WAL integrity"
  - "Close request DB connection before file operations to release WAL locks"
  - "Client-side .db extension check plus server-side PRAGMA integrity_check for double validation"
  - "data_cache.invalidate() after import to clear stale cached data"
metrics:
  duration: 2min
  completed: "2026-03-20T08:33:15Z"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
---

# Quick Task 260320-d5a: Database Import/Export Settings Card Summary

Superadmin database backup download and upload-replace via web UI with SQLite integrity validation

## What Was Done

### Task 1: Backend Export and Import Endpoints
- Added `send_file`, `shutil`, `tempfile` imports to app.py
- **GET /api/settings/db/export**: Copies live SQLite DB to temp file, sends as attachment with timestamped filename (`db_backup_<ISO>.db`), cleans up temp file in finally block
- **POST /api/settings/db/import**: Validates uploaded .db file via `PRAGMA integrity_check`, overwrites live database, invalidates data cache, emits `database_reset` socket event
- Both endpoints protected by `@superadmin_required` decorator
- All error paths return structured JSON with German error messages
- **Commit:** `b401a40`

### Task 2: Import/Export Card in db_settings.html
- New "Datenbank Import / Export" card inserted above existing "Herausforderungen" card
- Export button uses hidden anchor link technique for no-reload download
- Import section: file input (accept=".db"), disabled import button until valid file selected
- Client-side validation shows inline error for non-.db files
- Confirmation dialog before import: "Die bestehende Datenbank wird ueberschrieben"
- Inline error/success message divs with proper CSS variable colors
- Page auto-reloads 2 seconds after successful import
- Card uses matching blue border accent (`border-color: #0d6efd`)
- **Commit:** `75ede20`

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

- Both routes registered: `/api/settings/db/export` (GET) and `/api/settings/db/import` (POST)
- Both decorated with `@superadmin_required`
- Template contains all required UI elements: card heading, export button, file input, import button, error/success divs
- JavaScript handlers for export (hidden link click), import file validation, and import AJAX POST all present

## Self-Check: PASSED

- [x] app.py modified with both endpoints (lines 2562, 2608)
- [x] templates/db_settings.html modified with new card and JS
- [x] Commit b401a40 exists
- [x] Commit 75ede20 exists
