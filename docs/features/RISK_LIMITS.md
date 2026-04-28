# Hard Risk Limits & Circuit Breakers: MT5 Trading Bot

## Executive Summary

Defines immutable hard limits and automatic circuit breakers to protect capital, prevent catastrophic losses, and ensure system safety. These limits should be enforced at multiple levels with NO manual override capability for critical safeguards.

## 1. Position-Level Limits

### 1.1 Per-Trade Limits
- **Max Position Size**: 10% of account equity per trade
- **Min Position Size**: 0.01 lot (prevent rounding errors)
- **Max Leverage**: 10:1 (conservative for gold trading)
- **Lot Size Increment**: 0.01 lot minimum
- **Concurrent Positions**: Maximum 5 open positions
- **Validation**: All positions checked against limits before execution

### 1.2 Exposure Limits
- **Single Direction**: Max 30% net long OR short
- **Total Notional**: <100% of account equity
- **Margin Utilization**: <80% of available margin
- **Margin Alert**: Alert at 70%, halt trading at 80%
- **Forced Liquidation**: Automatic close at 90% margin

### 1.3 Risk Per Trade
- **Max Risk**: 1% of account per trade
- **Risk Calculation**: (Entry - Stop Loss) * Position Size / Account Equity
- **Validation**: Verify risk before order submission
- **Rejection**: Reject orders exceeding risk limit

## 2. Daily Limits

### 2.1 Daily Loss Limits (Cascading)
- **Level 1 (Yellow Alert)**: 2% loss → Alert to trader
- **Level 2 (Orange Alert)**: 3% loss → Reduce position size to 50%
- **Level 3 (Red Alert)**: 4% loss → Reduce to 25% position size
- **Level 4 (Emergency Stop)**: 5% loss → HALT ALL TRADING
- **Hard Stop**: 6% loss → Force close all positions
- **Recovery**: Reset at 00:00 UTC daily

### 2.2 Daily Win Limits (Risk Management)
- **Daily Win Cap**: 10% (prevents over-leverage after winning day)
- **Action**: Reduce leverage by 50% after 10% daily gain
- **Recovery**: Restore leverage at 00:00 UTC
- **Rationale**: Prevents overconfidence and excessive risk

### 2.3 Daily Trade Limits
- **Max Trades**: 20 trades per day
- **Max Winning Streaks**: Alert after 5 consecutive wins
- **Max Losing Streaks**: Halt trading after 3 consecutive losses
- **Consecutive Losses**: Reset at daily close (00:00 UTC)

## 3. Weekly/Monthly Limits

### 3.1 Weekly Limits
- **Max Weekly Loss**: 10% of account
- **Weekly Win Target**: 5-10% (reasonable target)
- **Reset**: Sunday 00:00 UTC
- **Action on Max Loss**: Require manager approval to trade next week

### 3.2 Monthly Limits
- **Max Monthly Loss**: 15% of account
- **Monthly Return Target**: 5-10% (realistic)
- **Reset**: First day of month
- **Action on Breach**: Freeze account pending review

## 4. Model & Prediction Limits

### 4.1 Prediction Confidence
- **Min Confidence**: 0.55 (55% predicted probability)
- **Low Confidence**: 0.50-0.55 → Skip trade (too risky)
- **Medium Confidence**: 0.55-0.65 → 50% position size
- **High Confidence**: 0.65-0.75 → 100% position size
- **Very High Confidence**: >0.75 → 100% position size (max)

### 4.2 Model Performance
- **Accuracy Floor**: If accuracy <50%, halt trading
- **Win Rate Floor**: If win rate <45%, reduce position size to 25%
- **Drift Threshold**: If model drift >0.3, retrain immediately
- **Daily Retraining**: Update model daily with latest data

### 4.3 Prediction Diversity
- **Ensemble Diversity**: Require 3+ models agreeing
- **Model Dissent**: If 2 models strongly disagree, skip trade
- **Consensus Threshold**: Need 60%+ agreement across ensemble
- **Veto Power**: Any model with <40% confidence forces skip

## 5. Market Condition Limits

### 5.1 Volatility Thresholds
- **Normal Volatility**: Trade at 100% position size
- **High Volatility (>1.5x normal)**: Reduce to 75% position size
- **Very High Volatility (>2x normal)**: Reduce to 50% position size
- **Extreme Volatility (>3x normal)**: HALT ALL TRADING
- **Measurement**: 14-period ATR compared to 30-day average

### 5.2 Liquidity Thresholds
- **Min Bid-Ask Spread**: <0.5 pips (normal market)
- **Alert**: If spread >1.0 pip
- **Reduce Position**: If spread >1.5 pips (use 50% sizing)
- **Halt Trading**: If spread >2.0 pips (insufficient liquidity)

### 5.3 News Event Protection
- **High Impact News**: 1 hour before/after → Reduce to 50% sizing
- **Medium Impact News**: 30 min before/after → Reduce to 75% sizing
- **Low Impact News**: Trade normally
- **Economic Calendar**: Monitor and enforce via automation

## 6. Drawdown Limits

### 6.1 Equity Drawdown
- **Initial Allocation**: 100% starting equity
- **Drawdown Level 1**: 10% drawdown → Alert
- **Drawdown Level 2**: 15% drawdown → Reduce position size to 75%
- **Drawdown Level 3**: 20% drawdown → Reduce position size to 50%
- **Drawdown Level 4**: 25% drawdown → Halt new positions
- **Drawdown Level 5**: 30% drawdown → FORCE CLOSE ALL POSITIONS

### 6.2 Recovery Targets
- **After 10% DD**: Need 2% gain to recover (1:5 recovery ratio)
- **After 20% DD**: Need 5% gain to recover (1:4 recovery ratio)
- **After 25% DD**: Need 6.7% gain to recover (1:3.75 recovery ratio)
- **After 30% DD**: Need 10% gain to recover (1:3 recovery ratio)

## 7. Execution Limits

### 7.1 Slippage Limits
- **Max Acceptable Slippage**: 1.0 pip (average for gold)
- **Alert Threshold**: 0.8 pip slippage
- **Retry Threshold**: 1.2 pip slippage (retry order)
- **Reject Threshold**: 2.0 pip slippage (reject and alert)

### 7.2 Order Validation
- **Pre-Execution**: Validate position size, price, stop loss
- **Duplicate Check**: Prevent duplicate orders within 1 second
- **Price Sanity**: Check price within ±5% of last quote
- **Timing**: Check market is within trading hours (not weekends)

### 7.3 Execution Speed
- **Max Execution Time**: 5 seconds (market order)
- **Alert**: If order takes >3 seconds
- **Cancel**: If order pending >5 seconds
- **Retry**: Auto-retry with market order if limit order fails

## 8. Account Limits

### 8.1 Margin Limits
- **Margin Requirement**: Must maintain >120% margin ratio
- **Alert**: 100% margin ratio (critical)
- **Halt New Positions**: <110% margin
- **Force Close**: <90% margin (broker margin call)
- **Monitoring**: Real-time margin tracking

### 8.2 Balance Verification
- **Reconciliation**: Daily 00:00 UTC reconciliation
- **Tolerance**: Allow ±0.1% variance from broker
- **Alert**: If variance >0.5%
- **Investigation**: If variance >1% → halt trading

### 8.3 Withdrawal Limits
- **Max Daily Withdrawal**: 20% of account balance
- **Weekly Withdrawal**: 40% of starting balance
- **Approval**: Require 24-hour hold before withdrawal
- **Trading Halt**: Cannot trade while withdrawal pending

## 9. System Health Limits

### 9.1 Connection Health
- **MT5 Connection**: Must reconnect if >30 seconds down
- **Data Feed Latency**: Alert if >5 seconds behind
- **API Latency**: Alert if >1000ms response time
- **Database Connection**: 5-minute timeout, auto-reconnect

### 9.2 Model Health
- **Model Latency**: Alert if inference >50ms
- **Model Errors**: Alert if prediction fails
- **Fallback**: Use random forest if DRL model fails
- **Manual Override**: Pause trading while investigating

### 9.3 Data Quality
- **Missing Data**: Alert if >5% data missing
- **Stale Data**: Alert if data >5 minutes old
- **Validation Errors**: Alert if >2% validation failures
- **Auto-Recovery**: Auto-retry, halt if persistent

## 10. Manual Override Controls

### 10.1 Override Restrictions
- **NO Override for**: Drawdown stops, margin calls, connection loss
- **Limited Override for**: Daily loss limits (requires manager approval)
- **Audit Trail**: Log all override attempts
- **Approval Process**: Require 2 approvals for override
- **Time Limit**: Override expires after 1 hour

### 10.2 Emergency Stop
- **Big Red Button**: One-click emergency close all positions
- **Access**: Only for authorized personnel
- **Logging**: Automatic logging with timestamp/user
- **Recovery**: Requires manual restart
- **Testing**: Monthly testing of emergency stop

## 11. Circuit Breaker Logic

### 11.1 Automatic Circuit Breakers
```
IF daily_loss > 5% THEN
  CLOSE_ALL_POSITIONS()
  HALT_TRADING()
  ALERT_EMERGENCY()
  EMAIL_MANAGER()
END IF

IF margin_ratio < 90% THEN
  FORCE_LIQUIDATE_POSITIONS()
  HALT_TRADING()
END IF

IF model_accuracy < 50% THEN
  HALT_TRADING()
  ALERT_TEAM()
END IF

IF connection_lost > 300_seconds THEN
  CLOSE_ALL_POSITIONS()
  HALT_TRADING()
END IF
```

### 11.2 Escalation Logic
- **Level 1**: Alert trader (yellow)
- **Level 2**: Reduce position size (orange)
- **Level 3**: Halt new positions (red)
- **Level 4**: Close all positions (critical)
- **Level 5**: Emergency shutdown (black)

## 12. Monitoring & Reporting

### 12.1 Real-Time Monitoring
- **Dashboard**: Live risk dashboard updated every second
- **Metrics**: Current loss %, margin ratio, open positions
- **Alerts**: Visual + audio alerts on threshold breach
- **Mobile**: Push notifications for critical alerts

### 12.2 Daily Reports
- **Risk Report**: Daily P&L, drawdown, margin utilization
- **Trade Report**: Completed trades with metrics
- **Alert Report**: All alerts triggered during day
- **Model Report**: Model accuracy, drift, performance

### 12.3 Audit Trail
- **All Decisions**: Log every trade decision
- **Override Attempts**: Log all manual overrides
- **Limit Breaches**: Log when limits are hit
- **Alerts**: Log all alerts triggered
- **Retention**: Keep 2+ years of audit logs

## Conclusion

These hard limits and circuit breakers are CRITICAL for survival in algorithmic trading. They must be:

✓ Non-negotiable (rarely override)
✓ Automatically enforced
✓ Transparently monitored
✓ Regularly stress-tested
✓ Conservative by default

Capital preservation is more important than returns. These limits protect against catastrophic losses from model failures, market anomalies, or operational errors.
