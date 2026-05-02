# 6-Layer Execution Filter

Implementation of the institutional-grade execution filter cascade.

## Validation Layers
1. **ATR Volatility**: Prevents entry during extreme volatility.
2. **Trend Angle**: Confirms the trend matches signal direction using regression.
3. **EMA Sequence**: Verifies the EMA stack (8, 21, 50, 200).
4. **Momentum**: Ensures RSI is in a healthy momentum zone.
5. **Session/Time**: Restricts trading to institutional GMT hours.
6. **Drawdown**: Hard circuit breaker for account protection.
