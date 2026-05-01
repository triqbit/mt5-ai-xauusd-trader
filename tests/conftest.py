import sys
from unittest.mock import MagicMock

import numpy as np

# Create a robust mock for talib
mock_talib = MagicMock()


def dummy_1_array(x, *args, **kwargs):
    return np.zeros(len(x))


def dummy_3_arrays(x, *args, **kwargs):
    return (np.zeros(len(x)), np.zeros(len(x)), np.zeros(len(x)))


def dummy_2_arrays(x, *args, **kwargs):
    return (np.zeros(len(x)), np.zeros(len(x)))


mock_talib.RSI.side_effect = dummy_1_array
mock_talib.MACD.side_effect = dummy_3_arrays
mock_talib.SMA.side_effect = dummy_1_array
mock_talib.EMA.side_effect = dummy_1_array
mock_talib.ATR.side_effect = lambda high, low, close, **kwargs: np.zeros(len(close))
mock_talib.BBANDS.side_effect = dummy_3_arrays
mock_talib.ADX.side_effect = lambda high, low, close, **kwargs: np.zeros(len(close))
mock_talib.STOCH.side_effect = lambda high, low, close, **kwargs: (
    np.zeros(len(close)),
    np.zeros(len(close)),
)
mock_talib.OBV.side_effect = lambda close, vol: np.zeros(len(close))

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

mock_mt5 = MagicMock()
mock_mt5.TIMEFRAME_M1 = 1
mock_mt5.TIMEFRAME_M5 = 5
mock_mt5.TIMEFRAME_M15 = 15
mock_mt5.TIMEFRAME_H1 = 16385
mock_mt5.ORDER_TYPE_BUY = 0
mock_mt5.ORDER_TYPE_SELL = 1
mock_mt5.SYMBOL_FILLING_IOC = 1
mock_mt5.ORDER_FILLING_IOC = 1
mock_mt5.ORDER_TIME_GTC = 0
sys.modules["MetaTrader5"] = mock_mt5
