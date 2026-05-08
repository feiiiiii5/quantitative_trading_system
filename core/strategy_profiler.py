"""
Strategy Performance Profiler
Measures per-strategy execution latency breakdown for optimization targeting.
"""
import logging
import time
from collections import defaultdict
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

__all__ = [
    "StrategyProfiler",
    "ProfilingReport",
    "get_profiler",
]


@dataclass
class PhaseMetrics:
    count: int = 0
    total_ns: int = 0
    min_ns: int = 0
    max_ns: int = 0

    @property
    def total_ms(self) -> float:
        return self.total_ns / 1_000_000

    @property
    def avg_ms(self) -> float:
        return self.total_ms / self.count if self.count > 0 else 0.0

    @property
    def min_ms(self) -> float:
        return self.min_ns / 1_000_000

    @property
    def max_ms(self) -> float:
        return self.max_ns / 1_000_000

    def record(self, duration_ns: int) -> None:
        self.count += 1
        self.total_ns += duration_ns
        if self.min_ns == 0:
            self.min_ns = duration_ns
        else:
            self.min_ns = min(self.min_ns, duration_ns)
        self.max_ns = max(self.max_ns, duration_ns)


@dataclass
class StrategyProfile:
    name: str
    phases: dict[str, PhaseMetrics] = field(default_factory=dict)
    total_bars: int = 0
    errors: int = 0

    def get_summary(self) -> dict:
        total_time = sum(p.total_ms for p in self.phases.values())
        return {
            "strategy": self.name,
            "total_bars": self.total_bars,
            "total_time_ms": round(total_time, 3),
            "time_per_bar_us": round(total_time * 1000 / self.total_bars, 3) if self.total_bars > 0 else 0,
            "errors": self.errors,
            "phases": {
                name: {
                    "calls": p.count,
                    "total_ms": round(p.total_ms, 3),
                    "avg_ms": round(p.avg_ms, 3),
                    "min_ms": round(p.min_ms, 3),
                    "max_ms": round(p.max_ms, 3),
                    "pct_of_total": round(p.total_ms / total_time * 100, 1) if total_time > 0 else 0,
                }
                for name, p in sorted(self.phases.items(), key=lambda x: -x[1].total_ms)
            },
        }


@dataclass
class ProfilingReport:
    profiles: dict[str, StrategyProfile] = field(default_factory=dict)
    hot_phases: dict[str, float] = field(default_factory=dict)

    def add_profile(self, profile: StrategyProfile) -> None:
        self.profiles[profile.name] = profile

    def get_top_slow_phases(self, top_n: int = 10) -> list[tuple[str, float]]:
        phase_totals: dict[str, float] = defaultdict(float)
        for profile in self.profiles.values():
            for name, metrics in profile.phases.items():
                phase_totals[name] += metrics.total_ms

        sorted_phases = sorted(phase_totals.items(), key=lambda x: -x[1])
        return sorted_phases[:top_n]

    def get_optimization_targets(self) -> list[dict]:
        targets = []
        for phase_name, total_ms in self.hot_phases.items():
            strategies = []
            for profile in self.profiles.values():
                if phase_name in profile.phases:
                    strategies.append({
                        "strategy": profile.name,
                        "time_ms": round(profile.phases[phase_name].total_ms, 3),
                    })
            if strategies:
                phase_total = sum(s["time_ms"] for s in strategies)
                for s in strategies:
                    s["pct"] = round(s["time_ms"] / phase_total * 100, 1) if phase_total > 0 else 0
                strategies.sort(key=lambda x: -x["time_ms"])
                targets.append({
                    "phase": phase_name,
                    "total_ms": round(total_ms, 3),
                    "affected_strategies": strategies[:5],
                })
        targets.sort(key=lambda x: -x["total_ms"])
        return targets

    def print_summary(self) -> None:
        logger.info("=" * 80)
        logger.info("STRATEGY PROFILING REPORT")
        logger.info("=" * 80)

        top_slow = self.get_top_slow_phases(5)
        logger.info("Top 5 slowest phases (all strategies):")
        for i, (phase, ms) in enumerate(top_slow, 1):
            logger.info("  %d. %s: %.2f ms", i, phase, ms)

        logger.info("Per-strategy breakdown:")
        for name, profile in self.profiles.items():
            summary = profile.get_summary()
            logger.info("  Strategy: %s", name)
            logger.info("    Bars: %d | Total: %.2fms | Per-bar: %.2fus",
                        summary['total_bars'], summary['total_time_ms'], summary['time_per_bar_us'])
            if summary['errors'] > 0:
                logger.info("    Errors: %d", summary['errors'])
            for phase_name, phase_data in list(summary['phases'].items())[:3]:
                logger.info("    %s: avg=%.3fms, total=%.2fms (%.1f%%)",
                            phase_name, phase_data['avg_ms'], phase_data['total_ms'], phase_data['pct_of_total'])

        logger.info("Optimization targets:")
        for target in self.get_optimization_targets()[:3]:
            logger.info("  %s (%.2fms total):", target['phase'], target['total_ms'])
            for s in target['affected_strategies']:
                logger.info("    - %s: %.2fms (%.1f%%)", s['strategy'], s['time_ms'], s['pct'])


class StrategyProfiler:
    _DEFAULT_PHASES = ("indicator_computation", "signal_generation", "preprocessing", "postprocessing", "total")
    _MIN_SLOW_THRESHOLD_MS = 0.1

    _instance: "StrategyProfiler | None" = None

    def __init__(self) -> None:
        self._reports: list[ProfilingReport] = []
        self._current: ProfilingReport | None = None
        self._enabled: bool = True
        self._phase_stack: list[tuple[str, int]] = []
        self._strategy_stack: list[str] = []

    @classmethod
    def get_instance(cls) -> "StrategyProfiler":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    def reset(self) -> None:
        self._reports.clear()
        self._current = None

    def start_session(self, name: str = "default") -> ProfilingReport:
        self._current = ProfilingReport()
        return self._current

    def end_session(self) -> ProfilingReport | None:
        if self._current is None:
            return None
        self._current.hot_phases = dict(self.get_top_slow_phases())
        self._reports.append(self._current)
        report = self._current
        self._current = None
        return report

    @contextmanager
    def profile_strategy(self, strategy_name: str) -> Any:
        if not self._enabled or self._current is None:
            yield None
            return

        if strategy_name not in self._current.profiles:
            self._current.profiles[strategy_name] = StrategyProfile(name=strategy_name)

        profile = self._current.profiles[strategy_name]
        self._strategy_stack.append(strategy_name)
        start_ns = time.perf_counter_ns()

        try:
            yield profile
        except Exception as exc:
            profile.errors += 1
            logger.debug("Strategy %s raised during profiling: %s", strategy_name, exc)
            raise
        finally:
            elapsed = time.perf_counter_ns() - start_ns
            profile.total_bars += 1
            phase = "total"
            if phase not in profile.phases:
                profile.phases[phase] = PhaseMetrics()
            profile.phases[phase].record(elapsed)
            self._strategy_stack.pop()

    @contextmanager
    def profile_phase(self, phase_name: str) -> Any:
        if not self._enabled or self._current is None or not self._strategy_stack:
            yield None
            return

        strategy_name = self._strategy_stack[-1]
        profile = self._current.profiles[strategy_name]
        self._phase_stack.append((phase_name, time.perf_counter_ns()))
        start_ns = time.perf_counter_ns()

        try:
            yield
        finally:
            elapsed = time.perf_counter_ns() - start_ns
            if phase_name not in profile.phases:
                profile.phases[phase_name] = PhaseMetrics()
            profile.phases[phase_name].record(elapsed)
            self._phase_stack.pop()

    def wrap_strategy(
        self,
        func: Callable,
        strategy_name: str,
        phases: tuple[str, ...] | None = None,
    ) -> Callable:
        if phases is None:
            phases = self._DEFAULT_PHASES

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not self._enabled or self._current is None:
                return func(*args, **kwargs)

            profile = self._current.profiles.setdefault(strategy_name, StrategyProfile(name=strategy_name))
            self._strategy_stack.append(strategy_name)

            try:
                with self.profile_phase("preprocessing"):
                    pass

                result = None
                with self.profile_phase("indicator_computation"):
                    result = func(*args, **kwargs)

                with self.profile_phase("signal_generation"):
                    pass

                with self.profile_phase("postprocessing"):
                    pass

                return result
            except Exception as exc:
                profile.errors += 1
                logger.debug("Strategy %s raised during profiled call: %s", strategy_name, exc)
                raise
            finally:
                profile.total_bars += 1
                self._strategy_stack.pop()

        return wrapper

    def get_latest_report(self) -> ProfilingReport | None:
        return self._reports[-1] if self._reports else None

    def get_top_slow_phases(self, top_n: int = 10) -> list[tuple[str, float]]:
        if not self._reports:
            return []
        return self._reports[-1].get_top_slow_phases(top_n)

    def instrument_backtest(
        self,
        data: pd.DataFrame,
        strategy_func: Callable,
        strategy_name: str,
    ) -> tuple[pd.DataFrame, ProfilingReport | None]:
        self.start_session(f"backtest_{strategy_name}")
        try:
            for idx in range(len(data)):
                with self.profile_strategy(strategy_name):
                    with self.profile_phase("indicator_computation"):
                        pass
                    with self.profile_phase("signal_generation"):
                        strategy_func(data.iloc[:idx + 1])
        finally:
            final_report = self.end_session()
        return data, final_report


def get_profiler() -> StrategyProfiler:
    return StrategyProfiler.get_instance()
