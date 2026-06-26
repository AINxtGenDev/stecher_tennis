#!/usr/bin/env python3
"""Transaction-safe local backup of the tennis SQLite database.

Uses the SQLite Online Backup API (the same mechanism as the app's
export_database) so the running application is never blocked and no torn /
inconsistent state is ever captured. Every backup is verified
(integrity_check + foreign_key_check + row sanity), checksummed (SHA-256),
and atomically published into a tiered hourly/daily/weekly retention layout.

Stdlib only. Runs inside the `backup` compose sidecar (same app image).

Modes:
  (default)        one-shot backup, exit 0 on success / 1 on failure
  --loop           immediate backup, then hourly forever; daily restore test
  --restore-test   restore newest backup into a throwaway DB and validate it
  --healthcheck    exit 0 if last success is recent, else 1 (Docker healthcheck)
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

DB_PATH = os.environ.get("DB_PATH", "/app/data/tennis.db")
BACKUP_DIR = os.environ.get("BACKUP_DIR", "/backups")
HOURLY_KEEP = int(os.environ.get("BACKUP_HOURLY_KEEP", "48"))
DAILY_KEEP = int(os.environ.get("BACKUP_DAILY_KEEP", "30"))
WEEKLY_KEEP = int(os.environ.get("BACKUP_WEEKLY_KEEP", "12"))
MIN_BYTES = int(os.environ.get("BACKUP_MIN_BYTES", "20480"))  # 20 KB truncation floor
STALE_SECONDS = int(os.environ.get("BACKUP_STALE_SECONDS", "4500"))  # 75 min
# Pluggable alert hook: a shell command; the message is passed on stdin.
# Left empty by default (log + Docker healthcheck cover detection for now).
ALERT_CMD = os.environ.get("BACKUP_ALERT_CMD", "")

HOURLY_DIR = os.path.join(BACKUP_DIR, "hourly")
DAILY_DIR = os.path.join(BACKUP_DIR, "daily")
WEEKLY_DIR = os.path.join(BACKUP_DIR, "weekly")
STATUS_FILE = os.path.join(BACKUP_DIR, "status.json")
LOG_FILE = os.path.join(BACKUP_DIR, "backup.log")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def log(level: str, msg: str) -> None:
    line = f"{now_utc().isoformat()} [{level}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def alert(msg: str) -> None:
    log("ALERT", msg)
    if not ALERT_CMD:
        return
    try:
        subprocess.run(ALERT_CMD, shell=True, input=msg.encode(),
                       timeout=30, check=False)
    except Exception as exc:  # alerting must never crash the backup loop
        log("ERROR", f"alert hook failed: {exc}")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_db(path: str) -> tuple[bool, str]:
    """Validate a backup copy: integrity, FK, and minimal schema/row sanity."""
    conn = sqlite3.connect(path)
    try:
        if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            return False, "integrity_check failed"
        if conn.execute("PRAGMA foreign_key_check").fetchall():
            return False, "foreign_key_check failed"
        players = conn.execute("SELECT COUNT(*) FROM players").fetchone()[0]
        if players < 1:
            return False, "players table empty"
        # view must be present and selectable (catches structural breakage)
        conn.execute("SELECT COUNT(*) FROM completed_challenges_view").fetchone()
        challenges = conn.execute("SELECT COUNT(*) FROM challenges").fetchone()[0]
        return True, f"{players} players, {challenges} challenges"
    finally:
        conn.close()


def _fsync_dir(path: str) -> None:
    try:
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        pass


def prune(directory: str, keep: int) -> None:
    files = sorted(glob.glob(os.path.join(directory, "tennis-*.db")))
    for old in files[:-keep] if keep > 0 else files:
        for p in (old, old + ".sha256"):
            try:
                os.remove(p)
            except OSError:
                pass


def promote(src_db: str, ts: datetime) -> None:
    """Copy the just-made backup into daily/ (1st of day) and weekly/ (Mondays)."""
    day = ts.strftime("%Y%m%d")
    if not glob.glob(os.path.join(DAILY_DIR, f"tennis-{day}*.db")):
        _copy_pair(src_db, DAILY_DIR)
    if ts.weekday() == 0 and not glob.glob(
            os.path.join(WEEKLY_DIR, f"tennis-{day}*.db")):
        _copy_pair(src_db, WEEKLY_DIR)


def _copy_pair(src_db: str, dest_dir: str) -> None:
    os.makedirs(dest_dir, exist_ok=True)
    shutil.copy2(src_db, os.path.join(dest_dir, os.path.basename(src_db)))
    sidecar = src_db + ".sha256"
    if os.path.exists(sidecar):
        shutil.copy2(sidecar, os.path.join(dest_dir, os.path.basename(sidecar)))


def write_status(ok: bool, detail: str, extra: dict | None = None) -> None:
    prev: dict = {}
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE) as fh:
                prev = json.load(fh)
        except (OSError, ValueError):
            prev = {}
    ts = now_utc().isoformat()
    status = {
        "last_run_utc": ts,
        "last_result": "ok" if ok else "fail",
        "detail": detail,
        "consecutive_failures": 0 if ok else prev.get("consecutive_failures", 0) + 1,
        "last_success_utc": ts if ok else prev.get("last_success_utc"),
        "last_restore_test_date": prev.get("last_restore_test_date"),
    }
    if extra:
        status.update(extra)
    tmp = STATUS_FILE + ".tmp"
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        with open(tmp, "w") as fh:
            json.dump(status, fh, indent=2)
        os.replace(tmp, STATUS_FILE)
    except OSError as exc:
        log("ERROR", f"status write failed: {exc}")


def backup_once() -> bool:
    if not os.path.exists(DB_PATH):
        write_status(False, "source missing")
        alert(f"backup FAILED: source DB missing at {DB_PATH}")
        return False

    os.makedirs(HOURLY_DIR, exist_ok=True)
    ts = now_utc()
    name = f"tennis-{ts.strftime('%Y%m%dT%H%M%SZ')}.db"
    fd, tmp = tempfile.mkstemp(suffix=".db", dir="/tmp")
    os.close(fd)
    started = time.monotonic()
    try:
        # Online Backup API — consistent snapshot, never blocks the writer.
        src = sqlite3.connect(DB_PATH, timeout=30)
        dst = sqlite3.connect(tmp)
        try:
            with dst:
                src.backup(dst)
        finally:
            dst.close()
            src.close()

        ok, detail = verify_db(tmp)
        if not ok:
            write_status(False, detail)
            alert(f"backup FAILED verification: {detail}")
            return False
        size = os.path.getsize(tmp)
        if size < MIN_BYTES:
            write_status(False, f"too small ({size} B)")
            alert(f"backup FAILED: file too small ({size} bytes)")
            return False

        digest = sha256_file(tmp)
        final = os.path.join(HOURLY_DIR, name)
        shutil.move(tmp, final)  # atomic rename within the same filesystem
        with open(final + ".sha256", "w") as fh:
            fh.write(f"{digest}  {name}\n")
        _fsync_dir(HOURLY_DIR)

        promote(final, ts)
        prune(HOURLY_DIR, HOURLY_KEEP)
        prune(DAILY_DIR, DAILY_KEEP)
        prune(WEEKLY_DIR, WEEKLY_KEEP)

        dur = time.monotonic() - started
        write_status(True, f"{detail}, {size} B, sha256 {digest[:12]}")
        log("INFO", f"backup ok: {name} ({size} B, sha256 {digest[:12]}, "
                    f"{dur:.2f}s) — {detail}")
        return True
    except Exception as exc:
        write_status(False, str(exc))
        alert(f"backup FAILED with exception: {exc}")
        log("ERROR", f"backup exception: {exc}")
        return False
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def restore_test() -> bool:
    """Prove recoverability: restore newest hourly backup and validate it."""
    candidates = sorted(glob.glob(os.path.join(HOURLY_DIR, "tennis-*.db")))
    if not candidates:
        log("ERROR", "restore-test: no backups found")
        return False
    newest = candidates[-1]

    sidecar = newest + ".sha256"
    if os.path.exists(sidecar):
        with open(sidecar) as fh:
            recorded = fh.read().split()[0]
        if sha256_file(newest) != recorded:
            alert(f"restore-test FAILED: checksum mismatch on {os.path.basename(newest)}")
            return False

    fd, tmp = tempfile.mkstemp(suffix=".db", dir="/tmp")
    os.close(fd)
    try:
        shutil.copy2(newest, tmp)
        ok, detail = verify_db(tmp)
        if not ok:
            alert(f"restore-test FAILED: {detail} ({os.path.basename(newest)})")
            return False
        log("INFO", f"restore-test PASS: {os.path.basename(newest)} — {detail}")
        return True
    except Exception as exc:
        alert(f"restore-test FAILED with exception: {exc}")
        return False
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def healthcheck() -> int:
    try:
        with open(STATUS_FILE) as fh:
            status = json.load(fh)
        last = status.get("last_success_utc")
        if not last:
            return 1
        age = (now_utc() - datetime.fromisoformat(last)).total_seconds()
        return 0 if age <= STALE_SECONDS else 1
    except (OSError, ValueError):
        return 1


def seconds_to_next_hour() -> float:
    now = now_utc()
    secs_into_hour = now.minute * 60 + now.second + now.microsecond / 1e6
    return max(1.0, 3600.0 - secs_into_hour)


def loop() -> None:
    log("INFO", f"backup loop started — DB={DB_PATH} DIR={BACKUP_DIR} "
                f"keep h/d/w={HOURLY_KEEP}/{DAILY_KEEP}/{WEEKLY_KEEP}")
    while True:
        ok = backup_once()
        # One restore test per UTC day, after a successful backup.
        if ok:
            today = now_utc().strftime("%Y%m%d")
            try:
                with open(STATUS_FILE) as fh:
                    last_test = json.load(fh).get("last_restore_test_date")
            except (OSError, ValueError):
                last_test = None
            if last_test != today:
                if restore_test():
                    write_status(True, "restore-test ok",
                                 {"last_restore_test_date": today})
        time.sleep(seconds_to_next_hour())


def main() -> int:
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "--healthcheck":
        return healthcheck()
    if arg == "--restore-test":
        return 0 if restore_test() else 1
    if arg == "--loop":
        loop()
        return 0
    return 0 if backup_once() else 1


if __name__ == "__main__":
    sys.exit(main())
