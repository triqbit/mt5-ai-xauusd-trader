# License Compliance Policy

## 1. Overview
This policy defines the standards for open-source and third-party license compliance for the MT5 AI/ML Trading Bot project. Our goal is to ensure legal safety, respect intellectual property, and maintain a production-ready codebase without licensing surprises.

## 2. License Categorization

### 2.1 Allowed Licenses (Permissive)
The following licenses are pre-approved for use in this project:
- **MIT**
- **Apache 2.0**
- **BSD-2-Clause / BSD-3-Clause**
- **PSF-2.0** (Python Software Foundation License)
- **ISC**
- **Unlicense**
- **CC0-1.0**

### 2.2 Restricted Licenses (Review Required)
The following licenses require explicit approval from a Release Reliability lead (Jules03) before integration:
- **LGPL** (GNU Lesser General Public License)
- **MPL** (Mozilla Public License)
- **EPL** (Eclipse Public License)

### 2.3 Disallowed Licenses (Copyleft/Viral/Proprietary)
The following licenses are **prohibited** as they may impose unacceptable requirements on our proprietary or core trading logic:
- **GPL** (v2 or v3)
- **AGPL**
- **SSPL**
- **Proprietary / Commercial** (unless a specific license has been purchased and documented)

## 3. Attribution Requirements
All third-party components must maintain proper attribution:
1. **License Files:** Original `LICENSE` files from integrated repositories must be preserved.
2. **Code Headers:** Files derived from external sources must include a header comment referencing the original source and license.
3. **Documentation:** Significant integrations must be listed in `docs/ATTRIBUTIONS.md`.

## 4. Automated Compliance
Compliance is enforced via:
- **CI Scanning:** `.github/workflows/license-check.yml` scans all Python dependencies on every pull request.
- **Fail-Fast Policy:** The CI pipeline will fail if any "Disallowed" license is detected in the dependency tree.

## 5. Dependency Management
- All new dependencies must be checked against this policy before being added to `requirements.txt`.
- A fresh license report is generated during the release process and stored in `docs/DEPENDENCY_LICENSES.md`.

---
*Last Updated: 2024-05-22*
*Owner: Jules03 (Release Reliability & Governance)*
