# 📜 Enterprise Audit Trail Framework

This document details the structured audit logging system designed for institutional compliance, traceability, and post-incident review.

## 🎯 Objectives
- **Attributability**: Every system decision is linked to an actor (system, risk_engine, deployer, ai_model).
- **Traceability**: Full decision chains for blocked trades and risk rejections.
- **Compliance**: Immutable log of configuration changes and deployment events.
- **Debugging**: Structured metadata for model predictions and runtime volatility.

## 🏗️ Audit Events

The `AuditLogger` (src/core/audit_log.py) implements the following structured events:

| Event Action | Actor | Description | Key Metadata |
| :--- | :--- | :--- | :--- |
| `config_change` | `system` | Captures changes to trading parameters. | `old_config`, `new_config` |
| `trade_blocked` | `risk_engine` | Details why a trade was rejected by filters. | `symbol`, `reason`, `decision_chain` |
| `prediction` | `ai_model` | Records model signal generation. | `symbol`, `direction`, `confidence`, `volatility` |
| `risk_decision` | `risk_engine` | Full risk engine approval/rejection chain. | `passed`, `decision_chain` |
| `deployment` | `deployer` | Release events and startup status. | `version`, `environment`, `status` |
| `mode_entry` | `system` | Transitions between demo, live, or backtest. | `mode`, `symbol` |

## 📊 Database Schema

Audit entries are persisted in the `audit_log` table (default: `audit.db` or primary PostgreSQL).

- `id`: Primary key.
- `created_at`: Timestamp (UTC).
- `actor`: Entity performing the action.
- `action`: Type of audit event.
- `details`: Human-readable summary.
- `metadata_json`: Machine-readable structured data.

## 🛠️ Usage for Post-Incident Review

To extract the decision chain for a specific symbol failure:

```sql
SELECT created_at, details, metadata_json
FROM audit_log
WHERE actor = 'risk_engine' AND action = 'trade_blocked' AND metadata_json->>'symbol' = 'XAUUSD'
ORDER BY created_at DESC;
```

---
*Maintained by Release Reliability & Governance (Jules03)*
