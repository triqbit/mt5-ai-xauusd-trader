import os
import tempfile
import unittest

import numpy as np
import pandas as pd

from src.models.regime_detector import MarketRegime, RegimeDetector


class TestRegimeDetector(unittest.TestCase):
    def setUp(self):
        # Using smaller windows to make test data generation easier
        self.detector = RegimeDetector(window=10, long_window=30)

    def test_ranging_regime(self):
        np.random.seed(42)
        # Random noise around a constant price
        data = pd.DataFrame(
            {
                "close": 2000.0 + np.random.randn(50) * 0.1,
                "high": 2000.2 + np.random.randn(50) * 0.1,
                "low": 1999.8 + np.random.randn(50) * 0.1,
                "open": 2000.0 + np.random.randn(50) * 0.1,
                "tick_volume": np.full(50, 100.0),
            }
        )
        info = self.detector.detect(data)
        self.assertEqual(info.label, MarketRegime.RANGING)

    def test_trending_regime(self):
        # Strong steady trend
        close = np.linspace(2000, 2100, 50)
        data = pd.DataFrame(
            {
                "close": close,
                "high": close + 0.1,
                "low": close - 0.1,
                "open": close - 0.05,
                "tick_volume": np.full(50, 100.0),
            }
        )
        info = self.detector.detect(data)
        self.assertEqual(info.label, MarketRegime.TRENDING)

    def test_news_shock_regime(self):
        # Extreme volatility and high ER
        # Stable then violent moves
        close = np.full(100, 2000.0)
        # Make a very sharp move in one direction to ensure high ER and high ATR ratio
        # Use variable moves to ensure high vol-of-vol
        for i in range(90, 100):
            if i % 2 == 0:
                close[i] = close[i - 1] * 1.15
            else:
                close[i] = close[i - 1] * 1.05

        high = close * 1.01
        low = close * 0.99
        # Need high volume for NEWS_SHOCK now
        volume = np.full(100, 100.0)
        volume[90:] = 3000.0  # Higher volume for robust ratio
        data = pd.DataFrame(
            {"close": close, "high": high, "low": low, "open": close - 0.5, "tick_volume": volume}
        )
        # Need to ensure vov is high. Volatility is zero before 90, then huge.
        info = self.detector.detect(data)
        self.assertEqual(info.label, MarketRegime.NEWS_SHOCK)

    def test_mean_reversion_regime(self):
        # High deviation (z-score) but low efficiency (oscillating)
        close = np.full(60, 2000.0)
        # Oscillate wildly at the end
        for i in range(50, 60):
            close[i] = 2000 + (20 if i % 2 == 0 else -20)

        # Ensure z-score is high at the very last point
        close[-1] = 2050

        high = close + 1.0
        low = close - 1.0
        data = pd.DataFrame(
            {
                "close": close,
                "high": high,
                "low": low,
                "open": close - 0.5,
                "tick_volume": np.full(60, 100.0),
            }
        )
        info = self.detector.detect(data)
        self.assertEqual(info.label, MarketRegime.MEAN_REVERSION)

    def test_low_volatility_drift(self):
        np.random.seed(42)
        # Low volatility but steady drift
        close_normal = 2000.0 + np.cumsum(np.random.randn(50) * 5.0)  # High vol initial
        # Very low vol drift at the end
        close_drift = close_normal[-1] + np.linspace(0.1, 2.0, 20)
        close = np.concatenate([close_normal, close_drift])

        # Initial high ATR, then very low ATR
        high = close + np.concatenate([np.full(50, 5.0), np.full(20, 0.05)])
        low = close - np.concatenate([np.full(50, 5.0), np.full(20, 0.05)])

        data = pd.DataFrame(
            {
                "close": close,
                "high": high,
                "low": low,
                "open": close - 0.1,
                "tick_volume": np.full(70, 100.0),
            }
        )
        info = self.detector.detect(data)
        self.assertEqual(info.label, MarketRegime.LOW_VOLATILITY_DRIFT)

    def test_label_history(self):
        np.random.seed(42)
        data = pd.DataFrame(
            {
                "close": 2000.0 + np.cumsum(np.random.randn(100) * 0.1),
                "high": 2000.5 + np.cumsum(np.random.randn(100) * 0.1),
                "low": 1999.5 + np.cumsum(np.random.randn(100) * 0.1),
                "open": 2000.0 + np.cumsum(np.random.randn(100) * 0.1),
                "tick_volume": np.full(100, 100.0),
            }
        )

        df_history = self.detector.label_history(data)
        self.assertIn("regime", df_history.columns)
        self.assertTrue(
            (
                df_history["regime"].iloc[: self.detector.long_window - 1]
                == MarketRegime.UNKNOWN.value
            ).all()
        )
        self.assertNotEqual(
            df_history["regime"].iloc[self.detector.long_window - 1], MarketRegime.UNKNOWN.value
        )

        idx = 50
        info_detect = self.detector.detect(data.iloc[: idx + 1])
        self.assertEqual(df_history["regime"].iloc[idx], info_detect.label.value)
        self.assertAlmostEqual(df_history["regime_confidence"].iloc[idx], info_detect.confidence)

    def test_insufficient_data(self):
        data = pd.DataFrame(
            {"close": [1.0, 2.0], "high": [1.1, 2.1], "low": [0.9, 1.9], "tick_volume": [100, 100]}
        )
        info = self.detector.detect(data)
        self.assertEqual(info.label, MarketRegime.UNKNOWN)

    def test_gmm_fit_and_detect(self):
        # Generate multi-regime data
        np.random.seed(42)
        ranging = 2000.0 + np.random.randn(100) * 0.1
        trending = np.linspace(2000, 2100, 100)
        volatile = 2100 + np.random.randn(100) * 5.0

        data = pd.DataFrame(
            {
                "close": np.concatenate([ranging, trending, volatile]),
                "high": np.concatenate([ranging + 0.1, trending + 0.1, volatile + 1.0]),
                "low": np.concatenate([ranging - 0.1, trending - 0.1, volatile - 1.0]),
                "open": np.concatenate([ranging, trending, volatile]) - 0.05,
                "tick_volume": np.random.randint(100, 200, 300),
            }
        )

        # Fit GMM
        self.detector.fit(data, n_clusters=3)
        self.assertIsNotNone(self.detector._gmm)
        self.assertTrue(len(self.detector._cluster_to_regime) > 0)

        # Post-fit detect should use GMM
        info_post = self.detector.detect(data.iloc[:50])
        self.assertIn(info_post.label, MarketRegime)
        self.assertGreater(info_post.confidence, 0.0)

    def test_vectorized_label_history(self):
        np.random.seed(42)
        data = pd.DataFrame(
            {
                "close": 2000.0 + np.cumsum(np.random.randn(150) * 0.1),
                "high": 2000.0 + np.cumsum(np.random.randn(150) * 0.1) + 0.1,
                "low": 2000.0 + np.cumsum(np.random.randn(150) * 0.1) - 0.1,
                "open": 2000.0 + np.cumsum(np.random.randn(150) * 0.1),
                "tick_volume": np.full(150, 100.0),
            }
        )

        df_vec = self.detector.label_history(data, use_vectorized=True)
        df_iter = self.detector.label_history(data, use_vectorized=False)

        self.assertIn("regime", df_vec.columns)
        self.assertEqual(len(df_vec), len(data))

        # Sample check for consistency at multiple points
        for idx in [80, 100, 140]:
            self.assertEqual(
                df_vec["regime"].iloc[idx], df_iter["regime"].iloc[idx], f"Mismatch at index {idx}"
            )

    def test_run_analysis_and_report(self):
        np.random.seed(42)
        data = pd.DataFrame(
            {
                "close": 2000.0 + np.cumsum(np.random.randn(200) * 0.1),
                "high": 2000.0 + np.cumsum(np.random.randn(200) * 0.1) + 0.1,
                "low": 2000.0 + np.cumsum(np.random.randn(200) * 0.1) - 0.1,
                "open": 2000.0 + np.cumsum(np.random.randn(200) * 0.1),
                "tick_volume": np.full(200, 100.0),
                "returns": np.random.randn(200) * 0.001,
            }
        )

        report = self.detector.run_analysis(data)
        from src.models.regime_detector import RegimeAnalysisReport

        self.assertIsInstance(report, RegimeAnalysisReport)
        self.assertTrue(len(report.counts_pct) > 0)
        self.assertTrue(len(report.avg_durations) > 0)
        self.assertIsNotNone(report.transitions)

        # Verify conversion to report section
        section = report.to_report_section()
        from src.research.reporting import RegimeSection

        self.assertIsInstance(section, RegimeSection)
        self.assertTrue(len(section.regimes) > 0)
        self.assertIn("Stability", section.transition_insights)

    def test_regime_info_transition_probabilities(self):
        """Verify that transition_probabilities are populated in RegimeInfo."""
        np.random.seed(42)
        data = pd.DataFrame(
            {
                "close": 2000.0 + np.random.randn(50) * 0.1,
                "high": 2000.2 + np.random.randn(50) * 0.1,
                "low": 1999.8 + np.random.randn(50) * 0.1,
                "open": 2000.0 + np.random.randn(50) * 0.1,
                "tick_volume": np.full(50, 100.0),
            }
        )

        # 1. Heuristic mode
        info_h = self.detector.detect(data)
        self.assertIsInstance(info_h.transition_probabilities, dict)
        self.assertIn(info_h.label.value, info_h.transition_probabilities)
        self.assertEqual(info_h.transition_probabilities[info_h.label.value], info_h.confidence)

        # 2. GMM mode
        # Generate some diverse data to fit GMM
        ranging = 2000.0 + np.random.randn(100) * 0.1
        trending = np.linspace(2000, 2050, 100)
        fit_data = pd.DataFrame(
            {
                "close": np.concatenate([ranging, trending]),
                "high": np.concatenate([ranging + 0.1, trending + 0.1]),
                "low": np.concatenate([ranging - 0.1, trending - 0.1]),
                "open": np.concatenate([ranging, trending]),
                "tick_volume": np.full(200, 100.0),
            }
        )
        self.detector.fit(fit_data, n_clusters=2)

        info_gmm = self.detector.detect(data)
        self.assertIsInstance(info_gmm.transition_probabilities, dict)
        self.assertGreater(len(info_gmm.transition_probabilities), 0)
        # Sum of probabilities should be approx 1.0
        self.assertAlmostEqual(sum(info_gmm.transition_probabilities.values()), 1.0, places=5)

    def test_performance_benchmarking(self):
        import time

        np.random.seed(42)
        # Generate a larger dataset
        size = 5000
        data = pd.DataFrame(
            {
                "close": 2000.0 + np.cumsum(np.random.randn(size) * 0.1),
                "high": 2000.0 + np.cumsum(np.random.randn(size) * 0.1) + 0.1,
                "low": 2000.0 + np.cumsum(np.random.randn(size) * 0.1) - 0.1,
                "open": 2000.0 + np.cumsum(np.random.randn(size) * 0.1),
                "tick_volume": np.full(size, 100.0),
            }
        )

        # Benchmarking label_history (vectorized)
        start_vec = time.time()
        self.detector.label_history(data, use_vectorized=True)
        end_vec = time.time()
        vec_time = end_vec - start_vec

        # Benchmarking label_history (iterative) - only on a subset to avoid excessive test time
        subset_size = 200
        start_iter = time.time()
        self.detector.label_history(data.iloc[:subset_size], use_vectorized=False)
        end_iter = time.time()
        iter_time_per_bar = (end_iter - start_iter) / subset_size

        # Extrapolate iterative time for full dataset
        extrapolated_iter_time = iter_time_per_bar * size

        print(f"\nPerformance Benchmark ({size} bars):")
        print(f"Vectorized Time: {vec_time:.4f}s")
        print(f"Iterative Time (Extrapolated): {extrapolated_iter_time:.4f}s")
        print(f"Speedup: {extrapolated_iter_time / vec_time:.1f}x")

        self.assertLess(vec_time, 1.0)  # Should be fast
        self.assertLess(vec_time, extrapolated_iter_time)

    def test_model_persistence(self):
        np.random.seed(42)
        # Generate some data to fit
        data = pd.DataFrame(
            {
                "close": 2000.0 + np.cumsum(np.random.randn(200) * 0.1),
                "high": 2000.0 + np.cumsum(np.random.randn(200) * 0.1) + 0.1,
                "low": 2000.0 + np.cumsum(np.random.randn(200) * 0.1) - 0.1,
                "open": 2000.0 + np.cumsum(np.random.randn(200) * 0.1),
                "tick_volume": np.full(200, 100.0),
            }
        )

        self.detector.fit(data, n_clusters=3)
        self.assertIsNotNone(self.detector._gmm)

        info_orig = self.detector.detect(data.iloc[-self.detector.long_window - 1 :])

        with tempfile.NamedTemporaryFile(suffix=".joblib", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            self.detector.save_model(tmp_path)
            self.assertTrue(os.path.exists(tmp_path))

            new_detector = RegimeDetector(
                window=self.detector.window, long_window=self.detector.long_window
            )
            new_detector.load_model(tmp_path)

            self.assertIsNotNone(new_detector._gmm)
            self.assertEqual(new_detector._cluster_to_regime, self.detector._cluster_to_regime)

            info_loaded = new_detector.detect(data.iloc[-self.detector.long_window - 1 :])

            self.assertEqual(info_orig.label, info_loaded.label)
            self.assertAlmostEqual(info_orig.confidence, info_loaded.confidence)
            self.assertAlmostEqual(info_orig.transition_score, info_loaded.transition_score)

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_nan_handling_in_features(self):
        """Verify robust feature extraction under incomplete data."""
        data = pd.DataFrame(
            {
                "close": [1000.0] * 50,
                "high": [1000.1] * 50,
                "low": [999.9] * 50,
                "open": [1000.0] * 50,
                "tick_volume": [100.0] * 50,
            }
        )
        # Inject NaNs
        data.iloc[10:20, 0] = np.nan

        features = self.detector._extract_features(data)
        self.assertFalse(features.isnull().values.any())
        # Check specific fills
        self.assertEqual(features["efficiency_ratio"].iloc[0], 0.5)
        self.assertEqual(features["atr_ratio"].iloc[0], 1.0)

    def test_regime_info_raw_features(self):
        """Ensure transparency data is correctly populated in the output object."""
        np.random.seed(42)
        data = pd.DataFrame(
            {
                "close": 2000.0 + np.random.randn(50) * 0.1,
                "high": 2000.2 + np.random.randn(50) * 0.1,
                "low": 1999.8 + np.random.randn(50) * 0.1,
                "open": 2000.0 + np.random.randn(50) * 0.1,
                "tick_volume": np.full(50, 100.0),
            }
        )
        info = self.detector.detect(data)
        self.assertIsInstance(info.raw_features, dict)
        self.assertIn("atr_ratio", info.raw_features)
        self.assertIn("angle", info.raw_features)
        self.assertIn("volume_ratio", info.raw_features)
        self.assertGreater(len(info.raw_features), 6)

    def test_edge_case_flat_data(self):
        """Ensure stability when price data is static."""
        data = pd.DataFrame(
            {
                "close": [2000.0] * 100,
                "high": [2000.0] * 100,
                "low": [2000.0] * 100,
                "open": [2000.0] * 100,
                "tick_volume": [100.0] * 100,
            }
        )
        info = self.detector.detect(data)
        self.assertEqual(info.label, MarketRegime.RANGING)
        self.assertEqual(info.confidence, 0.5)  # 1.0 - er(0.5)
        self.assertEqual(info.volatility_index, 1.0)  # filled value

    def test_unified_logic_consistency(self):
        """Ensure detect() matches the last row of label_history()."""
        np.random.seed(42)
        data = pd.DataFrame(
            {
                "close": 2000.0 + np.cumsum(np.random.randn(100) * 0.1),
                "high": 2001.0 + np.cumsum(np.random.randn(100) * 0.1),
                "low": 1999.0 + np.cumsum(np.random.randn(100) * 0.1),
                "open": 2000.0 + np.cumsum(np.random.randn(100) * 0.1),
                "tick_volume": np.full(100, 100.0),
            }
        )

        # 1. Heuristic mode
        df_history = self.detector.label_history(data)
        info_detect = self.detector.detect(data)

        self.assertEqual(info_detect.label.value, df_history["regime"].iloc[-1])
        self.assertAlmostEqual(info_detect.confidence, df_history["regime_confidence"].iloc[-1])
        self.assertAlmostEqual(
            info_detect.transition_score, df_history["regime_transition_score"].iloc[-1]
        )
        self.assertAlmostEqual(
            info_detect.volatility_index, df_history["volatility_index"].iloc[-1]
        )

        # 2. GMM mode
        self.detector.fit(data)
        df_history_gmm = self.detector.label_history(data)
        info_detect_gmm = self.detector.detect(data)

        self.assertEqual(info_detect_gmm.label.value, df_history_gmm["regime"].iloc[-1])
        self.assertAlmostEqual(
            info_detect_gmm.confidence, df_history_gmm["regime_confidence"].iloc[-1]
        )

    def test_get_regime_performance(self):
        """Verify institutional performance analysis by regime."""
        np.random.seed(42)
        data = pd.DataFrame(
            {
                "close": 2000.0 + np.cumsum(np.random.randn(100) * 0.1),
                "high": 2001.0 + np.cumsum(np.random.randn(100) * 0.1),
                "low": 1999.0 + np.cumsum(np.random.randn(100) * 0.1),
                "open": 2000.0 + np.cumsum(np.random.randn(100) * 0.1),
                "tick_volume": np.full(100, 100.0),
                "returns": np.random.randn(100) * 0.001,
            }
        )

        perf = self.detector.get_regime_performance(data)
        self.assertIsInstance(perf, pd.DataFrame)
        self.assertIn("sharpe", perf.columns)
        self.assertIn("total_return", perf.columns)
        self.assertIn("mean", perf.columns)
        self.assertGreater(len(perf), 0)

    def test_scaling_integration(self):
        """Verify that StandardScaler is integrated and active."""
        np.random.seed(42)
        # Generate data with high scale to ensure scaling matters
        data = pd.DataFrame(
            {
                "close": 20000.0 + np.cumsum(np.random.randn(100) * 10.0),
                "high": 20100.0 + np.cumsum(np.random.randn(100) * 10.0),
                "low": 19900.0 + np.cumsum(np.random.randn(100) * 10.0),
                "open": 20000.0 + np.cumsum(np.random.randn(100) * 10.0),
                "tick_volume": np.full(100, 100.0),
            }
        )

        self.detector.fit(data, n_clusters=2)
        self.assertTrue(hasattr(self.detector._scaler, "mean_"))
        self.assertEqual(len(self.detector._scaler.mean_), len(self.detector.FEATURE_COLUMNS))

        # Ensure detect uses the scaler
        info = self.detector.detect(data.iloc[-self.detector.long_window - 1 :])
        self.assertIsNotNone(info.label)

    def test_transition_probability_matrix_completeness(self):
        """Ensure transition matrix is a proper probability matrix."""
        np.random.seed(42)
        data = pd.DataFrame(
            {
                "close": 2000.0 + np.cumsum(np.random.randn(200) * 0.1),
                "high": 2001.0 + np.cumsum(np.random.randn(200) * 0.1),
                "low": 1999.0 + np.cumsum(np.random.randn(200) * 0.1),
                "open": 2000.0 + np.cumsum(np.random.randn(200) * 0.1),
                "tick_volume": np.full(200, 100.0),
            }
        )
        self.detector.fit(data, n_clusters=3)
        tm = self.detector.transition_matrix

        self.assertIsInstance(tm, pd.DataFrame)
        # Probabilities should sum to 1 across rows
        row_sums = tm.sum(axis=1)
        for s in row_sums:
            self.assertAlmostEqual(s, 1.0, places=5)

    def test_gmm_mapping_robustness(self):
        """Ensure cluster mapping works correctly with scaled data."""
        np.random.seed(42)
        # 1. Ranging data
        ranging = pd.DataFrame(
            {
                "close": [100.0] * 100 + np.random.randn(100) * 0.01,
                "high": [100.1] * 100 + np.random.randn(100) * 0.01,
                "low": [99.9] * 100 + np.random.randn(100) * 0.01,
                "open": [100.0] * 100 + np.random.randn(100) * 0.01,
                "tick_volume": np.full(100, 100.0),
            }
        )
        # 2. Trending data
        trending = pd.DataFrame(
            {
                "close": np.linspace(100, 200, 100),
                "high": np.linspace(100.1, 200.1, 100),
                "low": np.linspace(99.9, 199.9, 100),
                "open": np.linspace(100, 200, 100) - 0.05,
                "tick_volume": np.full(100, 100.0),
            }
        )
        data = pd.concat([ranging, trending])

        self.detector.fit(data, n_clusters=2)
        # Check if we have at least RANGING and TRENDING or similar mapped
        labels = list(self.detector._cluster_to_regime.values())
        self.assertIn(MarketRegime.RANGING, labels)
        self.assertIn(MarketRegime.TRENDING, labels)

    def test_gmm_fit_adaptive(self):
        """Verify BIC-based adaptive cluster selection."""
        np.random.seed(42)
        # 3 clusters of data
        c1 = 2000.0 + np.random.randn(100) * 0.1
        c2 = 2100.0 + np.linspace(0, 10, 100)  # trending-like
        c3 = 2200.0 + np.random.randn(100) * 5.0  # volatile

        data = pd.DataFrame(
            {
                "close": np.concatenate([c1, c2, c3]),
                "high": np.concatenate([c1, c2, c3]) + 0.1,
                "low": np.concatenate([c1, c2, c3]) - 0.1,
                "open": np.concatenate([c1, c2, c3]),
                "tick_volume": np.concatenate(
                    [np.full(100, 100), np.full(100, 200), np.full(100, 500)]
                ),
            }
        )

        # Range of clusters
        self.detector.fit(data, n_clusters=range(2, 6))
        self.assertIsNotNone(self.detector._gmm)
        self.assertIn(self.detector._gmm.n_components, [2, 3, 4, 5])

    def test_session_alignment_scores(self):
        """Validate session alignment scores for major trading sessions."""
        from datetime import datetime

        # London (08:00 UTC)
        ts_london = datetime(2024, 1, 1, 9, 0)
        score_london = self.detector._calculate_session_alignment(ts_london)
        self.assertEqual(score_london, 0.8)

        # NY (18:00 UTC)
        ts_ny = datetime(2024, 1, 1, 18, 0)
        score_ny = self.detector._calculate_session_alignment(ts_ny)
        self.assertEqual(score_ny, 0.8)

        # Overlap (14:00 UTC)
        ts_overlap = datetime(2024, 1, 1, 14, 0)
        score_overlap = self.detector._calculate_session_alignment(ts_overlap)
        self.assertEqual(score_overlap, 1.0)

        # Asian (04:00 UTC)
        ts_asian = datetime(2024, 1, 1, 4, 0)
        score_asian = self.detector._calculate_session_alignment(ts_asian)
        self.assertEqual(score_asian, 0.5)

        # Dead zone (22:30 UTC)
        ts_dead = datetime(2024, 1, 1, 22, 30)
        score_dead = self.detector._calculate_session_alignment(ts_dead)
        self.assertEqual(score_dead, 0.3)

    def test_volatility_alignment_scores(self):
        """Validate volatility alignment scoring for different regimes."""
        # Trending with normal volatility
        score_t = self.detector._calculate_volatility_alignment(MarketRegime.TRENDING, 1.2)
        self.assertEqual(score_t, 1.0)

        # Trending with extreme volatility
        score_t_ext = self.detector._calculate_volatility_alignment(MarketRegime.TRENDING, 3.5)
        self.assertEqual(score_t_ext, 0.6)

        # News shock with high volatility
        score_n = self.detector._calculate_volatility_alignment(MarketRegime.NEWS_SHOCK, 2.5)
        self.assertAlmostEqual(score_n, 1.0)

        # Ranging with low volatility
        score_r = self.detector._calculate_volatility_alignment(MarketRegime.RANGING, 0.5)
        self.assertAlmostEqual(score_r, 1.0)

        # Ranging with high volatility (poor alignment)
        score_r_high = self.detector._calculate_volatility_alignment(MarketRegime.RANGING, 2.0)
        self.assertAlmostEqual(score_r_high, 0.6)

    def test_label_history_alignment_data(self):
        """Ensure alignment columns are present and populated in label_history."""
        np.random.seed(42)
        idx = pd.date_range("2024-01-01", periods=100, freq="15min")
        data = pd.DataFrame(
            {
                "close": 2000.0 + np.cumsum(np.random.randn(100) * 0.1),
                "high": 2000.5 + np.cumsum(np.random.randn(100) * 0.1),
                "low": 1999.5 + np.cumsum(np.random.randn(100) * 0.1),
                "open": 2000.0 + np.cumsum(np.random.randn(100) * 0.1),
                "tick_volume": np.full(100, 100.0),
            },
            index=idx
        )

        df = self.detector.label_history(data)
        self.assertIn("session_alignment", df.columns)
        self.assertIn("volatility_alignment", df.columns)

        # Check a specific point in London session
        # idx[40] is roughly 10:00
        self.assertEqual(df["session_alignment"].iloc[40], 0.8)

    def test_print_transition_matrix(self):
        """Verify that print_transition_matrix runs without error when data is available."""
        np.random.seed(42)
        data = pd.DataFrame(
            {
                "close": 2000.0 + np.cumsum(np.random.randn(100) * 0.1),
                "high": 2001.0 + np.cumsum(np.random.randn(100) * 0.1),
                "low": 1999.0 + np.cumsum(np.random.randn(100) * 0.1),
                "open": 2000.0 + np.cumsum(np.random.randn(100) * 0.1),
                "tick_volume": np.full(100, 100.0),
            }
        )
        self.detector.fit(data, n_clusters=2)

        # Should not raise exception
        self.detector.print_transition_matrix()

        # Also test when matrix is None (should log warning but not crash)
        self.detector.transition_matrix = None
        self.detector.print_transition_matrix()


if __name__ == "__main__":
    unittest.main()
# Verified by Jules
