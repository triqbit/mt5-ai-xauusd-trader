# Audit Logging & Traceability Policy

This document defines the enterprise audit trail schema and implementation requirements for the MT5 AI Trading Bot.

## 1. Overview
The Audit Trail provides a tamper-evident, permanent record of critical system events, decisions, and configuration changes. It is essential for compliance, incident response, and performance attribution.

## 2. Event Categories
The following categories are supported by the `AuditLogger`:

- **CONFIG:** Changes to environment variables, Pydantic settings, or runtime configuration.
- **RISK:** Decisions made by the `RiskManager`, including circuit breaker triggers and trade rejections.
- **MODEL:** Model inference events, confidence score alerts, and model loading/unloading.
- **OPERATOR:** Manual interventions, command-line arguments used, and startup/shutdown events.
- **RELEASE:** Deployment events, version bumps, and migration executions.

## 3. Data Schema
Audit entries are stored in the `audit_log` table:

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | Integer | Primary Key |
| `timestamp` | DateTime | UTC timestamp of the event |
| `category` | String | Event category (see above) |
| `event_type` | String | Specific event identifier |
| `actor` | String | Identity of the triggering component or user |
| `description` | Text | Human-readable explanation of the event |
| `metadata_json` | JSON | Structured data for automated analysis |

## 4. Implementation Guidelines
- **No Short-Circuiting in Risk:** The `RiskManager` must evaluate all risk filters and log the entire decision chain to the audit trail.
- **Initialization:** The `AuditLogger` must be initialized at application startup before any critical logic executes.
- **Immutability:** Audit records should never be deleted or modified. The `data_cleanup.py` script preserves audit records for a minimum of 2 years.

## 5. Retrieval & Analysis
Audit logs can be queried via standard SQL. For high-level reporting, use the `/health/readiness` endpoint or the built-in monitoring dashboards.
