#!/bin/bash

# ==============================================================================
# Automated Dependency Audit Script
# ==============================================================================
# This script performs:
# 1. Outdated package check (pip list --outdated)
# 2. Security vulnerability scan (pip-audit)
#
# Usage:
#   bash scripts/dependency_check.sh [requirements_file]
#
# If no requirements file is provided, it defaults to requirements.txt.
# ==============================================================================

set -e

REQUIREMENTS_FILE=${1:-requirements.txt}

if [ ! -f "$REQUIREMENTS_FILE" ]; then
    echo "Error: Requirements file '$REQUIREMENTS_FILE' not found."
    exit 1
fi

echo "=============================================================================="
echo "Checking for outdated packages in $REQUIREMENTS_FILE..."
echo "=============================================================================="
# Filter out warnings and only show the table
pip list --outdated --format columns

echo ""
echo "=============================================================================="
echo "Scanning for security vulnerabilities in $REQUIREMENTS_FILE..."
echo "=============================================================================="
if ! command -v pip-audit &> /dev/null; then
    echo "pip-audit not found. Installing..."
    pip install pip-audit
fi

# Run pip-audit on the requirements file
pip-audit -r "$REQUIREMENTS_FILE"

echo ""
echo "=============================================================================="
echo "Dependency audit complete."
echo "=============================================================================="
