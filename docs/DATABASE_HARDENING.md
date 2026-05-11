# SQLite Hardening and Database Reliability

To ensure enterprise-grade reliability when using SQLite in the MT5 Trading Bot, the following hardening measures have been implemented in `src/core/database.py`.

## 1. Foreign Key Enforcement
SQLite has foreign key support but disables it by default for backward compatibility. We enable it on every connection using:
```sql
PRAGMA foreign_keys = ON;
```
This ensures referential integrity across our relational schema (e.g., preventing `ExecutionQuality` records from existing without a corresponding `Trade`).

## 2. Write-Ahead Logging (WAL) Mode
We enable WAL mode to improve concurrency and durability:
```sql
PRAGMA journal_mode = WAL;
```
Benefits:
- **Concurrency**: Readers do not block writers and writers do not block readers. This is critical for a trading bot where logging and execution analysis shouldn't block real-time trade updates.
- **Performance**: WAL is significantly faster in most scenarios as it reduces the number of disk writes for transactions.
- **Resilience**: Improved resistance to database corruption during power failures or system crashes.

## 3. Implementation Details
The hardening is applied via SQLAlchemy event listeners to the `Engine` object, ensuring that every connection in the pool is correctly configured before use.

```python
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    import sqlite3
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()
```

## 4. Verification
Relational integrity and pragma settings are verified by `tests/test_sqlite_hardening.py`.
