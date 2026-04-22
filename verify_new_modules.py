
import pandas as pd
import numpy as np
from src.core.feature_engineering import FeatureEngineer
from src.trading.execution_filter import ExecutionFilter
from src.trading.backtester import Backtester

def test_feature_engineering():
    print("Testing FeatureEngineer...")
    df = pd.DataFrame({
        "time": pd.date_range(start="2023-01-01", periods=500, freq="5min"),
        "open": np.random.randn(500).cumsum() + 2000,
        "high": np.random.randn(500).cumsum() + 2005,
        "low": np.random.randn(500).cumsum() + 1995,
        "close": np.random.randn(500).cumsum() + 2000,
        "tick_volume": np.random.randint(100, 1000, 500)
    })
    fe = FeatureEngineer()
    try:
        df_feat = fe.generate_features(df)
        print(f"Features generated: {len(df_feat.columns)}")
        df_norm = fe.normalize_features(df_feat)
        print("Normalization successful.")
        return True
    except Exception as e:
        print(f"FeatureEngineer test failed: {e}")
        return False

def test_execution_filter():
    print("Testing ExecutionFilter...")
    # Minimal DF for execution filter (needs high/low/close for ATR/RSI)
    df = pd.DataFrame({
        "high": np.random.randn(200).cumsum() + 2005,
        "low": np.random.randn(200).cumsum() + 1995,
        "close": np.random.randn(200).cumsum() + 2000,
    })
    ef = ExecutionFilter()
    try:
        decision = ef.validate(df, direction=1)
        print(f"Decision: {decision}")
        return True
    except Exception as e:
        print(f"ExecutionFilter test failed: {e}")
        return False

if __name__ == "__main__":
    fe_ok = test_feature_engineering()
    ef_ok = test_execution_filter()
    if fe_ok and ef_ok:
        print("Verification script PASSED.")
    else:
        print("Verification script FAILED.")
