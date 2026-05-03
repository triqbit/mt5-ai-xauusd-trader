"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/lstm_model.py
LSTM sequence model using PyTorch for short-term price prediction.
"""

import logging
from pathlib import Path
from typing import Any, Optional, Union

import numpy as np

try:
    import torch
    import torch.nn as nn
except ImportError:
    torch = None
    nn = None

from src.core.constants import SignalDirection
from src.models.base_model import BaseModel, Signal


class LSTMPricePredictor(nn.Module if nn else object):
    """
    Simple LSTM-based neural network for price direction prediction.

    Attributes:
        lstm: LSTM layer for processing temporal sequences.
        fc: Fully connected layer for classification (HOLD, BUY, SELL).
    """

    def __init__(
        self, input_dim: int, hidden_dim: int = 64, num_layers: int = 2
    ) -> None:
        """
        Initializes the LSTM architecture.

        Args:
            input_dim: Number of input features per time step.
            hidden_dim: Number of hidden units in LSTM layers.
            num_layers: Number of recurrent layers.

        Raises:
            ImportError: If PyTorch is not installed.
        """
        if not nn:
            raise ImportError("PyTorch is required for LSTMPricePredictor")
        super().__init__()
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_dim, 3)  # Outputs: [hold, buy, sell]

    def forward(self, x: Any) -> Any:
        """
        Forward pass of the network.

        Args:
            x: Input tensor of shape (batch, seq_len, input_dim).

        Returns:
            Logits for each class (HOLD, BUY, SELL).
        """
        # lstm output: (batch, seq_len, hidden_dim)
        # hn: (num_layers, batch, hidden_dim)
        _, (hn, _) = self.lstm(x)

        # Use the hidden state from the last layer and last time step
        out = self.fc(hn[-1])
        return out


class LSTMModel(BaseModel):
    """
    Wrapper for LSTMPricePredictor implementing the BaseModel interface.

    Attributes:
        logger: Logger instance for monitoring model activity.
        device: Torch device (cpu or cuda).
        model: LSTMPricePredictor instance.
    """

    def __init__(
        self,
        input_dim: int = 140,
        hidden_dim: int = 64,
        num_layers: int = 2,
        model_path: Optional[Union[str, Path]] = None,
        device: str = "cpu",
    ) -> None:
        """
        Initializes the LSTMModel wrapper.

        Args:
            input_dim: Number of input features per time step.
            hidden_dim: Number of hidden units in LSTM layers.
            num_layers: Number of recurrent layers.
            model_path: Optional path to a pre-trained model checkpoint (.pt or .pth).
            device: Computing device to use ('cpu', 'cuda', 'auto').
        """
        self.logger = logging.getLogger(__name__)

        # Device selection logic
        if torch:
            if device == "auto":
                self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            else:
                self.device = torch.device(device)
        else:
            self.device = None

        self.model = None

        if torch:
            try:
                self.model = LSTMPricePredictor(
                    input_dim, hidden_dim, num_layers
                ).to(self.device)

                if model_path and Path(model_path).exists():
                    self.logger.info(f"Loading LSTM model from {model_path}")
                    self.model.load_state_dict(
                        torch.load(model_path, map_location=self.device)
                    )
                    self.model.eval()
                else:
                    self.logger.debug("LSTMModel initialized with random weights.")

            except Exception as e:
                self.logger.error(f"Failed to initialize LSTM model: {e}")
                self.model = None
        else:
            self.logger.warning("PyTorch not found. LSTMModel is disabled.")

    def predict(self, features: np.ndarray) -> Signal:
        """
        Predicts price direction using the LSTM network.

        Args:
            features: Input features array of shape (seq_len, n_features)
                      or (batch, seq_len, n_features).

        Returns:
            A Signal object with direction, confidence, and probability distribution.
        """
        if self.model is None or not torch:
            return Signal(
                direction=SignalDirection.HOLD,
                confidence=0.0,
                metadata={"error": "Model not initialized or PyTorch missing"},
            )

        try:
            # Ensure input is a torch tensor and moved to the correct device
            x = torch.from_numpy(features).float().to(self.device)

            # Handle (seq_len, n_features) -> (1, seq_len, n_features)
            if x.dim() == 2:
                x = x.unsqueeze(0)
            elif x.dim() != 3:
                raise ValueError(
                    f"Expected 2D or 3D input, got {x.dim()}D with shape {x.shape}"
                )

            self.model.eval()
            with torch.no_grad():
                logits = self.model(x)
                probs = torch.softmax(logits, dim=-1).cpu().numpy()[0]

            action_idx = np.argmax(probs)
            confidence = float(probs[action_idx])

            # Mapping: 0 -> HOLD, 1 -> BUY, 2 -> SELL
            direction_map = {
                0: SignalDirection.HOLD,
                1: SignalDirection.BUY,
                2: SignalDirection.SELL,
            }

            return Signal(
                direction=direction_map.get(action_idx, SignalDirection.HOLD),
                confidence=confidence,
                metadata={
                    "probabilities": probs.tolist(),
                    "device": str(self.device),
                },
            )

        except Exception as e:
            self.logger.exception(f"Error during LSTM prediction: {e}")
            return Signal(
                direction=SignalDirection.HOLD,
                confidence=0.0,
                metadata={"error": str(e)},
            )

    def save(self, path: Union[str, Path]) -> None:
        """
        Saves the model weights to the specified path.

        Args:
            path: Target file path for the state dictionary.
        """
        if self.model is not None and torch:
            torch.save(self.model.state_dict(), path)
            self.logger.info(f"LSTM model saved to {path}")
        else:
            self.logger.error("Attempted to save LSTMModel but no model is loaded.")
