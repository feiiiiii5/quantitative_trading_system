"""
Tests for Strategy Performance Profiler
"""
import time

import pandas as pd

from core.strategy_profiler import (
    PhaseMetrics,
    ProfilingReport,
    StrategyProfile,
    StrategyProfiler,
    get_profiler,
)


class TestPhaseMetrics:
    def test_record_single(self):
        m = PhaseMetrics()
        m.record(1_500_000)
        assert m.count == 1
        assert m.total_ms == 1.5
        assert m.avg_ms == 1.5
        assert m.min_ms == 1.5
        assert m.max_ms == 1.5

    def test_record_multiple(self):
        m = PhaseMetrics()
        m.record(1_000_000)
        m.record(2_000_000)
        m.record(3_000_000)
        assert m.count == 3
        assert m.total_ms == 6.0
        assert m.avg_ms == 2.0
        assert m.min_ms == 1.0
        assert m.max_ms == 3.0

    def test_record_empty(self):
        m = PhaseMetrics()
        assert m.avg_ms == 0.0


class TestStrategyProfile:
    def test_get_summary(self):
        p = StrategyProfile(name="TestStrategy")
        m1 = PhaseMetrics()
        m1.record(1_000_000)
        m1.record(2_000_000)
        m2 = PhaseMetrics()
        m2.record(500_000)
        p.phases["a"] = m1
        p.phases["b"] = m2
        p.total_bars = 10

        summary = p.get_summary()
        assert summary["strategy"] == "TestStrategy"
        assert summary["total_bars"] == 10
        assert summary["total_time_ms"] == 3.5
        assert "a" in summary["phases"]
        assert "b" in summary["phases"]


class TestProfilingReport:
    def test_add_profile(self):
        report = ProfilingReport()
        profile = StrategyProfile(name="S1")
        report.add_profile(profile)
        assert "S1" in report.profiles

    def test_get_top_slow_phases(self):
        report = ProfilingReport()
        p1 = StrategyProfile(name="S1")
        p1.phases["indicator"] = PhaseMetrics()
        p1.phases["indicator"].record(5_000_000)
        p2 = StrategyProfile(name="S2")
        p2.phases["indicator"] = PhaseMetrics()
        p2.phases["indicator"].record(3_000_000)
        report.add_profile(p1)
        report.add_profile(p2)

        top = report.get_top_slow_phases(3)
        assert top[0][0] == "indicator"
        assert top[0][1] == 8.0

    def test_get_optimization_targets(self):
        report = ProfilingReport()
        p = StrategyProfile(name="S1")
        m = PhaseMetrics()
        m.record(10_000_000)
        p.phases["indicator_computation"] = m
        report.add_profile(p)
        report.hot_phases = {"indicator_computation": 10.0}

        targets = report.get_optimization_targets()
        assert len(targets) == 1
        assert targets[0]["phase"] == "indicator_computation"
        assert targets[0]["total_ms"] == 10.0


class TestStrategyProfiler:
    def test_singleton(self):
        p1 = get_profiler()
        p2 = get_profiler()
        assert p1 is p2

    def test_enable_disable(self):
        p = StrategyProfiler()
        p.disable()
        assert not p._enabled
        p.enable()
        assert p._enabled

    def test_start_end_session(self):
        p = StrategyProfiler()
        report = p.start_session()
        assert report is not None
        assert p._current is report
        ended = p.end_session()
        assert ended is report
        assert p._current is None

    def test_profile_strategy_context(self):
        p = StrategyProfiler()
        p.start_session()
        with p.profile_strategy("TestStrat") as profile:
            assert profile is not None
            time.sleep(0.001)
        ended = p.end_session()
        assert "TestStrat" in ended.profiles
        assert ended.profiles["TestStrat"].total_bars == 1
        assert ended.profiles["TestStrat"].phases["total"].count == 1

    def test_profile_phase_nested(self):
        p = StrategyProfiler()
        p.start_session()
        with p.profile_strategy("S1"):
            with p.profile_phase("phase_a"):
                time.sleep(0.001)
            with p.profile_phase("phase_b"):
                time.sleep(0.001)
        ended = p.end_session()
        profile = ended.profiles["S1"]
        assert "phase_a" in profile.phases
        assert "phase_b" in profile.phases
        assert profile.phases["phase_a"].count == 1
        assert profile.phases["phase_b"].count == 1

    def test_profile_strategy_disabled(self):
        p = StrategyProfiler()
        p.disable()
        p.start_session()
        with p.profile_strategy("S1"):
            time.sleep(0.001)
        ended = p.end_session()
        assert "S1" not in ended.profiles

    def test_profile_phase_no_strategy(self):
        p = StrategyProfiler()
        p.start_session()
        with p.profile_phase("orphan"):
            pass
        ended = p.end_session()
        assert ended is not None
        assert len(ended.profiles) == 0

    def test_instrument_backtest(self):
        p = StrategyProfiler()
        p.enable()
        data = pd.DataFrame({"close": [100.0, 101.0, 102.0, 101.5, 103.0]})
        signals = []

        def strategy_func(bar_data):
            signals.append(1)

        _, report = p.instrument_backtest(data, strategy_func, "TestStrat")
        assert report is not None
        assert "TestStrat" in report.profiles

    def test_get_latest_report(self):
        p = StrategyProfiler()
        assert p.get_latest_report() is None
        p.start_session()
        p.end_session()
        assert p.get_latest_report() is not None

    def test_print_summary_no_crash(self):
        p = StrategyProfiler()
        report = ProfilingReport()
        p._reports.append(report)
        report.print_summary()
