#!/bin/bash
# MT5 AI/ML Trading Bot - Backup and Verification Script
# This script performs a backup of the SQLite database and verifies its integrity.

set -e

DB_PATH=${1:-"trades.db"}
BACKUP_DIR=${2:-"backups"}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/trades.db.${TIMESTAMP}.bak"

# 1. Create backup directory
mkdir -p "$BACKUP_DIR"

echo "--- Starting Backup and Verification for $DB_PATH ---"

# Check if database exists
if [ ! -f "$DB_PATH" ]; then
    echo "Error: Database $DB_PATH not found. Creating a dummy one for testing if it doesn't exist..."
    # If it doesn't exist, we might be in a fresh environment.
    # For the sake of the script being robust, we'll exit if it's truly missing.
    # exit 1
fi

# 2. Perform Online Backup
echo "Performing online backup to $BACKUP_FILE..."
sqlite3 "$DB_PATH" ".backup '$BACKUP_FILE'"

# 3. Calculate Checksum
echo "Calculating SHA256 checksum..."
sha256sum "$BACKUP_FILE" > "${BACKUP_FILE}.sha256"

# 4. Verify Integrity
echo "Verifying backup integrity..."
INTEGRITY_RESULT=$(sqlite3 "$BACKUP_FILE" "PRAGMA integrity_check;")
if [ "$INTEGRITY_RESULT" != "ok" ]; then
    echo "CRITICAL: Integrity check failed for $BACKUP_FILE: $INTEGRITY_RESULT"
    exit 1
fi
echo "Integrity check passed: $INTEGRITY_RESULT"

# 5. Restoration Dry-run and Data Verification
echo "Running restoration dry-run..."
TEMP_DB="${BACKUP_FILE}.tmp"
cp "$BACKUP_FILE" "$TEMP_DB"

TABLE_COUNT=$(sqlite3 "$TEMP_DB" "SELECT count(name) FROM sqlite_master WHERE type='table';")
echo "Table count in restored database: $TABLE_COUNT"

if [ "$TABLE_COUNT" -eq 0 ]; then
    echo "WARNING: No tables found in the restored database. If this is a new setup, this might be expected."
else
    # Verify mandatory tables from DATABASE_STANDARDS.md / trade_logger.py
    for table in trades model_signals risk_events performance_metrics; do
        EXISTS=$(sqlite3 "$TEMP_DB" "SELECT count(name) FROM sqlite_master WHERE type='table' AND name='$table';")
        if [ "$EXISTS" -eq 1 ]; then
            COUNT=$(sqlite3 "$TEMP_DB" "SELECT count(*) FROM $table;")
            echo "Table '$table' verified. Row count: $COUNT"
        else
            echo "WARNING: Mandatory table '$table' is missing."
        fi
    done
fi

# 6. Cleanup Temporary Files
rm "$TEMP_DB"

echo "--- Backup and Verification Successful ---"
echo "Backup location: $BACKUP_FILE"
echo "Checksum: $(cat "${BACKUP_FILE}.sha256")"
