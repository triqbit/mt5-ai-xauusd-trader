# License Compliance Policy

## ⚖️ Overview
This document defines the formal license compliance policy for the MT5 AI/ML Trading Bot. Ensuring all third-party dependencies adhere to permissive licensing is critical for enterprise delivery, avoiding legal risks and intellectual property "pollution" from copyleft licenses.

## 🏛️ Attribution Requirements
All third-party code integrated into this repository must be properly attributed.
- **Direct Integration (Vendoring):** Any code copied directly from external sources must be documented in `ATTRIBUTIONS.md` in the root directory.
- **Dependency Attribution:** Runtime and development dependencies are tracked in the [Dependency License Report](DEPENDENCY_LICENSES.md).
- **Notices:** Preserve all original copyright notices and license files in integrated source code.

## ✅ Allowed Licenses (Permissive)
The following licenses are pre-approved for use. They allow for commercial use, modification, and distribution without requiring the source code of the bot itself to be released.
- **MIT License**
- **Apache License 2.0**
- **BSD (2-Clause and 3-Clause)**
- **PSF (Python Software Foundation)**
- **Unlicense / Public Domain**
- **ISC License**
- **Mozilla Public License 2.0 (MPL 2.0)**

## ⚠️ Restricted Licenses (Review Required)
The following licenses are allowed but must be used as external dependencies only (dynamic linking):
- **LGPL (v2.1, v3)** - Allowed as long as the library is used without modification.
- **Other/Proprietary** - Allowed for specific commercial SDKs (e.g., MetaAPI, NVIDIA CUDA) where no open-source alternative exists.

## 🚫 Disallowed Licenses (Copyleft & Restricted)
The following licenses are strictly prohibited to protect the project's intellectual property:
- **GPL (v2, v3)** - Prohibited due to "viral" copyleft requirements.
- **AGPL (Affero GPL)** - Prohibited due to network-triggered copyleft.
- **CC-BY-NC (Non-Commercial)** - Prohibited as this is an enterprise-ready commercial tool.
- **SSPL (Server Side Public License)**
- **Proprietary/EULA** - Prohibited without explicit legal sign-off and purchase.

## 🤖 Automated License Scanning
License compliance is enforced automatically via CI to prevent accidental introduction of incompatible licenses.
- **Tool:** `pip-licenses`
- **Workflow:** `.github/workflows/license-check.yml`
- **Trigger:** Every Pull Request and push to `main`.
- **Enforcement:** The CI job will fail if a dependency with a disallowed license is detected.

## 📝 Dependency License Report
The [DEPENDENCY_LICENSES.md](DEPENDENCY_LICENSES.md) file contains a comprehensive report of all current Python dependencies, their versions, licenses, and URLs. This report is regenerated during the release process and on every CI run.

## 🚩 Detection and Resolution of Risky Licenses
If the automated scanner detects a risky or incompatible license:
1. **Identify Alternatives:** Search for a permissively licensed replacement.
2. **Impact Assessment:** Determine if the dependency is critical or can be removed.
3. **Formal Exception:** If no alternative exists, a formal risk assessment must be performed by the Governance Lead.

### Verified Exceptions
The following dependencies have been manually reviewed and approved despite "UNKNOWN" or non-standard license metadata:
- **MetaAPI / metaapi-cloud-sdk:** Proprietary/Commercial. Excluded from automated scans due to environment constraints but approved for production use.
- **pandas-ta:** UNKNOWN license metadata, but verified as LGPL/MIT compatible.
- **peewee:** UNKNOWN by scanner, but MIT licensed.
- **NVIDIA CUDA components:** Proprietary (LicenseRef-NVIDIA-Proprietary).

### LGPL Policy
LGPL dependencies are pre-approved for CI to ensure build stability, provided they are used as external libraries (dynamic linking) without modification to the library source.

---
*Last Updated: 2025-06-10*
*Owner: Jules03 (Release & Governance Lead)*
