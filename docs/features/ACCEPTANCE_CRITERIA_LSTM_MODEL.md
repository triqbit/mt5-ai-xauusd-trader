# Acceptance Criteria: LSTM Model (Sequential Prediction)

## Functional Acceptance Criteria
- **Behavior:**
    - Predict price direction (Buy/Sell/Hold) based on temporal sequences of technical indicators.
    - Support both standard LSTM and Attention-based LSTM architectures.
    - Output standardized `Signal` objects with direction and confidence (probabilities).
- **Edge Cases:**
    - Handle missing PyTorch installation by disabling the model gracefully.
    - Handle inputs with incorrect dimensions (must support both 2D and 3D feature arrays).
    - Provide fallback neutral signals on inference error.
- **Inputs/Outputs:**
    - **Inputs:** NumPy array of features (seq_len, n_features).
    - **Outputs:** `Signal` object (direction, confidence, probabilities).

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for both `LSTMPricePredictor` and `LSTMAttentionModel` (forward pass).
    - Integration tests for `LSTMModel` wrapper (prediction, loading/saving).
    - Minimum 85% coverage for `src/models/lstm_model.py`.
- **Performance:**
    - Inference latency < 50ms on CPU for a single observation.
- **Error Handling:**
    - Exception handling for model loading (file not found, shape mismatch).
- **Observability:**
    - Log device placement (CPU/CUDA) and model version at startup.
    - Log probabilities for each action in `DEBUG` mode.

## Operational Acceptance
- **Documentation:**
    - Model architecture summary (layers, hidden units, attention heads).
    - Feature indexing requirements for the input vector.
- **Configuration:**
    - Configurable `hidden_dim`, `num_layers`, and `model_path`.
- **Rollback:**
    - Revert to a previous `.pt` checkpoint if performance degrades.
- **Monitoring:**
    - Monitor prediction confidence distribution to detect "certainty drift".

## Release Readiness
- **Deployment:** Requires PyTorch 2.x and valid model weights in the artifact store.
- **Backward Compatibility:** Must support the `BaseModel` abstract interface.
- **Migration:** Legacy checkpoints may require permutation of the output layer (hold, buy, sell).
- **Sign-off:** Requires approval from the ML Research Lead (Jules01).
