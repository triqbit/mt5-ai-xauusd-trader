# Acceptance Criteria: Hardened Risk Management

## Functional Acceptance Criteria
- **Behavior:** Enforce strict risk limits including max positions, risk per trade, and daily drawdown circuit breakers.
- **Edge Cases:**
    - Handle scenarios where the account balance cannot be retrieved (fail-safe: lock trading).
    - Handle multi-position risk correlation (e.g., gold vs. silver).
    - Correctly calculate lot size for fractional accounts.
- **Inputs/Outputs:**
    - **Inputs:** `TradeSignal`, current account balance, open positions.
    - **Outputs:** `RiskApproval` (Boolean), calculated lot size, reason for rejection.

## Technical Acceptance
- **Test Coverage:**
    - Property-based testing for position sizing logic (e.g., using Hypothesis).
    - Unit tests for all circuit breaker scenarios (100% coverage).
- **Performance:**
    - Risk approval latency < 10ms.
- **Error Handling:**
    - Any error in risk calculation must result in a "REJECT" signal for safety.
- **Observability:**
    - Log every risk rejection with the specific rule violated (e.g., "Daily loss limit reached").

## Operational Acceptance
- **Documentation:**
    - Maintain `RISK_LIMITS.md` with current production parameters.
    - Provide a runbook for emergency manual override of the risk manager.
- **Configuration:**
    - All risk limits must be defined in Pydantic settings with strict validation ranges.
- **Rollback:**
    - Changes to risk logic must be reversible via git revert without affecting other modules.
- **Monitoring:**
    - Alert immediately on any "Risk Reject" event in a live account.

## Release Readiness
- **Deployment:** Must be bundled with the core trading engine.
- **Backward Compatibility:** Risk settings should be versioned to avoid misconfiguration after upgrades.
- **Migration:** Existing risk parameters must be validated against new schema constraints.
- **Sign-off:** Mandatory sign-off from the Risk Officer.
