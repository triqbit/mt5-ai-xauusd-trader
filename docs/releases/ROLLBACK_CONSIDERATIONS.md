# Rollback Considerations: Configuration and Validation Updates

## Overview
This document outlines the rollback procedures and impacts for changes related to configuration synchronization and enhanced validation rules.

## Change Summary
- Added `MODEL_CALIBRATION_THRESHOLD` to `.env.example`.
- Implemented calibration threshold validation in `src/core/config_validator.py`.

## Rollback Procedure

### 1. Code Reversion
If the new validation logic causes unexpected startup failures in production:
1. Revert the changes to `src/core/config_validator.py`.
2. Revert the changes to `.env.example`.
3. Re-deploy the previous stable version of the application.

### 2. Configuration Adjustment
Instead of a full code rollback, if a specific threshold is too restrictive:
1. Update the `.env` file to set `MODEL_CALIBRATION_THRESHOLD` to a higher value (within the warning range, e.g., 0.30) to allow the application to start while still providing warnings.
2. Restart the application.

## Impact of Rollback
- **Security/Risk**: Rolling back the validation logic removes a safety gate that prevents the bot from trading with poorly calibrated models. This increases the risk of "overconfident" incorrect trades.
- **Compatibility**: Rolling back these changes has no impact on existing databases or historical data, as these are startup-time configuration checks.
- **Monitoring**: Warnings related to model calibration will no longer appear in logs or dashboards if the validator is reverted.

## Verification after Rollback
1. Run `python scripts/doctor.py` to ensure the system is in a known good state.
2. Verify that the application starts without `MODEL_CALIBRATION_THRESHOLD` errors.
