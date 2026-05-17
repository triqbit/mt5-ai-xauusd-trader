# Acceptance Criteria: Cross-Agent Harmonization & API Standardization

## Functional Acceptance Criteria
- **Behavior:**
    - Resolve functional overlaps and API drift between autonomous agents (Jules01-04) to maintain a coherent single-product vision.
    - Standardize cross-module interfaces using Pydantic models or established Protocol/Abstract Base Classes (e.g., `BaseModel` for AI models, `RiskDecision` for risk results).
    - Synchronize domain-specific terminology across logging, documentation, and source code (e.g., "lot size" vs "position size").
    - Reconcile conflicting feature implementations (e.g., ensuring both ML and Macro signals use the same centralized `ExecutionFilter`).
- **Edge Cases:**
    - Handle scenarios where two agents propose different architectural patterns for the same problem (e.g., Async vs Sync database access).
    - Resolve "Circular Import" dependencies introduced by cross-agent module integration.
- **Inputs/Outputs:**
    - **Inputs:** PRs from Jules01-04, Product Coherence Audit results.
    - **Outputs:** Harmonized code base with unified APIs and zero redundant component clusters.

## Technical Acceptance
- **Test Coverage:**
    - Integration tests covering the full "Signal to Execution" pipeline, ensuring no data type or contract mismatches between modules authored by different agents.
    - Verification that all agents' work passes a unified test suite (no "agent-specific" silos).
- **Performance:**
    - Unified APIs must not introduce additional latency compared to legacy/fragmented implementations.
- **Error Handling:**
    - Standardize exception hierarchy across all modules to ensure consistent error trapping and reporting.
- **Observability:**
    - Ensure unified logging format (`structlog`) is used by all agents' code for consistent trace correlation.

## Operational Acceptance
- **Documentation:**
    - Authoritative interface definitions in `docs/architecture/API_STANDARDS.md`.
- **Configuration:**
    - Standardize configuration keys in `TradingConfig` to avoid duplicate or conflicting settings.
- **Rollback:**
    - N/A (Consolidation requirement).
- **Monitoring:**
    - Track "API Consistency Score" in the process integrity dashboard.

## Release Readiness
- **Deployment:** Mandatory requirement for every Release Candidate (RC).
- **Backward Compatibility:** Harmonization must preserve core functionality for existing configurations.
- **Migration:** All fragmented legacy modules (e.g., `risk_engine.py` vs `risk_manager.py`) must be merged and deprecated.
- **Sign-off:** Requires approval from the Product Steward (Jules05).
