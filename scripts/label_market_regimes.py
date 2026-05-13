"""
MT5 AI/ML Trading Bot - Enterprise Edition
scripts/label_market_regimes.py

Institutional-grade (Validated) CLI utility for historical market regime labeling.
Processes OHLCV data and adds regime-based annotations for research and model training.

Usage:
    python scripts/label_market_regimes.py --input data.csv --output labeled_data.csv --window 20
"""

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))

import structlog

from src.models.regime_detector import RegimeDetector

logger = structlog.get_logger(__name__)


def label_data(
    input_path: str, output_path: str, window: int, long_window: int, use_gmm: str | None
):
    """
    Labels historical OHLCV data with market regimes.
    """
    if not os.path.exists(input_path):
        logger.error("input_file_not_found", path=input_path)
        return

    logger.info("loading_data", path=input_path)
    # Detect separator (comma or tab)
    try:
        df = pd.read_csv(input_path)
        if len(df.columns) < 2:
            df = pd.read_csv(input_path, sep="\t")
    except Exception as e:
        logger.error("data_load_failed", error=str(e))
        return

    # Check for required columns
    required = ["open", "high", "low", "close"]
    missing = [col for col in required if col not in df.columns.map(str.lower)]
    if missing:
        logger.error("missing_required_columns", missing=missing)
        return

    # Normalize column names to lowercase
    df.columns = [col.lower() for col in df.columns]

    detector = RegimeDetector(window=window, long_window=long_window)

    if use_gmm and os.path.exists(use_gmm):
        logger.info("loading_gmm_model", path=use_gmm)
        detector.load_model(use_gmm)
    elif use_gmm:
        logger.warning("gmm_model_not_found_fitting_new", path=use_gmm)
        detector.fit(df)
        detector.save_model(use_gmm)

    logger.info("labeling_history", bars=len(df))
    labeled_df = detector.label_history(df, use_vectorized=True)

    logger.info("saving_labeled_data", path=output_path)
    labeled_df.to_csv(output_path, index=False)

    # Generate analysis report
    report = detector.run_analysis(labeled_df)
    logger.info("regime_distribution", counts=report.counts_pct)

    print("\nRegime Distribution:")
    for label, pct in report.counts_pct.items():
        print(f"  {label:20}: {pct:5.2f}%")


def main():
    parser = argparse.ArgumentParser(description="Label historical OHLCV data with market regimes.")
    parser.add_argument("--input", required=True, help="Path to input OHLCV CSV file")
    parser.add_argument("--output", required=True, help="Path to save labeled CSV file")
    parser.add_argument(
        "--window", type=int, default=20, help="Lookback window for features (default: 20)"
    )
    parser.add_argument(
        "--long-window",
        type=int,
        default=100,
        help="Long lookback window for ATR ratio (default: 100)",
    )
    parser.add_argument(
        "--model",
        help="Optional path to GMM model file. If provided and doesn't exist, a model will be trained and saved.",
    )

    args = parser.parse_args()

    label_data(args.input, args.output, args.window, args.long_window, args.model)


if __name__ == "__main__":
    main()
