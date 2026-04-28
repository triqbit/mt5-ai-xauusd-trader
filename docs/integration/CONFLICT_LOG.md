# Cross-Agent Conflict Log

## [2024-05-22] - Initial Audit

### 1. Logic Fragmentation in `main.py`
- **Affected Files**: `main.py`
- **Agents**: Jules01 (Implementation), Jules02 (Observability)
- **Priority**: High
- **Impact**: System runs `run_live` twice if in demo/live mode. Second call lacks `trade_logger`. `RiskManager` is initialized twice, once with logger and once with monitor, causing potential loss of monitoring or logging capabilities.
- **Resolution Plan**: Unify `RiskManager` initialization to include both `trade_logger` and `monitor`. Ensure `run_live` is called only once with all components.
- **Owner**: Jules05 (Harmonization)

### 2. Assumption Drift in `RiskManager` Confidence Threshold
- **Affected Files**: `src/trading/risk_manager.py`, `src/core/config.py`
- **Agents**: Jules01 (Risk Engine), Jules02 (Config Management)
- **Priority**: Medium
- **Impact**: `RiskManager` uses a hardcoded 0.55 threshold, while `TradingConfig` defines 0.6. This leads to inconsistent signal rejection.
- **Resolution Plan**: Update `RiskManager._check_minimum_confidence` to use `self.cfg.confidence_threshold`.
- **Owner**: Jules05 (Harmonization)

### 3. Inconsistent Logging in `gym_env.py`
- **Affected Files**: `src/environment/gym_env.py`
- **Agents**: Jules01 (Environment)
- **Priority**: Low
- **Impact**: `TradingEnv.render` uses `print()` which bypasses the structured logging system configured in `main.py`.
- **Resolution Plan**: Replace `print()` with `logger.info()`.
- **Owner**: Jules05 (Harmonization)
