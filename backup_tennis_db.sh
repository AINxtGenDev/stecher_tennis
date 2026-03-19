#!/bin/bash

# A robust script to back up the SQLite database.
# Best practices:
# - Use `set -euo pipefail` for strict error handling.
# - Use `sqlite3 .backup` for safe, atomic "hot" backups.
# - Use a `trap` to ensure cleanup of temporary files.
# - Use `mktemp` for secure temporary file creation.
# - Check for command dependencies before running.

set -euo pipefail

# Configuration
# NOTE: Ensure this script is run by a user with read/write access to these directories.
SOURCE_DB="${DB_PATH:-/home/stecher/stecher_tennis/tennis.db}"
BACKUP_DIR="/home/stecher/stecher_tennis/backup"
DATETIME=$(date +"%Y%m%d_%H%M")
BACKUP_FILE="${BACKUP_DIR}/backup_tennisdb.${DATETIME}.zip"
LOG_FILE="${BACKUP_DIR}/backup.log"
RETENTION_HOURS=168  # Number of hours to keep backups (7 days = 168 hours)
TMP_DIR="/home/stecher/tmp" # User-owned temporary directory

# This temporary file will be created by mktemp and cleaned up by the trap.
TMP_DB=""

# This trap ensures the temporary file is removed even if the script fails.
cleanup() {
    rm -f "${TMP_DB:-}"
}
trap cleanup EXIT

# Function for logging
log() {
    echo "$(date +'%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
    echo "$1"
}

# Create directories if they don't exist
for DIR in "$BACKUP_DIR" "$TMP_DIR"; do
    if [ ! -d "$DIR" ]; then
        mkdir -p "$DIR"
        if [ $? -ne 0 ]; then
            log "ERROR: Failed to create directory at $DIR"
            exit 1
        fi
        log "Created directory at $DIR"
    fi
done

# --- Pre-flight Checks ---

# Check for required commands
if ! command -v sqlite3 &>/dev/null; then
    log "ERROR: sqlite3 command not found. Please install it."
    exit 1
fi
if ! command -v zip &>/dev/null; then
    log "ERROR: zip command not found. Please install it."
    exit 1
fi

# Check if source database exists
if [ ! -f "$SOURCE_DB" ]; then
    log "ERROR: Source database not found at $SOURCE_DB"
    exit 1
fi
log "Starting backup of $SOURCE_DB"

# --- Main Backup Logic ---

# 1. Create a secure, unique temporary file for the backup.
TMP_DB=$(mktemp "${TMP_DIR}/tennis_db_backup.XXXXXXXXXX.db")
log "Created temporary file: $TMP_DB"

# 2. Use sqlite3's .backup command for a safe, atomic "hot" backup.
# This is the recommended way to back up a live SQLite database (especially with WAL mode).
# The script will exit automatically on failure because of 'set -e'.
log "Performing atomic backup to temporary file..."
sqlite3 "$SOURCE_DB" ".backup '$TMP_DB'"
log "Atomic backup successful."

# 3. Zip the consistent backup file with high compression.
log "Zipping the backup file to $BACKUP_FILE"
zip -9 -j "$BACKUP_FILE" "$TMP_DB"

# 4. Verify backup file was created and log its size.
BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
BACKUP_SIZE_BYTES=$(stat -f%z "$BACKUP_FILE" 2>/dev/null || stat -c%s "$BACKUP_FILE" 2>/dev/null)

if [ "$BACKUP_SIZE_BYTES" -lt 1024 ]; then
    log "WARNING: Backup file is very small ($BACKUP_SIZE), this might indicate the source DB is empty."
fi
log "SUCCESS: Backup completed successfully at $BACKUP_FILE (Size: $BACKUP_SIZE)"

# --- Cleanup of Old Backups ---
# Convert retention hours to minutes for more precise cleanup
RETENTION_MINUTES=$((RETENTION_HOURS * 60))

# Find and delete old backup files
DELETED_COUNT=$(find "$BACKUP_DIR" -name "backup_tennisdb.*.zip" -type f -mmin +$RETENTION_MINUTES -delete -print 2>/dev/null | wc -l)

if [ "$DELETED_COUNT" -gt 0 ]; then
    log "Cleaned up $DELETED_COUNT old backup file(s)."
else
    log "No old backup files found for cleanup (retention period: $RETENTION_HOURS hours)."
fi

# Optional: Log current backup count
CURRENT_BACKUPS=$(find "$BACKUP_DIR" -name "backup_tennisdb.*.zip" -type f | wc -l)
log "Current number of backup files: $CURRENT_BACKUPS"
