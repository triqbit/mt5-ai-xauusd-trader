import sys
from unittest.mock import MagicMock

import numpy as np

# Mock talib before any imports
mock_talib = MagicMock()

# Setup common TA-Lib functions to return expected types matching input length
mock_talib.RSI.side_effect = lambda x, **kwargs: np.zeros(len(x))
mock_talib.MACD.side_effect = lambda x, *args, **kwargs: (np.zeros(len(x)), np.zeros(len(x)), np.zeros(len(x)))
mock_talib.SMA.side_effect = lambda x, **kwargs: np.zeros(len(x))
mock_talib.EMA.side_effect = lambda x, **kwargs: np.zeros(len(x))
mock_talib.ATR.side_effect = lambda h, l, c, **kwargs: np.zeros(len(c))
mock_talib.BBANDS.side_effect = lambda x, **kwargs: (np.zeros(len(x)), np.zeros(len(x)), np.zeros(len(x)))
mock_talib.ADX.side_effect = lambda h, l, c, **kwargs: np.zeros(len(c))
mock_talib.STOCH.side_effect = lambda h, l, c, **kwargs: (np.zeros(len(c)), np.zeros(len(c)))
mock_talib.OBV.side_effect = lambda c, v: np.zeros(len(c))

# Mock candle patterns
pattern_list = [
    'CDL2CROWS', 'CDL3BLACKCROWS', 'CDL3INSIDE', 'CDL3LINESTRIKE', 'CDL3OUTSIDE',
    'CDL3STARSINSOUTH', 'CDL3WHITESOLDIERS', 'CDLABANDONEDBABY', 'CDLADVANCEBLOCK',
    'CDLBELTHOLD', 'CDLBREAKAWAY', 'CDLCLOSINGMARUBOZU', 'CDLCONCEALBABYSWALL',
    'CDLCOUNTERATTACK', 'CDLDARKCLOUDCOVER', 'CDLDOJI', 'CDLDOJISTAR', 'CDLDRAGONFLYDOJI',
    'CDLENGULFING', 'CDLEVENINGDOJISTAR', 'CDLEVENINGSTAR', 'CDLGAPSIDESIDEWHITE',
    'CDLGRAVESTONEDOJI', 'CDLHAMMER', 'CDLHANGINGMAN', 'CDLHARAMI', 'CDLHARAMICROSS',
    'CDLHIGHWAVE', 'CDLHIKKAKE', 'CDLHIKKAKEMOD', 'CDLHOMINGPIGEON', 'CDLIDENTICAL3CROWS',
    'CDLINNECK', 'CDLINVERTEDHAMMER', 'CDLKICKING', 'CDLKICKINGBYLENGTH', 'CDLLADDERBOTTOM',
    'CDLLONGLEGGEDDOJI', 'CDLLONGLINE', 'CDLMARUBOZU', 'CDLMATCHINGLOW', 'CDLMATHOLD',
    'CDLMORNINGDOJISTAR', 'CDLMORNINGSTAR', 'CDLONNECK', 'CDLPIERCING', 'CDLRICKSHAWMAN',
    'CDLRISEFALL3METHODS', 'CDLSEPARATINGLINES', 'CDLSHOOTINGSTAR', 'CDLSHORTLINE',
    'CDLSPINNINGTOP', 'CDLSTALLEDPATTERN', 'CDLSTICKSANDWICH', 'CDLTAKURI', 'CDLTASUKIGAP',
    'CDLTHRUSTING', 'CDLTRISTAR', 'CDLUNIQUE3RIVER', 'CDLUPSIDEGAP2CROWS', 'CDLXSIDEGAP3METHODS'
]

mock_talib.get_function_groups.return_value = {"Pattern Recognition": pattern_list}
for pattern in pattern_list:
    setattr(mock_talib, pattern, lambda *args: np.zeros(len(args[0])))

sys.modules["talib"] = mock_talib

# Mock MetaTrader5 (Windows only)
mock_mt5 = MagicMock()
sys.modules["MetaTrader5"] = mock_mt5

# Mock torch (heavy dependency)
mock_torch = MagicMock()
mock_torch.from_numpy.side_effect = lambda x: MagicMock()
mock_torch.FloatTensor.side_effect = lambda x: MagicMock()
mock_torch.tensor.side_effect = lambda x: MagicMock()


# Helper to mock argmax(...).item()
def mock_argmax(*args, **kwargs):
    m = MagicMock()
    m.item.return_value = 0  # Default to index 0 (BUY in transformer map)
    return m


mock_torch.argmax.side_effect = mock_argmax
sys.modules["torch"] = mock_torch

# Mock torch.nn
mock_nn = MagicMock()


class MockModule:
    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return self.forward(*args, **kwargs)

    def forward(self, *args, **kwargs):
        # Default mock output for LSTMAttentionModel forward
        m = MagicMock()
        m.shape = (2, 3)
        return m

    def to(self, *args, **kwargs):
        return self

    def eval(self, *args, **kwargs):
        return self

    def load_state_dict(self, *args, **kwargs):
        pass

    def cpu(self, *args, **kwargs):
        return self

    def numpy(self, *args, **kwargs):
        return np.zeros((2, 3))


mock_nn.Module = MockModule
sys.modules["torch.nn"] = mock_nn
mock_torch.nn = mock_nn

# Mock other torch.nn components used in ensemble.py
for name in ["LSTM", "MultiheadAttention", "LayerNorm", "Sequential", "Linear", "GELU", "Dropout"]:
    mock_component_class = MagicMock()
    mock_instance = MagicMock()
    if name == "LSTM":
        # LSTM should return (output, (h_n, c_n))
        res = MagicMock()
        res.mean.return_value = MagicMock()
        mock_instance.return_value = (res, (MagicMock(), MagicMock()))
    elif name == "MultiheadAttention":
        # MultiheadAttention should return (output, weights)
        mock_instance.return_value = (MagicMock(), MagicMock())
    elif name == "Sequential":
        res = MagicMock()
        res.shape = (2, 3)
        mock_instance.return_value = res
    mock_component_class.return_value = mock_instance
    setattr(mock_nn, name, mock_component_class)

# Mock torch.softmax and other functions
mock_torch.softmax.side_effect = lambda x, dim=-1: x
mock_torch.randn.side_effect = lambda *args: MagicMock()
mock_torch.device.side_effect = lambda x: MagicMock()

# Add specific MT5 constants that might be used
mock_mt5.TIMEFRAME_M5 = 5
mock_mt5.TIMEFRAME_M15 = 15
mock_mt5.TIMEFRAME_H1 = 16385
mock_mt5.ORDER_TYPE_BUY = 0
mock_mt5.ORDER_TYPE_SELL = 1
mock_mt5.SYMBOL_FILLING_IOC = 1
mock_mt5.ORDER_FILLING_IOC = 1
mock_mt5.ORDER_TIME_GTC = 0

# Mock trade_logger to avoid real DB if needed, but integration tests usually want a real :memory: DB
