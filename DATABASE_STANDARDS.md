# Database Standards for MT5 AI/ML Trading Bot

## 1. Schema Design & Architecture

### 1.1 Database Technology Stack
- **Primary Database**: PostgreSQL 13+ (ACID compliance, JSON support, range types)
- **Time-Series Data**: TimescaleDB extension for high-frequency trading data
- **Caching Layer**: Redis 6.0+ for real-time market data and model predictions
- **Data Warehouse**: ClickHouse for analytics and backtesting data
- **Backup**: AWS S3 or equivalent for disaster recovery

### 1.2 Schema Normalization
- **Normalization Level**: 3rd Normal Form (3NF) minimum
- **Denormalization**: Only for proven performance bottlenecks with documented justification
- **Key Constraints**: 
  - All tables must have primary keys
  - Foreign key constraints enforced at database level
  - Unique constraints on natural keys where applicable

### 1.3 Audit Trail
Every table must include:
```sql
CREATE TABLE market_data (
  id BIGSERIAL PRIMARY KEY,
  symbol VARCHAR(20) NOT NULL,
  timeframe VARCHAR(10) NOT NULL,
  open_price DECIMAL(12,5) NOT NULL,
  close_price DECIMAL(12,5) NOT NULL,
  volume BIGINT NOT NULL,
  
  -- Audit columns (mandatory)
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  created_by VARCHAR(100),
  updated_by VARCHAR(100),
  
  -- Soft delete
  deleted_at TIMESTAMPTZ,
  is_deleted BOOLEAN DEFAULT FALSE,
  
  CONSTRAINT check_prices CHECK (open_price > 0 AND close_price > 0),
  CONSTRAINT check_volume CHECK (volume >= 0)
);

CREATE INDEX idx_market_data_symbol_timeframe 
  ON market_data(symbol, timeframe, created_at DESC);
CREATE INDEX idx_market_data_created_at 
  ON market_data(created_at DESC);
```

### 1.4 Table Partitioning Strategy
For high-volume tables:
- **Partition by**: Time (daily for OHLCV, hourly for ticks)
- **Retention Policy**: 
  - Tick data: 3 months
  - OHLCV data: 5+ years
  - Trade logs: 7 years (regulatory)
  - Model training data: Indefinite

## 2. Query Standards & Performance

### 2.1 Query Best Practices
```sql
-- GOOD: Explicit columns, parameterized queries
SELECT symbol, timeframe, close_price, volume
FROM market_data
WHERE symbol = $1 
  AND timeframe = $2
  AND created_at >= $3
  AND is_deleted = FALSE
ORDER BY created_at DESC
LIMIT 1000;

-- BAD: SELECT *, implicit joins, missing indexes
SELECT * FROM market_data, trades 
WHERE market_data.id = trades.market_data_id;
```

### 2.2 Index Strategy
- **Query Analysis**: Use EXPLAIN ANALYZE for all new queries
- **Index Types**:
  - B-tree: Default for equality and range queries
  - Hash: For exact equality matches only
  - GiST: For geographic/range queries
  - BRIN: For sorted data (time-series)
- **Avoid Over-indexing**: Maximum 5-7 indexes per table

### 2.3 Connection Management
```python
# Good: Connection pooling
from sqlalchemy import create_engine

engine = create_engine(
    'postgresql://user:password@localhost/trading_db',
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,  # Verify connections are alive
    pool_recycle=3600,   # Recycle connections every hour
    echo=False
)

# All database operations use this engine
connection = engine.connect()
```

### 2.4 Transaction Handling
```python
def save_trade_execution(trade_data):
    """Save trade with transaction integrity."""
    try:
        with engine.begin() as conn:
            # Insert trade record
            trade_id = conn.execute(
                "INSERT INTO trades (symbol, side, volume, price, status) "
                "VALUES ($1, $2, $3, $4, $5) RETURNING id",
                [trade_data.symbol, trade_data.side, 
                 trade_data.volume, trade_data.price, 'PENDING']
            ).scalar()
            
            # Update account balance (atomic with trade)
            conn.execute(
                "UPDATE accounts SET balance = balance - $1 "
                "WHERE id = $2",
                [trade_data.cost, trade_data.account_id]
            )
            
            return trade_id
    except Exception as e:
        # Transaction auto-rolled back by context manager
        logger.error(f"Trade execution failed: {str(e)}")
        raise
```

## 3. Data Integrity & Validation

### 3.1 Constraint Types
```sql
-- Domain constraints
ALTER TABLE trading_orders ADD CONSTRAINT check_volume_positive 
  CHECK (volume > 0);

-- Not null constraints
ALTER TABLE market_data ALTER COLUMN close_price SET NOT NULL;

-- Unique constraints for business rules
ALTER TABLE api_keys ADD CONSTRAINT uq_api_key_user 
  UNIQUE (user_id, provider);

-- Referential integrity
ALTER TABLE trades ADD CONSTRAINT fk_trades_account 
  FOREIGN KEY (account_id) REFERENCES accounts(id) 
  ON DELETE RESTRICT ON UPDATE CASCADE;
```

### 3.2 Data Validation Rules
- **Prices**: Must be positive, reasonable bounds (e.g., 0.01 - 10,000 for XAUUSD)
- **Volumes**: Must be positive, comply with broker limits
- **Timestamps**: Must be in valid range, not in future
- **Status Values**: Must be from predefined enum set
- **Risk Metrics**: Must comply with position sizing rules

### 3.3 Regular Consistency Checks
```sql
-- Check for orphaned records
SELECT t.id FROM trades t 
LEFT JOIN accounts a ON t.account_id = a.id 
WHERE a.id IS NULL;

-- Verify account balance calculation
SELECT account_id, SUM(profit_loss) as calculated_balance 
FROM trade_history 
GROUP BY account_id 
HAVING SUM(profit_loss) != (
  SELECT balance FROM accounts WHERE id = account_id
);

-- Check for duplicate trades
SELECT symbol, entry_time, COUNT(*) 
FROM trades 
GROUP BY symbol, entry_time 
HAVING COUNT(*) > 1;
```

## 4. Backup & Disaster Recovery

### 4.1 Backup Strategy
- **Frequency**: 
  - Full backup: Daily (non-business hours)
  - Incremental: Every 6 hours
  - Transaction logs: Continuous archiving
- **Retention**: 
  - Daily backups: 30 days
  - Weekly backups: 90 days
  - Monthly backups: 1 year
- **Location**: Geographically distributed (primary + 2 replicas)

### 4.2 Backup Procedure
```bash
#!/bin/bash
# Daily PostgreSQL backup script

BACKUP_DIR="/backups/trading_db"
DB_NAME="mt5_trading"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Full backup
pg_dump -Fc -v -U postgres $DB_NAME > \
  $BACKUP_DIR/full_backup_$TIMESTAMP.dump

# Compress
gzip $BACKUP_DIR/full_backup_$TIMESTAMP.dump

# Upload to S3
aws s3 cp $BACKUP_DIR/full_backup_$TIMESTAMP.dump.gz \
  s3://trading-backups/daily/

# Verify backup integrity
pg_restore -l $BACKUP_DIR/full_backup_$TIMESTAMP.dump | wc -l

# Cleanup old backups (keep 30 days)
find $BACKUP_DIR -name "*.dump.gz" -mtime +30 -delete
```

### 4.3 Recovery Testing
- **Frequency**: Monthly full recovery test
- **Procedure**: Restore to test environment, verify data integrity
- **Documentation**: Maintain recovery runbook with tested commands
- **RTO Target**: < 4 hours
- **RPO Target**: < 1 hour

## 5. Database Monitoring & Maintenance

### 5.1 Performance Monitoring Metrics
```sql
-- Monitor table sizes
SELECT 
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
  n_live_tup as row_count,
  last_vacuum,
  last_autovacuum
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Monitor index performance
SELECT 
  schemaname,
  tablename,
  indexname,
  idx_scan,
  idx_tup_read,
  idx_tup_fetch,
  pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

-- Monitor slow queries
SELECT 
  query,
  calls,
  mean_time,
  max_time,
  total_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 20;
```

### 5.2 Maintenance Tasks
- **VACUUM**: Daily (auto-enabled), full vacuum weekly
- **ANALYZE**: After bulk loads, updates to pg_stat
- **REINDEX**: Monthly check for bloat, rebuild if > 30%
- **CLUSTER**: Quarterly reorganization of heavily queried tables

### 5.3 Alert Thresholds
- **Disk Space**: Alert at 80%, critical at 95%
- **Connection Count**: Alert at 80% of max_connections
- **Query Time**: Alert if slow query > 10 seconds
- **Lock Wait**: Alert if transaction wait > 5 seconds
- **Replication Lag**: Alert if > 1 second

## 6. Security & Access Control

### 6.1 Database Users & Privileges
```sql
-- Application user (restricted)
CREATE ROLE app_user WITH LOGIN PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE mt5_trading TO app_user;
GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO app_user;
REVOKE DELETE, TRUNCATE ON ALL TABLES IN SCHEMA public FROM app_user;

-- Read-only user for analytics
CREATE ROLE analytics_user WITH LOGIN PASSWORD 'secure_password';
GRANT SELECT ON ALL TABLES IN SCHEMA public TO analytics_user;

-- Admin user (restricted access, audit all actions)
CREATE ROLE admin_user WITH LOGIN PASSWORD 'secure_password' SUPERUSER;
```

### 6.2 Data Encryption
- **Encryption at Rest**: Enable in PostgreSQL or storage layer
- **Encryption in Transit**: TLS 1.2+ for all connections
- **Sensitive Fields**: Encrypt API keys, account numbers, passwords
```python
from cryptography.fernet import Fernet

cipher = Fernet(encryption_key)

def save_api_key(user_id, api_key, provider):
    encrypted_key = cipher.encrypt(api_key.encode())
    db.insert('api_keys', {
        'user_id': user_id,
        'provider': provider,
        'encrypted_key': encrypted_key
    })
```

### 6.3 Access Audit Logging
```sql
-- Create audit table
CREATE TABLE audit_log (
  id BIGSERIAL PRIMARY KEY,
  table_name VARCHAR(100),
  operation VARCHAR(10), -- SELECT, INSERT, UPDATE, DELETE
  user_name VARCHAR(100),
  timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
  old_values JSONB,
  new_values JSONB,
  query TEXT
);

-- Enable auditing
CREATE TRIGGER audit_trades_changes
AFTER INSERT OR UPDATE OR DELETE ON trades
FOR EACH ROW
EXECUTE FUNCTION audit_trigger_func();
```

## 7. Data Quality Standards

### 7.1 Data Completeness
- **Required Fields**: All NOT NULL fields must have values
- **Historical Data**: Must be validated before import
- **Real-Time Data**: Validation on receipt from data provider

### 7.2 Data Accuracy
- **Price Validation**: Spot check against market feed
- **Volume Validation**: Compare with exchange reports
- **Reconciliation**: Daily reconciliation of trades with MT5 platform

### 7.3 Data Freshness
- **Market Data**: Updated within 1-5 seconds
- **Trade Data**: Updated immediately upon execution
- **Account Data**: Updated within 10 seconds
- **Stale Data Alert**: Trigger if no update received in 60 seconds

## 8. Query Optimization Checklist

- [ ] EXPLAIN ANALYZE reviewed for all queries
- [ ] Appropriate indexes created and tested
- [ ] Query execution time < 1 second (typical)
- [ ] Connection pooling configured
- [ ] N+1 query problem identified and resolved
- [ ] Prepared statements used for all dynamic queries
- [ ] No SELECT * without WHERE clause
- [ ] Batch operations used for bulk inserts/updates
- [ ] Cache strategy implemented for frequently accessed data

---

**Last Updated**: January 2026
**Version**: 1.0
**Maintained By**: Infrastructure Team
**Review Frequency**: Quarterly
