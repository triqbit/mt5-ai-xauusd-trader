### Dependency and Environment Hygiene Improvements

#### Configuration Hardening
- **Alignment with RISK_LIMITS.md:** Updated `src/core/config.py` with strict Pydantic `Field` constraints (`ge`, `le`) to match enterprise risk standards. Unsafe configurations are now rejected at startup.
- **Tighter Bounds:**
    - `max_positions`: reduced maximum from 10 to 5.
    - `risk_per_trade`: reduced maximum from 5% to 2%.
    - `max_daily_loss`: reduced maximum from 20% to 6%.
    - `confidence_threshold`: minimum set to 0.5.
    - `model_accuracy_floor`: minimum set to 0.5.
    - `model_win_rate_floor`: minimum set to 0.4.

#### Dependency Synchronization
- **Consistency:** Unified versions of `scikit-learn==1.7.2` and `structlog==25.5.0` across `requirements.txt`, `requirements-linux.txt`, and `requirements-docker.txt` to eliminate environment drift.
- **Type Safety:** Added missing type stubs (`types-redis`, `types-requests`, `types-python-dateutil`, `types-setuptools`, `types-PyYAML`) to CI requirements to improve static analysis reliability.

#### Code Quality & Fixes
- **Fix:** Added missing `Dict` import in `src/trading/execution_filter.py` to resolve CI linting errors.
- **Validation:** Verified Pydantic enforcement logic and ensured compatibility with existing test suites.
