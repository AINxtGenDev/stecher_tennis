#!/bin/bash

# Tennis Database Backup Script (No privileged operations)
# Purpose: Creates a 3-hourly backup of the tennis database with date-time stamped filename
# Runs every 3 hours via crontab

# Configuration
SOURCE_DB="/home/stecher/stecher_tennis/tennis.db"
BACKUP_DIR="/home/stecher/stecher_tennis/backup"
DATETIME=$(date +"%Y%m%d_%H%M")
BACKUP_FILE="${BACKUP_DIR}/backup_tennisdb.${DATETIME}.zip"
LOG_FILE="${BACKUP_DIR}/backup.log"
RETENTION_HOURS=168  # Number of hours to keep backups (7 days = 168 hours)
TMP_DIR="/home/stecher/tmp"  # User-owned temporary directory

# Function for logging
log() {
    echo "$(date +'%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
    echo "$(date +'%Y-%m-%d %H:%M:%S') - $1"
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

# Check if source database exists
if [ ! -f "$SOURCE_DB" ]; then
    log "ERROR: Source database not found at $SOURCE_DB"
    exit 1
fi

# Check if database is accessible (not locked)
if ! sqlite3 "$SOURCE_DB" "SELECT 1;" >/dev/null 2>&1; then
    log "WARNING: Database appears to be locked or inaccessible, attempting backup anyway"
fi

# Create backup
log "Starting 3-hourly backup of $SOURCE_DB"

# Create a temporary copy to avoid backing up a file that might be changing
TMP_DB="${TMP_DIR}/tennis_db_backup_${DATETIME}.db"
cp "$SOURCE_DB" "$TMP_DB"
if [ $? -ne 0 ]; then
    log "ERROR: Failed to create temporary copy of database"
    exit 1
fi

# Verify the temporary copy is a valid SQLite database
if ! sqlite3 "$TMP_DB" "SELECT count(*) FROM sqlite_master;" >/dev/null 2>&1; then
    log "ERROR: Temporary database copy appears to be corrupted"
    rm "$TMP_DB"
    exit 1
fi

# Zip the backup file with compression
zip -9 -j "$BACKUP_FILE" "$TMP_DB"
ZIP_STATUS=$?
rm "$TMP_DB"  # Clean up temp file regardless of zip success

if [ $ZIP_STATUS -ne 0 ]; then
    log "ERROR: Failed to create zip backup at $BACKUP_FILE"
    exit 1
fi

# Verify backup file was created successfully and has reasonable size
if [ -f "$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    BACKUP_SIZE_BYTES=$(stat -f%z "$BACKUP_FILE" 2>/dev/null || stat -c%s "$BACKUP_FILE" 2>/dev/null)
    
    # Check if backup is suspiciously small (less than 1KB might indicate an issue)
    if [ "$BACKUP_SIZE_BYTES" -lt 1024 ]; then
        log "WARNING: Backup file is very small ($BACKUP_SIZE), this might indicate an issue"
    fi
    
    log "SUCCESS: 3-hourly backup completed successfully at $BACKUP_FILE (Size: $BACKUP_SIZE)"
else
    log "ERROR: Backup file not found after backup process"
    exit 1
fi

# Keep only backups within the retention period
# Convert retention hours to minutes for more precise cleanup
RETENTION_MINUTES=$((RETENTION_HOURS * 60))

# Find and delete old backup files
DELETED_COUNT=$(find "$BACKUP_DIR" -name "backup_tennisdb.*.zip" -type f -mmin +$RETENTION_MINUTES -delete -print 2>/dev/null | wc -l)

if [ "$DELETED_COUNT" -gt 0 ]; then
    log "Cleaned up $DELETED_COUNT old backup files, keeping backups from the last $RETENTION_HOURS hours"
else
    log "No old backup files found for cleanup (retention: $RETENTION_HOURS hours)"
fi

# Optional: Log current backup count
CURRENT_BACKUPS=$(find "$BACKUP_DIR" -name "backup_tennisdb.*.zip" -type f | wc -l)
log "Current number of backup files: $CURRENT_BACKUPS"

exit 0