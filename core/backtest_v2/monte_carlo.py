import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class MonteCarloResult:
    ruin_probability: float = 0.0
    worst_max_drawdown: float = 0.0
    best_max_drawdown: float = 0.0
    avg_max_drawdown: float = 0.0
    sharpe_ci_lower: float = 0.0
    sharpe_ci_upper: float = 0.0
    sharpe_mean: float = 0.0
    return_ci_lower: float = 0.0
    return_ci_upper: float = 0.0
    return_mean: float = 0.0
    drawdown_distribution: List[float] = field(default_factory=list)
    sharpe_distribution: List[float] = field(default_factory=list)
    return_distribution: List[float] = field(default_factory=list)
    n_simulations: int = 0
    ruin_threshold: float = 0.0

    def to_dict(self) -> dict:
        return {
            "ruin_probability": round(self.ruin_probability, 4),
            "worst_max_drawdown": round(self.worst_max_drawdown, 2),
            "best_max_drawdown": round(self.best_max_drawdown, 2),
            "avg_max_drawdown": round(self.avg_max_drawdown, 2),
            "sharpe_ci": [round(self.sharpe_ci_lower, 2), round(self.sharpe_ci_upper, 2)],
            "sharpe_mean": round(self.sharpe_mean, 2),
            "return_ci": [round(self.return_ci_lower, 2), round(self.return_ci_upper, 2)],
            "return_mean": round(self.return_mean, 2),
            "n_simulations": self.n_simulations,
            "ruin_threshold": round(self.ruin_threshold, 2),
            "drawdown_distribution": [round(d, 2) for d in self.drawdown_distribution[-100:]],
            "sharpe_distribution": [round(s, 2) for s in self.sharpe_distribution[-100:]],
            "return_distribution": [round(r, 2) for r in self.return_distribution[-100:]],
        }


class MonteCarloStressTest:
    def __init__(
        self,
        initial_capital: float = 100000.0,
        ruin_threshold: float = 0.1,
        confidence_level: float = 0.95,
        risk_free_rate: float = 0.03,
    ):
        self.initial_capital = initial_capital
        self.ruin_threshold = ruin_threshold
        self.confidence_level = confidence_level
        self.risk_free_rate = risk_free_rate

    def run(
        self,
        equity_curve: List[float],
        n_simulations: int = 1000,
        method: str = "bootstrap",
    ) -> MonteCarloResult:
        if not equity_curve or len(equity_curve) < 30:
            return MonteCarloResult(n_simulations=n_simulations)

        daily_returns = np.diff(equity_curve) / np.maximum(equity_curve[:-1], 1)
        daily_returns = daily_returns[np.isfinite(daily_returns)]

        if len(daily_returns) < 10:
            return MonteCarloResult(n_simulations=n_simulations)

        max_drawdowns = []
        sharpe_ratios = []
        total_returns = []
        ruin_count = 0

        for _ in range(n_simulations):
            if method == "bootstrap":
                sim_returns = self._bootstrap_returns(daily_returns)
            else:
                sim_returns = self._parametric_returns(daily_returns)

            sim_equity = self._build_equity_curve(sim_returns)
            dd = self._calc_max_drawdown(sim_equity)
            sharpe = self._calc_sharpe(sim_returns)
            total_ret = (sim_equity[-1] / self.initial_capital - 1) * 100

            max_drawdowns.append(dd)
            sharpe_ratios.append(sharpe)
            total_returns.append(total_ret)

            if sim_equity[-1] < self.initial_capital * self.ruin_threshold:
                ruin_count += 1

        max_drawdowns = np.array(max_drawdowns)
        sharpe_ratios = np.array(sharpe_ratios)
        total_returns = np.array(total_returns)

        alpha = 1 - self.confidence_level
        ci_lower_idx = int(len(sharpe_ratios) * alpha / 2)
        ci_upper_idx = int(len(sharpe_ratios) * (1 - alpha / 2))

        sorted_sharpe = np.sort(sharpe_ratios)
        sorted_returns = np.sort(total_returns)

        return MonteCarloResult(
            ruin_probability=ruin_count / n_simulations,
            worst_max_drawdown=float(np.max(max_drawdowns)),
            best_max_drawdown=float(np.min(max_drawdowns)),
            avg_max_drawdown=float(np.mean(max_drawdowns)),
            sharpe_ci_lower=float(sorted_sharpe[ci_lower_idx]) if ci_lower_idx < len(sorted_sharpe) else 0,
            sharpe_ci_upper=float(sorted_sharpe[ci_upper_idx]) if ci_upper_idx < len(sorted_sharpe) else 0,
            sharpe_mean=float(np.mean(sharpe_ratios)),
            return_ci_lower=float(sorted_returns[ci_lower_idx]) if ci_lower_idx < len(sorted_returns) else 0,
            return_ci_upper=float(sorted_returns[ci_upper_idx]) if ci_upper_idx < len(sorted_returns) else 0,
            return_mean=float(np.mean(total_returns)),
            drawdown_distribution=max_drawdowns.tolist(),
            sharpe_distribution=sharpe_ratios.tolist(),
            return_distribution=total_returns.tolist(),
            n_simulations=n_simulations,
            ruin_threshold=self.ruin_threshold,
        )

    def run_stress_scenarios(
        self,
        equity_curve: List[float],
        scenarios: Optional[Dict[str, dict]] = None,
    ) -> Dict[str, MonteCarloResult]:
        if scenarios is None:
            scenarios = {
                "2008_crisis": {"shock": -0.40, "duration": 30, "volatility_mult": 3.0},
                "2015_crash": {"shock": -0.30, "duration": 15, "volatility_mult": 2.5},
                "2020_covid": {"shock": -0.35, "duration": 20, "volatility_mult": 2.8},
                "flash_crash": {"shock": -0.20, "duration": 1, "volatility_mult": 5.0},
                "slow_bleed": {"shock": -0.50, "duration": 120, "volatility_mult": 1.5},
            }

        results = {}

        def _run_scenario(name_params):
            name, params = name_params
            stressed_curve = self._apply_stress(equity_curve, params)
            mc_result = self.run(stressed_curve, n_simulations=500)
            return name, mc_result

        with ThreadPoolExecutor() as executor:
            futures = {executor.submit(_run_scenario, (name, params)): name for name, params in scenarios.items()}
            for future in as_completed(futures):
                try:
                    name, mc_result = future.result()
                    results[name] = mc_result
                except Exception as e:
                    name = futures[future]
                    logger.error(f"Stress scenario {name} failed: {e}")

        return results

    def _bootstrap_returns(self, daily_returns: np.ndarray) -> np.ndarray:
        n = len(daily_returns)
        indices = np.random.randint(0, n, size=n)
        return daily_returns[indices]

    def _parametric_returns(self, daily_returns: np.ndarray) -> np.ndarray:
        mean = np.mean(daily_returns)
        std = np.std(daily_returns)
        n = len(daily_returns)
        return np.random.normal(mean, std, size=n)

    def _build_equity_curve(self, returns: np.ndarray) -> np.ndarray:
        equity = np.zeros(len(returns) + 1)
        equity[0] = self.initial_capital
        for i in range(len(returns)):
            equity[i + 1] = equity[i] * (1 + returns[i])
            if equity[i + 1] <= 0:
                equity[i + 1:] = 0
                break
        return equity

    def _calc_max_drawdown(self, equity: np.ndarray) -> float:
        peak = equity[0]
        max_dd = 0.0
        for e in equity:
            peak = max(peak, e)
            dd = (peak - e) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)
        return max_dd * 100

    def _calc_sharpe(self, returns: np.ndarray) -> float:
        if len(returns) < 10 or np.std(returns) <= 0:
            return 0.0
        return (np.mean(returns) - self.risk_free_rate / 252) / np.std(returns) * np.sqrt(252)

    def _apply_stress(self, equity_curve: List[float], params: dict) -> List[float]:
        equity = np.array(equity_curve, dtype=float)
        shock = params.get("shock", -0.3)
        duration = params.get("duration", 30)
        vol_mult = params.get("volatility_mult", 2.0)

        n = len(equity)
        if n < duration + 10:
            return equity.tolist()

        daily_returns = np.diff(equity) / np.maximum(equity[:-1], 1)

        start_idx = n // 3
        for i in range(start_idx, min(start_idx + duration, len(daily_returns))):
            daily_shock = shock / duration
            noise = np.random.normal(0, np.std(daily_returns) * (vol_mult - 1))
            daily_returns[i] += daily_shock + noise

        stressed_equity = np.zeros(n)
        stressed_equity[0] = self.initial_capital
        for i in range(len(daily_returns)):
            stressed_equity[i + 1] = stressed_equity[i] * (1 + daily_returns[i])
            if stressed_equity[i + 1] <= 0:
                stressed_equity[i + 1:] = 0
                break

        return stressed_equity.tolist()
