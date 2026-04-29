# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Automated dependency management: Updated all requirements files (`requirements.txt`, `requirements-docker.txt`, `requirements-ci.txt`) with safe upgrades using `pur`.
- Security hardening: Performed security audit on dependencies using `pip-audit`. Fixed multiple vulnerabilities by upgrading `requests`, `aiohttp`, `python-dotenv`, and other packages.

### Added
- Created `scripts/dependency_check.sh` for automated weekly dependency audits, covering both outdated and security checks.
