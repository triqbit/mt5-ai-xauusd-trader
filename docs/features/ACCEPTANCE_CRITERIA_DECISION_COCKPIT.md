# Acceptance Criteria: Explainable Regime-Aware Decision Cockpit (TUI)

## Functional Acceptance Criteria
- **Behavior:**
    - Provide a real-time terminal dashboard visualizing the bot's internal state.
    - Display current Market Regime, Volatility State, and Ensemble Consensus.
    - Show recent trade signals with their corresponding "Signal Explanation" (why it was taken/rejected).
- **Edge Cases:**
    - Correct rendering when terminal size is too small (scrolling or condensed view).
    - Handling disconnection from MT5 or the database by showing a "Stale Data" warning.
- **Inputs/Outputs:**
    - **Inputs:** Telemetry stream from `main.py` including model outputs, regime detector state, and risk manager status.
    - **Outputs:** Interactive or auto-refreshing terminal UI using the `rich` library.

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for TUI data formatting and panel logic.
    - Integration tests for the telemetry thread to ensure it doesn't leak memory or block the main trading loop.
- **Performance:**
    - CPU overhead must remain < 5% on a standard 1-vCPU VPS instance.
    - Refresh rate should be configurable, defaulting to 1Hz.
- **Error Handling:**
    - Catch and log errors in terminal rendering without crashing the core trading bot.
- **Observability:**
    - The cockpit itself is an observability tool, but it should also log its own health status to the system log.

## Operational Acceptance
- **Documentation:**
    - User guide for interpreting the dashboard panels.
    - README section on TUI keybindings (if any).
- **Configuration:**
    - `COCKPIT_REFRESH_RATE`: Time between UI updates.
    - `COCKPIT_THEME`: Support for "dark" and "light" color schemes if applicable.
    - `--headless` flag: To disable the TUI when running in background/CI environments.
- **Rollback:**
    - If the TUI causes performance issues, it can be disabled via the `--headless` flag.
- **Monitoring:**
    - Dashboard should display a "System Health" panel derived from the Enterprise Health Gate.

## Release Readiness
- **Deployment:** Independent of core trading logic, but requires the "Explainability" module to be active.
- **Backward Compatibility:** Must work in standard SSH sessions (No X11 required).
- **Migration:** No data migration required.
- **Sign-off:** Requires approval from the Observability Lead (Jules02).
