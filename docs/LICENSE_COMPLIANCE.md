# License Compliance & Attribution Framework

## Overview

This document defines the license compliance policy for the MT5 Trading Bot Monorepo. We use automated scanning and strict policy enforcement to ensure that all third-party dependencies and integrated code comply with our licensing standards.

---

## License Policy

### Allowed Licenses (Permissive)
The following licenses are generally approved for use in this project:
- **MIT** / **MIT-CMU** / **MIT-0**
- **Apache 2.0**
- **BSD (2-Clause and 3-Clause)**
- **PSF-2.0** (Python Software Foundation License)
- **ISC**
- **Unlicense** / **Public Domain**
- **0BSD**
- **CC0-1.0**

### Restricted Licenses (Acceptable for Dependencies)
The following licenses are acceptable when used as external dependencies, provided we do not modify their source code or statically link in a way that triggers copyleft requirements:
- **LGPL (v2.1, v3)** (e.g., `python-telegram-bot`, `frozendict`)
- **MPL 2.0** (e.g., `certifi`, `hypothesis`, `pathspec`)
- **NVIDIA Proprietary** (for CUDA/GPU acceleration libraries)

### Disallowed Licenses (Copyleft/Incompatible)
The following licenses are strictly prohibited for core project code or any library that requires us to open-source our own proprietary trading logic:
- **GPL (v2, v3)**
- **AGPL**
- **SSPL**

---

## Automated License Scanning

We use `pip-licenses` to audit our Python dependencies.

### CI/CD Enforcement
A GitHub Action (`.github/workflows/license-check.yml`) runs on every pull request to:
1. Scan all installed packages.
2. Verify that all licenses are in the approved list.
3. Fail the build if a "Disallowed" license is detected.

### Manual Audit Command
To run a manual audit and generate a report:
```bash
pip install pip-licenses
pip-licenses --format=markdown --output-file=docs/DEPENDENCY_LICENSES.md --with-urls
```

To check for policy violations (current approved set for CI):
```bash
pip-licenses --allow-only "MIT;Apache;BSD;PSF;ISC;Unlicense;MPL;LGPL;Proprietary;NVIDIA;CC0;0BSD" --partial-match
```

---

## Attribution Requirements

### Integrated Repositories
When code is integrated from other repositories (e.g., MIT/Apache 2.0 licensed projects), the following must be maintained:

1. **Original License File**: Must be preserved in the module directory (e.g., `src/core/rl_algorithms/ppo/LICENSE`).
2. **Code Headers**: Maintain original copyright notices in source files.
3. **ATTRIBUTIONS.md**: All significant third-party integrations must be listed in the root `ATTRIBUTIONS.md` file.

### Notice Files
For Apache 2.0 dependencies, any required `NOTICE` files must be included in the distribution as per the license terms.

---

## Risky or Incompatible Licenses

### Detection
The automated scanner detects risky licenses by matching against the disallowed list. Any package identified with "GPL" (excluding LGPL) or "AGPL" will trigger an immediate CI failure.

### Mitigation
If a required dependency uses a disallowed license:
1. **Identify Alternatives**: Search for a permissively licensed equivalent.
2. **Isolation**: If no alternative exists, the component must be isolated behind a clear interface (e.g., a separate microservice) to prevent license contagion, subject to legal approval.

---

## Dependency License Report

The current snapshot of all dependency licenses is maintained in:
👉 **[docs/DEPENDENCY_LICENSES.md](DEPENDENCY_LICENSES.md)**

This report is regenerated during major releases and environment updates.

---

## Compliance Checklist

- [ ] New dependency license verified before adding to `requirements.txt`.
- [ ] No GPL/AGPL dependencies introduced.
- [ ] Original license files preserved for integrated code.
- [ ] `ATTRIBUTIONS.md` updated for new third-party integrations.
- [ ] CI License check passing.
- [ ] `docs/DEPENDENCY_LICENSES.md` updated.
