#!/bin/bash
# MT5 AI/ML Trading Bot - Disaster Recovery Functional Verification
# This script verifies the end-to-end backup and restoration process.

set -e

# Configuration
TEST_DIR="dr_test_env"
BACKUP_ROOT="${TEST_DIR}/backups"
LOGS_DIR="${TEST_DIR}/logs"
REPORTS_DIR="${TEST_DIR}/reports"
MODELS_DIR="${TEST_DIR}/models/trained"
TRADES_DB="${TEST_DIR}/trades.db"
AUDIT_DB="${TEST_DIR}/audit.db"

echo "=== Starting Disaster Recovery Functional Verification ==="

# 1. Setup Test Environment
echo "[1/6] Setting up test environment..."
rm -rf "${TEST_DIR}"
mkdir -p "${BACKUP_ROOT}" "${LOGS_DIR}" "${REPORTS_DIR}" "${MODELS_DIR}"

# 2. Initialize Mock Databases with Required Schema
echo "[2/6] Initializing mock databases..."
sqlite3 "${TRADES_DB}" "CREATE TABLE trades (id INTEGER PRIMARY KEY); INSERT INTO trades DEFAULT VALUES;"
sqlite3 "${TRADES_DB}" "CREATE TABLE model_signals (id INTEGER PRIMARY KEY); INSERT INTO model_signals DEFAULT VALUES;"
sqlite3 "${TRADES_DB}" "CREATE TABLE risk_events (id INTEGER PRIMARY KEY); INSERT INTO risk_events DEFAULT VALUES;"
sqlite3 "${TRADES_DB}" "CREATE TABLE performance_metrics (id INTEGER PRIMARY KEY); INSERT INTO performance_metrics DEFAULT VALUES;"
sqlite3 "${TRADES_DB}" "CREATE TABLE blocked_signal_analysis (id INTEGER PRIMARY KEY); INSERT INTO blocked_signal_analysis DEFAULT VALUES;"
sqlite3 "${TRADES_DB}" "CREATE TABLE execution_qualities (id INTEGER PRIMARY KEY); INSERT INTO execution_qualities DEFAULT VALUES;"

sqlite3 "${AUDIT_DB}" "CREATE TABLE audit_log (id INTEGER PRIMARY KEY); INSERT INTO audit_log DEFAULT VALUES;"

touch "${LOGS_DIR}/test.log"
touch "${REPORTS_DIR}/test_report.pdf"
touch "${MODELS_DIR}/test_model.pt"

# 3. Run Backup and Verification Script
echo "[3/6] Running backup_verify.sh..."
export DB_FILES="${TRADES_DB} ${AUDIT_DB}"
export BACKUP_ROOT="${BACKUP_ROOT}"
export LOGS_DIR="${LOGS_DIR}"
export REPORTS_DIR="${REPORTS_DIR}"
export MODELS_DIR="${MODELS_DIR}"
export BACKUP_LOG="${TEST_DIR}/backup.log"

bash scripts/backup_verify.sh

# 4. Simulate Disaster (Delete databases)
echo "[4/6] Simulating disaster (deleting databases)..."
rm -f "${TRADES_DB}" "${AUDIT_DB}"
rm -rf "${LOGS_DIR}" "${REPORTS_DIR}"

# 5. Perform Restoration (Following docs/DISASTER_RECOVERY.md)
echo "[5/6] Performing restoration..."
LATEST_TRADES_BACKUP=$(ls -t "${BACKUP_ROOT}/db/trades_"*.db | head -1)
LATEST_AUDIT_BACKUP=$(ls -t "${BACKUP_ROOT}/db/audit_"*.db | head -1)
LATEST_LOGS_ARCHIVE=$(ls -t "${BACKUP_ROOT}/logs/logs_"*.tar.gz | head -1)
LATEST_REPORTS_ARCHIVE=$(ls -t "${BACKUP_ROOT}/reports/reports_"*.tar.gz | head -1)

echo "Restoring from: ${LATEST_TRADES_BACKUP}"
cp "${LATEST_TRADES_BACKUP}" "${TRADES_DB}"
echo "Restoring from: ${LATEST_AUDIT_BACKUP}"
cp "${LATEST_AUDIT_BACKUP}" "${AUDIT_DB}"

echo "Restoring logs from: ${LATEST_LOGS_ARCHIVE}"
mkdir -p "${LOGS_DIR}"
tar -xzf "${LATEST_LOGS_ARCHIVE}" -C "${LOGS_DIR}/"

echo "Restoring reports from: ${LATEST_REPORTS_ARCHIVE}"
mkdir -p "${REPORTS_DIR}"
tar -xzf "${LATEST_REPORTS_ARCHIVE}" -C "${REPORTS_DIR}/"

# 6. Verify Restored Data
echo "[6/6] Verifying restored data..."

# Verify Trades DB
TRADES_COUNT=$(sqlite3 "${TRADES_DB}" "SELECT count(*) FROM trades;")
if [ "${TRADES_COUNT}" -eq 1 ]; then
    echo "SUCCESS: trades table restored correctly."
else
    echo "FAILURE: trades table restoration failed."
    exit 1
fi

# Verify Audit DB
AUDIT_COUNT=$(sqlite3 "${AUDIT_DB}" "SELECT count(*) FROM audit_log;")
if [ "${AUDIT_COUNT}" -eq 1 ]; then
    echo "SUCCESS: audit_log table restored correctly."
else
    echo "FAILURE: audit_log table restoration failed."
    exit 1
fi

# Verify Files
if [ -f "${LOGS_DIR}/test.log" ] && [ -f "${REPORTS_DIR}/test_report.pdf" ]; then
    echo "SUCCESS: Log and report files restored correctly."
else
    echo "FAILURE: Log/Report file restoration failed."
    exit 1
fi

echo "=== Disaster Recovery Verification Completed Successfully ==="
rm -rf "${TEST_DIR}"
