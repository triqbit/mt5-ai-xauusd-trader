# License Compliance Policy

## ⚖️ Overview
This document defines the license compliance policy for the MT5 AI/ML Trading Bot. As an enterprise-grade trading system, ensuring all third-party dependencies adhere to permissive licensing is critical to avoid legal risks and intellectual property "pollution" from copyleft licenses.

## 🏛️ Core Attribution
This project integrates code and architectural patterns from multiple open-source repositories. **Formal attribution for these integrated components is maintained in [ATTRIBUTIONS.md](../ATTRIBUTIONS.md).**

All developers must ensure that any direct code integration (vendoring) is documented in `ATTRIBUTIONS.md` with the corresponding license and source URL.

## ✅ Allowed Licenses (Permissive)
The following licenses are pre-approved for use in this project:
- **MIT License**
- **Apache License 2.0**
- **BSD (2-Clause and 3-Clause)**
- **PSF (Python Software Foundation)**
- **Unlicense / Public Domain**
- **ISC License**
- **Mozilla Public License 2.0 (MPL 2.0)**

## ⚠️ Restricted Licenses (Review Required)
The following licenses are allowed but must be used as external dependencies only (dynamic linking):
- **LGPL (v2.1, v3)** - Allowed as long as the library is used without modification and user-replaceability is maintained.

## 🚫 Disallowed Licenses (Copyleft & Restricted)
The following licenses are strictly prohibited unless a formal legal exception is granted:
- **GPL (v2, v3)** - Due to "viral" copyleft requirements.
- **AGPL (Affero GPL)** - Due to network-triggered copyleft.
- **CC-BY-NC (Non-Commercial)** - Prohibited as this is an enterprise/commercial-ready tool.
- **SSPL (Server Side Public License)**
- **Proprietary/EULA** (without explicit purchase and legal sign-off).

## 🤖 Automated Enforcement
The project uses GitHub Actions to enforce these rules on every Pull Request.
- **Tool:** `pip-licenses`
- **Workflow:** `.github/workflows/license-check.yml`
- **Action:** Failure to comply with the "Allowed" list will block the merge.

## 📝 Dependency Reporting
A full list of runtime dependencies and their detected licenses is available in [DEPENDENCY_LICENSES.md](DEPENDENCY_LICENSES.md). This report is updated automatically by the CI pipeline.

## 🚩 Handling Risky or Incompatible Licenses
If a required dependency uses a disallowed or unknown license:
1. **Identify Alternatives:** Search for a permissively licensed alternative.
2. **Impact Assessment:** Determine if the library is optional or can be replaced by custom implementation.
3. **Formal Exception:** If no alternative exists, escalate to the repository maintainer for a formal risk assessment.

---
*Last Updated: 2024-05-22*
