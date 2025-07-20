#!/bin/bash

# Clear the screen for a clean output
clear

# A robust script to check the health and basic stats of the SQLite database.
# Best practices:
# - Exit immediately if a command exits with a non-zero status.
set -e
# - Treat unset variables as an error when substituting.
set -u
# - Pipelines return the exit status of the last command to exit with a non-zero status.
set -o pipefail

# --- Configuration ---
# Assumes the script is in the same directory as the database.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
DB_PATH="${SCRIPT_DIR}/tennis.db"

# --- Functions for colored output ---
log_info() {
    # Blue for informational messages
    echo -e "\n\033[1;34m[INFO]\033[0m $1"
}

log_ok() {
    # Green for success messages
    echo -e "\033[0;32m[OK]\033[0m $1"
}

log_error() {
    # Red for error messages
    echo -e "\033[0;31m[ERROR]\033[0m $1" >&2
}

# --- Pre-flight Checks ---
# 1. Check if sqlite3 command exists
if ! command -v sqlite3 &> /dev/null; then
    log_error "sqlite3 command not found. Please install it to run this script."
    exit 1
fi

# 2. Check if database file exists
if [ ! -f "$DB_PATH" ]; then
    log_error "Database file not found at: $DB_PATH"
    exit 1
fi

# --- Main Logic ---
echo "=== Tennis Database Health Check ==="
echo "Database: $DB_PATH"

# 1. Integrity Check
# This is the most thorough check. 'quick_check' is a subset of this, so it's not needed.
log_info "1. Running Full Integrity Check..."
integrity_result=$(sqlite3 "$DB_PATH" "PRAGMA integrity_check;")
if [ "$integrity_result" == "ok" ]; then
    log_ok "Integrity check passed."
else
    log_error "Integrity check FAILED with result: $integrity_result"
    exit 1
fi

# 2. Foreign Key Check
# This pragma returns no output if there are no violations.
log_info "2. Running Foreign Key Check..."
fk_result=$(sqlite3 "$DB_PATH" "PRAGMA foreign_key_check;")
if [ -z "$fk_result" ]; then
    log_ok "Foreign key constraints are valid."
else
    log_error "Foreign key violations found:"
    echo "$fk_result"
    exit 1
fi

# 3. Schema and Info
# Combine multiple PRAGMA and queries into one call for efficiency.
log_info "3. Displaying Database Schema and Stats..."
sqlite3 "$DB_PATH" <<EOF
.header on
.mode column

-- Table and View list
SELECT type, name FROM sqlite_master WHERE type IN ('table', 'view') ORDER BY type, name;

-- Index list
SELECT name, tbl_name FROM sqlite_master WHERE type = 'index' AND name NOT LIKE 'sqlite_%' ORDER BY name;

-- Row Counts for key tables
SELECT COUNT(*) AS player_count FROM players;
SELECT COUNT(*) AS total_challenges FROM challenges;
SELECT COUNT(*) AS active_challenges FROM challenges WHERE resolved = 0;
EOF

if [ $? -eq 0 ]; then
    log_ok "Database info displayed successfully."
else
    log_error "Failed to retrieve database info."
    exit 1
fi

echo ""
log_ok "=== All database checks completed successfully. ==="

exit 0

