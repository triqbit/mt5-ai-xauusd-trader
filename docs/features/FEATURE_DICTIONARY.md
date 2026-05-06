# Feature Dictionary

## Overview
This document describes the 140+ technical features engineered by the `FeatureEngineer` class.

## Base Timeframe Features (M1/M5)
Calculated directly on the primary timeframe of the input data.

### Technical Indicators
- **RSI (14)**: Relative Strength Index.
- **MFI (14)**: Money Flow Index.
- **CCI (14)**: Commodity Channel Index.
- **MOM (10)**: Momentum.
- **MACD**: Moving Average Convergence Divergence (12, 26, 9), including Signal and Histogram.
- **ATR (14)**: Average True Range.
- **Bollinger Bands (20, 2)**: Upper, Middle, and Lower bands, plus Band Width.
- **EMA Stacks**: Exponential Moving Averages for periods 8, 21, 50, and 200.
- **EMA Distances**: Percentage distance from price to each EMA.
- **ADX (14)**: Average Directional Index.
- **Williams %R (14)**: Percentage price oscillator.
- **Ultimate Oscillator (7, 14, 28)**: Combined momentum indicator.
- **Stochastic**: Slow K and Slow D (5, 3, 3).
- **Hilbert Transform**: Trendline, DC Period, Phasor (In-Phase/Quad), Sine/Lead Sine, and Trend Mode.
- **Donchian Channels**: High, Low, and Mid bands (20 period).
- **Keltner Channels**: Upper, Lower, and Mid bands (20 EMA, 2x ATR).

### Candle Patterns (60+)
All TA-Lib Pattern Recognition functions computed for both base and MTF data, including but not limited to:
- Doji, Engulfing, Hammer, Morning Star, Shooting Star, etc.

### Price Action
- **Returns**: 1-period and 5-period percentage change.
- **Log Returns**: Natural log of price changes.
- **Day Range**: (High - Low) / Close.
- **Body Size**: (Close - Open) / (High - Low).
- **Rolling Slopes**: Linear regression slopes for 5 and 20 period windows.

### Volume
- **Relative Volume (RVOL)**: Current volume vs 20-period average.
- **VWAP Stacks**: Volume Weighted Average Price for periods 20, 50, and 100.
- **VWAP Distances**: Percentage distance from price to each VWAP.
- **OBV**: On-Balance Volume.
- **VPT**: Volume Price Trend.
- **Volume Profile Proxies**: Point of Control (POC), Value Area High (VAH), and Value Area Low (VAL).

## Multi-Timeframe (MTF) Features
Data is resampled to higher timeframes, indicators are calculated, and then aligned with the base timeframe using a 1-period shift to prevent look-ahead bias.

Supported timeframes: **M1, M5, M15, H1, H4, D1**.

Indicators computed for each timeframe:
- RSI, MACD, ATR, Bollinger Bands, EMA Stacks, ADX, Stochastic.

## Normalization
Features are normalized using either **Z-Score** or **MinMax** scaling, with statistics preserved for inference consistency.
