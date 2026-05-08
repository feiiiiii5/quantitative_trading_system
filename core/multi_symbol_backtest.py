"""
Multi-Symbol Backtest Engine
Runs the same strategy across multiple symbols with correlation-aware position sizing.
"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from core.backtest import BacktestEngine, BacktestResult
from core.strategies import STRATEGY_REGISTRY

logger = logging.getLogger(__name__)

__all__ = [
    "MultiSymbolConfig",
    "SymbolResult",
    "MultiSymbolBacktest",
    "run_multi_symbol",
]


@dataclass
class MultiSymbolConfig:
    strategy_name: str
    symbols: list[str]
    initial_capital: float = 1_000_000.0
    max_positions: int = 5
    correlation_threshold: float = 0.7
    position_method: str = "equal_weight"
    parallel: bool = True
    max_workers: int = 4
    correlation_window: int = 20


@dataclass
class SymbolResult:
    symbol: str
    result: BacktestResult
    weight: float
    final_capital: float
    allocation_pct: float


@dataclass
class MultiSymbolReport:
    config: MultiSymbolConfig
    symbol_results: dict[str, SymbolResult]
    total_return: float = 0.0
    portfolio_sharpe: float = 0.0
    portfolio_max_dd: float = 0.0
    portfolio_win_rate: float = 0.0
    total_trades: int = 0
    correlation_matrix: dict[str, dict[str, float]] = field(default_factory=dict)
    weights: dict[str, float] = field(default_factory=dict)
    capital_history: list[dict[str, float]] = field(default_factory=list)
    combined_equity: list[float] = field(default_factory=list)
    combined_drawdown: list[float] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "config": {
                "strategy_name": self.config.strategy_name,
                "symbols": self.config.symbols,
                "initial_capital": self.config.initial_capital,
                "max_positions": self.config.max_positions,
                "position_method": self.config.position_method,
                "correlation_threshold": self.config.correlation_threshold,
            },
            "portfolio": {
                "total_return": round(self.total_return, 4),
                "portfolio_sharpe": round(self.portfolio_sharpe, 2),
                "portfolio_max_dd": round(self.portfolio_max_dd, 4),
                "portfolio_win_rate": round(self.portfolio_win_rate, 4),
                "total_trades": self.total_trades,
            },
            "weights": {k: round(v, 4) for k, v in self.weights.items()},
            "correlation_matrix": self.correlation_matrix,
            "symbols": {
                sym: {
                    "weight": round(sr.weight, 4),
                    "allocation_pct": round(sr.allocation_pct, 4),
                    "final_capital": round(sr.final_capital, 2),
                    "return": round(sr.result.total_return, 4),
                    "sharpe": round(sr.result.sharpe_ratio, 2),
                    "max_dd": round(sr.result.max_drawdown, 4),
                    "trades": sr.result.total_trades,
                }
                for sym, sr in self.symbol_results.items()
            },
        }


class MultiSymbolBacktest:
    def __init__(self, config: MultiSymbolConfig):
        self._config = config
        self._backtester = BacktestEngine()

    def _run_single(
        self,
        symbol: str,
        data: pd.DataFrame,
        capital: float,
    ) -> SymbolResult:
        strategy_cls = STRATEGY_REGISTRY.get(self._config.strategy_name)
        if strategy_cls is None:
            strategy_cls = STRATEGY_REGISTRY.get("DualMAStrategy")
        strategy = strategy_cls()
        result = self._backtester.run(
            strategy=strategy,
            df=data,
            symbol=symbol,
        )
        final = capital * (1 + result.total_return)
        return SymbolResult(
            symbol=symbol,
            result=result,
            weight=0.0,
            final_capital=final,
            allocation_pct=0.0,
        )

    def _compute_correlation_matrix(
        self,
        returns_by_symbol: dict[str, pd.Series],
    ) -> dict[str, dict[str, float]]:
        if len(returns_by_symbol) < 2:
            return {}

        aligned = {}
        for sym, ret in returns_by_symbol.items():
            if len(ret) > 5:
                aligned[sym] = ret.reset_index(drop=True)

        min_len = min(len(v) for v in aligned.values()) if aligned else 0
        if min_len < 5:
            return {}

        df = pd.DataFrame({sym: series.iloc[:min_len] for sym, series in aligned.items()})
        corr = df.corr()
        return {
            str(sym_a): {
                str(sym_b): round(val, 4)
                for sym_b, val in row.items()
            }
            for sym_a, row in corr.iterrows()
        }

    def _compute_weights(
        self,
        results: list[SymbolResult],
        returns_by_symbol: dict[str, pd.Series],
    ) -> dict[str, float]:
        method = self._config.position_method
        if method == "equal_weight":
            n = len(results)
            return {r.symbol: 1.0 / n for r in results}
        if method == "sharpe_weighted":
            total_sharpe = sum(max(r.result.sharpe_ratio, 0.1) for r in results)
            return {r.symbol: max(r.result.sharpe_ratio, 0.1) / total_sharpe for r in results}
        if method == "inverse_vol":
            vols = {r.symbol: max(r.result.annual_volatility, 1e-6) for r in results}
            total = sum(1 / v for v in vols.values())
            return {sym: (1 / vol) / total for sym, vol in vols.items()}
        if method == "correlation_adjusted":
            weights = {r.symbol: max(r.result.sharpe_ratio, 0.1) for r in results}
            for sym_a in weights:
                for sym_b, corr_val in self._correlation_matrix.get(sym_a, {}).items():
                    if (sym_b in weights and sym_b != sym_a and abs(corr_val) > self._config.correlation_threshold and
                            weights[sym_a] <= weights.get(sym_b, 0)):
                        weights[sym_a] *= (1 - abs(corr_val) * 0.5)
            total = sum(weights.values())
            return {k: v / total for k, v in weights.items()}
        return {r.symbol: 1.0 / len(results) for r in results}

    def _aggregate_results(
        self,
        results: list[SymbolResult],
        weights: dict[str, float],
    ) -> tuple[float, float, float, float, int]:
        returns = []
        all_trades = 0
        total_wins = 0

        for r in results:
            w = weights.get(r.symbol, 0)
            returns.append(r.result.total_return * w)
            all_trades += r.result.total_trades
            total_wins += r.result.win_trades

        weighted_return = sum(returns)
        weighted_sharpe = sum(r.result.sharpe_ratio * weights.get(r.symbol, 0) for r in results)
        weighted_dd = sum(r.result.max_drawdown * weights.get(r.symbol, 0) for r in results)
        win_rate = total_wins / all_trades if all_trades > 0 else 0.0

        return weighted_return, weighted_sharpe, weighted_dd, win_rate, all_trades

    def run(
        self,
        data_by_symbol: dict[str, pd.DataFrame],
    ) -> MultiSymbolReport:
        valid_symbols = [
            sym for sym, df in data_by_symbol.items()
            if df is not None and len(df) > 30
        ]
        if not valid_symbols:
            raise ValueError("No valid symbol data provided")

        logger.info("Starting multi-symbol backtest for %s symbols", len)

        results: list[SymbolResult] = []
        returns_by_symbol: dict[str, pd.Series] = {}

        if self._config.parallel and len(valid_symbols) > 1:
            capital_per = self._config.initial_capital / len(valid_symbols)
            with ThreadPoolExecutor(max_workers=self._config.max_workers) as executor:
                futures = {
                    executor.submit(self._run_single, sym, data_by_symbol[sym], capital_per): sym
                    for sym in valid_symbols
                }
                for future in as_completed(futures):
                    sym = futures[future]
                    try:
                        result = future.result()
                        results.append(result)
                        if result.result.equity_curve and len(result.result.equity_curve) > 1:
                            rets = pd.Series(result.result.equity_curve).pct_change().dropna()
                            if len(rets) > 5:
                                returns_by_symbol[result.symbol] = rets
                        logger.info("  %s: return=%s, sharpe=%s", sym, result, result)
                    except Exception as ex:
                        logger.warning("  %s: failed - %s", sym, ex)
        else:
            capital_per = self._config.initial_capital / len(valid_symbols)
            for sym in valid_symbols:
                try:
                    result = self._run_single(sym, data_by_symbol[sym], capital_per)
                    results.append(result)
                    if result.result.equity_curve and len(result.result.equity_curve) > 1:
                        rets = pd.Series(result.result.equity_curve).pct_change().dropna()
                        if len(rets) > 5:
                            returns_by_symbol[result.symbol] = rets
                    logger.info("  %s: return=%s, sharpe=%s", sym, result, result)
                except Exception as ex:
                    logger.warning("  %s: failed - %s", sym, ex)

        self._correlation_matrix = self._compute_correlation_matrix(returns_by_symbol)
        weights = self._compute_weights(results, returns_by_symbol)

        total_return, portfolio_sharpe, portfolio_max_dd, win_rate, total_trades = self._aggregate_results(
            results, weights
        )

        for r in results:
            r.weight = weights.get(r.symbol, 0.0)
            r.allocation_pct = r.weight * 100

        report = MultiSymbolReport(
            config=self._config,
            symbol_results={r.symbol: r for r in results},
            total_return=total_return,
            portfolio_sharpe=portfolio_sharpe,
            portfolio_max_dd=portfolio_max_dd,
            portfolio_win_rate=win_rate,
            total_trades=total_trades,
            correlation_matrix=self._correlation_matrix,
            weights=weights,
        )

        logger.info("Portfolio: return=%s, sharpe=%s, max_dd=%s", total_return, portfolio_sharpe, portfolio_max_dd)
        return report


def run_multi_symbol(
    data_by_symbol: dict[str, pd.DataFrame],
    strategy_name: str,
    initial_capital: float = 1_000_000.0,
    position_method: str = "equal_weight",
    correlation_threshold: float = 0.7,
    parallel: bool = True,
) -> MultiSymbolReport:
    config = MultiSymbolConfig(
        strategy_name=strategy_name,
        symbols=list(data_by_symbol.keys()),
        initial_capital=initial_capital,
        position_method=position_method,
        correlation_threshold=correlation_threshold,
        parallel=parallel,
    )
    engine = MultiSymbolBacktest(config)
    return engine.run(data_by_symbol)
