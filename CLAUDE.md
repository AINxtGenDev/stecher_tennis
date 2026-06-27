# CLAUDE.md

Guidance for Claude Code (claude.ai/code) when working in this repository.

## Project Overview

German-language tennis ranking web app for a club. Players view their ranking in
a pyramid, challenge higher-ranked players, and submitted results re-rank
automatically. Current version is in `APP_VERSION` (`app.py`).

## Tech Stack

- **Backend**: Flask + Flask-SocketIO (eventlet async) + Flask-Login + Flask-WTF
- **Database**: SQLite 3 (WAL mode, foreign keys enabled)
- **Frontend**: Jinja2 templates, Bootstrap 5, jQuery, Socket.IO client
- **Auth**: bcrypt password hashing, three privilege levels (player/admin/superadmin)
- **Deploy**: Docker Compose (app + Caddy) on Raspberry Pi; Caddy does HTTPS via DuckDNS DNS-01 ACME

## Commands

```bash
python app.py                 # dev server, binds FLASK_HOST:FLASK_PORT (default 0.0.0.0:5000); auto-inits DB
pytest                        # tests
black app.py && flake8 app.py # format + lint
./check_db.sh                 # integrity_check + foreign_key_check + stats on local tennis.db

# Local Docker stack (prod parity)
docker compose up -d                 # app + caddy + backup sidecar; gunicorn binds :5000 internally
docker compose logs -f app|backup    # logs
python backup_db.py                  # one-shot manual DB backup (the running sidecar does this hourly)
```

Note: `backup_tennis_db.sh` is **dead** (targets the abandoned native-install path); the live
backup is the Docker `backup` sidecar running `backup_db.py` — see Deployment.

## Architecture

The entire backend is a single `app.py` (~2,785 lines): routes, business logic, DB
access, WebSocket handlers, and helpers — no module separation. Line numbers below
are approximate; **grep the symbol** (they're the durable anchors).

### Navigation (`app.py`)

- **Setup/config** (top): `SECRET_KEY` enforcement, `DB_PATH` resolution (Docker vs local), CSRF/CORS, `eventlet.monkey_patch()`, `APP_VERSION`
- **`init_db()`** — schema init + index creation, idempotent (safe to re-run; never reseeds an existing DB)
- **`serialize_player()`** — player/challenge rows → JSON (authenticated path; includes credentials fields)
- **`get_realtime_data_cached()`** — 10s TTL thread-safe cache; one DB read per window
- **`emit_data_update()`** — Socket.IO delta broadcasts to the `tennis_updates` room
- **`create_pyramid()`** — pyramid layout algorithm
- **`resolve_expired_challenges()`** — 10-day auto-resolve, fired by a throttled `@app.before_request` hook (≤1×/min)
- **Auth routes**: `/` `/login` `/logout`
- **Views**: `/index` `/admin` `/db_settings`; **`/rangliste`** = public, unauthenticated, read-only (uses a strict field whitelist — never leaks username/hash/privilege)
- **Data API**: `/api/realtime_data` `/get_players` `/eligible_opponents` `/api/public/ranking`
- **Actions**: `/challenge` `/newplayer_challenge` `/toggle_availability` `/update_scheduled_date` `/submit_result`
- **Admin**: `/add_player` `/update_player` `/delete_player` `/set_player_block_status`
- **Superadmin**: `/change_password` `/reset_completed_challenges_display` `/api/settings/db/{export,import}` `/reset_database`
- **WebSocket**: handlers near end of file (grep `@socketio.on`)

### Database

Schema in `schema.sql`. Initial data from `initial_players.json` on reset.
- **players**: rank, availability, blocking status, credentials
- **challenges**: challenger/opponent, deadline (10 days), result, scheduled date
- **completed_challenges_view**: VIEW joining challenges with player names

DB import/export and backups use the **SQLite Online Backup API** (`conn.backup`),
never a file copy — required for safe hot backups of the WAL-mode DB.

### Challenge business rules

- Ranks 1-10: can challenge any higher-ranked player
- Ranks 11+: limited by rank distance (typically within 5 ranks)
- 7-day post-match block between the same opponents
- Unavailable players cannot be challenged
- New (unranked) players enter by challenging someone in ranks 11-44
- Winner is **recomputed server-side** from set scores in `/submit_result` (WR-07) — a claimed
  result that contradicts the scores is rejected before any DB write

## Environment Configuration (`.env`)

- `SECRET_KEY` — session encryption (**required**; app refuses to start without it)
- `DB_PATH` — DB location (Docker sets `/app/data/tennis.db`; unset → project root `tennis.db`)
- `CORS_ALLOWED_ORIGINS` — comma-separated trusted origins
- `FLASK_DEBUG` — debug mode (false in prod)
- `FLASK_HOST` / `FLASK_PORT` — bind for `python app.py` only (default 0.0.0.0:5000); Docker always binds :5000
- `TEST_DATE` — override system time for testing (`YYYY-MM-DD-HH-MM-SS`)
- HTTPS/Caddy: `DUCKDNS_DOMAIN` `DUCKDNS_TOKEN` `ACME_EMAIL` `ACME_CA` `HTTPS_PORT`

## Guardrails

- Never commit or sync credential handout files `spieler*.txt` (e.g. `spieler_admins.txt`) —
  they hold real player/admin logins. They are git-ignored (`.gitignore`); keep it that way.
  Same for `.env` and local `*.db` backups.

## Deployment

Production runs as a **Docker Compose stack**, NOT a systemd/native service (the
`99_rpi.txt` systemd flow is legacy). Three hardened containers (`read_only`,
`cap_drop: ALL`, `no-new-privileges`):
- **app** — Flask/gunicorn/eventlet (single worker), DB in the `tennis_data` volume
- **caddy** — HTTPS via DuckDNS DNS-01 ACME
- **backup** — hourly transaction-safe DB backup (`backup_db.py --loop`): verify + SHA-256 +
  tiered hourly/daily/weekly retention + daily restore test; backups on a host bind-mount
  (`backups/`) outside the volume

There are **two Raspberry Pi boxes — TEST and PROD** (live club). They share the
same OS hostname, so **disambiguate by domain/port, never hostname**. Box
identity/access, the off-box PROD→TEST backup replication, and current ops state
live in `SESSION_CHECKPOINT.md`. Full setup: `README.md`; backup design:
`documentation/db-backup-plan.md`.

Deploy: image change → `docker compose pull && up -d`; compose/script-only change →
`git pull && docker compose up -d`. The DB volume persists across recreation.
