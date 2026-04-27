#!/bin/bash
# MT5 AI/ML Trading Bot - Backup & Verification Script
# This script performs a consistent backup of the SQLite database and verifies its integrity.

set -e # Exit on error

# Configuration
DB_PATH=${1:-"trades.db"}
BACKUP_DIR=${2:-"backups/db"}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/trades_backup_${TIMESTAMP}.sqlite"
LATEST_LINK="${BACKUP_DIR}/trades_backup_latest.sqlite"

mkdir -p "$BACKUP_DIR"

echo "Starting backup for $DB_PATH..."

# 1. Consistent Backup using SQLite .backup
if [ ! -f "$DB_PATH" ]; then
    echo "Error: Database file $DB_PATH not found!"
    exit 1
fi

sqlite3 "$DB_PATH" ".backup '$BACKUP_FILE'"

# 2. Integrity Check
echo "Verifying integrity of $BACKUP_FILE..."
INTEGRITY=$(sqlite3 "$BACKUP_FILE" "PRAGMA integrity_check;")
if [ "$INTEGRITY" != "ok" ]; then
    echo "Error: Backup integrity check failed: $INTEGRITY"
    exit 1
fi
echo "Integrity check passed."

# 3. Restoration Dry-run
echo "Performing restoration dry-run..."
TEST_DB="${BACKUP_DIR}/test_restore_${TIMESTAMP}.sqlite"
cp "$BACKUP_FILE" "$TEST_DB"

# Verify we can read from the trades table if it exists
if sqlite3 "$TEST_DB" "SELECT name FROM sqlite_master WHERE type='table' AND name='trades';" | grep -q "trades"; then
    ROW_COUNT=$(sqlite3 "$TEST_DB" "SELECT count(*) FROM trades;")
    echo "Restoration dry-run successful. trades table row count: $ROW_COUNT"
else
    echo "Restoration dry-run warning: trades table not found (might be a new DB). Checking sqlite_master instead."
    ROW_COUNT=$(sqlite3 "$TEST_DB" "SELECT count(*) FROM sqlite_master;")
    echo "Master table count: $ROW_COUNT"
fi
rm "$TEST_DB"

# 4. Retention Cleanup (Keep last 30 days of backups)
echo "Cleaning up old backups (retention policy: 30 days)..."
find "$BACKUP_DIR" -name "trades_backup_*.sqlite*" -type f -mtime +30 -delete

# 5. Generate Checksum
echo "Generating SHA256 checksum..."
sha256sum "$BACKUP_FILE" > "${BACKUP_FILE}.sha256"

# 6. Update latest link
ln -sf "trades_backup_${TIMESTAMP}.sqlite" "$LATEST_LINK"
ln -sf "trades_backup_${TIMESTAMP}.sqlite.sha256" "${LATEST_LINK}.sha256"

echo "Backup and verification completed successfully: $BACKUP_FILE"
