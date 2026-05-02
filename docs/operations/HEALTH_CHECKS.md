# Enterprise Health Monitoring System

The MT5 Trading Bot implements an enterprise-grade health monitoring system to ensure operational reliability and production safety.

## Architecture

The system is centered around the `HealthChecker` class in `src/core/health.py`. It provides a FastAPI router that exposes several monitoring endpoints.

### Endpoints

- **GET /health/liveness**: Returns a simple 200 OK if the application process is running. Used by container orchestrators to detect deadlocks or crashes.
- **GET /health/readiness**: Performs a comprehensive check of all critical dependencies. Returns 200 OK only if the system is fully ready to trade. Returns 503 Service Unavailable if any critical component has FAILED.
- **GET /health/full**: Returns a detailed report of all component statuses, regardless of their health level.
- **GET /metrics**: (Integrated via Prometheus client) Exports real-time health gauges for monitoring and alerting.

## Monitored Components

The following components are tracked with three possible states: `HEALTHY`, `DEGRADED`, and `FAILED`.

### 1. Database
- **Check**: Verifies connectivity to the SQLAlchemy-backed database.
- **Criticality**: FAILED if unreachable.

### 2. MT5 Connector
- **Check**: Verifies if the MetaTrader 5 terminal (or MetaAPI fallback) is initialized and active.
- **Criticality**: FAILED if connection is down.

### 3. ML Model Ensemble
- **Check**: Verifies that the PPO, LSTM, and Dreamer models are correctly loaded.
- **States**:
  - `HEALTHY`: All 3 models loaded.
  - `DEGRADED`: At least one but not all models loaded.
  - `FAILED`: No models loaded.

### 4. Redis
- **Check**: Verifies connectivity to the Redis cache (if configured).
- **States**:
  - `DEGRADED`: Redis client not installed.
  - `FAILED`: Redis server unreachable.

### 5. Configuration
- **Check**: Runs the `ConfigValidator` to ensure the current environment variables are valid and safe for the selected mode.
- **Criticality**: FAILED if critical validation errors are found.

### 6. Disk Space
- **Check**: Ensures the `logs/` directory has at least 100MB of free space.
- **Criticality**: FAILED if space is below threshold.

## Startup Health Gate

The `main.py` entry point includes a mandatory health gate. On startup:
1. All health checks are executed.
2. The results are displayed in a formatted table.
3. If the overall status is **FAILED**, the application logs a `CRITICAL` error and exits immediately (status code 1).
4. If the status is **DEGRADED**, the application logs a `WARNING` but is permitted to continue.

## Prometheus Integration

The following gauges are updated on every health check:
- `health_liveness_status`
- `health_database_status`
- `health_mt5_status`
- `health_models_status`
- `health_config_status`
- `health_disk_status`
- `health_redis_status`
- `health_overall_status`

Status values are mapped to: `HEALTHY` = 1.0, `DEGRADED` = 0.5, `FAILED` = 0.0.
