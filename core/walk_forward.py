import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class WalkForwardConfig:
    train_ratio: float = 0.6
    validation_ratio: float = 0.2
    test_ratio: float = 0.2
    n_splits: int = 5
    min_train_size: int = 120
    expanding_window: bool = False


@dataclass
class WalkForwardSplit:
    train_start: int
    train_end: int
    val_start: int
    val_end: int
    test_start: int
    test_end: int


@dataclass
class WalkForwardResult:
    split_index: int
    train_metrics: Dict
    val_metrics: Dict
    test_metrics: Dict
    overfitting_score: float
    data_split: WalkForwardSplit


def generate_walk_forward_splits(
    total_length: int,
    config: WalkForwardConfig = None,
) -> List[WalkForwardSplit]:
    config = config or WalkForwardConfig()
    splits = []
    n = total_length

    if config.expanding_window:
        test_size = max(int(n * config.test_ratio), 20)
        val_size = max(int(n * config.validation_ratio), 20)
        min_train = config.min_train_size

        step = max((n - min_train - val_size - test_size) // max(config.n_splits - 1, 1), 10)
        for i in range(config.n_splits):
            train_end = min_train + i * step + val_size + test_size
            if train_end > n:
                train_end = n
            val_end = train_end - test_size
            train_real_end = val_end - val_size

            if train_real_end < min_train:
                continue

            splits.append(WalkForwardSplit(
                train_start=0,
                train_end=train_real_end,
                val_start=train_real_end,
                val_end=val_end,
                test_start=val_end,
                test_end=train_end,
            ))
    else:
        test_size = max(int(n * config.test_ratio), 20)
        val_size = max(int(n * config.validation_ratio), 20)
        train_size = n - test_size - val_size

        if train_size < config.min_train_size:
            train_size = config.min_train_size
            remaining = n - train_size
            val_size = remaining // 2
            test_size = remaining - val_size

        step = max((train_size - config.min_train_size) // max(config.n_splits - 1, 1), 10)
        for i in range(config.n_splits):
            current_train_size = config.min_train_size + i * step
            if current_train_size + val_size + test_size > n:
                current_train_size = n - val_size - test_size
            if current_train_size < config.min_train_size:
                break

            train_end = current_train_size
            val_end = train_end + val_size
            test_end = val_end + test_size

            splits.append(WalkForwardSplit(
                train_start=0,
                train_end=train_end,
                val_start=train_end,
                val_end=val_end,
                test_start=val_end,
                test_end=test_end,
            ))

    return splits


def calc_overfitting_score(
    train_metrics: Dict,
    val_metrics: Dict,
    test_metrics: Dict,
) -> float:
    train_sharpe = train_metrics.get("sharpe_ratio", 0)
    val_sharpe = val_metrics.get("sharpe_ratio", 0)
    test_sharpe = test_metrics.get("sharpe_ratio", 0)

    train_val_gap = abs(train_sharpe - val_sharpe)
    val_test_gap = abs(val_sharpe - test_sharpe)

    if abs(train_sharpe) > 1e-10:
        degradation = (train_sharpe - val_sharpe) / abs(train_sharpe)
    else:
        degradation = 0.0

    score = min(1.0, (train_val_gap * 0.5 + val_test_gap * 0.3 + max(0, degradation) * 0.2))
    return round(score, 4)


def calc_strategy_metrics(
    equity_curve: List[float],
    risk_free_rate: float = 0.03,
) -> Dict:
    if len(equity_curve) < 2:
        return {
            "total_return": 0.0,
            "cagr": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "max_drawdown": 0.0,
            "volatility": 0.0,
            "win_rate": 0.0,
            "calmar_ratio": 0.0,
        }

    eq = pd.Series(equity_curve)
    returns = eq.pct_change().dropna()

    total_return = (eq.iloc[-1] / eq.iloc[0]) - 1 if eq.iloc[0] > 0 else 0.0
    n_years = max(len(returns) / 252, 1e-6)
    cagr = (1 + total_return) ** (1 / n_years) - 1 if total_return > -1 else total_return

    excess = returns - risk_free_rate / 252
    std = returns.std()
    sharpe = (excess.mean() / std * np.sqrt(252)) if std > 1e-12 else 0.0

    downside = excess[excess < 0]
    downside_std = np.sqrt(np.mean(downside ** 2)) if len(downside) > 0 else 0.0
    sortino = (excess.mean() / downside_std * np.sqrt(252)) if downside_std > 1e-12 else 0.0

    cummax = eq.cummax()
    drawdown = (eq - cummax) / cummax
    max_dd = float(drawdown.min())

    vol = float(std * np.sqrt(252))

    positive = (returns > 0).sum()
    win_rate = float(positive / len(returns)) if len(returns) > 0 else 0.0

    calmar = cagr / abs(max_dd) if abs(max_dd) > 1e-10 else 0.0

    return {
        "total_return": round(total_return, 6),
        "cagr": round(cagr, 6),
        "sharpe_ratio": round(sharpe, 4),
        "sortino_ratio": round(sortino, 4),
        "max_drawdown": round(max_dd, 6),
        "volatility": round(vol, 6),
        "win_rate": round(win_rate, 4),
        "calmar_ratio": round(calmar, 4),
    }


class WalkForwardValidator:
    def __init__(self, config: WalkForwardConfig = None):
        self._config = config or WalkForwardConfig()

    def validate(
        self,
        df: pd.DataFrame,
        strategy,
        backtest_engine,
        initial_capital: float = 1000000,
    ) -> List[WalkForwardResult]:
        splits = generate_walk_forward_splits(len(df), self._config)
        results = []

        for idx, split in enumerate(splits):
            train_df = df.iloc[split.train_start:split.train_end].copy()
            val_df = df.iloc[split.val_start:split.val_end].copy()
            test_df = df.iloc[split.test_start:split.test_end].copy()

            if len(train_df) < 20 or len(val_df) < 5 or len(test_df) < 5:
                continue

            try:
                train_result = backtest_engine.run(strategy, train_df)
                val_result = backtest_engine.run(strategy, val_df)
                test_result = backtest_engine.run(strategy, test_df)

                train_metrics = calc_strategy_metrics(train_result.equity_curve)
                val_metrics = calc_strategy_metrics(val_result.equity_curve)
                test_metrics = calc_strategy_metrics(test_result.equity_curve)

                overfitting = calc_overfitting_score(train_metrics, val_metrics, test_metrics)

                results.append(WalkForwardResult(
                    split_index=idx,
                    train_metrics=train_metrics,
                    val_metrics=val_metrics,
                    test_metrics=test_metrics,
                    overfitting_score=overfitting,
                    data_split=split,
                ))
            except Exception as e:
                logger.warning(f"Walk-forward split {idx} failed: {e}")
                continue

        return results

    def get_validation_report(self, results: List[WalkForwardResult]) -> Dict:
        if not results:
            return {"error": "No valid walk-forward results"}

        avg_train_sharpe = np.mean([r.train_metrics.get("sharpe_ratio", 0) for r in results])
        avg_val_sharpe = np.mean([r.val_metrics.get("sharpe_ratio", 0) for r in results])
        avg_test_sharpe = np.mean([r.test_metrics.get("sharpe_ratio", 0) for r in results])
        avg_overfitting = np.mean([r.overfitting_score for r in results])

        avg_test_return = np.mean([r.test_metrics.get("total_return", 0) for r in results])
        avg_test_max_dd = np.mean([r.test_metrics.get("max_drawdown", 0) for r in results])

        consistency = 0
        for r in results:
            if r.test_metrics.get("sharpe_ratio", 0) > 0:
                consistency += 1
        consistency_rate = consistency / len(results)

        return {
            "n_splits": len(results),
            "avg_train_sharpe": round(avg_train_sharpe, 4),
            "avg_val_sharpe": round(avg_val_sharpe, 4),
            "avg_test_sharpe": round(avg_test_sharpe, 4),
            "sharpe_degradation": round(avg_train_sharpe - avg_test_sharpe, 4),
            "avg_overfitting_score": round(avg_overfitting, 4),
            "avg_test_return": round(avg_test_return, 6),
            "avg_test_max_drawdown": round(avg_test_max_dd, 6),
            "consistency_rate": round(consistency_rate, 4),
            "is_robust": avg_overfitting < 0.3 and avg_test_sharpe > 0.5 and consistency_rate > 0.6,
        }
