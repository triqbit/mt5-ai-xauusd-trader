# Acceptance Criteria: Synthetic Data Engine

## Functional Acceptance Criteria
- **Behavior:**
    - Generate high-fidelity synthetic OHLCV data for XAUUSD to facilitate stress testing and model training.
    - Support generation of specific market regimes (Trending, Ranging, Flash Crash).
    - Ensure technical indicators calculated on synthetic data are consistent with real data patterns.
- **Edge Cases:**
    - Correct handling of weekend gaps and holiday closures in synthetic timelines.
    - Generation of realistic "Fat Tail" events.
- **Inputs/Outputs:**
    - **Inputs:** Seed parameters, desired regime, time range, volatility scale.
    - **Outputs:** `pd.DataFrame` with OHLCV data and volume.

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for statistical properties of generated data (mean, variance, skewness).
    - Verification that `FeatureEngineer` works correctly with synthetic data outputs.
- **Performance:**
    - Ability to generate 1 year of M1 data in < 5 seconds.
- **Error Handling:**
    - Validate input parameters to prevent infinite loops or invalid price generation (e.g., negative prices).
- **Observability:**
    - Log parameters used for data generation to ensure reproducibility.

## Operational Acceptance
- **Documentation:**
    - Guide for researchers on how to use the `SyntheticDataEngine` for training and stress testing.
- **Configuration:**
    - CLI interface for data generation tasks.
- **Rollback:**
    - N/A (Research tool).
- **Monitoring:**
    - N/A.

## Release Readiness
- **Deployment:** Research tool; can be deployed independently.
- **Backward Compatibility:** N/A.
- **Migration:** N/A.
- **Sign-off:** Requires approval from the Quant Lead (Jules04).
