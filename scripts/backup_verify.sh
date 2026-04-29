#!/bin/bash
# MT5 Trading Bot - Backup and Verification Script
# Performs online SQLite backup, bundles logs, generates checksums, and dry-runs restoration.
# Author: Jules03 (Release Reliability & Governance)

set -e

DB_FILE=${1:-"trades.db"}
BACKUP_DIR_ABS=$(pwd)/${2:-"backups"}
LOGS_DIR=${3:-"logs"}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Ensure backup directory exists
mkdir -p "${BACKUP_DIR_ABS}"

echo "--- Starting Backup Process ---"

# 1. Source Database Validation
if [ ! -f "${DB_FILE}" ]; then
    echo "CRITICAL ERROR: Source database ${DB_FILE} not found. Aborting backup."
    exit 1
fi

# 2. Perform online backup using SQLite .backup command
echo "Performing online backup for ${DB_FILE}..."
DB_BACKUP_NAME="backup_${TIMESTAMP}.db"
sqlite3 "${DB_FILE}" ".backup '${BACKUP_DIR_ABS}/${DB_BACKUP_NAME}'"

# 3. Bundle Logs
LOGS_BACKUP_NAME="backup_${TIMESTAMP}_logs.tar.gz"
if [ -d "${LOGS_DIR}" ]; then
    echo "Bundling logs from ${LOGS_DIR}..."
    tar -czf "${BACKUP_DIR_ABS}/${LOGS_BACKUP_NAME}" -C "${LOGS_DIR}" .
else
    echo "Warning: Logs directory ${LOGS_DIR} not found. Skipping log bundle."
fi

# 4. Restoration Dry-run & Integrity Check
RESTORE_TEST_DB="${BACKUP_DIR_ABS}/restore_test_${TIMESTAMP}.db"
cp "${BACKUP_DIR_ABS}/${DB_BACKUP_NAME}" "${RESTORE_TEST_DB}"

echo "Running SQLite integrity check..."
INTEGRITY_RESULT=$(sqlite3 "${RESTORE_TEST_DB}" "PRAGMA integrity_check;")

if [ "${INTEGRITY_RESULT}" != "ok" ]; then
    echo "CRITICAL ERROR: Integrity check failed for restored backup!"
    rm -f "${RESTORE_TEST_DB}"
    exit 1
fi
echo "Integrity check passed."
rm -f "${RESTORE_TEST_DB}"

# 5. Compression and Checksum
echo "Compressing database backup..."
gzip -f "${BACKUP_DIR_ABS}/${DB_BACKUP_NAME}"
DB_GZ_NAME="${DB_BACKUP_NAME}.gz"

echo "Generating checksums..."
cd "${BACKUP_DIR_ABS}"
sha256sum "${DB_GZ_NAME}" > "${DB_GZ_NAME}.sha256"
if [ -f "${LOGS_BACKUP_NAME}" ]; then
    sha256sum "${LOGS_BACKUP_NAME}" > "${LOGS_BACKUP_NAME}.sha256"
fi

echo "--- Backup Verification Successful ---"
ls -lh "${DB_GZ_NAME}"*

# 6. Rotation (Cleanup files older than 30 days)
echo "Checking for old backups to rotate..."
find . -name "backup_*" -mtime +30 -type f -delete
echo "Rotation complete."

exit 0
