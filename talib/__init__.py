import numpy as np
def RSI(close, timeperiod=14): return np.full_like(close, 60.0)
def MACD(close, fastperiod=12, slowperiod=26, signalperiod=9): return np.zeros_like(close), np.zeros_like(close), np.zeros_like(close)
def ATR(high, low, close, timeperiod=14): return np.full_like(close, 1.0)
def BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0): return np.zeros_like(close), np.zeros_like(close), np.zeros_like(close)
def EMA(close, timeperiod=30):
    if timeperiod == 8: return np.full_like(close, 2010.0)
    if timeperiod == 21: return np.full_like(close, 2005.0)
    if timeperiod == 50: return np.full_like(close, 2000.0)
    if timeperiod == 200: return np.full_like(close, 1990.0)
    return np.zeros_like(close)
def ADX(high, low, close, timeperiod=14): return np.zeros_like(close)
def STOCH(high, low, close, **kwargs): return np.zeros_like(close), np.zeros_like(close)
def OBV(close, volume): return np.zeros_like(close)
def get_function_groups(): return {'Pattern Recognition': []}
