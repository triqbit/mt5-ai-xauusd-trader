# Enterprise Health Checks

The MT5 AI/ML Trading Bot includes an enterprise-grade health check system for production monitoring and startup gating.

## Endpoints

The health check endpoints are exposed via FastAPI (default port 8000, prefix `/health`). The system also includes a standalone metrics endpoint (`GET /metrics`) for Prometheus monitoring.

### 1. Liveness Probe (`GET /health/liveness`)
**Purpose:** Indicates if the application process is alive.
- **Success (200 OK):** Application is running.
- **Use case:** Kubernetes liveness probe to restart "hung" containers.

### 2. Readiness Probe (`GET /health/readiness`)
**Purpose:** Indicates if the application is ready to handle trading requests.
- **Success (200 OK):** All critical components (MT5, Database, Models, Audit Log) are healthy.
- **Failure (503 Service Unavailable):** One or more critical components failed.
- **Use case:** Kubernetes readiness probe, Load Balancer health check.

### 3. Full Report (`GET /health/full`)
**Purpose:** Provides a detailed breakdown of all system components.
- **Status:** `healthy`, `degraded`, or `failed`.
- **Components tracked:**
    - `liveness`: Process status.
    - `database`: Primary trade database connectivity.
    - `mt5`: MetaTrader 5 terminal/cloud connection.
    - `models`: Loading status of AI models (PPO, LSTM, Dreamer).
    - `config`: Environment and risk limit validation.
    - `disk`: Sufficient space in the `logs/` directory.
    - `redis`: (Optional) Redis cache connectivity.
    - `audit_log`: Enterprise traceability initialization.

## Startup Health Gate

The application performs a mandatory full health check during startup (`main.py`) using the `HealthChecker.startup_gate()` method.

- **CRITICAL FAILURE:** If any component returns a `FAILED` status, the application will log a `CRITICAL` error and refuse to start (exit code 1). The gate returns a `HealthReport` which is reused to display diagnostic information without re-running expensive checks.
- **DEGRADED STATUS:** If components return a `DEGRADED` status (e.g., optional Redis unreachable), the application will log a `WARNING` but continue to start.

## Prometheus Metrics

Health status is exported to Prometheus via the `system_component_health` gauge.
- `1.0`: Healthy
- `0.5`: Degraded
- `0.0`: Failed

Labels: `component` (e.g., `mt5`, `database`).
