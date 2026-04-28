#!/bin/bash
# MT5 AI/ML Trading Bot - Backup & Verification Script
# This script performs an automated backup of the SQLite database,
# verifies its integrity, and runs a restoration dry-run.

set -e

# Configuration
DB_FILE="trades.db"
BACKUP_DIR="backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/trades_${TIMESTAMP}.db"
LOG_FILE="logs/backup_verify.log"

# Ensure directories exist
mkdir -p "${BACKUP_DIR}"
mkdir -p "logs"

echo "[$(date)] Starting backup and verification process..." | tee -a "${LOG_FILE}"

# 1. Check if database exists
if [ ! -f "${DB_FILE}" ]; then
    echo "ERROR: Database file ${DB_FILE} not found." | tee -a "${LOG_FILE}"
    exit 1
fi

# 2. Perform SQLite Online Backup
echo "Creating backup: ${BACKUP_FILE}..." | tee -a "${LOG_FILE}"
sqlite3 "${DB_FILE}" ".backup '${BACKUP_FILE}'"

if [ $? -ne 0 ]; then
    echo "ERROR: SQLite backup failed." | tee -a "${LOG_FILE}"
    exit 1
fi

# 3. Integrity Check
echo "Running physical integrity check..." | tee -a "${LOG_FILE}"
INTEGRITY_RESULT=$(sqlite3 "${BACKUP_FILE}" "PRAGMA integrity_check;")

if [ "${INTEGRITY_RESULT}" != "ok" ]; then
    echo "ERROR: Backup integrity check failed: ${INTEGRITY_RESULT}" | tee -a "${LOG_FILE}"
    rm "${BACKUP_FILE}"
    exit 1
fi
echo "Integrity check passed." | tee -a "${LOG_FILE}"

# 4. Restoration Dry-run
echo "Performing restoration dry-run..." | tee -a "${LOG_FILE}"
DRY_RUN_DB="trades_dryrun_tmp.db"

# Copy backup to temp file
cp "${BACKUP_FILE}" "${DRY_RUN_DB}"

# Verify we can read from it
TABLE_COUNT=$(sqlite3 "${DRY_RUN_DB}" "SELECT count(*) FROM sqlite_master WHERE type='table';")
echo "Verified ${TABLE_COUNT} tables in restored database." | tee -a "${LOG_FILE}"

if [ "${TABLE_COUNT}" -eq 0 ]; then
    echo "ERROR: Restored database contains no tables." | tee -a "${LOG_FILE}"
    rm "${DRY_RUN_DB}"
    exit 1
fi

# Cleanup dry-run artifact
rm "${DRY_RUN_DB}"

# 5. Compression
echo "Compressing backup..." | tee -a "${LOG_FILE}"
gzip "${BACKUP_FILE}"
FINAL_BACKUP="${BACKUP_FILE}.gz"

# 6. Generate Checksum for the compressed artifact
echo "Generating SHA256 checksum for ${FINAL_BACKUP}..." | tee -a "${LOG_FILE}"
sha256sum "${FINAL_BACKUP}" > "${FINAL_BACKUP}.sha256"
echo "Checksum generated: $(cat ${FINAL_BACKUP}.sha256)" | tee -a "${LOG_FILE}"

# 7. Retention Cleanup (Keep last 30 days)
echo "Cleaning up old backups and checksums (30 day retention)..." | tee -a "${LOG_FILE}"
# Remove old .gz files
find "${BACKUP_DIR}" -name "trades_*.db.gz" -mtime +30 -delete
# Remove old .sha256 files
find "${BACKUP_DIR}" -name "trades_*.db.gz.sha256" -mtime +30 -delete

echo "[$(date)] Backup and verification process completed successfully." | tee -a "${LOG_FILE}"
