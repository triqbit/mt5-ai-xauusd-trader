# 📈 Execution Filter Trading Logic

The `ExecutionFilter` implements an 11-layer validation cascade to vet institutional trading signals before execution. This ensures that every trade aligns with volatility, trend, momentum, and risk standards.

## 🛡️ The 11-Layer Cascade

### 1. ATR Volatility Threshold (`ATR_VOLATILITY`)
- **Purpose**: Prevents entering trades during extreme, erratic volatility.
- **Logic**: Compares the current ATR (Average True Range) to its 100-period average.
- **Threshold**: Blocks if `current_atr / average_atr > 3.0`.

### 2. Trend Angle Confirmation (`TREND_ANGLE`)
- **Purpose**: Ensures the trade direction aligns with the established price trend.
- **Logic**: Calculates the linear regression slope of the 21-period EMA over the last 20 bars.
- **Validation**:
  - **BUY**: Slope must be > 0.
  - **SELL**: Slope must be < 0.

### 3. EMA Sequence Check (`EMA_SEQUENCE`)
- **Purpose**: Validates institutional trend alignment using multiple time-weighted averages.
- **Logic**: Checks the vertical stack of EMA 8, 21, 50, and 200.
- **Validation**:
  - **BUY**: EMA 8 > EMA 21 > EMA 50 > EMA 200.
  - **SELL**: EMA 8 < EMA 21 < EMA 50 < EMA 200.

### 4. Momentum Filter (`MOMENTUM`)
- **Purpose**: Ensures the trade is entered during healthy momentum zones, avoiding overextended markets.
- **Logic**: Uses a 14-period RSI (Relative Strength Index).
- **Validation**:
  - **BUY**: 50 <= RSI <= 75.
  - **SELL**: 25 <= RSI <= 50.

### 5. Session/Time Filter (`SESSION_CLOSED`)
- **Purpose**: Limits trading to institutional hours when liquidity is highest.
- **Hours**: Sunday 17:00 GMT to Friday 16:00 GMT.
- **Logic**: Blocks all signals outside this window (including all of Saturday).

### 6. Drawdown Circuit Breaker (`DRAWDOWN_LIMIT`)
- **Purpose**: Protects the account from catastrophic losses.
- **Logic**: Monitors the current account drawdown.
- **Threshold**: Blocks all signals if `current_drawdown >= 12%`.

### 7. Model Stability (`MODEL_STABILITY`)
- **Purpose**: Prevents execution if model performance is degrading.
- **Logic**: Monitors model drift and accuracy against institutional thresholds.

### 8. Performance Guard (`PERFORMANCE_FLOOR`)
- **Purpose**: Halts trading if historical win rate falls below floor.
- **Logic**: Checks win rate over the last 20+ trades.

### 9. Confidence Threshold (`CONFIDENCE_THRESHOLD`)
- **Purpose**: Ensures only high-conviction signals are executed.
- **Logic**: Requires signal confidence to exceed minimum threshold (default 0.55).

### 10. Signal Consistency (`SIGNAL_FLICKER`)
- **Purpose**: Filters out rapidly alternating buy/sell signals.
- **Logic**: Analyzes signal history within a rolling window.

### 11. Macro Risk Gate (`MACRO_EVENT`)
- **Purpose**: Protects against high-impact macroeconomic events.
- **Logic**: Blocks trades during active high-impact news windows.

## 📊 Execution Decision Output

Every validation returns an `ExecutionDecision` object:

- `signal`: The original `TradeSignal`.
- `is_approved`: Boolean indicating if all layers passed.
- `confidence_score`: The model's confidence in the signal.
- `blocked_by`: The ID of the first layer that failed (e.g., `EMA_SEQUENCE`).
- `trace`: A detailed audit log of every layer's metrics (slopes, ratios, EMA values).
