# Automated Local DB Backup — Design & Operations

Hourly, transaction-safe, versioned, verified local backups of the SQLite
player database (`tennis_data` volume → `/app/data/tennis.db`).

## Architecture

A dedicated **`backup` sidecar** in `docker-compose.yml`, reusing the app image
(it already ships Python 3.12 + the `sqlite3` stdlib module). It runs
`backup_db.py --loop` and is declared in compose, so TEST (nechvatal) and PROD
(tc-breakpoint) stay identical and reboot-safe (`restart: unless-stopped`).

- Mounts `tennis_data:/app/data` **read-write** — SQLite WAL needs to write the
  `-shm` shared-memory index to read a live DB from a second process; the backup
  itself only *reads*. This is normal multi-process WAL, identical to how the app
  opens additional connections. It never holds a long write lock.
- Mounts `./backups` (host dir) **outside** the live data volume, so backups
  survive `docker volume rm` / volume corruption (DR isolation).
- Hardened identically to app/caddy: `read_only`, `cap_drop: ALL`,
  `no-new-privileges`, tmpfs `/tmp` for the staging file.

## Backup procedure (per run)

1. **Snapshot** via the SQLite Online Backup API (`Connection.backup`) — the same
   primitive as `app.py:export_database`. Consistent, non-blocking, never `cp`.
2. **Verify the copy**: `PRAGMA integrity_check` = ok, `PRAGMA foreign_key_check`
   empty, `players` ≥ 1, `completed_challenges_view` selectable, size ≥ 20 KB.
3. **Checksum** SHA-256 → written to a `.sha256` sidecar.
4. **Publish atomically** (`shutil.move` rename) + `fsync` the directory.
5. **Promote** into tiers and **prune** to retention limits.

A failure at any step aborts the publish, records the failure, and fires the
alert hook — a partial file is never visible under its final name.

## Naming, versioning, retention

- Filename: `tennis-YYYYMMDDTHHMMSSZ.db` (UTC, sortable, unique) + `.sha256`.
- Tiers (env-tunable):

  | Dir | Keep | Window | Promotion |
  |---|---|---|---|
  | `backups/hourly/` | 48 | 2 days | every run |
  | `backups/daily/`  | 30 | 30 days | first success each UTC day |
  | `backups/weekly/` | 12 | ~3 months | first success each Monday |

## Integrity, logging, monitoring

- Per-run line → container stdout (Docker json-file) **and** `backups/backup.log`.
- `backups/status.json` heartbeat: `last_success_utc`, `last_result`,
  `consecutive_failures`, `last_restore_test_date`.
- Docker `healthcheck` runs `backup_db.py --healthcheck` → container goes
  **unhealthy** if no success within 75 min (`BACKUP_STALE_SECONDS`).
- Alerting: `BACKUP_ALERT_CMD` (shell command, message on stdin) runs on failure.
  Currently **unset** — detection is log + healthcheck. Wire to Telegram/email later.

## Automatic restore test

Once per UTC day after a successful backup, `--restore-test` takes the newest
hourly backup, **verifies its SHA-256**, restores it into a throwaway `/tmp` DB,
and re-runs integrity/FK/row checks. Proves *recoverability*, not just existence.
Result logged as `restore-test PASS/FAIL`; FAIL fires the alert hook.

## Configuration (env)

| Var | Default | Meaning |
|---|---|---|
| `DB_PATH` | `/app/data/tennis.db` | source DB |
| `BACKUP_DIR` | `/backups` | output root |
| `BACKUP_HOURLY_KEEP` | 48 | hourly retention |
| `BACKUP_DAILY_KEEP` | 30 | daily retention |
| `BACKUP_WEEKLY_KEEP` | 12 | weekly retention |
| `BACKUP_MIN_BYTES` | 20480 | truncation floor |
| `BACKUP_STALE_SECONDS` | 4500 | healthcheck staleness threshold |
| `BACKUP_ALERT_CMD` | (empty) | failure alert hook |

## Per-box setup

```bash
cd ~/stecher_tennis
git pull
mkdir -p backups && sudo chown 1000:1000 backups   # appuser (uid 1000) writes here
docker compose up -d                                # creates the backup sidecar
docker compose ps                                   # backup -> Up (healthy)
docker compose logs --tail=20 backup                # "backup ok: tennis-...db"
ls -R backups                                        # hourly/ daily/ + status.json
```

## Manual full-restore drill (recommended quarterly)

1. Pick a backup: `ls -lt backups/daily`.
2. Verify checksum: `sha256sum -c backups/daily/tennis-<ts>.db.sha256`.
3. Restore via the superadmin web import (`/api/settings/db/import`, the
   app-owned safe path) **or** stop the app and replace the volume copy.
4. Confirm the ranking renders and counts match.

## Off-box replication (PROD → TEST)

Local backups alone don't survive host/SSD death, so PROD mirrors its
`backups/` to the TEST box (nechvatal, .213) over the LAN.

- **Transport:** host-level `rsync -a --delete` via `sync_backups_offsite.sh`
  (generic; config from env). Runs on the host, not in a container, because the
  backups live on the host filesystem.
- **Auth:** a dedicated `~/.ssh/offsite_backup` ed25519 key on PROD, authorized
  on TEST with `command="rrsync -wo …",restrict,from="192.168.1.180"` — it can
  **only** rsync-write into `~/offsite-backups/from-tc-breakpoint/`, only from
  PROD's IP, no shell/forwarding. Verified: arbitrary commands are rejected.
- **Schedule:** systemd timer `tennis-backup-sync.timer` on PROD, hourly at
  `:10` (after the top-of-hour backup), `Persistent=true` (catches up after
  downtime). Service runs as `User=stecher`.
- **Observability:** `backups/sync.log` + `backups/sync_status.json` on PROD;
  `journalctl -u tennis-backup-sync` for run history.
- **Mirror semantics:** `--delete` keeps TEST an exact, bounded replica of
  PROD's retention set. A dead/unreadable source can't run the sync, so real
  disk-death does not propagate an empty mirror.

Manual run / check:
```bash
# on PROD
sudo systemctl start tennis-backup-sync.service     # run now
systemctl list-timers tennis-backup-sync.timer      # next fire
cat ~/stecher_tennis/backups/sync_status.json
# on TEST
ls -R ~/offsite-backups/from-tc-breakpoint
```

## Notes / future

- Supersedes the legacy `backup_tennis_db.sh` (targeted the abandoned native
  install path and host `sqlite3`/`zip` — wrong for the Docker deployment).
- **Further DR (optional):** a third copy off-LAN (cloud bucket via `rclone`,
  or pull to the workstation), and the symmetric TEST → PROD direction if TEST
  data ever needs the same protection.
