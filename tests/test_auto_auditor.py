import numpy as np
import pandas as pd
import pytest

from core.auto_auditor import (
    OverfittingDetector,
    ReturnAnomalyDetector,
    SignalAnomalyDetector,
    AutoAuditor,
    OverfittingReport,
    AnomalyReport,
    SignalAnomalyReport,
    FullAuditReport,
)


class TestOverfittingDetector:
    def test_no_overfitting(self):
        detector = OverfittingDetector()
        train = {"sharpe_ratio": 1.0}
        test = {"sharpe_ratio": 0.8}
        report = detector.detect(train, test)
        assert isinstance(report, OverfittingReport)
        assert not report.is_overfitted or report.overfitting_score < 0.8

    def test_overfitting(self):
        detector = OverfittingDetector()
        train = {"sharpe_ratio": 3.0}
        test = {"sharpe_ratio": 0.2}
        report = detector.detect(train, test)
        assert report.is_overfitted
        assert report.overfitting_score > 0.3

    def test_with_walk_forward(self):
        detector = OverfittingDetector()
        train = {"sharpe_ratio": 1.5}
        test = {"sharpe_ratio": 0.8}
        wf = [
            {"test_metrics": {"sharpe_ratio": 0.9}},
            {"test_metrics": {"sharpe_ratio": 0.7}},
            {"test_metrics": {"sharpe_ratio": -0.1}},
        ]
        report = detector.detect(train, test, wf)
        assert isinstance(report.consistency_score, float)


class TestReturnAnomalyDetector:
    def test_normal_returns(self):
        np.random.seed(42)
        detector = ReturnAnomalyDetector()
        returns = pd.Series(np.random.randn(100) * 0.02)
        report = detector.detect(returns)
        assert isinstance(report, AnomalyReport)
        assert not report.has_anomaly or report.anomaly_score < 0.5

    def test_extreme_returns(self):
        detector = ReturnAnomalyDetector(zscore_threshold=2.0, max_single_day_return=0.30)
        returns = pd.Series([0.01] * 50 + [0.50] + [0.01] * 49)
        report = detector.detect(returns)
        assert report.has_anomaly or report.anomaly_score > 0

    def test_consecutive_losses(self):
        detector = ReturnAnomalyDetector(max_consecutive_losses=5)
        returns = pd.Series([-0.01] * 15 + [0.01] * 10)
        report = detector.detect(returns)
        assert "consecutive_losses" in report.anomaly_types

    def test_short_series(self):
        detector = ReturnAnomalyDetector()
        returns = pd.Series([0.01, 0.02])
        report = detector.detect(returns)
        assert not report.has_anomaly


class TestSignalAnomalyDetector:
    def test_normal_signals(self):
        np.random.seed(42)
        detector = SignalAnomalyDetector()
        signals = pd.Series(np.random.choice([0, 1, -1], 100, p=[0.6, 0.2, 0.2]))
        report = detector.detect(signals)
        assert isinstance(report, SignalAnomalyReport)

    def test_concentrated_signals(self):
        detector = SignalAnomalyDetector(max_signal_concentration=0.5)
        signals = pd.Series([0] * 95 + [1] * 5)
        report = detector.detect(signals)
        assert report.concentration_score > 0.5

    def test_stale_signal(self):
        detector = SignalAnomalyDetector(stale_threshold=10)
        signals = pd.Series([1] + [0] * 50)
        report = detector.detect(signals)
        assert report.stale_signal

    def test_short_series(self):
        detector = SignalAnomalyDetector()
        signals = pd.Series([0, 1])
        report = detector.detect(signals)
        assert isinstance(report, SignalAnomalyReport)


class TestAutoAuditor:
    def test_audit_passing(self):
        np.random.seed(42)
        auditor = AutoAuditor()
        train = {"sharpe_ratio": 1.0}
        test = {"sharpe_ratio": 0.8}
        returns = pd.Series(np.random.randn(100) * 0.02)
        report = auditor.audit(train, test, returns)
        assert isinstance(report, FullAuditReport)
        assert isinstance(report.passed, bool)
        assert isinstance(report.recommendations, list)

    def test_audit_failing(self):
        np.random.seed(42)
        auditor = AutoAuditor()
        train = {"sharpe_ratio": 3.0}
        test = {"sharpe_ratio": 0.1}
        returns = pd.Series([-0.05] * 30 + [0.50] + [-0.05] * 19)
        report = auditor.audit(train, test, returns)
        assert isinstance(report.overall_score, float)
        assert len(report.recommendations) > 0

    def test_audit_with_signals(self):
        np.random.seed(42)
        auditor = AutoAuditor()
        train = {"sharpe_ratio": 1.0}
        test = {"sharpe_ratio": 0.7}
        returns = pd.Series(np.random.randn(100) * 0.02)
        signals = pd.Series(np.random.choice([0, 1, -1], 100))
        report = auditor.audit(train, test, returns, signals=signals)
        assert isinstance(report, FullAuditReport)
