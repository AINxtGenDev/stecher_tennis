#!/bin/bash
# Off-box mirror of the local DB backups to another host via a restricted
# rsync (rrsync) key. Host-specific config comes from the environment (set by
# the systemd unit); the script itself is generic and reproducible.
#
#   OFFSITE_DEST     rsync destination, e.g. "stecher@192.168.1.213:" (rrsync root)
#   OFFSITE_PORT     ssh port (default 22)
#   OFFSITE_KEY      path to the dedicated private key
#   OFFSITE_SRC_DIR  backups dir to mirror (default ~/stecher_tennis/backups)
#
# Mirrors with --delete so the remote is an exact, bounded replica of the
# source's current retention set. (A dead/unreadable source can't run this, so
# real disk-death does not propagate an empty mirror.)
set -uo pipefail

SRC_DIR="${OFFSITE_SRC_DIR:-$HOME/stecher_tennis/backups}"
DEST="${OFFSITE_DEST:?set OFFSITE_DEST=user@host:}"
PORT="${OFFSITE_PORT:-22}"
KEY="${OFFSITE_KEY:?set OFFSITE_KEY=/path/to/private_key}"

LOG="$SRC_DIR/sync.log"
STATUS="$SRC_DIR/sync_status.json"

ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
log() { echo "$(ts) [$1] $2" | tee -a "$LOG"; }

write_status() {  # $1=ok|fail  $2=detail
    printf '{\n  "last_run_utc": "%s",\n  "last_result": "%s",\n  "detail": "%s",\n  "dest": "%s"\n}\n' \
        "$(ts)" "$1" "$2" "$DEST" > "$STATUS.tmp" && mv "$STATUS.tmp" "$STATUS"
}

if [ ! -d "$SRC_DIR" ]; then
    log ERROR "source dir missing: $SRC_DIR"
    write_status fail "source missing"
    exit 1
fi

if rsync -a --delete \
    -e "ssh -i $KEY -p $PORT -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=15 -o StrictHostKeyChecking=accept-new" \
    "$SRC_DIR/" "$DEST"; then
    log INFO "offsite sync ok -> $DEST"
    write_status ok "mirror complete"
else
    rc=$?
    log ERROR "offsite sync FAILED (rsync exit $rc) -> $DEST"
    write_status fail "rsync exit $rc"
    exit "$rc"
fi
