import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats

from core.backtest import BacktestEngine, BacktestResult
from core.strategies import BaseStrategy

logger = logging.getLogger(__name__)


@dataclass
class WalkForwardSplit:
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    train_metrics: dict = field(default_factory=dict)
    test_metrics: dict = field(default_factory=dict)


@dataclass
class WalkForwardResult:
    strategy_name: str
    symbol: str
    n_splits: int
    train_period: int
    test_period: int
    splits: list[WalkForwardSplit] = field(default_factory=list)
    aggregate: dict = field(default_factory=dict)
    overfitting_score: float = 0.0
    p_value: float = 1.0
    is_significant: bool = False

    def to_dict(self) -> dict:
        return {
            "strategy_name": self.strategy_name,
            "symbol": self.symbol,
            "n_splits": self.n_splits,
            "train_period": self.train_period,
            "test_period": self.test_period,
            "splits": [
                {
                    "train_start": s.train_start,
                    "train_end": s.train_end,
                    "test_start": s.test_start,
                    "test_end": s.test_end,
                    "train_metrics": s.train_metrics,
                    "test_metrics": s.test_metrics,
                }
                for s in self.splits
            ],
            "aggregate": self.aggregate,
            "overfitting_score": round(self.overfitting_score, 4),
            "p_value": self.p_value,
            "is_significant": self.is_significant,
        }


@dataclass
class WalkForwardConfig:
    n_splits: int = 5
    train_period: int = 252
    test_period: int = 63
    val_period: int = 21
    min_train_size: int = 100
    expanding_window: bool = False
    initial_capital: float = 100000.0


@dataclass
class _WFSplit:
    train_start: int
    train_end: int
    val_start: int
    val_end: int
    test_start: int
    test_end: int


def generate_walk_forward_splits(
    n_bars: int,
    config: WalkForwardConfig | None = None,
) -> list[_WFSplit]:
    config = config or WalkForwardConfig()
    splits: list[_WFSplit] = []

    val_period = config.val_period
    test_period = config.test_period
    min_train = config.min_train_size

    if n_bars < min_train + val_period + test_period:
        return splits

    train_start = 0
    train_end = min_train

    while True:
        val_start = train_end
        val_end = val_start + val_period
        test_start = val_end
        test_end = test_start + test_period

        if test_end > n_bars:
            break

        splits.append(_WFSplit(
            train_start=train_start,
            train_end=train_end,
            val_start=val_start,
            val_end=val_end,
            test_start=test_start,
            test_end=test_end,
        ))

        if config.expanding_window:
            train_end += test_period
        else:
            train_start += test_period
            train_end += test_period

    return splits


def calc_overfitting_score(
    train_metrics: dict,
    val_metrics: dict,
    test_metrics: dict,
) -> float:
    train_sharpe = train_metrics.get("sharpe_ratio", 0.0)
    val_sharpe = val_metrics.get("sharpe_ratio", 0.0)
    test_sharpe = test_metrics.get("sharpe_ratio", 0.0)

    if abs(train_sharpe) < 1e-10:
        return 0.0

    train_val_degradation = abs(train_sharpe - val_sharpe) / abs(train_sharpe)
    val_test_degradation = abs(val_sharpe - test_sharpe) / max(abs(val_sharpe), 1e-10)

    score = (train_val_degradation + val_test_degradation) / 2.0
    return min(1.0, max(0.0, score))


def calc_strategy_metrics(equity_curve: list) -> dict:
    if len(equity_curve) < 2:
        return {
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "cagr": 0.0,
            "total_return": 0.0,
        }

    equity = np.array(equity_curve, dtype=float)
    returns = np.diff(equity) / equity[:-1]

    total_return = float(equity[-1] / equity[0] - 1)

    n_days = len(equity) - 1
    years = max(n_days / 252, 1e-6)
    cagr = float((1 + total_return) ** (1 / years) - 1) if total_return > -1 else 0.0

    std = float(np.std(returns)) * np.sqrt(252)
    sharpe = (cagr - 0.03) / std if std > 0 else 0.0

    cummax = np.maximum.accumulate(equity)
    drawdown = (equity - cummax) / cummax
    max_drawdown = float(np.min(drawdown))

    return {
        "sharpe_ratio": round(sharpe, 4),
        "max_drawdown": round(max_drawdown, 4),
        "cagr": round(cagr, 4),
        "total_return": round(total_return, 4),
    }


class WalkForwardValidator:

    def __init__(self, config: WalkForwardConfig | None = None):
        self._config = config or WalkForwardConfig()


def _extract_metrics(result: BacktestResult) -> dict:
    return {
        "total_return": round(result.total_return, 4),
        "annual_return": round(result.annual_return, 4),
        "sharpe_ratio": round(result.sharpe_ratio, 4),
        "max_drawdown": round(result.max_drawdown, 4),
        "win_rate": round(result.win_rate, 4),
        "total_trades": result.total_trades,
        "profit_factor": round(result.profit_factor, 4),
    }


def walk_forward_analysis(
    strategy: BaseStrategy,
    df: pd.DataFrame,
    symbol: str = "",
    train_period: int = 252,
    test_period: int = 63,
    n_splits: int = 5,
    initial_capital: float = 100000,
    engine: BacktestEngine | None = None,
) -> WalkForwardResult:
    if df is None or len(df) < train_period + test_period:
        return WalkForwardResult(
            strategy_name=strategy.name,
            symbol=symbol,
            n_splits=0,
            train_period=train_period,
            test_period=test_period,
        )

    if "date" not in df.columns:
        return WalkForwardResult(
            strategy_name=strategy.name,
            symbol=symbol,
            n_splits=0,
            train_period=train_period,
            test_period=test_period,
        )

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)

    total_bars = len(df)
    min_bars = train_period + test_period * n_splits
    if total_bars < min_bars:
        actual_splits = max(1, (total_bars - train_period) // test_period)
        if actual_splits < 1:
            return WalkForwardResult(
                strategy_name=strategy.name,
                symbol=symbol,
                n_splits=0,
                train_period=train_period,
                test_period=test_period,
            )
        n_splits = actual_splits

    if engine is None:
        engine = BacktestEngine(initial_capital=initial_capital)

    result = WalkForwardResult(
        strategy_name=strategy.name,
        symbol=symbol,
        n_splits=n_splits,
        train_period=train_period,
        test_period=test_period,
    )

    train_returns = []
    test_returns = []
    train_sharpes = []
    test_sharpes = []

    for i in range(n_splits):
        train_start_idx = 0
        train_end_idx = train_period + i * test_period
        test_start_idx = train_end_idx
        test_end_idx = min(test_start_idx + test_period, total_bars)

        if test_end_idx <= test_start_idx:
            break

        train_df = df.iloc[train_start_idx:train_end_idx].copy()
        test_df = df.iloc[test_start_idx:test_end_idx].copy()

        if len(train_df) < 20 or len(test_df) < 5:
            break

        train_dates = train_df["date"]
        test_dates = test_df["date"]

        split = WalkForwardSplit(
            train_start=str(train_dates.iloc[0])[:10],
            train_end=str(train_dates.iloc[-1])[:10],
            test_start=str(test_dates.iloc[0])[:10],
            test_end=str(test_dates.iloc[-1])[:10],
        )

        try:
            train_result = engine.run(strategy, train_df, symbol)
            split.train_metrics = _extract_metrics(train_result)
            train_returns.append(train_result.total_return)
            train_sharpes.append(train_result.sharpe_ratio)
        except Exception as e:
            logger.warning("Walk-forward train split %s failed: %s", i, e)
            split.train_metrics = {"error": str(e)}

        try:
            test_result = engine.run(strategy, test_df, symbol)
            split.test_metrics = _extract_metrics(test_result)
            test_returns.append(test_result.total_return)
            test_sharpes.append(test_result.sharpe_ratio)
        except Exception as e:
            logger.warning("Walk-forward test split %s failed: %s", i, e)
            split.test_metrics = {"error": str(e)}

        result.splits.append(split)

    if train_returns and test_returns:
        avg_train_return = float(np.mean(train_returns))
        avg_test_return = float(np.mean(test_returns))
        avg_train_sharpe = float(np.mean(train_sharpes)) if train_sharpes else 0
        avg_test_sharpe = float(np.mean(test_sharpes)) if test_sharpes else 0

        oos_ratio = avg_test_return / avg_train_return if avg_train_return != 0 else 0

        degradation = 0.0
        if avg_train_return != 0:
            degradation = (avg_train_return - avg_test_return) / abs(avg_train_return)

        overfitting_score = max(0.0, min(1.0, degradation))

        result.aggregate = {
            "avg_train_return": round(avg_train_return, 4),
            "avg_test_return": round(avg_test_return, 4),
            "avg_train_sharpe": round(avg_train_sharpe, 4),
            "avg_test_sharpe": round(avg_test_sharpe, 4),
            "oos_ratio": round(oos_ratio, 4),
            "degradation_pct": round(degradation * 100, 2),
            "n_valid_splits": len(result.splits),
        }
        result.overfitting_score = overfitting_score

        if len(train_sharpes) >= 3 and len(test_sharpes) >= 3:
            train_arr = np.array(train_sharpes, dtype=float)
            test_arr = np.array(test_sharpes, dtype=float)
            train_arr = train_arr[np.isfinite(train_arr)]
            test_arr = test_arr[np.isfinite(test_arr)]
            if len(train_arr) >= 3 and len(test_arr) >= 3:
                diff = train_arr - test_arr
                if np.std(diff) > 1e-10:
                    try:
                        _, p_val = stats.wilcoxon(diff, alternative="two-sided")
                        result.p_value = round(float(p_val), 4)
                        result.is_significant = bool(p_val < 0.05)
                        result.aggregate["significance_p_value"] = result.p_value
                        result.aggregate["is_significant"] = result.is_significant
                    except Exception as e:
                        logger.debug("Wilcoxon test failed: %s", e)

    return result
