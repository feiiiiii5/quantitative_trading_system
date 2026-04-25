import itertools
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from core.strategies import BaseStrategy

logger = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    params: dict
    sharpe_ratio: float = 0.0
    total_return: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "params": self.params,
            "sharpe_ratio": round(self.sharpe_ratio, 2),
            "total_return": round(self.total_return, 2),
            "max_drawdown": round(self.max_drawdown, 2),
            "win_rate": round(self.win_rate, 2),
            "score": round(self.score, 4),
        }


@dataclass
class WalkForwardResult:
    train_results: List[OptimizationResult] = field(default_factory=list)
    test_results: List[OptimizationResult] = field(default_factory=list)
    best_params: dict = field(default_factory=dict)
    stability_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "train_results": [r.to_dict() for r in self.train_results],
            "test_results": [r.to_dict() for r in self.test_results],
            "best_params": self.best_params,
            "stability_score": round(self.stability_score, 4),
        }


class ParamOptimizer:
    def __init__(
        self,
        initial_capital: float = 100000.0,
        commission_rate: float = 0.0003,
        slippage: float = 0.001,
        risk_free_rate: float = 0.03,
    ):
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage = slippage
        self.risk_free_rate = risk_free_rate

    def grid_search(
        self,
        strategy_class: type,
        param_grid: Dict[str, List],
        df: pd.DataFrame,
        symbol: str = "",
        metric: str = "sharpe",
        top_n: int = 10,
    ) -> List[OptimizationResult]:
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        combinations = list(itertools.product(*values))

        results = []
        total = len(combinations)
        logger.info(f"Grid search: {total} combinations")

        for idx, combo in enumerate(combinations):
            params = dict(zip(keys, combo))
            try:
                strategy = strategy_class(**params)
                result = self._evaluate(strategy, df, symbol)
                result.params = params
                results.append(result)
            except Exception as e:
                logger.debug(f"Grid search combo {idx} failed: {e}")

        if metric == "sharpe":
            results.sort(key=lambda r: r.sharpe_ratio, reverse=True)
        elif metric == "return":
            results.sort(key=lambda r: r.total_return, reverse=True)
        elif metric == "score":
            results.sort(key=lambda r: r.score, reverse=True)
        else:
            results.sort(key=lambda r: r.sharpe_ratio, reverse=True)

        return results[:top_n]

    def bayesian_optimize(
        self,
        strategy_class: type,
        param_ranges: Dict[str, Tuple],
        df: pd.DataFrame,
        symbol: str = "",
        n_trials: int = 50,
        metric: str = "sharpe",
    ) -> List[OptimizationResult]:
        try:
            import optuna
        except ImportError:
            logger.warning("optuna not installed, falling back to grid search")
            param_grid = {k: list(range(int(v[0]), int(v[1]) + 1, max(1, int((v[1] - v[0]) / 5)))) for k, v in param_ranges.items()}
            return self.grid_search(strategy_class, param_grid, df, symbol, metric)

        results = []

        def objective(trial):
            params = {}
            for name, (low, high) in param_ranges.items():
                if isinstance(low, int) and isinstance(high, int):
                    params[name] = trial.suggest_int(name, low, high)
                else:
                    params[name] = trial.suggest_float(name, low, high)

            try:
                strategy = strategy_class(**params)
                result = self._evaluate(strategy, df, symbol)
                result.params = params
                results.append(result)
                if metric == "sharpe":
                    return result.sharpe_ratio
                elif metric == "return":
                    return result.total_return
                else:
                    return result.score
            except Exception:
                return -999

        try:
            study = optuna.create_study(direction="maximize")
            study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
        except Exception as e:
            logger.error(f"Bayesian optimization failed: {e}")

        results.sort(key=lambda r: r.sharpe_ratio if metric == "sharpe" else r.total_return, reverse=True)
        return results[:10]

    def walk_forward(
        self,
        strategy_class: type,
        param_grid: Dict[str, List],
        df: pd.DataFrame,
        symbol: str = "",
        n_splits: int = 5,
        train_ratio: float = 0.7,
    ) -> WalkForwardResult:
        if df.empty or len(df) < 60:
            return WalkForwardResult()

        n = len(df)
        fold_size = n // n_splits
        train_size = int(fold_size * train_ratio)

        wf_result = WalkForwardResult()
        param_stability: Dict[str, List] = {}

        for fold in range(n_splits):
            start = fold * fold_size
            train_end = min(start + train_size, n)
            test_end = min(start + fold_size, n)

            if test_end <= train_end:
                continue

            train_df = df.iloc[start:train_end].reset_index(drop=True)
            test_df = df.iloc[train_end:test_end].reset_index(drop=True)

            if len(train_df) < 30 or len(test_df) < 10:
                continue

            best_train = self.grid_search(strategy_class, param_grid, train_df, symbol, top_n=1)
            if best_train:
                wf_result.train_results.append(best_train[0])
                best_params = best_train[0].params

                for k, v in best_params.items():
                    if k not in param_stability:
                        param_stability[k] = []
                    param_stability[k].append(v)

                try:
                    test_strategy = strategy_class(**best_params)
                    test_result = self._evaluate(test_strategy, test_df, symbol)
                    test_result.params = best_params
                    wf_result.test_results.append(test_result)
                except Exception as e:
                    logger.debug(f"Walk-forward test fold {fold} failed: {e}")

        if wf_result.train_results:
            wf_result.best_params = wf_result.train_results[0].params

        if param_stability:
            stability_scores = []
            for k, vals in param_stability.items():
                if len(vals) > 1:
                    cv = np.std(vals) / max(np.mean(vals), 1e-8)
                    stability_scores.append(1.0 / (1.0 + cv))
            if stability_scores:
                wf_result.stability_score = float(np.mean(stability_scores))

        return wf_result

    def _evaluate(self, strategy: BaseStrategy, df: pd.DataFrame, symbol: str) -> OptimizationResult:
        from core.backtest import BacktestEngine
        engine = BacktestEngine(
            initial_capital=self.initial_capital,
            commission_rate=self.commission_rate,
            slippage=self.slippage,
            risk_free_rate=self.risk_free_rate,
        )
        bt_result = engine.run(strategy, df)

        score = (
            bt_result.sharpe_ratio * 0.4
            + bt_result.total_return / 100 * 0.3
            + (1 - bt_result.max_drawdown / 100) * 0.2
            + bt_result.win_rate / 100 * 0.1
        )

        return OptimizationResult(
            sharpe_ratio=bt_result.sharpe_ratio,
            total_return=bt_result.total_return,
            max_drawdown=bt_result.max_drawdown,
            win_rate=bt_result.win_rate,
            score=score,
        )

    def generate_heatmap_data(
        self, results: List[OptimizationResult], param_x: str, param_y: str,
    ) -> dict:
        x_vals = sorted(set(r.params.get(param_x, 0) for r in results))
        y_vals = sorted(set(r.params.get(param_y, 0) for r in results))

        result_map = {}
        for r in results:
            x = r.params.get(param_x, 0)
            y = r.params.get(param_y, 0)
            result_map[(x, y)] = r.sharpe_ratio

        z_data = []
        for y in y_vals:
            row = []
            for x in x_vals:
                row.append(result_map.get((x, y), 0))
            z_data.append(row)

        return {
            "x": x_vals,
            "y": y_vals,
            "z": z_data,
            "x_label": param_x,
            "y_label": param_y,
            "z_label": "Sharpe Ratio",
        }
