"""Strategy parameter optimizer using grid search and walk-forward analysis."""
from __future__ import annotations

import itertools
import logging
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from core.metrics import InstitutionalMetrics, calc_all_metrics

logger = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    params: dict[str, Any]
    metrics: InstitutionalMetrics

    @property
    def sharpe(self) -> float:
        return self.metrics.sharpe_ratio

    @property
    def total_return(self) -> float:
        return self.metrics.total_return

    @property
    def max_drawdown(self) -> float:
        return self.metrics.max_drawdown

    def to_dict(self) -> dict:
        return {
            "params": self.params,
            "sharpe": self.sharpe,
            "total_return": self.total_return,
            "max_drawdown": self.max_drawdown,
            "win_rate": self.metrics.win_rate,
            "profit_loss_ratio": self.metrics.profit_loss_ratio,
        }


class StrategyOptimizer:
    def __init__(
        self,
        strategy_class: type,
        param_grid: dict[str, list[Any]],
        metric: str = "sharpe_ratio",
    ):
        self.strategy_class = strategy_class
        self.param_grid = param_grid
        self.metric = metric
        self.results: list[OptimizationResult] = []

    def _generate_param_combinations(self) -> list[dict[str, Any]]:
        keys = list(self.param_grid.keys())
        values = list(self.param_grid.values())
        combinations = list(itertools.product(*values))
        return [dict(zip(keys, combo, strict=True)) for combo in combinations]

    def optimize(
        self,
        data: pd.DataFrame,
        initial_capital: float = 100000.0,
        max_combinations: int = 1000,
    ) -> list[OptimizationResult]:
        combinations = self._generate_param_combinations()
        if len(combinations) > max_combinations:
            logger.warning(
                f"Parameter combinations {len(combinations)} exceeds max {max_combinations}, "
                "sampling subset"
            )
            indices = np.random.choice(
                len(combinations), max_combinations, replace=False
            )
            combinations = [combinations[i] for i in sorted(indices)]

        self.results = []
        for params in combinations:
            try:
                strategy = self.strategy_class(**params)
                equity_curve = self._backtest_strategy(strategy, data, initial_capital)
                returns = pd.Series(
                    np.diff(equity_curve) / equity_curve[:-1],
                    index=range(1, len(equity_curve)),
                )
                metrics = calc_all_metrics(equity_curve, returns)
                result = OptimizationResult(params=params, metrics=metrics)
                self.results.append(result)
            except Exception as e:
                logger.debug("Strategy failed with params %s: %s", params, e)
                continue

        return sorted(self.results, key=lambda x: getattr(x, self.metric, 0), reverse=True)

    def _backtest_strategy(
        self,
        strategy: Any,
        data: pd.DataFrame,
        initial_capital: float,
    ) -> np.ndarray:
        n = len(data)
        closes = data["close"].to_numpy()
        equity_curve = np.empty(n + 1, dtype=np.float64)
        equity_curve[0] = initial_capital

        position = 0.0

        for i in range(n):
            signal = strategy.generate_signal(data.iloc[: i + 1])
            price = closes[i]

            if signal.signal_type.value == "buy" and position == 0:
                position = initial_capital / price
                initial_capital = 0.0
            elif signal.signal_type.value == "sell" and position > 0:
                initial_capital = position * price
                position = 0.0

            equity_curve[i + 1] = position * price if position > 0 else initial_capital

        if position > 0:
            equity_curve[-1] = position * closes[-1]

        return equity_curve

    def get_best(self, n: int = 5) -> list[OptimizationResult]:
        return self.results[:n]

    def get_worst(self, n: int = 5) -> list[OptimizationResult]:
        return self.results[-n:]


def quick_optimize(
    strategy_class: type,
    param_grid: dict[str, list[Any]],
    data: pd.DataFrame,
    metric: str = "sharpe_ratio",
    top_n: int = 5,
) -> list[dict]:
    optimizer = StrategyOptimizer(strategy_class, param_grid, metric)
    optimizer.optimize(data)
    return [r.to_dict() for r in optimizer.get_best(top_n)]
