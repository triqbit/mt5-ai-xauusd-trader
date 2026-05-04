#!/bin/bash
# MT5 AI/ML Trading Bot - Disaster Recovery Backup & Verification Script
# This script performs a backup of the SQLite databases (trades.db, audit.db),
# archives logs and reports, generates SHA256 checksums, and verifies backup integrity.

set -e

# Configuration
DB_FILES=("trades.db" "audit.db")
LOGS_DIR="logs"
REPORTS_DIR="reports"
BACKUP_ROOT="backups"
DB_BACKUP_DIR="${BACKUP_ROOT}/db"
LOGS_BACKUP_DIR="${BACKUP_ROOT}/logs"
REPORTS_BACKUP_DIR="${BACKUP_ROOT}/reports"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RETENTION_DAYS=30

# Create backup directories
mkdir -p "${DB_BACKUP_DIR}"
mkdir -p "${LOGS_BACKUP_DIR}"
mkdir -p "${REPORTS_BACKUP_DIR}"

echo "[$(date)] Starting Disaster Recovery Backup Process..."

# 1. Database Backup Loop
for DB_FILE in "${DB_FILES[@]}"; do
    if [ -f "${DB_FILE}" ]; then
        DB_BASE=$(basename "${DB_FILE}" .db)
        BACKUP_FILE="${DB_BACKUP_DIR}/${DB_BASE}_${TIMESTAMP}.db"
        echo "Backing up database ${DB_FILE} to ${BACKUP_FILE}..."

        # Use sqlite3 .backup command for a safe online/hot backup
        if command -v sqlite3 >/dev/null 2>&1; then
            sqlite3 "${DB_FILE}" ".backup '${BACKUP_FILE}'"

            # 2. Automated Verification (Restoration Dry-run)
            echo "Verifying backup integrity for ${BACKUP_FILE} (SQLite dry-run)..."
            INTEGRITY=$(sqlite3 "${BACKUP_FILE}" "PRAGMA integrity_check;")
            if [ "${INTEGRITY}" == "ok" ]; then
                echo "SUCCESS: ${DB_FILE} backup integrity verified."
            else
                echo "FAILURE: ${DB_FILE} backup integrity check failed: ${INTEGRITY}"
                exit 1
            fi
        else
            echo "WARNING: sqlite3 not found, falling back to cp for ${DB_FILE}. Hot backup not guaranteed."
            cp "${DB_FILE}" "${BACKUP_FILE}"
        fi

        # 3. Checksum Generation
        echo "Generating SHA256 checksum for ${BACKUP_FILE}..."
        (cd "${DB_BACKUP_DIR}" && sha256sum "$(basename "${BACKUP_FILE}")" > "$(basename "${BACKUP_FILE}").sha256")
    else
        echo "INFO: ${DB_FILE} not found. Skipping backup for this database."
    fi
done

# 4. Logs Archival
if [ -d "${LOGS_DIR}" ] && [ "$(ls -A ${LOGS_DIR})" ]; then
    LOGS_ARCHIVE="${LOGS_BACKUP_DIR}/logs_${TIMESTAMP}.tar.gz"
    echo "Archiving logs to ${LOGS_ARCHIVE}..."
    tar -czf "${LOGS_ARCHIVE}" -C "${LOGS_DIR}" .

    # 4.1 Verify Log Archive Integrity
    echo "Verifying log archive integrity..."
    if tar -tzf "${LOGS_ARCHIVE}" > /dev/null; then
        echo "SUCCESS: Log archive integrity verified."
    else
        echo "FAILURE: Log archive is corrupt."
        exit 1
    fi

    (cd "${LOGS_BACKUP_DIR}" && sha256sum "$(basename "${LOGS_ARCHIVE}")" > "$(basename "${LOGS_ARCHIVE}").sha256")
else
    echo "INFO: Logs directory empty or not found. Skipping log archival."
fi

# 5. Reports Archival
if [ -d "${REPORTS_DIR}" ] && [ "$(ls -A ${REPORTS_DIR})" ]; then
    REPORTS_ARCHIVE="${REPORTS_BACKUP_DIR}/reports_${TIMESTAMP}.tar.gz"
    echo "Archiving reports to ${REPORTS_ARCHIVE}..."
    tar -czf "${REPORTS_ARCHIVE}" -C "${REPORTS_DIR}" .

    # 5.1 Verify Report Archive Integrity
    echo "Verifying report archive integrity..."
    if tar -tzf "${REPORTS_ARCHIVE}" > /dev/null; then
        echo "SUCCESS: Report archive integrity verified."
    else
        echo "FAILURE: Report archive is corrupt."
        exit 1
    fi

    (cd "${REPORTS_BACKUP_DIR}" && sha256sum "$(basename "${REPORTS_ARCHIVE}")" > "$(basename "${REPORTS_ARCHIVE}").sha256")
else
    echo "INFO: Reports directory empty or not found. Skipping report archival."
fi

# 6. Retention Policy Enforcement
echo "Enforcing retention policy (Pruning files older than ${RETENTION_DAYS} days)..."
# Prune data files and their associated .sha256 files
find "${BACKUP_ROOT}" -type f -mtime +${RETENTION_DAYS} -exec rm -f {} +

echo "[$(date)] Disaster Recovery Backup Process Completed Successfully."
