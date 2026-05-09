"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/lstm_model.py
LSTM sequence model using PyTorch for short-term price prediction.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

try:
    import torch
    import torch.nn as nn
except ImportError:
    torch = None
    nn = None

if TYPE_CHECKING:
    import torch

from src.core.constants import ModelAction, SignalDirection
from src.models.base_model import BaseModel, Signal


class LSTMAttentionModel(nn.Module if nn else object):
    """
    Bidirectional LSTM with multi-head self-attention.

    Architecture:
        1. Bidirectional LSTM for temporal feature extraction.
        2. Multi-head Self-Attention to focus on critical time steps.
        3. Layer Normalization and Residual connection.
        4. Global Average Pooling.
        5. Fully Connected head for 3-class classification (HOLD, BUY, SELL).

    Input: (batch, seq_len, n_features)
    Output: (batch, 3) -> [HOLD_logit, BUY_logit, SELL_logit]
    """

    def __init__(
        self,
        n_features: int = 140,
        hidden_size: int = 128,
        num_layers: int = 2,
        n_heads: int = 8,
        dropout: float = 0.2,
    ) -> None:
        """
        Initializes the Attention-based LSTM model.

        Args:
            n_features: Number of input features per time step.
            hidden_size: Hidden dimension of LSTM layers.
            num_layers: Number of stacked LSTM layers.
            n_heads: Number of attention heads.
            dropout: Dropout probability.

        Raises:
            ImportError: If PyTorch is not installed.
        """
        if not nn:
            raise ImportError("PyTorch is required for LSTMAttentionModel")
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=n_features,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.attn = nn.MultiheadAttention(
            embed_dim=hidden_size * 2,
            num_heads=n_heads,
            dropout=dropout,
            batch_first=True,
        )
        self.norm = nn.LayerNorm(hidden_size * 2)
        self.head = nn.Sequential(
            nn.Linear(hidden_size * 2, 64),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(64, 3),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass of the LSTMAttentionModel.

        Args:
            x: Input tensor of shape (batch, seq_len, n_features).

        Returns:
            Logits of shape (batch, 3).
        """
        out, _ = self.lstm(x)  # (B, T, 2*H)
        attn_out, _ = self.attn(out, out, out)
        out = self.norm(out + attn_out)  # residual
        pooled = out.mean(dim=1)  # global average pool
        return self.head(pooled)  # (B, 3)


class LSTMPricePredictor(nn.Module if nn else object):
    """
    Standard LSTM-based neural network for price direction prediction.

    Simple architecture using the final hidden state of an LSTM for classification.

    Attributes:
        lstm: LSTM layer for processing temporal sequences.
        fc: Fully connected layer for classification (HOLD, BUY, SELL).
    """

    def __init__(self, input_dim: int, hidden_dim: int = 64, num_layers: int = 2) -> None:
        """
        Initializes the standard LSTM architecture.

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

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass of the network.

        Args:
            x: Input tensor of shape (batch, seq_len, input_dim).

        Returns:
            Logits for each class (HOLD, BUY, SELL).
        """
        # hn: (num_layers, batch, hidden_dim)
        _, (hn, _) = self.lstm(x)

        # Use the hidden state from the last layer and last time step
        out = self.fc(hn[-1])
        return out


class LSTMModel(BaseModel):
    """
    Wrapper for LSTM-based models implementing the BaseModel interface.

    Handles data preprocessing (tensors, device placement) and post-processing
    (probabilities, Signal objects).

    Attributes:
        logger: Logger instance for monitoring model activity.
        device: Torch device (cpu or cuda).
        model: Underlying PyTorch model instance.

    Examples:
        >>> agent = LSTMModel(input_dim=140, use_attention=True)
        >>> signal = agent.predict(np.random.randn(20, 140))
        >>> print(signal.direction)
    """

    def __init__(
        self,
        input_dim: int = 140,
        hidden_dim: int = 64,
        num_layers: int = 2,
        model_path: str | Path | None = None,
        device: str = "cpu",
        use_attention: bool = False,
    ) -> None:
        """
        Initializes the LSTMModel wrapper.

        Args:
            input_dim: Number of input features per time step.
            hidden_dim: Number of hidden units in LSTM layers.
            num_layers: Number of recurrent layers.
            model_path: Optional path to a pre-trained model checkpoint (.pt or .pth).
            device: Computing device to use ('cpu', 'cuda', 'auto').
            use_attention: Whether to use the Attention-based LSTM architecture.
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
                if use_attention:
                    self.logger.info("Initializing LSTMAttentionModel...")
                    self.model = LSTMAttentionModel(
                        n_features=input_dim,
                        hidden_size=hidden_dim,
                        num_layers=num_layers,
                    ).to(self.device)
                else:
                    self.logger.info("Initializing LSTMPricePredictor...")
                    self.model = LSTMPricePredictor(input_dim, hidden_dim, num_layers).to(
                        self.device
                    )

                if model_path and Path(model_path).exists():
                    self.logger.info(f"Loading LSTM model from {model_path}")
                    self.model.load_state_dict(
                        torch.load(model_path, map_location=self.device, weights_only=True)
                    )
                    self.model.eval()
                else:
                    self.logger.debug("LSTMModel initialized with random weights.")

            except Exception as e:
                self.logger.error(f"Failed to initialize LSTM model: {e}")
                self.model = None
        else:
            self.logger.warning("PyTorch not found. LSTMModel is disabled.")

    def predict(self, features: np.ndarray, **kwargs: Any) -> Signal:
        """
        Predicts price direction using the LSTM network.

        Args:
            features: Input features array of shape (seq_len, n_features)
                      or (batch, seq_len, n_features).
            **kwargs: Ignored.

        Returns:
            A Signal object with direction, confidence, and probability distribution.

        Raises:
            ValueError: If features contain NaN/Inf or have invalid shape.
        """
        # Production-grade robustness: Check for NaN or Inf in input features
        if not np.isfinite(features).all():
            self.logger.error("Input features contain NaN or Inf values.")
            return Signal(
                direction=SignalDirection.HOLD,
                confidence=0.0,
                metadata={"error": "Invalid features: NaN or Inf detected"},
            )

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
                self.logger.error(f"Expected 2D or 3D input, got {x.dim()}D with shape {x.shape}")
                return Signal(
                    direction=SignalDirection.HOLD,
                    confidence=0.0,
                    metadata={"error": f"Invalid input shape: {x.shape}"},
                )

            self.model.eval()
            with torch.no_grad():
                logits = self.model(x)
                probs = torch.softmax(logits, dim=-1).cpu().numpy()[0]

            action_idx = int(np.argmax(probs))
            confidence = float(probs[action_idx])

            return Signal(
                direction=ModelAction(action_idx).to_direction(),
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

    def save(self, path: str | Path) -> None:
        """
        Saves the model weights to the specified path.

        Args:
            path: Target file path for the state dictionary.

        Raises:
            IOError: If saving the model fails.
        """
        if self.model is not None and torch:
            torch.save(self.model.state_dict(), path)
            self.logger.info(f"LSTM model saved to {path}")
        else:
            self.logger.error("Attempted to save LSTMModel but no model is loaded.")


__all__ = ["LSTMAttentionModel", "LSTMModel", "LSTMPricePredictor"]
