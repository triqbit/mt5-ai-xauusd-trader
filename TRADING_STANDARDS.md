# Trading Standards for MT5 AI/ML Trading Bot

## 1. Risk Management Standards

### 1.1 Position Sizing Rules
- **Maximum Position Size**: Limited to 5% of account equity per trade
- **Leverage Limits**: Maximum 1:50 for gold (XAUUSD) trading
- **Correlation Limits**: No 2+ correlated positions simultaneously
- **Portfolio Heat**: Maximum 20% of equity at risk across all positions

### 1.2 Risk Parameters
```python
# Example position sizing calculation
def calculate_position_size(
    account_equity: float,
    risk_percentage: float,
    stop_loss_pips: float,
    pip_value: float
) -> float:
    """Calculate position size based on risk management rules."""
    # Risk per trade in currency
    risk_amount = account_equity * (risk_percentage / 100)
    
    # Position size in lots
    position_size = risk_amount / (stop_loss_pips * pip_value)
    
    # Apply maximum position limit (5% of equity)
    max_position = (account_equity * 0.05) / (pip_value * 100)
    
    return min(position_size, max_position)
```

### 1.3 Stop-Loss & Take-Profit Rules
- **Minimum Stop Distance**: 10 pips for XAUUSD
- **Mandatory Stop-Loss**: Every trade must have a hard stop-loss
- **Risk-Reward Ratio**: Minimum 1:1.5 (1 risked to gain 1.5)
- **Trailing Stops**: Implement after profit threshold (e.g., +50 pips)
- **Profit Target Levels**: Multiple profit levels with partial exits

### 1.4 Daily Loss Limits (Circuit Breaker)
- **Daily Loss Limit**: 3% of account equity
- **Weekly Loss Limit**: 8% of account equity
- **Monthly Loss Limit**: 15% of account equity
- **Consequence**: Halt trading when limits reached, resume next period
- **Alert System**: Email/SMS notification when approaching limits

## 2. Order Management & Execution

### 2.1 Order Validation Framework
```python
class OrderValidator:
    """Validate all orders before execution."""
    
    def validate_order(self, order: Order) -> Tuple[bool, str]:
        """Validate order against all trading rules."""
        checks = [
            self._check_position_size(order),
            self._check_daily_loss_limit(order),
            self._check_correlation(order),
            self._check_stop_loss(order),
            self._check_take_profit(order),
            self._check_market_hours(order),
            self._check_news_event_risk(order),
        ]
        
        for is_valid, message in checks:
            if not is_valid:
                return False, message
        
        return True, "Order validated successfully"
    
    def _check_stop_loss(self, order: Order) -> Tuple[bool, str]:
        """Ensure stop-loss is within acceptable range."""
        if order.stop_loss is None:
            return False, "Stop-loss is required"
        
        distance_pips = abs(order.entry_price - order.stop_loss) / self.pip_value
        if distance_pips < 10:
            return False, f"Stop-loss too close: {distance_pips} pips"
        
        return True, "Stop-loss validated"
```

### 2.2 Order Execution Standards
- **Order Types**: Market, Limit, Stop-Loss only (no pending orders beyond 5 minutes)
- **Slippage Tolerance**: Maximum 2 pips slippage acceptable
- **Order Confirmation**: All fills must be confirmed against MT5 platform
- **Rejected Orders**: Log and analyze all rejected orders
- **Partial Fills**: Handle partial fills explicitly in code

### 2.3 Trade Reconciliation
- **Frequency**: Real-time reconciliation with MT5
- **Procedure**: Every hour: verify open positions, compare P&L, check balance
- **Discrepancy Handling**: Halt trading, investigate, resolve before resuming
- **Documentation**: Log all reconciliation results

## 3. Backtesting Standards

### 3.1 Backtesting Requirements
- **Historical Data Range**: Minimum 5 years of OHLCV data
- **Data Quality**: Verified against multiple sources for accuracy
- **Market Conditions**: Test through multiple market regimes:
  - Bull markets (2015-2017)
  - Bear markets (2018, 2020)
  - Sideways/consolidation periods
  - High volatility periods (Brexit, COVID, Fed announcements)

### 3.2 Backtest Metrics
```
Required Performance Metrics:
- Total Return: Target 50-100% annually
- Sharpe Ratio: Target > 2.0
- Sortino Ratio: Target > 3.0
- Max Drawdown: Maximum 25% of peak equity
- Win Rate: Target 55-65%
- Profit Factor: Target > 2.0 (wins/losses)
- Recovery Factor: Target > 2.0 (net profit/max drawdown)
```

### 3.3 Backtest Validation
- **Out-of-Sample Testing**: 20% of data reserved for testing
- **Walk-Forward Analysis**: Rolling 1-year windows with quarterly recalibration
- **Sensitivity Analysis**: Test parameter variations (±10%, ±20%)
- **Monte Carlo Simulation**: Randomize order sequence, test robustness
- **Optimization Risk**: Avoid over-fitting with parameter limits

## 4. Live Trading Standards

### 4.1 Paper Trading Phase
- **Duration**: Minimum 2 weeks before live trading
- **Success Criteria**: 
  - 70%+ win rate in paper trading
  - Sharpe ratio > 2.0
  - No losses exceeding 2% per trade
  - Consistent performance across market conditions
- **Documentation**: Log all paper trades for review

### 4.2 Live Trading Graduation
- **Phase 1 (Weeks 1-2)**: Micro lots, 0.01 lot per trade, $100-500 risk per trade
- **Phase 2 (Weeks 3-4)**: Mini lots, 0.1 lot per trade, $500-1,000 risk per trade
- **Phase 3 (Weeks 5+)**: Standard lots, 0.5-1.0 lot per trade, $1,000+ risk per trade
- **Graduation Criteria**: Each phase requires 70%+ win rate before advancing

### 4.3 Live Trading Monitoring
```python
class LiveTradingMonitor:
    """Real-time monitoring of live trading operations."""
    
    def monitor_trade(self, trade: Trade) -> None:
        """Continuous monitoring of active trades."""
        while trade.is_open:
            current_price = self.get_current_price()
            
            # Check stop-loss and take-profit
            self._check_exit_conditions(trade, current_price)
            
            # Monitor drawdown
            self._check_max_drawdown(trade)
            
            # Check for unusual price movements
            self._check_price_anomalies(trade, current_price)
            
            # Log performance metrics
            self._log_trade_metrics(trade)
            
            time.sleep(60)  # Check every minute
```

### 4.4 Emergency Procedures
- **System Failure**: Automatic stop-loss conversion to market order
- **Broker Disconnect**: Hold all positions, reconnect and verify
- **Unusual Price**: Manual review before execution
- **Margin Call**: Immediately liquidate worst-performing positions
- **Circuit Breaker**: Halt trading if daily loss limit reached

## 5. Data Feed & Market Hours Standards

### 5.1 Approved Trading Hours
- **XAUUSD Hours**: Sunday 17:00 - Friday 16:00 GMT
- **High Volatility Hours**: 12:30-14:30 GMT (US market open)
- **Low Liquidity Avoid**: Friday 14:00-16:00 GMT (market close)
- **Holiday Trading**: NO trading on major holidays (Christmas, New Year, etc.)

### 5.2 Data Feed Requirements
- **Price Feed**: Real-time from MT5 with < 100ms latency
- **Update Frequency**: Ticks updated every 100-500ms
- **Data Validation**: Check for gaps, spikes, and anomalies
- **Backup Feed**: Alternative data source if primary fails
- **Data Logging**: Timestamp all price data for audit trail

### 5.3 Economic Calendar Integration
```
HIGH IMPACT NEWS - PAUSE TRADING 30 MINUTES BEFORE & AFTER:
- Non-Farm Payroll (1st Friday of month)
- FOMC Rate Decisions (8 times per year)
- Fed Chair Speeches (sporadic)
- ISM Manufacturing/Services

MEDIUM IMPACT - CAUTION TRADING:
- CPI/PPI Releases
- Treasury Auctions
- Unemployment Claims
- Retail Sales
```

## 6. Model Performance Validation

### 6.1 Strategy Performance Review
- **Daily**: Review P&L, win rate, drawdown
- **Weekly**: Analyze trade patterns, identify issues
- **Monthly**: Comprehensive performance audit
- **Quarterly**: Full strategy validation and recalibration

### 6.2 Signal Accuracy Metrics
- **True Positive Rate**: Profitable signals / Total signals
- **False Positive Rate**: Losing signals / Total signals
- **Signal Frequency**: Trades per week (target: 5-15)
- **Signal Timing**: Entry accuracy vs optimal entry points

### 6.3 Performance Degradation Detection
```
Retraining Triggers (Automatic):
- Win rate drops below 50% (consecutive 10 trades)
- Sharpe ratio falls below 1.5
- Monthly loss exceeds 10% of equity
- Strategy underperforms random entries for 5 consecutive days

Action: Stop trading, retrain model, run validation before resume
```

## 7. Audit & Compliance

### 7.1 Trade Audit Trail
- **Every Trade Logged**: Entry time, price, size, exit time, P&L
- **Decision Log**: Why each trade was taken (signals, reasoning)
- **Modification Log**: Any manual overrides or interventions
- **Performance Attribution**: Credit correct predictions, analyze errors

### 7.2 Compliance Checklist
- [ ] All trades have stop-loss orders
- [ ] Position sizes comply with equity rules
- [ ] Daily loss limits enforced
- [ ] No trades during prohibited hours
- [ ] Data reconciliation completed daily
- [ ] Model performance within expected parameters
- [ ] Risk metrics within tolerance
- [ ] Backup systems operational

### 7.3 Reporting Standards
- **Daily Report**: Generated automatically, sent to stakeholders
- **Weekly Summary**: Performance metrics, trades analysis
- **Monthly Report**: Detailed performance review, strategy metrics
- **Quarterly Review**: Strategy effectiveness, recommendations

## 8. Emergency Protocols

### 8.1 Margin Call Procedures
1. Immediately notify all stakeholders
2. Liquidate 50% of worst-performing positions
3. If still critical, liquidate all positions
4. Suspend trading until account restored to 2:1 margin

### 8.2 System Failure Recovery
1. Detect failure within 1 minute (automated)
2. Convert all pending orders to market orders
3. Activate backup MT5 connection
4. Reconnect within 5 minutes
5. Verify all positions after reconnection

### 8.3 Force Stop Procedures
- **Daily Loss Limit Hit**: Stop all new trades immediately
- **Consecutive Losses (5)**: Manual review required before resuming
- **System Error (2+)**: Halt trading for 24 hours, investigate
- **Model Failure**: Revert to previous validated version

---

**Last Updated**: January 2026
**Version**: 1.0
**Maintained By**: Trading Operations Team
**Review Frequency**: Monthly
