# Acceptance Criteria: Automated Model Promotion Workflow

## Functional Acceptance Criteria
- **Behavior:**
    - Provide an automated script (`scripts/promote_model.py`) to transition validated models from the Research/Experimental stage to the Production environment.
    - Validate that the candidate model passes all "Golden Metadata" benchmarks (Sharpe, MaxDD, Win Rate) relative to the current production baseline.
    - Automatically update the system configuration (`config.yaml` or `.env`) to point to the newly promoted model path.
    - Generate a "Promotion Manifest" including model version, validation metrics, and the hash of the model artifacts.
- **Edge Cases:**
    - Block promotion if the candidate model shows a >5% performance degradation compared to the current baseline.
    - Handle missing artifact files or corrupted model weights by aborting the promotion.
    - Prevent promotion if the model's feature signature does not match the current `FeatureEngineer` version.
- **Inputs/Outputs:**
    - **Inputs:** Candidate model path, validation results (backtest JSON), environment target (Staging/Production).
    - **Outputs:** Updated configuration, archived old model, and a persistent `PROMOTION_LOG.md` entry.

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for the promotion script's logic, including metadata comparison and config file manipulation.
    - Integration tests verifying that the bot correctly loads the newly promoted model after a restart.
- **Performance:**
    - Promotion execution (file copy and config update) must complete in < 10 seconds.
- **Error Handling:**
    - Transactional promotion: If any step fails (e.g., config update), the script must rollback the artifact move and restore the previous configuration.
- **Observability:**
    - Log every promotion attempt (success or fail) with detailed attribution (which model, which version, who triggered it).

## Operational Acceptance
- **Documentation:**
    - Guide on the "Model Lifecycle" from training to promotion in `docs/research/MODEL_PROMOTION.md`.
    - Instructions for manual rollback of a model promotion.
- **Configuration:**
    - `MODEL_PROMOTION_THRESHOLD`: Configurable metric deltas that trigger a block.
    - `MODEL_REGISTRY_PATH`: Directory for persistent model storage.
- **Rollback:**
    - Support for `make rollback-model` to instantly revert to the previous version.
- **Monitoring:**
    - Display current "Model Version" and "Promotion Date" in the Decision Cockpit.

## Release Readiness
- **Deployment:** Part of the Research & Operations tooling suite.
- **Backward Compatibility:** Must support the loading of historical model formats if required.
- **Migration:** N/A.
- **Sign-off:** Requires approval from the Quant Lead (Jules04) and Product Steward (Jules05).
