import numpy as np
import pandas as pd
import pytest

from core.ml_strategy_framework import (
    SKLEARN_AVAILABLE,
    DistributionDriftMonitor,
    DriftResult,
    MLStrategyPipeline,
    MetaLabelingResult,
    mdi_importance,
    triple_barrier_labels,
)


class TestTripleBarrierLabels:
    def test_basic_labeling(self):
        np.random.seed(42)
        n = 60
        prices = pd.Series(100 + np.cumsum(np.random.randn(n) * 0.5))
        returns = prices.pct_change().dropna()
        rolling_std = returns.rolling(10).std().dropna()
        trgt = rolling_std.reindex(prices.index).ffill().fillna(0.01)
        events = pd.DataFrame({"t0": prices.index, "trgt": trgt.values})
        events = events.set_index("t0")

        result = triple_barrier_labels(prices, events)
        assert "label" in result.columns
        assert set(result["label"].unique()).issubset({-1, 0, 1})

    def test_custom_pt_sl(self):
        np.random.seed(42)
        n = 60
        prices = pd.Series(100 + np.cumsum(np.random.randn(n) * 0.5))
        returns = prices.pct_change().dropna()
        trgt = returns.rolling(10).std().dropna().reindex(prices.index).ffill().fillna(0.01)
        events = pd.DataFrame({"t0": prices.index, "trgt": trgt.values}).set_index("t0")

        result = triple_barrier_labels(prices, events, pt_sl=[2.0, 1.0])
        assert len(result) > 0

    def test_empty_events(self):
        prices = pd.Series([100.0, 101.0, 102.0])
        events = pd.DataFrame(columns=["t0", "trgt"])
        result = triple_barrier_labels(prices, events)
        assert len(result) == 0

    def test_labels_are_integers(self):
        np.random.seed(42)
        n = 60
        prices = pd.Series(100 + np.cumsum(np.random.randn(n) * 0.5))
        returns = prices.pct_change().dropna()
        trgt = returns.rolling(10).std().dropna().reindex(prices.index).ffill().fillna(0.01)
        events = pd.DataFrame({"t0": prices.index, "trgt": trgt.values}).set_index("t0")

        result = triple_barrier_labels(prices, events)
        if len(result) > 0:
            assert result["label"].dtype in (int, np.int64, np.int32)


class TestDistributionDriftMonitor:
    def test_no_drift(self):
        np.random.seed(42)
        current = pd.DataFrame({"f1": np.random.randn(100), "f2": np.random.randn(100)})
        reference = pd.DataFrame({"f1": np.random.randn(100), "f2": np.random.randn(100)})
        monitor = DistributionDriftMonitor(significance_level=0.01)
        result = monitor.monitor(current, reference)
        assert isinstance(result, DriftResult)
        assert isinstance(result.drift_detected, bool)
        assert isinstance(result.ks_statistics, dict)
        assert isinstance(result.alert_level, str)
        assert result.alert_level in ("normal", "warning", "critical")

    def test_drift_detected(self):
        np.random.seed(42)
        reference = pd.DataFrame({"f1": np.random.randn(100) * 0.1})
        current = pd.DataFrame({"f1": np.random.randn(100) * 10.0 + 5.0})
        monitor = DistributionDriftMonitor(significance_level=0.05)
        result = monitor.monitor(current, reference)
        assert result.drift_detected is True
        assert len(result.drifted_features) > 0

    def test_critical_alert_level(self):
        np.random.seed(42)
        reference = pd.DataFrame({
            "f1": np.random.randn(100),
            "f2": np.random.randn(100),
            "f3": np.random.randn(100),
        })
        current = pd.DataFrame({
            "f1": np.random.randn(100) * 10 + 5,
            "f2": np.random.randn(100) * 10 + 5,
            "f3": np.random.randn(100) * 10 + 5,
        })
        monitor = DistributionDriftMonitor(significance_level=0.05, alert_threshold=0.3)
        result = monitor.monitor(current, reference)
        if result.drift_detected and len(result.drifted_features) / 3 >= 0.3:
            assert result.alert_level == "critical"

    def test_no_common_columns(self):
        current = pd.DataFrame({"a": [1.0, 2.0]})
        reference = pd.DataFrame({"b": [1.0, 2.0]})
        monitor = DistributionDriftMonitor()
        result = monitor.monitor(current, reference)
        assert result.drift_detected is True
        assert result.alert_level == "critical"


class TestMDIImportance:
    def test_with_model(self):
        if not SKLEARN_AVAILABLE:
            pytest.skip("scikit-learn not available")
        from sklearn.ensemble import RandomForestClassifier

        np.random.seed(42)
        n = 100
        x = pd.DataFrame({"f1": np.random.randn(n), "f2": np.random.randn(n)})
        y = pd.Series(np.random.randint(0, 2, n))
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        model.fit(x, y)
        importance = mdi_importance(model, ["f1", "f2"])
        assert "f1" in importance
        assert "f2" in importance
        assert abs(sum(importance.values()) - 1.0) < 0.01

    def test_without_feature_importances(self):
        class FakeModel:
            pass
        importance = mdi_importance(FakeModel(), ["a", "b", "c"])
        assert len(importance) == 3
        assert abs(sum(importance.values()) - 1.0) < 0.01


class TestMLStrategyPipeline:
    def test_generate_labels_triple_barrier(self):
        np.random.seed(42)
        n = 60
        prices = pd.Series(100 + np.cumsum(np.random.randn(n) * 0.5))
        pipeline = MLStrategyPipeline()
        result = pipeline.generate_labels(prices, method="triple_barrier")
        assert "label" in result.columns

    def test_generate_labels_unknown_method(self):
        np.random.seed(42)
        n = 60
        prices = pd.Series(100 + np.cumsum(np.random.randn(n) * 0.5))
        pipeline = MLStrategyPipeline()
        with pytest.raises(ValueError, match="Unknown label generation method"):
            pipeline.generate_labels(prices, method="unknown")
