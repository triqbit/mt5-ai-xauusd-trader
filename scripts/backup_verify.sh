#!/bin/bash
# MT5 AI/ML Trading Bot - Disaster Recovery Backup & Verification Script
# This script performs a backup of the SQLite databases (trades.db, audit.db),
# archives logs and reports, generates SHA256 checksums, and verifies backup integrity.

set -e

# Configuration
# Allow environment variables to override defaults
DB_FILES_ENV=${DB_FILES:-"trades.db audit.db"}
IFS=' ' read -r -a DB_FILES <<< "$DB_FILES_ENV"

LOGS_DIR=${LOGS_DIR:-"logs"}
REPORTS_DIR=${REPORTS_DIR:-"reports"}
MODELS_DIR=${MODELS_DIR:-"models/trained"}
BACKUP_ROOT=${BACKUP_ROOT:-"backups"}
DB_BACKUP_DIR="${BACKUP_ROOT}/db"
LOGS_BACKUP_DIR="${BACKUP_ROOT}/logs"
REPORTS_BACKUP_DIR="${BACKUP_ROOT}/reports"
MODELS_BACKUP_DIR="${BACKUP_ROOT}/models"
BACKUP_LOG="logs/backup.log"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RETENTION_DAYS=30
MIN_DISK_SPACE_MB=500

# Create necessary directories
mkdir -p "${DB_BACKUP_DIR}"
mkdir -p "${LOGS_BACKUP_DIR}"
mkdir -p "${REPORTS_BACKUP_DIR}"
mkdir -p "${MODELS_BACKUP_DIR}"
mkdir -p "logs"

log_message() {
    local MESSAGE="[$(date +'%Y-%m-%d %H:%M:%S')] $1"
    echo "${MESSAGE}"
    echo "${MESSAGE}" >> "${BACKUP_LOG}"
}

log_message "Starting Disaster Recovery Backup Process..."

# 0. Dependencies Check
for cmd in sqlite3 tar sha256sum awk find; do
    if ! command -v $cmd >/dev/null 2>&1; then
        log_message "FAILURE: Required command '$cmd' not found. Please install it."
        exit 1
    fi
done

# 0.1 Disk Space Check
if command -v df >/dev/null 2>&1; then
    # Target the directory where backups are stored
    FREE_SPACE=$(df -m "${BACKUP_ROOT}" | awk 'NR==2 {print $4}')
    if [ -z "$FREE_SPACE" ] || ! [[ "$FREE_SPACE" =~ ^[0-9]+$ ]]; then
        FREE_SPACE=$(df -m "${BACKUP_ROOT}" | tail -1 | awk '{print $(NF-2)}')
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
        sqlite3 "${DB_FILE}" ".backup '${BACKUP_FILE}'"

        # 2. Automated Verification (Restoration Dry-run)
        log_message "PHASE: Restoration Dry-run for ${BACKUP_FILE}..."

        log_message "STEP 2.0: Verifying backup integrity for ${BACKUP_FILE} (SQLite dry-run)..."
        INTEGRITY=$(sqlite3 "${BACKUP_FILE}" "PRAGMA integrity_check;")
        if [ "${INTEGRITY}" == "ok" ]; then
            log_message "SUCCESS: ${DB_FILE} backup integrity verified."
        else
            log_message "FAILURE: ${DB_FILE} backup integrity check failed: ${INTEGRITY}"
            exit 1
        fi

        # 2.1 Schema Validation (Enhanced Restore Test)
        log_message "STEP 2.1: Validating schema for ${BACKUP_FILE}..."
        REQUIRED_TABLES=()
        if [ "${DB_BASE}" == "trades" ]; then
            REQUIRED_TABLES=("trades" "risk_events" "performance_metrics" "model_signals" "blocked_signal_analysis" "execution_qualities")
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

        # 2.2 Data Access Test (Restore Dry-run)
        log_message "STEP 2.2: Performing Data Access Test for ${BACKUP_FILE}..."
        for table in "${REQUIRED_TABLES[@]}"; do
            ROW_COUNT=$(sqlite3 "${BACKUP_FILE}" "SELECT count(*) FROM ${table};" 2>/dev/null || echo "ERROR")
            if [[ "${ROW_COUNT}" =~ ^[0-9]+$ ]]; then
                log_message "SUCCESS: Data Access Test passed for ${BACKUP_FILE} table '${table}' (${ROW_COUNT} rows)."
            else
                log_message "FAILURE: Data Access Test failed for ${BACKUP_FILE} table '${table}'. Could not read data."
                exit 1
            fi
        done

        # 3. Checksum Generation and Verification
        log_message "PHASE: Checksum Generation and Verification for ${BACKUP_FILE}..."
        log_message "STEP 3.0: Generating SHA256 checksum for ${BACKUP_FILE}..."
        (cd "${DB_BACKUP_DIR}" && sha256sum "$(basename "${BACKUP_FILE}")" > "$(basename "${BACKUP_FILE}").sha256")

        log_message "Verifying SHA256 checksum for ${BACKUP_FILE}..."
        if (cd "${DB_BACKUP_DIR}" && sha256sum -c "$(basename "${BACKUP_FILE}").sha256" > /dev/null); then
            log_message "SUCCESS: Checksum verification passed for ${BACKUP_FILE}."
        else
            log_message "FAILURE: Checksum verification failed for ${BACKUP_FILE}."
            exit 1
        fi
    else
        log_message "INFO: ${DB_FILE} not found. Skipping backup for this database."
    fi
done

# 4. Logs Archival
log_message "PHASE: Logs Archival..."
if [ -d "${LOGS_DIR}" ] && [ "$(ls -A ${LOGS_DIR} 2>/dev/null)" ]; then
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

    log_message "Verifying SHA256 checksum for ${LOGS_ARCHIVE}..."
    if (cd "${LOGS_BACKUP_DIR}" && sha256sum -c "$(basename "${LOGS_ARCHIVE}").sha256" > /dev/null); then
        log_message "SUCCESS: Checksum verification passed for ${LOGS_ARCHIVE}."
    else
        log_message "FAILURE: Checksum verification failed for ${LOGS_ARCHIVE}."
        exit 1
    fi
else
    log_message "INFO: Logs directory empty or not found. Skipping log archival."
fi

# 5. Reports Archival
log_message "PHASE: Reports Archival..."
if [ -d "${REPORTS_DIR}" ] && [ "$(ls -A ${REPORTS_DIR} 2>/dev/null)" ]; then
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

    log_message "Verifying SHA256 checksum for ${REPORTS_ARCHIVE}..."
    if (cd "${REPORTS_BACKUP_DIR}" && sha256sum -c "$(basename "${REPORTS_ARCHIVE}").sha256" > /dev/null); then
        log_message "SUCCESS: Checksum verification passed for ${REPORTS_ARCHIVE}."
    else
        log_message "FAILURE: Checksum verification failed for ${REPORTS_ARCHIVE}."
        exit 1
    fi
else
    log_message "INFO: Reports directory empty or not found. Skipping report archival."
fi

# 6. Models Archival
log_message "PHASE: Models Archival..."
if [ -d "${MODELS_DIR}" ] && [ "$(ls -A ${MODELS_DIR} 2>/dev/null)" ]; then
    MODELS_ARCHIVE="${MODELS_BACKUP_DIR}/models_${TIMESTAMP}.tar.gz"
    log_message "Archiving models to ${MODELS_ARCHIVE}..."
    tar -czf "${MODELS_ARCHIVE}" -C "${MODELS_DIR}" .

    # 6.1 Verify Model Archive Integrity
    log_message "Verifying model archive integrity..."
    if tar -tzf "${MODELS_ARCHIVE}" > /dev/null; then
        log_message "SUCCESS: Model archive integrity verified."
    else
        log_message "FAILURE: Model archive is corrupt."
        exit 1
    fi

    (cd "${MODELS_BACKUP_DIR}" && sha256sum "$(basename "${MODELS_ARCHIVE}")" > "$(basename "${MODELS_ARCHIVE}").sha256")

    log_message "Verifying SHA256 checksum for ${MODELS_ARCHIVE}..."
    if (cd "${MODELS_BACKUP_DIR}" && sha256sum -c "$(basename "${MODELS_ARCHIVE}").sha256" > /dev/null); then
        log_message "SUCCESS: Checksum verification passed for ${MODELS_ARCHIVE}."
    else
        log_message "FAILURE: Checksum verification failed for ${MODELS_ARCHIVE}."
        exit 1
    fi
else
    log_message "INFO: Models directory empty or not found. Skipping model archival."
fi

# 7. Retention Policy Enforcement
log_message "Enforcing retention policy (Pruning files older than ${RETENTION_DAYS} days)..."
# Prune data files and their associated .sha256 files using specific patterns for safety
find "${BACKUP_ROOT}" -type f \( -name "*.db" -o -name "*.tar.gz" -o -name "*.sha256" \) -mtime +${RETENTION_DAYS} -exec rm -f {} +

log_message "Disaster Recovery Backup Process Completed Successfully."
