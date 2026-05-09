# Enterprise Health Monitoring System

This document outlines the production health monitoring infrastructure for the MT5 AI/ML Trading Bot.

## 1. Overview

The system implements enterprise-grade monitoring aligned with Service Level Objectives (SLOs). It provides automated probes for orchestration (Kubernetes/Docker) and detailed status for human operators.

## 2. Health Endpoints

The monitoring API is available at `/health` (default port 8000).

| Endpoint | Purpose | Target | Response Code |
|----------|---------|--------|---------------|
| `/health/liveness` | Process Heartbeat | Orchestrators | 200 (Active) |
| `/health/readiness` | Dependency Check | Load Balancers | 200 (Ready), 503 (Failed) |
| `/health/full` | Detailed Status | Operators | 200 (JSON Report) |
| `/metrics` | Prometheus Export | Grafana/Alertmanager | 200 (Metrics) |

## 3. Components Monitored

1.  **Liveness**: Process status and responsiveness.
2.  **Environment**: OS, Python version, and Hardware acceleration (GPU/CPU).
3.  **Database**: Connectivity to the primary SQL database.
4.  **MT5 Connector**: Connection to MetaTrader terminal or MetaAPI cloud, including terminal `algo_trading` status.
5.  **Models**: Verification that AI models (PPO, LSTM, Dreamer) are loaded and reporting metrics.
6.  **Config**: Validation of current environment variables against enterprise safety bounds.
7.  **Disk Space**: Verification that sufficient space remains for audit logs.
8.  **Redis**: Connectivity to the optional cache layer.
9.  **Audit Log**: Verification that the traceability layer is active.

## 4. Startup Health Gate

The application implements a mandatory startup gate. If any **CRITICAL** dependency check fails (Database, MT5, Config, Models), the application will refuse to start and log a failure event to the audit trail.

## 5. Prometheus Metrics

The system exports health status for all components as Gauges:
- `system_component_health{component="..."}`
  - `1.0`: Healthy
  - `0.5`: Degraded (Warning)
  - `0.0`: Failed (Critical)

## 6. Audit Trail Integration

All health gate transitions (Success, Warning, Failure) are recorded in the `audit_log` table for compliance and incident post-mortems.

## 7. Structured Observability

To ensure high-fidelity failure attribution and trace correlation, critical path components use structured logging via `structlog`:

- **Circuit Breaker**: Transitions between `CLOSED`, `OPEN`, and `HALF_OPEN` states are logged with full context (name, failure counts, and errors).
- **MT5 Connector**: All connection attempts, data retrieval failures, and order execution events are logged with structured fields (server, login, error codes, tickets).
- **Trace Correlation**: Every log entry generated during a trading cycle iteration includes a unique `trace_id` for end-to-end debugging.
