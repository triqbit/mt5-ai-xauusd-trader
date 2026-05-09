# Acceptance Criteria: License Compliance & Governance

## Functional Acceptance Criteria
- **Behavior:**
    - Automatically scan all project dependencies for license types.
    - Maintain a "Blocklist" of incompatible licenses (e.g., AGPLv3, SSPL).
    - Block PRs that introduce dependencies with incompatible or ambiguous licenses.
    - Generate a "Software Bill of Materials" (SBOM) including license information.
- **Edge Cases:**
    - Handle dual-licensed packages (e.g., MIT/Apache 2.0).
    - Handle dependencies of dependencies (transitive licenses).
- **Inputs/Outputs:**
    - **Inputs:** `requirements.txt`, `pyproject.toml`, License database (e.g., from `pip-licenses`).
    - **Outputs:** License Audit Report, SBOM (CycloneDX/SPDX format).

## Technical Acceptance
- **Test Coverage:**
    - Verification of the license scan CI step using a dummy "bad license" package.
- **Performance:**
    - License scan must complete in < 60 seconds.
- **Error Handling:**
    - Clearly identify the specific package and license causing a failure.
- **Observability:**
    - Periodic license compliance status in the Release Readiness report.

## Operational Acceptance
- **Documentation:**
    - List of pre-approved licenses.
    - Process for requesting a license exception.
- **Configuration:**
    - `LICENSE_BLOCKLIST`: Configurable list of restricted licenses.
- **Rollback:**
    - N/A.
- **Monitoring:**
    - Track "License Debt" (packages with unknown or suspicious licenses).

## Release Readiness
- **Deployment:** Integrated into the CI pipeline.
- **Backward Compatibility:** N/A.
- **Migration:** Retroactive scan of the entire repository history.
- **Sign-off:** Requires approval from the Release Reliability Lead (Jules03) and Legal/Compliance.
