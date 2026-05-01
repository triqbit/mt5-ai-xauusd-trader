# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Enterprise-grade health check system in `src/core/health.py`.
- Mandatory startup health gate in `main.py` to prevent execution in invalid states.
- FastAPI-compatible health endpoints for production monitoring.
- Comprehensive unit and integration tests for the health check framework.
- Semantic versioning policy (`docs/VERSIONING_POLICY.md`).
- Automated changelog generation workflow (`.github/workflows/changelog.yml`).
- Initial `CHANGELOG.md` template.

### Changed
- Refactored release orchestration to integrate automated versioning logic.

## [1.0.0] - 2024-05-24
### Added
- Initial enterprise-grade trading engine.
- MT5 integration and risk management framework.
- CI/CD pipelines for validation and security.
