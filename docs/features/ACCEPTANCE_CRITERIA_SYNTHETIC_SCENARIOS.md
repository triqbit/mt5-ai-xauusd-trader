# Acceptance Criteria: Full-Cascade Synthetic Scenarios

## Functional Acceptance Criteria
- **Behavior:**
    - Validate the entire trading cascade (Signal -> Risk -> Execution -> Logging) using high-fidelity synthetic market scenarios.
    - Scenarios must include: `FLASH_CRASH`, `LOW_LIQUIDITY_GAP`, `EXTREME_VOLATILITY`, and `REGIME_SHIFT`.
    - Ensure that the "9-Layer Execution Filter" correctly blocks signals during adversarial scenarios.
- **Edge Cases:**
    - Validate system behavior when synthetic data feeds are interrupted or corrupted.
    - Verify that "Capital Preservation" modes engage correctly under stress.
- **Inputs/Outputs:**
    - **Inputs:** `ScenarioGenerator` configurations.
    - **Outputs:** `ValidationReport` with pass/fail status for each safety layer.

## Technical Acceptance
- **Test Coverage:**
    - End-to-end integration tests using `tests/test_institutional_integration.py`.
    - Automated safety gate in CI that runs synthetic scenarios on every PR.
- **Performance:**
    - Full-cascade validation for one scenario must complete in < 30 seconds.
- **Error Handling:**
    - Any safety failure in a scenario must be reported with a full trace of the "Execution Decision".
- **Observability:**
    - Log "Scenario Started" and "Scenario Result" to the Audit Log.

## Operational Acceptance
- **Documentation:**
    - Detailed guide on adding new synthetic scenarios.
- **Configuration:**
    - Ability to run specific scenarios via CLI (e.g., `pytest --scenario=FLASH_CRASH`).
- **Rollback:**
    - N/A (Validation tool).
- **Monitoring:**
    - N/A.

## Release Readiness
- **Deployment:** Mandatory for all Release Candidates.
- **Backward Compatibility:** N/A.
- **Migration:** N/A.
- **Sign-off:** Requires approval from the Security & Quality Lead (Jules02) and Quant Lead (Jules04).
