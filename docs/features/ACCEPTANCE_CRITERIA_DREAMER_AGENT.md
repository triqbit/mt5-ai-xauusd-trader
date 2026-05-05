# Acceptance Criteria: Dreamer Agent (World Model RL)

## Functional Acceptance Criteria
- **Behavior:**
    - Interface for model-based reinforcement learning using the DreamerV3 architecture.
    - Maintain a recurrent latent state across trading steps.
    - Support state resets at the beginning of trading sessions or episodes.
- **Edge Cases:**
    - (Current) Placeholder mode: Must return a neutral `HOLD` signal with 0% confidence until full implementation.
    - Correctly handle latent state updates (`update_state`) even in placeholder mode.
- **Inputs/Outputs:**
    - **Inputs:** Market observation features, previous action, reward, and terminal flag.
    - **Outputs:** `Signal` object.

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for the wrapper interface and state reset logic.
    - Mock tests for latent state transitions.
- **Performance:**
    - (Target) Inference including state update < 200ms.
- **Error Handling:**
    - Logging of implementation stubs and placeholder status.
- **Observability:**
    - Log every latent state reset.
    - Explicitly flag "World Model Inference Not Implemented" in signal metadata.

## Operational Acceptance
- **Documentation:**
    - Technical roadmap for transitioning from placeholder to full DreamerV3 implementation.
- **Configuration:**
    - Placeholder configuration dictionary support.
- **Rollback:**
    - N/A (Currently in development/placeholder state).
- **Monitoring:**
    - N/A.

## Release Readiness
- **Deployment:** Deployed as a stub/placeholder to ensure ensemble interface compatibility.
- **Backward Compatibility:** Must adhere to the `BaseModel` prediction signature.
- **Migration:** No data migration.
- **Sign-off:** Requires approval from the ML Research Lead (Jules01).
