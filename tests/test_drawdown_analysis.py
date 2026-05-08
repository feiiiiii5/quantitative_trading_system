import numpy as np
import pytest

from core.drawdown_analysis import (
    DrawdownPeriod,
    DrawdownReport,
    _compute_drawdown_distribution,
    _extract_drawdown_periods,
    analyze_drawdown,
    compute_underwater_curve,
    rolling_max_drawdown,
)


class TestDrawdownPeriodToDict:
    def test_drawdown_period_to_dict(self) -> None:
        period = DrawdownPeriod(
            peak_idx=0,
            trough_idx=3,
            recovery_idx=6,
            peak_value=100.0,
            trough_value=85.5,
            depth=0.145,
            duration=3,
            recovery_duration=3,
        )
        d = period.to_dict()
        assert d["peak_idx"] == 0
        assert d["trough_idx"] == 3
        assert d["recovery_idx"] == 6
        assert d["peak_value"] == 100.0
        assert d["trough_value"] == 85.5
        assert d["depth"] == pytest.approx(0.145, abs=1e-6)
        assert d["duration"] == 3
        assert d["recovery_duration"] == 3


class TestDrawdownReportToDict:
    def test_drawdown_report_to_dict(self) -> None:
        period = DrawdownPeriod(
            peak_idx=0, trough_idx=2, recovery_idx=4,
            peak_value=100.0, trough_value=90.0,
            depth=0.1, duration=2, recovery_duration=2,
        )
        report = DrawdownReport(
            max_drawdown=0.1,
            max_drawdown_duration=2,
            max_drawdown_recovery=2,
            current_drawdown=0.0,
            avg_drawdown=0.1,
            avg_drawdown_duration=2.0,
            drawdown_periods=[period],
            underwater_curve=[0.0, -0.05, -0.1, -0.05, 0.0],
            drawdown_distribution={"count": 1},
            calmar_ratio=1.5,
            sterling_ratio=1.2,
            burke_ratio=0.8,
        )
        d = report.to_dict()
        assert d["max_drawdown"] == pytest.approx(0.1, abs=1e-6)
        assert d["max_drawdown_duration"] == 2
        assert d["max_drawdown_recovery"] == 2
        assert d["current_drawdown"] == pytest.approx(0.0, abs=1e-6)
        assert d["avg_drawdown"] == pytest.approx(0.1, abs=1e-6)
        assert d["avg_drawdown_duration"] == pytest.approx(2.0, abs=1e-2)
        assert len(d["drawdown_periods"]) == 1
        assert d["drawdown_periods"][0]["depth"] == pytest.approx(0.1, abs=1e-6)
        assert len(d["underwater_curve"]) == 5
        assert d["drawdown_distribution"] == {"count": 1}
        assert d["calmar_ratio"] == pytest.approx(1.5, abs=1e-4)
        assert d["sterling_ratio"] == pytest.approx(1.2, abs=1e-4)
        assert d["burke_ratio"] == pytest.approx(0.8, abs=1e-4)


class TestComputeUnderwaterCurve:
    def test_compute_underwater_curve_monotonic_up(self) -> None:
        equity = np.array([100.0, 110.0, 120.0, 130.0])
        result = compute_underwater_curve(equity)
        np.testing.assert_array_equal(result, np.zeros(4))

    def test_compute_underwater_curve_with_drawdown(self) -> None:
        equity = np.array([100.0, 110.0, 99.0, 105.0])
        result = compute_underwater_curve(equity)
        assert result[0] == pytest.approx(0.0)
        assert result[1] == pytest.approx(0.0)
        assert result[2] == pytest.approx((99.0 - 110.0) / 110.0)
        assert result[3] == pytest.approx((105.0 - 110.0) / 110.0)

    def test_compute_underwater_curve_empty(self) -> None:
        result = compute_underwater_curve(np.array([]))
        assert len(result) == 0


class TestExtractDrawdownPeriods:
    def test_extract_drawdown_periods_no_drawdown(self) -> None:
        equity = np.array([100.0, 110.0, 120.0, 130.0])
        underwater = compute_underwater_curve(equity)
        periods = _extract_drawdown_periods(underwater, equity)
        assert periods == []

    def test_extract_drawdown_periods_single_drawdown(self) -> None:
        equity = np.array([100.0, 110.0, 99.0, 105.0, 115.0])
        underwater = compute_underwater_curve(equity)
        periods = _extract_drawdown_periods(underwater, equity)
        assert len(periods) >= 1
        period = periods[0]
        assert period.trough_idx == 2
        assert period.recovery_idx == 4
        assert period.depth > 0

    def test_extract_drawdown_periods_unrecovered(self) -> None:
        equity = np.array([100.0, 110.0, 99.0, 95.0, 90.0])
        underwater = compute_underwater_curve(equity)
        periods = _extract_drawdown_periods(underwater, equity)
        assert len(periods) >= 1
        assert periods[-1].recovery_idx is None
        assert periods[-1].recovery_duration is None


class TestAnalyzeDrawdown:
    def test_analyze_drawdown_monotonic_up(self) -> None:
        equity = np.array([100.0, 110.0, 120.0, 130.0, 140.0])
        report = analyze_drawdown(equity)
        assert report.max_drawdown == 0.0

    def test_analyze_drawdown_with_drawdown(self) -> None:
        equity = np.array([100.0, 110.0, 99.0, 105.0, 115.0])
        report = analyze_drawdown(equity)
        expected_max_dd = abs((99.0 - 110.0) / 110.0)
        assert report.max_drawdown == pytest.approx(expected_max_dd, rel=1e-4)

    def test_analyze_drawdown_empty_equity(self) -> None:
        report = analyze_drawdown(np.array([]))
        assert report.max_drawdown == 0.0
        assert report.max_drawdown_duration == 0
        assert report.max_drawdown_recovery is None
        assert report.current_drawdown == 0.0
        assert report.avg_drawdown == 0.0
        assert report.avg_drawdown_duration == 0.0

    def test_analyze_drawdown_single_point(self) -> None:
        report = analyze_drawdown(np.array([100.0]))
        assert report.max_drawdown == 0.0
        assert report.max_drawdown_duration == 0
        assert report.current_drawdown == 0.0

    def test_analyze_drawdown_list_input(self) -> None:
        equity = [100.0, 110.0, 99.0, 105.0, 115.0]
        report = analyze_drawdown(equity)
        assert report.max_drawdown > 0.0

    def test_analyze_drawdown_with_returns(self) -> None:
        equity = np.array([100.0, 110.0, 99.0, 105.0, 115.0])
        returns = np.array([0.10, -0.10, 0.0606, 0.0952])
        report = analyze_drawdown(equity, returns=returns)
        assert report.calmar_ratio != 0.0

    def test_analyze_drawdown_current_drawdown(self) -> None:
        equity = np.array([100.0, 110.0, 99.0, 95.0])
        report = analyze_drawdown(equity)
        expected_current = abs((95.0 - 110.0) / 110.0)
        assert report.current_drawdown == pytest.approx(expected_current, rel=1e-4)


class TestRollingMaxDrawdown:
    def test_rolling_max_drawdown_monotonic_up(self) -> None:
        equity = np.array([100.0, 110.0, 120.0, 130.0, 140.0])
        result = rolling_max_drawdown(equity, window=3)
        np.testing.assert_array_equal(result, np.zeros(5))

    def test_rolling_max_drawdown_short_equity(self) -> None:
        equity = np.array([100.0])
        result = rolling_max_drawdown(equity, window=3)
        np.testing.assert_array_equal(result, np.zeros(1))

    def test_rolling_max_drawdown_with_drawdown(self) -> None:
        equity = np.array([100.0, 110.0, 99.0, 105.0, 115.0, 100.0])
        result = rolling_max_drawdown(equity, window=3)
        assert result[-1] < 0.0


class TestComputeDrawdownDistribution:
    def test_compute_drawdown_distribution_empty(self) -> None:
        dist = _compute_drawdown_distribution([])
        assert dist["count"] == 0

    def test_compute_drawdown_distribution_with_periods(self) -> None:
        periods = [
            DrawdownPeriod(
                peak_idx=0, trough_idx=2, recovery_idx=4,
                peak_value=100.0, trough_value=90.0,
                depth=0.1, duration=2, recovery_duration=2,
            ),
            DrawdownPeriod(
                peak_idx=4, trough_idx=6, recovery_idx=8,
                peak_value=105.0, trough_value=94.5,
                depth=0.1, duration=2, recovery_duration=2,
            ),
        ]
        dist = _compute_drawdown_distribution(periods)
        assert dist["count"] == 2
        assert "depth" in dist
        assert "duration" in dist
        assert "min" in dist["depth"]
        assert "max" in dist["depth"]
        assert "mean" in dist["depth"]
