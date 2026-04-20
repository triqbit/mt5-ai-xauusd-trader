"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/lstm_model.py
LSTM-based sequence model for price prediction.
"""

import torch
import torch.nn as nn
import numpy as np
from typing import Optional, Union
from pathlib import Path

from src.models.base_model import BaseModel, Signal

class LSTMNet(nn.Module):
    """
    PyTorch LSTM network for sequence processing.
    """
    def __init__(self, input_size: int, hidden_size: int = 64, num_layers: int = 2, output_size: int = 3):
        super(LSTMNet, self).__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, seq_len, input_size)
        out, _ = self.lstm(x)
        # Take the last time step output
        out = self.fc(out[:, -1, :])
        return out

class LSTMModel(BaseModel):
    """
    LSTM sequence model wrapper.
    """
    def __init__(self, input_size: int = 140, hidden_size: int = 64,
                 model_path: Optional[Union[str, Path]] = None, device: str = "cpu"):
        self.device = torch.device(device)
        self.model = LSTMNet(input_size, hidden_size).to(self.device)

        if model_path and Path(model_path).exists():
            self.model.load_state_dict(
                torch.load(model_path, map_location=self.device, weights_only=True)
            )

        self.model.eval()

    def predict(self, features: np.ndarray) -> Signal:
        """
        Predict trading signal from sequence of features.

        Args:
            features: Input features. Expects (seq_len, input_size)
                     but handles flattening if needed.

        Returns:
            Signal object.
        """
        # If features are flattened (as in TradingEnv), we might need to reshape
        # For simplicity, if it's 1D, we assume it's one step or needs reshaping
        # Production-ready models would know their expected input shape.

        with torch.no_grad():
            # Convert to tensor and add batch dimension
            x = torch.FloatTensor(features).to(self.device)
            if x.dim() == 1:
                x = x.unsqueeze(0).unsqueeze(0) # (1, 1, input_size)
            elif x.dim() == 2:
                x = x.unsqueeze(0) # (1, seq_len, input_size)

            logits = self.model(x)
            probs = torch.softmax(logits, dim=-1).cpu().numpy()[0]

            action_idx = int(np.argmax(probs))
            confidence = float(probs[action_idx])

            # 0=Hold, 1=Buy, 2=Sell
            direction_map = {0: 0, 1: 1, 2: -1}
            direction = direction_map[action_idx]

            return Signal(direction=direction, confidence=confidence)
