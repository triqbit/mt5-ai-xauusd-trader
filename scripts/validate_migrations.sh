#!/bin/bash
set -e

# Use an ephemeral SQLite database for validation
# We use a distinct name to avoid clobbering production/dev databases
export DATABASE_URL="sqlite:///test_migrations_validation.db"

echo "🚀 Starting migration validation..."

# 1. Upgrade to head
echo "  - Upgrading to head..."
alembic -x db_url=$DATABASE_URL upgrade head

# 2. Check for missing migrations (sync check)
# Check if the 'check' command is available in this version of alembic
if alembic --help | grep -q "check"; then
    echo "  - Checking for out-of-sync models (alembic check)..."
    alembic -x db_url=$DATABASE_URL check
else
    echo "  - Skipping 'alembic check' (not supported by this version of alembic)"
fi

# 3. Reversibility check: Downgrade back to base
echo "  - Testing reversibility (downgrading to base)..."
alembic -x db_url=$DATABASE_URL downgrade base

# 4. Re-upgrade to head to ensure clean state
echo "  - Re-upgrading to head..."
alembic -x db_url=$DATABASE_URL upgrade head

# Cleanup
if [ -f "test_migrations_validation.db" ]; then
    rm test_migrations_validation.db
fi

echo "✅ Migration validation completed successfully."
