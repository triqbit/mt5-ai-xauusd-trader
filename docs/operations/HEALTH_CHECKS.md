# Enterprise Health Check System

## Overview

The MT5 Trading Bot implements a multi-tiered, enterprise-grade health check system to ensure operational reliability, production safety, and observability. This system is centered around the `HealthChecker` class in `src/core/health.py` and is integrated into the application startup sequence and production monitoring API.

## Core Components

### 1. HealthChecker

The `HealthChecker` performs deep diagnostics across several dimensions:

-   **Liveness**: Heartbeat check to confirm the process is active and responsive.
-   **Readiness**: Aggregates all dependency and resource checks to determine if the bot is ready to handle trading operations.
-   **Dependency Health**:
    -   **Database**: Validates reachability of the primary trade database.
    -   **MT5/MetaAPI**: Verifies connection status, account permissions, and symbol tradability.
    -   **Models**: Ensures required AI model weights (PPO, LSTM, Transformer, etc.) are loaded in memory.
    -   **Audit Log**: Verifies initialization of the enterprise audit trail.
-   **System Resources**:
    -   **CPU Usage**: Monitors CPU utilization with non-blocking checks.
    -   **Memory**: Monitors RAM availability.
    -   **Disk Space**: Ensures the log directory has sufficient space for operation.
-   **Environment**: Reports OS, Python version, and hardware acceleration (CUDA/MPS/CPU).
-   **Configuration**: Runs the `ConfigValidator` to ensure `.env` and runtime settings are valid.
-   **Resilience (Circuit Breakers)**: Monitors the state of internal circuit breakers (e.g., MT5Connector) to detect persistent failures.

### 2. Resilience and Self-Healing

The bot implements advanced resilience patterns to handle transient and persistent failures:

#### Circuit Breaker Pattern
Integrated into the `MT5Connector`, the Circuit Breaker prevents the system from repeatedly attempting failed operations during broker downtime or network instability.
- **States**: `CLOSED` (Normal), `OPEN` (Failures detected, requests blocked), `HALF_OPEN` (Testing for recovery).
- **Threshold**: Trips after 5 consecutive connection or data retrieval failures.
- **Recovery**: Automatically attempts to probe the connection after a 60-second cooldown.

### 3. Startup Health Gate

The bot enforces a "fail-fast" policy through the `startup_gate()` method. During initialization, the application executes all critical health checks. If any mandatory dependency (MT5, Database, Models, Config) fails, the application raises a `RuntimeError` and refuses to start. This prevents "ghost" deployments where the bot runs but is unable to trade or log data correctly.

### 3. Monitoring API

A FastAPI-based micro-app provides standardized endpoints for production monitoring (e.g., Kubernetes, Datadog, Prometheus):

-   **`/health/liveness`**: Returns `200 OK` if the process is alive.
-   **`/health/readiness`**: Returns `200 OK` with a full report if all critical checks pass, or `503 Service Unavailable` if any check fails.
-   **`/health/full`**: Provides a detailed JSON report of all components, messages, and suggested remedies.
-   **`/metrics`**: Exposes Prometheus metrics for component health gauges.

## Prometheus Metrics

The system exports health status as gauges under the `system_component_health` metric:

-   **1.0**: Healthy
-   **0.5**: Degraded (Warnings present, but still operational)
-   **0.0**: Failed (Critical dependency down)

Labels are used to distinguish components: `liveness`, `database`, `mt5`, `models`, `config`, `disk`, `redis`, `audit_log`, and `system_resources`.

## Operational Use

### Pre-flight Check
You can manually trigger a full health diagnostic using the CLI:
```bash
python main.py --check
```

### Local Development
The health API can be started independently for testing or monitoring:
```python
from src.core.health import create_health_app
app = create_health_app()
# Run with uvicorn
```
