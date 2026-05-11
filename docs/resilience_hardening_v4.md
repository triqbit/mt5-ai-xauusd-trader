# Resilience Hardening v4

This document describes the hardening of the MT5Connector data retrieval paths.

## Key Changes
- All primary data retrieval methods (account info, positions, etc.) now use a logic/wrapper pattern.
- Exponential backoff retries and circuit breakers are applied to these paths.
- Improved failure detection raises explicit MT5DataError when the SDK returns None.
- Safe failure propagation in get_account_balance prevents dangerous zero-balance assumptions.
