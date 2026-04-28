# Runbook 06: Monitoring Alert Triage

## Description
This runbook provides instructions for triaging Telegram alerts sent by the bot.

## Alert Severity Matrix

| Alert Message | Severity | Action Required |
| :--- | :--- | :--- |
| `🚨 CRITICAL: Circuit Breaker Triggered!` | **P1 (Critical)** | Immediate stop/verify positions. See Runbook 03. |
| `⚠️ WARNING: Model Confidence Degradation` | **P2 (High)** | Investigate market conditions. Possible manual halt. |
| `📅 Daily Summary` | **P4 (Info)** | No action. Review for performance tracking. |
| `Failed to send Telegram message` (Logs) | **P3 (Medium)** | Check Telegram Bot API status and Token. |

## Triage Steps

### 1. Handling P1 Alerts (Circuit Breaker)
**Step-by-step Instructions:**
1. Open MT5 Terminal or Broker App immediately.
2. Ensure no rogue orders are open.
3. Check bot logs for the exact drawdown value and time.
4. Follow **Runbook 03**.

### 2. Handling P2 Alerts (Confidence Degradation)
**Step-by-step Instructions:**
1. Check the `current` vs `threshold` confidence in the alert.
2. If confidence is significantly below threshold (e.g., < 0.4 while threshold is 0.6), consider the market "untradeable" for the current model.
3. Monitor logs for high signal rejection rate.
4. Consult with Quant Strategist (Jules04) regarding model retraining.

### 3. Handling P3 Alerts (Alerting System Failure)
**Step-by-step Instructions:**
1. If you notice missing daily summaries, check the bot's log for `telegram.error.TelegramError`.
2. Verify `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID` are still valid.
3. Check internet connectivity from the production server.

## Escalation Path
1. P1 Alerts: On-call trader and Platform Engineer.
2. P2 Alerts: Quant Strategist.
3. Persistent Alerting Failures: Platform Engineer (Jules03).

## Verification Commands
```bash
# Check for recent alerts in logs
grep -E "CRITICAL|WARNING|alert" logs/app.log | tail -n 20
```
