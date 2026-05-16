# Acceptance Criteria: Interactive Setup Wizard

## Functional Acceptance Criteria
- **Behavior:**
    - Provide an interactive, menu-driven CLI experience via `python main.py --setup` to guide new users through configuration.
    - Support configuration of:
        - Broker Credentials (MT5 login, password, server).
        - Trading Modes (Live vs. Demo).
        - Risk Limits (Max daily loss, max positions).
        - Feature Toggles (Telegram alerts, monitoring, macro-defensive).
    - Automatically validate user inputs (e.g., ensuring numeric values for risk limits) before saving.
    - Write configuration to the appropriate `.env` or YAML file securely.
- **Edge Cases:**
    - Handle interruption (Ctrl+C) gracefully without corrupting existing configuration files.
    - Provide a "Skip" option for optional parameters.
    - Handle existing configuration by offering "Update" or "Overwrite" options.
- **Inputs/Outputs:**
    - **Inputs:** Interactive CLI prompts and user keyboard input.
    - **Outputs:** Updated `.env` or `config.yaml` and a "Configuration Successful" summary.

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for the wizard's logic using mock input/output (e.g., using `unittest.mock`).
    - Validation of the output file schema against `TradingConfig` Pydantic models.
- **Performance:**
    - Wizard responsiveness (latency between prompt and input processing) < 100ms.
- **Error Handling:**
    - Invalid inputs must trigger an immediate re-prompt with an explanation of the required format.
- **Observability:**
    - Log successful configuration updates (without secrets) to the system audit trail.

## Operational Acceptance
- **Documentation:**
    - Guide in the README.md explaining how to use the setup wizard for initial deployment.
    - Description of which parameters are "Safe" vs. "Sensitive" (requiring caution).
- **Configuration:**
    - The wizard itself is the primary configuration tool.
- **Rollback:**
    - Provide an option to "Undo" or "Revert to Backup" within the wizard session.
- **Monitoring:**
    - N/A.

## Release Readiness
- **Deployment:** Part of the "Usability & Onboarding" release tier.
- **Backward Compatibility:** Must not break existing manual configuration methods.
- **Migration:** No data migration required.
- **Sign-off:** Requires approval from the UX/Quality Lead (Jules02) and Product Steward (Jules05).
