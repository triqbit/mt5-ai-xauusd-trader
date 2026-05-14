# Acceptance Criteria: Observability & Trace Correlation

## Purpose
To ensure that every trading signal can be traced through the entire pipeline (generation -> filtering -> risk -> execution -> logging) using a unique correlation ID, and to unify the decision-making data structures.

## Core Requirements

### 1. Trace ID Propagation
- [x] Every trade lifecycle MUST have a unique `trace_id` (UUID v4 format).
- [x] The `trace_id` MUST be generated at the start of the trading loop in `main.py`.
- [x] The `trace_id` MUST be propagated through `TradeSignal`, `ExecutionDecision`, and stored in the database via `ModelSignal` and `Trade` tables.
- [x] The first 8 characters of the `trace_id` MUST be included in MetaTrader 5 order comments for brokerage-side correlation (format: `AI:algorithm:trace_id`).

### 2. Unified Decision Modeling
- [x] Use a centralized Pydantic `ExecutionDecision` model in `src/core/schemas.py` to replace fragmented dataclasses.
- [x] `ExecutionDecision` MUST include an explicit `is_approved` boolean to satisfy technical trust and prevent ambiguous decision states.
- [x] All components (ExecutionFilter, SignalExplainer) MUST use the unified Pydantic model.

### 3. Database Integrity
- [x] `model_signals` and `trades` tables MUST include an indexed `trace_id` column.
- [x] `TradeLogger` MUST prioritize the `trace_id` from the signal/execution context over implicit global state where possible.

### 4. Verification
- [x] Automated tests in `tests/test_trace_correlation.py` verify end-to-end ID flow.
- [x] Automated tests in `tests/test_execution_traceability.py` verify that rejection reasons and trace IDs are correctly captured in audit logs.
- [x] Schema governance tests verify that `is_approved` is a mandatory field for decisions.

## Operational Benefit
Reduces root-cause analysis time by allowing engineers to grep logs, query the database, and check brokerage comments using a single, unified ID for any specific trading opportunity.
