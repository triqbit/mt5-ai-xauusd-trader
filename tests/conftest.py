import sys
from unittest.mock import MagicMock

import numpy as np

# Mock talib before any imports
mock_talib = MagicMock()

# Mock telegram
sys.modules["telegram"] = MagicMock()
sys.modules["telegram.ext"] = MagicMock()

# Setup common TA-Lib functions to return expected types matching input length
mock_talib.RSI.side_effect = lambda x, **kwargs: np.zeros(len(x))
mock_talib.MACD.side_effect = lambda x, *args, **kwargs: (
    np.zeros(len(x)),
    np.zeros(len(x)),
    np.zeros(len(x)),
)
mock_talib.SMA.side_effect = lambda x, **kwargs: np.zeros(len(x))
mock_talib.EMA.side_effect = lambda x, **kwargs: np.zeros(len(x))
mock_talib.ATR.side_effect = lambda h, lo, c, **kwargs: np.zeros(len(c))
mock_talib.BBANDS.side_effect = lambda x, **kwargs: (
    np.zeros(len(x)),
    np.zeros(len(x)),
    np.zeros(len(x)),
)
mock_talib.ADX.side_effect = lambda h, lo, c, **kwargs: np.zeros(len(c))
mock_talib.PLUS_DI.side_effect = lambda h, lo, c, **kwargs: np.zeros(len(c))
mock_talib.MINUS_DI.side_effect = lambda h, lo, c, **kwargs: np.zeros(len(c))
mock_talib.STOCH.side_effect = lambda h, lo, c, **kwargs: (np.zeros(len(c)), np.zeros(len(c)))
mock_talib.OBV.side_effect = lambda c, v: np.zeros(len(c))
mock_talib.MFI.side_effect = lambda h, lo, c, v, **kwargs: np.zeros(len(c))
mock_talib.CCI.side_effect = lambda h, lo, c, **kwargs: np.zeros(len(c))
mock_talib.MOM.side_effect = lambda c, **kwargs: np.zeros(len(c))
mock_talib.WILLR.side_effect = lambda h, lo, c, **kwargs: np.zeros(len(c))
mock_talib.ULTOSC.side_effect = lambda h, lo, c, **kwargs: np.zeros(len(c))
mock_talib.LINEARREG_SLOPE.side_effect = lambda x, **kwargs: np.zeros(len(x))
mock_talib.HT_TRENDLINE.side_effect = lambda x: np.zeros(len(x))
mock_talib.HT_DCPERIOD.side_effect = lambda x: np.zeros(len(x))
mock_talib.HT_PHASOR.side_effect = lambda x: (np.zeros(len(x)), np.zeros(len(x)))
mock_talib.HT_SINE.side_effect = lambda x: (np.zeros(len(x)), np.zeros(len(x)))
mock_talib.HT_TRENDMODE.side_effect = lambda x: np.zeros(len(x))
mock_talib.MAX.side_effect = lambda x, **kwargs: np.zeros(len(x))
mock_talib.MIN.side_effect = lambda x, **kwargs: np.zeros(len(x))
mock_talib.SUM.side_effect = lambda x, **kwargs: np.zeros(len(x))
mock_talib.ROCP.side_effect = lambda x, **kwargs: np.zeros(len(x))

# Mock candle patterns
pattern_list = [
    "CDL2CROWS",
    "CDL3BLACKCROWS",
    "CDL3INSIDE",
    "CDL3LINESTRIKE",
    "CDL3OUTSIDE",
    "CDL3STARSINSOUTH",
    "CDL3WHITESOLDIERS",
    "CDLABANDONEDBABY",
    "CDLADVANCEBLOCK",
    "CDLBELTHOLD",
    "CDLBREAKAWAY",
    "CDLCLOSINGMARUBOZU",
    "CDLCONCEALBABYSWALL",
    "CDLCOUNTERATTACK",
    "CDLDARKCLOUDCOVER",
    "CDLDOJI",
    "CDLDOJISTAR",
    "CDLDRAGONFLYDOJI",
    "CDLENGULFING",
    "CDLEVENINGDOJISTAR",
    "CDLEVENINGSTAR",
    "CDLGAPSIDESIDEWHITE",
    "CDLGRAVESTONEDOJI",
    "CDLHAMMER",
    "CDLHANGINGMAN",
    "CDLHARAMI",
    "CDLHARAMICROSS",
    "CDLHIGHWAVE",
    "CDLHIKKAKE",
    "CDLHIKKAKEMOD",
    "CDLHOMINGPIGEON",
    "CDLIDENTICAL3CROWS",
    "CDLINNECK",
    "CDLINVERTEDHAMMER",
    "CDLKICKING",
    "CDLKICKINGBYLENGTH",
    "CDLLADDERBOTTOM",
    "CDLLONGLEGGEDDOJI",
    "CDLLONGLINE",
    "CDLMARUBOZU",
    "CDLMATCHINGLOW",
    "CDLMATHOLD",
    "CDLMORNINGDOJISTAR",
    "CDLMORNINGSTAR",
    "CDLONNECK",
    "CDLPIERCING",
    "CDLRICKSHAWMAN",
    "CDLRISEFALL3METHODS",
    "CDLSEPARATINGLINES",
    "CDLSHOOTINGSTAR",
    "CDLSHORTLINE",
    "CDLSPINNINGTOP",
    "CDLSTALLEDPATTERN",
    "CDLSTICKSANDWICH",
    "CDLTAKURI",
    "CDLTASUKIGAP",
    "CDLTHRUSTING",
    "CDLTRISTAR",
    "CDLUNIQUE3RIVER",
    "CDLUPSIDEGAP2CROWS",
    "CDLXSIDEGAP3METHODS",
]

mock_talib.get_function_groups.return_value = {"Pattern Recognition": pattern_list}
for pattern in pattern_list:
    setattr(mock_talib, pattern, lambda *args: np.zeros(len(args[0])))

sys.modules["talib"] = mock_talib

# Mock MetaTrader5 (Windows only)
mock_mt5 = MagicMock()
sys.modules["MetaTrader5"] = mock_mt5

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
