# Enterprise Audit Traceability

The MT5 AI/ML Trading Bot features a robust, structured audit logging system designed for production traceability, regulatory compliance, and post-incident analysis.

## Overview

Unlike standard application logs, the **Audit Trail** captures high-integrity records of every critical decision made by the bot. This includes:
- **Signal Vetting:** Why a signal was approved or blocked by the `ExecutionFilter`.
- **Risk Evaluation:** The full 6-layer risk check results for every signal.
- **System Events:** Startup, shutdown, and configuration changes.

## Structured Metadata

Audit entries utilize a `metadata_json` column (SQLAlchemy JSON type) to store machine-readable context. This allows for complex querying and automated reporting.

### Signal Evaluation Schema (Risk Manager)
```json
{
  "signal_id": 123,
  "symbol": "XAUUSD",
  "direction": 1,
  "passed": false,
  "layers": {
    "circuit_breaker": true,
    "daily_loss": true,
    "max_positions": true,
    "symbol_allocation": true,
    "minimum_confidence": false,
    "risk_reward": true
  }
}
```

### Signal Vetting Schema (Execution Filter)
```json
{
  "signal_id": 123,
  "symbol": "XAUUSD",
  "approved": true,
  "layers": {
    "atr_volatility": true,
    "trend_angle": true,
    "ema_sequence": true,
    "momentum": true,
    "session_time": true,
    "drawdown_limit": true
  }
}
```

## How to Query

The audit trail is stored in the primary database (or a separate `audit.db` if PostgreSQL is not used).

### Using SQL
To find all trades rejected due to the "minimum_confidence" risk layer:
```sql
SELECT * FROM audit_log
WHERE actor = 'risk_manager'
AND metadata_json->'layers'->>'minimum_confidence' = 'false';
```

### Using Python (AuditLogger)
```python
from src.core.audit_log import AuditLogger, AuditEntry
from sqlalchemy import select

logger = AuditLogger.get_instance()
with logger.Session() as session:
    entries = session.scalars(
        select(AuditEntry).where(AuditEntry.actor == 'execution_filter')
    ).all()
```

## Policy Compliance
The audit system is a mandatory component for production readiness. Merges that modify core trading logic must ensure that corresponding decision layers are correctly reflected in the audit trail.
