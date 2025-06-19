#!/bin/bash

# Tennis Database Backup Script (No privileged operations)
# Purpose: Creates a daily backup of the tennis database with date-stamped filename

# Configuration
SOURCE_DB="/home/stecher/stecher_tennis/tennis.db"
BACKUP_DIR="/home/stecher/stecher_tennis/backup"
DATE=$(date +"%Y%m%d")
BACKUP_FILE="${BACKUP_DIR}/backup_tennisdb.${DATE}.zip"
LOG_FILE="${BACKUP_DIR}/backup.log"
RETENTION_DAYS=30  # Number of backups to keep
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

# Create backup
log "Starting backup of $SOURCE_DB"

# Create a temporary copy to avoid backing up a file that might be changing
TMP_DB="${TMP_DIR}/tennis_db_backup_${DATE}.db"
cp "$SOURCE_DB" "$TMP_DB"
if [ $? -ne 0 ]; then
    log "ERROR: Failed to create temporary copy of database"
    exit 1
fi

# Zip the backup file
zip -j "$BACKUP_FILE" "$TMP_DB"
ZIP_STATUS=$?
rm "$TMP_DB"  # Clean up temp file regardless of zip success

if [ $ZIP_STATUS -ne 0 ]; then
    log "ERROR: Failed to create zip backup at $BACKUP_FILE"
    exit 1
fi

# Verify backup file was created successfully
if [ -f "$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log "SUCCESS: Backup completed successfully at $BACKUP_FILE (Size: $BACKUP_SIZE)"
else
    log "ERROR: Backup file not found after backup process"
    exit 1
fi

# Keep only the most recent backups based on retention policy
find "$BACKUP_DIR" -name "backup_tennisdb.*.zip" -type f -mtime +$RETENTION_DAYS -delete 2>/dev/null
log "Cleaned up old backup files, keeping the last $RETENTION_DAYS days of backups"

exit 0
