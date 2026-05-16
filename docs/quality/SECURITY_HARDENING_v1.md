# Enterprise Quality Guard - Security & Documentation Integrity

This document outlines the mandatory quality gates for security and documentation.

## 1. Documentation Integrity
- All modifications to `src/` or `main.py` MUST be accompanied by an update to relevant documentation in `docs/`.
- Change summary: Implemented `pydantic.SecretStr` for sensitive configuration fields and hardened PyTorch model loading.

## 2. Security Hardening
- Sensitive fields (MT5 passwords, API tokens) MUST use `SecretStr` to prevent accidental logging.
- Access MUST be via `.get_secret_value()`.
- Logging configuration MUST place masking processors after exception/stack trace renderers to ensure all output is scrubbed.
- PyTorch model loading MUST use `weights_only=True` in `torch.load()` to prevent arbitrary code execution from untrusted model files.
