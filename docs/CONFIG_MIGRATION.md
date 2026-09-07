# Configuration System Migration Guide

This guide describes how to migrate from the legacy `TradingConfig` system to the new `ConfigManager`.

## Overview

The new system provides:
- Environment-specific configurations (`dev`, `staging`, `prod`).
- Dynamic reloading without process restart.
- Secret management abstraction.
- Audit trail for all configuration changes.
- Strict Pydantic v2 validation.

## Changes

### 1. New Imports

Replace imports of `TradingConfig` or `get_config` from `src.core.config`.

**Old:**
```python
from src.core.config import get_config
cfg = get_config()
```

**New:**
```python
from src.core.config_manager import ConfigManager
cm = ConfigManager()
cfg = cm.config
```

### 2. Environment Variables

The system now respects the `APP_ENV` environment variable to load specific `.env` files:
- `APP_ENV=dev` loads `.env.dev` (or `.env` if not found).
- `APP_ENV=prod` loads `.env.prod`.

### 3. Dynamic Reloading

If you need to reload configuration at runtime:
```python
cm.reload()
new_cfg = cm.config
```

### 4. Secret Management

Instead of hardcoding secrets in `.env`, use a `SecretProvider`:
```python
from src.core.config_manager import ConfigManager, MockSecretProvider

secrets = {"MT5_PASSWORD": "secure_password"}
cm = ConfigManager(secret_provider=MockSecretProvider(secrets))
```

### 5. Audit Trail

Configuration changes are now logged to `logs/config_audit.jsonl`. You can also access them programmatically:
```python
changes = cm.audit_trail
```

## Migration Steps

1. Create environment-specific `.env` files (e.g., `.env.dev`, `.env.prod`).
2. Update entry points (like `main.py`) to use `ConfigManager`.
3. (Optional) Implement a production `SecretProvider` for AWS or Vault.
4. Verify validation rules; some fields now have stricter constraints.
