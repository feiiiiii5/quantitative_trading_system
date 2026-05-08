"""Advanced Risk Analytics Module.

Provides comprehensive risk metrics including VaR, CVaR, stress testing,
tail risk measures, and risk attribution. Designed for real-time risk monitoring.
"""
import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class RiskMetrics:
    var_95: float = 0.0
    var_99: float = 0.0
    cvar_95: float = 0.0
    cvar_99: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    calmar_ratio: float = 0.0
    sortino_ratio: float = 0.0
    tail_ratio: float = 0.0
    skewness: float = 0.0
    kurtosis: float = 0.0
    omega_ratio: float = 0.0


@dataclass
class StressTestResult:
    scenario_name: str
    portfolio_loss: float
    portfolio_loss_pct: float
    recovery_time_days: int | None = None


class AdvancedRiskAnalytics:
    def __init__(
        self,
        risk_free_rate: float = 0.03,
        target_return: float = 0.0,
    ):
        self._risk_free_rate = risk_free_rate
        self._target_return = target_return

    def calculate_var(
        self,
        returns: pd.Series,
        confidence_levels: list[float] = None,
    ) -> dict[str, float]:
        if confidence_levels is None:
            confidence_levels = [0.95, 0.99]

        results = {}
        for cl in confidence_levels:
            var = np.percentile(returns.dropna(), (1 - cl) * 100)
            results[f"var_{int(cl*100)}"] = float(var)

        return results

    def calculate_cvar(
        self,
        returns: pd.Series,
        confidence_levels: list[float] = None,
    ) -> dict[str, float]:
        if confidence_levels is None:
            confidence_levels = [0.95, 0.99]

        results = {}
        for cl in confidence_levels:
            var_threshold = np.percentile(returns.dropna(), (1 - cl) * 100)
            cvar = returns[returns <= var_threshold].mean()
            results[f"cvar_{int(cl*100)}"] = float(cvar) if np.isfinite(cvar) else 0.0

        return results

    def calculate_max_drawdown(
        self,
        equity_curve: pd.Series,
    ) -> tuple[float, int]:
        if len(equity_curve) < 2:
            return 0.0, 0

        running_max = equity_curve.expanding().max()
        drawdown = (equity_curve - running_max) / running_max

        max_dd = float(drawdown.min())
        max_dd_idx = drawdown.idxmin()

        peak_idx = equity_curve[:max_dd_idx].idxmax()
        duration = (max_dd_idx - peak_idx).days if hasattr(max_dd_idx - peak_idx, 'days') else 0

        return abs(max_dd), duration

    def calculate_drawdown_curve(
        self,
        equity_curve: pd.Series,
    ) -> pd.Series:
        running_max = equity_curve.expanding().max()
        drawdown = (equity_curve - running_max) / running_max
        return drawdown

    def calculate_sortino_ratio(
        self,
        returns: pd.Series,
        target_return: float = 0.0,
    ) -> float:
        excess_returns = returns - target_return
        downside_returns = excess_returns[excess_returns < 0]

        if len(downside_returns) < 2:
            return 0.0

        downside_std = np.sqrt((downside_returns ** 2).mean())
        if downside_std < 1e-12:
            return 0.0

        mean_excess = excess_returns.mean()
        return float(mean_excess / downside_std)

    def calculate_omega_ratio(
        self,
        returns: pd.Series,
        threshold: float = 0.0,
    ) -> float:
        gains = returns[returns > threshold].sum()
        losses = abs(returns[returns < threshold].sum())

        if losses < 1e-12:
            return 999.0 if gains > 0 else 0.0

        return float(gains / losses)

    def calculate_tail_ratio(self, returns: pd.Series) -> float:
        upper_tail = returns[returns > 0].abs().mean()
        lower_tail = returns[returns < 0].abs().mean()

        if lower_tail < 1e-12:
            return 0.0

        return float(upper_tail / lower_tail)

    def calculate_moments(self, returns: pd.Series) -> dict[str, float]:
        r = returns.dropna()
        if len(r) < 3:
            return {"skewness": 0.0, "kurtosis": 0.0}

        return {
            "skewness": float(pd.Series(r).skew()),
            "kurtosis": float(pd.Series(r).kurtosis()),
        }

    def calculate_risk_metrics(
        self,
        returns: pd.Series,
        equity_curve: pd.Series | None = None,
    ) -> RiskMetrics:
        metrics = RiskMetrics()

        var_dict = self.calculate_var(returns)
        metrics.var_95 = var_dict.get("var_95", 0.0)
        metrics.var_99 = var_dict.get("var_99", 0.0)

        cvar_dict = self.calculate_cvar(returns)
        metrics.cvar_95 = cvar_dict.get("cvar_95", 0.0)
        metrics.cvar_99 = cvar_dict.get("cvar_99", 0.0)

        if equity_curve is not None:
            max_dd, duration = self.calculate_max_drawdown(equity_curve)
            metrics.max_drawdown = max_dd
            metrics.max_drawdown_duration = duration

            if max_dd > 0:
                annual_return = returns.mean() * 252
                metrics.calmar_ratio = float(annual_return / max_dd)

        metrics.sortino_ratio = self.calculate_sortino_ratio(returns)
        metrics.omega_ratio = self.calculate_omega_ratio(returns)
        metrics.tail_ratio = self.calculate_tail_ratio(returns)

        moments = self.calculate_moments(returns)
        metrics.skewness = moments["skewness"]
        metrics.kurtosis = moments["kurtosis"]

        return metrics

    def stress_test(
        self,
        returns: pd.Series,
        scenarios: dict[str, float] | None = None,
    ) -> list[StressTestResult]:
        if scenarios is None:
            scenarios = {
                "2008_crisis": -0.40,
                "2020_covid": -0.34,
                "dot_com_bubble": -0.45,
                "rate_hike": -0.15,
                "market_turbulence": -0.20,
            }

        current_value = 1000000
        results = []

        for name, shock in scenarios.items():
            loss = current_value * shock
            results.append(StressTestResult(
                scenario_name=name,
                portfolio_loss=loss,
                portfolio_loss_pct=shock,
            ))

        return results

    def calculate_risk_contribution(
        self,
        positions: dict[str, float],
        volatilities: dict[str, float],
        correlations: dict[tuple[str, str], float],
    ) -> dict[str, float]:
        total_vol = sum(volatilities.values())
        if total_vol < 1e-12:
            return dict.fromkeys(positions, 0.0)

        contributions = {}
        for name, vol in volatilities.items():
            weight = positions.get(name, 0)
            contributions[name] = weight * vol / total_vol

        return contributions

    def get_risk_report(
        self,
        returns: pd.Series,
        equity_curve: pd.Series | None = None,
    ) -> dict:
        metrics = self.calculate_risk_metrics(returns, equity_curve)
        stress_results = self.stress_test(returns)

        return {
            "var_95": round(metrics.var_95, 4),
            "var_99": round(metrics.var_99, 4),
            "cvar_95": round(metrics.cvar_95, 4),
            "cvar_99": round(metrics.cvar_99, 4),
            "max_drawdown": round(metrics.max_drawdown, 4),
            "sortino_ratio": round(metrics.sortino_ratio, 4),
            "omega_ratio": round(metrics.omega_ratio, 4),
            "tail_ratio": round(metrics.tail_ratio, 4),
            "skewness": round(metrics.skewness, 4),
            "kurtosis": round(metrics.kurtosis, 4),
            "stress_tests": [
                {"scenario": s.scenario_name, "loss_pct": round(s.portfolio_loss_pct, 4)}
                for s in stress_results
            ],
        }
