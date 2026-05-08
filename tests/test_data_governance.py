import numpy as np
import pandas as pd
import pytest

from core.data_governance import (
    AdjustMode,
    AnomalyDetector,
    AnomalyRecord,
    AnomalyType,
    Severity,
)


class TestAnomalyType:
    def test_values(self):
        assert AnomalyType.Z_SCORE.value == "z_score"
        assert AnomalyType.EXCHANGE_LIMIT.value == "exchange_limit"
        assert AnomalyType.VOLUME_SPIKE.value == "volume_spike"


class TestSeverity:
    def test_values(self):
        assert Severity.LOW.value == "low"
        assert Severity.MEDIUM.value == "medium"
        assert Severity.HIGH.value == "high"
        assert Severity.CRITICAL.value == "critical"


class TestAdjustMode:
    def test_values(self):
        assert AdjustMode.NONE.value == ""
        assert AdjustMode.QFQ.value == "qfq"
        assert AdjustMode.HFQ.value == "hfq"


class TestAnomalyRecord:
    def test_creation(self):
        rec = AnomalyRecord(
            symbol="600000",
            date="2024-01-15",
            anomaly_type="z_score",
            severity="high",
            details="z=4.50",
        )
        assert rec.symbol == "600000"
        assert rec.anomaly_type == "z_score"
        assert rec.severity == "high"


class TestAnomalyDetector:
    @pytest.fixture
    def detector(self):
        return AnomalyDetector(z_score_threshold=3.0, volume_spike_ratio=1000.0)

    def test_detect_z_score_normal(self, detector):
        np.random.seed(42)
        n = 100
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=n),
            "close": 100 + np.cumsum(np.random.randn(n) * 0.5),
        })
        results = detector.detect_z_score(df, "600000")
        assert isinstance(results, list)

    def test_detect_z_score_with_outlier(self, detector):
        n = 50
        prices = [100.0] * n
        prices[-1] = 200.0
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=n),
            "close": prices,
        })
        results = detector.detect_z_score(df, "600000")
        assert len(results) > 0
        assert results[0].anomaly_type == AnomalyType.Z_SCORE.value

    def test_detect_z_score_empty_df(self, detector):
        df = pd.DataFrame()
        results = detector.detect_z_score(df, "600000")
        assert results == []

    def test_detect_z_score_missing_column(self, detector):
        df = pd.DataFrame({"date": ["2024-01-01"], "open": [10.0]})
        results = detector.detect_z_score(df, "600000")
        assert results == []

    def test_detect_exchange_limit_main_board(self, detector):
        n = 20
        prices = [100.0] * n
        prices[-1] = 115.0
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=n),
            "close": prices,
        })
        results = detector.detect_exchange_limit(df, "600000")
        assert len(results) > 0
        assert results[0].anomaly_type == AnomalyType.EXCHANGE_LIMIT.value

    def test_detect_exchange_limit_star_board(self, detector):
        n = 20
        prices = [100.0] * n
        prices[-1] = 130.0
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=n),
            "close": prices,
        })
        results = detector.detect_exchange_limit(df, "688001")
        assert len(results) > 0

    def test_detect_exchange_limit_within_limit(self, detector):
        n = 20
        prices = [100.0] * n
        prices[-1] = 105.0
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=n),
            "close": prices,
        })
        results = detector.detect_exchange_limit(df, "600000")
        assert len(results) == 0

    def test_detect_volume_spike(self, detector):
        n = 30
        volumes = [1000.0] * (n - 1) + [5_000_000.0]
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=n),
            "close": 100.0,
            "volume": volumes,
        })
        results = detector.detect_volume_spike(df, "600000")
        assert len(results) > 0
        assert results[0].anomaly_type == AnomalyType.VOLUME_SPIKE.value

    def test_detect_volume_spike_normal(self, detector):
        n = 30
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=n),
            "close": 100.0,
            "volume": [1000.0 + i * 10 for i in range(n)],
        })
        results = detector.detect_volume_spike(df, "600000")
        assert len(results) == 0

    def test_detect_all(self, detector):
        n = 30
        prices = [100.0] * (n - 1) + [120.0]
        volumes = [1000.0] * (n - 1) + [5_000_000.0]
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=n),
            "close": prices,
            "volume": volumes,
        })
        results = detector.detect_all(df, "600000")
        assert len(results) > 0
        types = {r.anomaly_type for r in results}
        assert AnomalyType.EXCHANGE_LIMIT.value in types or AnomalyType.VOLUME_SPIKE.value in types

    def test_infer_board(self, detector):
        assert detector._infer_board("600000") == "main"
        assert detector._infer_board("300001") == "gem"
        assert detector._infer_board("688001") == "star"
        assert detector._infer_board("830001") == "bse"
