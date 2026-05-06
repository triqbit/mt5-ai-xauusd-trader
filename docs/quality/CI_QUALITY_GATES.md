# CI Quality Gates

This document outlines the automated quality gates enforced in the CI pipeline to maintain system integrity and reliability.

## Database Schema Drift Detection

To prevent production runtime errors caused by missing database migrations, the CI pipeline enforces a **Schema Drift Check**.

### How it works:
1. The CI environment initializes a fresh database using `alembic upgrade head`.
2. It then runs `alembic check`.
3. If any SQLAlchemy models have been modified without a corresponding Alembic migration being generated, the check fails.

### How to resolve a failure:
If your PR fails this gate, you likely modified a file in `src/core/trade_logger.py` or other model-defining files. You must generate a migration:

```bash
# 1. Ensure your local environment is up to date
PYTHONPATH=. alembic upgrade head

# 2. Generate the migration
PYTHONPATH=. alembic revision --autogenerate -m "describe your changes"

# 3. Commit the new migration file in migrations/versions/
```

## Dependency Harmonization

The project maintains multiple requirements files (`requirements.txt`, `requirements-ci.txt`, etc.). The CI pipeline validates that these dependencies are consistent and free of conflicts.

### Key Policies:
- **Pinned Versions**: All core dependencies must use exact pinned versions (`==`).
- **Conflict Resolution**: Conflicts (e.g., Starlette/FastAPI version mismatches) must be resolved by aligning all requirements files to a compatible, security-vetted version.
