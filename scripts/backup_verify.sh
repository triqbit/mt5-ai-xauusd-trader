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
BACKUP_LOG="logs/backup.log"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RETENTION_DAYS=30
MIN_DISK_SPACE_MB=500

# Create necessary directories
mkdir -p "${DB_BACKUP_DIR}"
mkdir -p "${LOGS_BACKUP_DIR}"
mkdir -p "${REPORTS_BACKUP_DIR}"
mkdir -p "logs"

log_message() {
    local MESSAGE="[$(date +'%Y-%m-%d %H:%M:%S')] $1"
    echo "${MESSAGE}"
    echo "${MESSAGE}" >> "${BACKUP_LOG}"
}

log_message "Starting Disaster Recovery Backup Process..."

# 0. Dependencies Check
for cmd in sqlite3 tar sha256sum awk; do
    if ! command -v $cmd >/dev/null 2>&1; then
        log_message "FAILURE: Required command '$cmd' not found. Please install it."
        exit 1
    fi
done

# 0.1 Disk Space Check
if command -v df >/dev/null 2>&1; then
    # More robust df parsing using POSIX output and targeting the current directory's partition
    FREE_SPACE=$(df -m . | awk 'NR==2 {print $4}')
    # If NR==2 didn't work (e.g. long filesystem name), try the last field of the last line
    if [ -z "$FREE_SPACE" ] || ! [[ "$FREE_SPACE" =~ ^[0-9]+$ ]]; then
        FREE_SPACE=$(df -m . | tail -1 | awk '{print $(NF-2)}')
    fi

    if [ "${FREE_SPACE}" -lt "${MIN_DISK_SPACE_MB}" ]; then
        log_message "FAILURE: Insufficient disk space for backup. Required: ${MIN_DISK_SPACE_MB}MB, Available: ${FREE_SPACE}MB"
        exit 1
    fi
    log_message "Disk space check passed: ${FREE_SPACE}MB available."
fi

# 1. Database Backup Loop
for DB_FILE in "${DB_FILES[@]}"; do
    if [ -f "${DB_FILE}" ]; then
        DB_BASE=$(basename "${DB_FILE}" .db)
        BACKUP_FILE="${DB_BACKUP_DIR}/${DB_BASE}_${TIMESTAMP}.db"
        log_message "Backing up database ${DB_FILE} to ${BACKUP_FILE}..."

        # Use sqlite3 .backup command for a safe online/hot backup
        if command -v sqlite3 >/dev/null 2>&1; then
            sqlite3 "${DB_FILE}" ".backup '${BACKUP_FILE}'"

            # 2. Automated Verification (Restoration Dry-run)
            log_message "Verifying backup integrity for ${BACKUP_FILE} (SQLite dry-run)..."
            INTEGRITY=$(sqlite3 "${BACKUP_FILE}" "PRAGMA integrity_check;")
            if [ "${INTEGRITY}" == "ok" ]; then
                log_message "SUCCESS: ${DB_FILE} backup integrity verified."
            else
                log_message "FAILURE: ${DB_FILE} backup integrity check failed: ${INTEGRITY}"
                exit 1
            fi

            # 2.1 Schema Validation (Enhanced Restore Test)
            log_message "Validating schema for ${BACKUP_FILE}..."
            REQUIRED_TABLES=()
            if [ "${DB_BASE}" == "trades" ]; then
                REQUIRED_TABLES=("trades" "risk_events" "performance_metrics" "model_signals")
            elif [ "${DB_BASE}" == "audit" ]; then
                REQUIRED_TABLES=("audit_log")
            fi

            VALID=true
            for table in "${REQUIRED_TABLES[@]}"; do
                TABLE_CHECK=$(sqlite3 "${BACKUP_FILE}" "SELECT name FROM sqlite_master WHERE type='table' AND name='${table}';")
                if [ -z "${TABLE_CHECK}" ]; then
                    log_message "FAILURE: Schema validation failed for ${BACKUP_FILE}. Table '${table}' missing."
                    VALID=false
                    break
                fi
            done

            if [ "${VALID}" == "true" ]; then
                log_message "SUCCESS: Schema validation passed for ${BACKUP_FILE}."
            else
                log_message "FAILURE: Schema validation failed for ${BACKUP_FILE}. Required table not found."
                exit 1
            fi
        else
            log_message "WARNING: sqlite3 not found, falling back to cp for ${DB_FILE}. Hot backup not guaranteed."
            cp "${DB_FILE}" "${BACKUP_FILE}"
        fi

        # 3. Checksum Generation
        log_message "Generating SHA256 checksum for ${BACKUP_FILE}..."
        (cd "${DB_BACKUP_DIR}" && sha256sum "$(basename "${BACKUP_FILE}")" > "$(basename "${BACKUP_FILE}").sha256")
    else
        log_message "INFO: ${DB_FILE} not found. Skipping backup for this database."
    fi
done

# 4. Logs Archival
if [ -d "${LOGS_DIR}" ] && [ "$(ls -A ${LOGS_DIR})" ]; then
    LOGS_ARCHIVE="${LOGS_BACKUP_DIR}/logs_${TIMESTAMP}.tar.gz"
    log_message "Archiving logs to ${LOGS_ARCHIVE}..."
    tar -czf "${LOGS_ARCHIVE}" -C "${LOGS_DIR}" .

    # 4.1 Verify Log Archive Integrity
    log_message "Verifying log archive integrity..."
    if tar -tzf "${LOGS_ARCHIVE}" > /dev/null; then
        log_message "SUCCESS: Log archive integrity verified."
    else
        log_message "FAILURE: Log archive is corrupt."
        exit 1
    fi

    (cd "${LOGS_BACKUP_DIR}" && sha256sum "$(basename "${LOGS_ARCHIVE}")" > "$(basename "${LOGS_ARCHIVE}").sha256")
else
    log_message "INFO: Logs directory empty or not found. Skipping log archival."
fi

# 5. Reports Archival
if [ -d "${REPORTS_DIR}" ] && [ "$(ls -A ${REPORTS_DIR})" ]; then
    REPORTS_ARCHIVE="${REPORTS_BACKUP_DIR}/reports_${TIMESTAMP}.tar.gz"
    log_message "Archiving reports to ${REPORTS_ARCHIVE}..."
    tar -czf "${REPORTS_ARCHIVE}" -C "${REPORTS_DIR}" .

    # 5.1 Verify Report Archive Integrity
    log_message "Verifying report archive integrity..."
    if tar -tzf "${REPORTS_ARCHIVE}" > /dev/null; then
        log_message "SUCCESS: Report archive integrity verified."
    else
        log_message "FAILURE: Report archive is corrupt."
        exit 1
    fi

    (cd "${REPORTS_BACKUP_DIR}" && sha256sum "$(basename "${REPORTS_ARCHIVE}")" > "$(basename "${REPORTS_ARCHIVE}").sha256")
else
    log_message "INFO: Reports directory empty or not found. Skipping report archival."
fi

# 6. Retention Policy Enforcement
log_message "Enforcing retention policy (Pruning files older than ${RETENTION_DAYS} days)..."
# Prune data files and their associated .sha256 files
find "${BACKUP_ROOT}" -type f -mtime +${RETENTION_DAYS} -exec rm -f {} +

log_message "Disaster Recovery Backup Process Completed Successfully."
