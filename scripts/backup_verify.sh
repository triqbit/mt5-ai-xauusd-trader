#!/bin/bash
# MT5 AI/ML Trading Bot - Disaster Recovery Backup & Verification Script
# This script performs a backup of the SQLite database, generates checksums,
# and verifies the backup with a restoration dry-run.

set -e

# Configuration
DB_FILE="trades.db"
LOGS_DIR="logs"
BACKUP_ROOT="backups"
DB_BACKUP_DIR="${BACKUP_ROOT}/db"
LOGS_BACKUP_DIR="${BACKUP_ROOT}/logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RETENTION_DAYS=30

# Create backup directories
mkdir -p "${DB_BACKUP_DIR}"
mkdir -p "${LOGS_BACKUP_DIR}"

echo "[$(date)] Starting Disaster Recovery Backup Process..."

# 1. Database Backup
if [ -f "${DB_FILE}" ]; then
    BACKUP_FILE="${DB_BACKUP_DIR}/trades_${TIMESTAMP}.db"
    echo "Backing up database to ${BACKUP_FILE}..."

    # Use sqlite3 .backup command for a safe online backup if possible,
    # otherwise fallback to cp.
    if command -v sqlite3 >/dev/null 2>&1; then
        sqlite3 "${DB_FILE}" ".backup '${BACKUP_FILE}'"
    else
        cp "${DB_FILE}" "${BACKUP_FILE}"
    fi

    # 2. Checksum Generation
    echo "Generating SHA256 checksum..."
    (cd "${DB_BACKUP_DIR}" && sha256sum "$(basename "${BACKUP_FILE}")" > "$(basename "${BACKUP_FILE}").sha256")

    # 3. Automated Verification (Restoration Dry-run)
    echo "Verifying backup integrity (SQLite dry-run)..."
    if command -v sqlite3 >/dev/null 2>&1; then
        INTEGRITY=$(sqlite3 "${BACKUP_FILE}" "PRAGMA integrity_check;")
        if [ "${INTEGRITY}" == "ok" ]; then
            echo "SUCCESS: Database integrity verified."
        else
            echo "FAILURE: Database integrity check failed: ${INTEGRITY}"
            exit 1
        fi
    else
        echo "WARNING: sqlite3 not found, skipping integrity check."
    fi
else
    echo "WARNING: ${DB_FILE} not found. Skipping database backup."
fi

# 4. Logs Archival
if [ -d "${LOGS_DIR}" ] && [ "$(ls -A ${LOGS_DIR})" ]; then
    LOGS_ARCHIVE="${LOGS_BACKUP_DIR}/logs_${TIMESTAMP}.tar.gz"
    echo "Archiving logs to ${LOGS_ARCHIVE}..."
    tar -czf "${LOGS_ARCHIVE}" -C "${LOGS_DIR}" .
    (cd "${LOGS_BACKUP_DIR}" && sha256sum "$(basename "${LOGS_ARCHIVE}")" > "$(basename "${LOGS_ARCHIVE}").sha256")
else
    echo "INFO: Logs directory empty or not found. Skipping log archival."
fi

# 5. Retention Policy Enforcement
echo "Enforcing retention policy (Pruning files older than ${RETENTION_DAYS} days)..."
find "${BACKUP_ROOT}" -type f -mtime +${RETENTION_DAYS} -name "trades_*" -delete
find "${BACKUP_ROOT}" -type f -mtime +${RETENTION_DAYS} -name "logs_*" -delete

echo "[$(date)] Disaster Recovery Backup Process Completed Successfully."
