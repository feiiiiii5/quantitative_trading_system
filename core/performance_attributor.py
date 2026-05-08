from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

__all__ = [
    "PerformanceAttributor",
    "AttributionResult",
    "FactorExposure",
]


@dataclass
class FactorExposure:
    beta: float
    alpha: float
    r_squared: float
    residual_vol: float
    tracking_error: float | None = None


@dataclass
class AttributionResult:
    total_return: float
    active_return: float
    sector_allocation_return: float
    stock_selection_return: float
    interaction_return: float
    benchmark_return: float
    factor_exposures: dict[str, FactorExposure]
    period_returns: pd.DataFrame
    cumulative_portfolio: pd.Series
    cumulative_benchmark: pd.Series
    summary: dict


class PerformanceAttributor:
    def attribute(
        self,
        portfolio_returns: pd.Series,
        benchmark_returns: pd.Series | None = None,
        sector_map: dict[str, str] | None = None,
        factor_benchmarks: dict[str, pd.Series] | None = None,
    ) -> AttributionResult:
        portfolio_returns = portfolio_returns.dropna()
        if len(portfolio_returns) < 5:
            raise ValueError("Need at least 5 periods for attribution analysis")

        symbols = portfolio_returns.index.get_level_values(0).unique() if portfolio_returns.index.nlevels > 1 else None
        total_return = float((1 + portfolio_returns).prod() - 1)

        if benchmark_returns is not None:
            aligned = portfolio_returns.align(benchmark_returns, join="inner")
            portfolio_returns_aligned = aligned[0].dropna()
            benchmark_returns_aligned = aligned[1].dropna()
            common_idx = portfolio_returns_aligned.index.intersection(benchmark_returns_aligned.index)
            portfolio_returns_aligned = portfolio_returns_aligned.loc[common_idx]
            benchmark_returns_aligned = benchmark_returns_aligned.loc[common_idx]
            active_return = float((1 + portfolio_returns_aligned).prod() - 1) - float((1 + benchmark_returns_aligned).prod() - 1)
            benchmark_return = float((1 + benchmark_returns_aligned).prod() - 1)
            sector_alloc_ret, stock_sel_ret, interact_ret = self._brinson(
                portfolio_returns_aligned, benchmark_returns_aligned, sector_map, symbols
            )
        else:
            benchmark_return = 0.0
            active_return = total_return
            sector_alloc_ret, stock_sel_ret, interact_ret = 0.0, total_return, 0.0

        factor_exposures = {}
        if factor_benchmarks:
            for name, factor_ret in factor_benchmarks.items():
                aligned_portfolio = portfolio_returns.align(factor_ret, join="inner")
                p_ret = aligned_portfolio[0].dropna()
                f_ret = aligned_portfolio[1].dropna()
                common = p_ret.index.intersection(f_ret.index)
                if len(common) >= 10:
                    factor_exposures[name] = self._regression(p_ret.loc[common], f_ret.loc[common])

        cumulative_p = (1 + portfolio_returns).cumprod()
        cumulative_b = (1 + benchmark_returns_aligned).cumprod() if benchmark_returns is not None else cumulative_p

        period_df = pd.DataFrame({
            "portfolio_return": portfolio_returns,
            "benchmark_return": benchmark_returns if benchmark_returns is not None else 0.0,
        }).dropna()

        return AttributionResult(
            total_return=round(total_return, 4),
            active_return=round(active_return, 4),
            sector_allocation_return=round(sector_alloc_ret, 4),
            stock_selection_return=round(stock_sel_ret, 4),
            interaction_return=round(interact_ret, 4),
            benchmark_return=round(benchmark_return, 4),
            factor_exposures=factor_exposures,
            period_returns=period_df,
            cumulative_portfolio=cumulative_p,
            cumulative_benchmark=cumulative_b,
            summary={
                "total_periods": len(portfolio_returns),
                "win_rate": round(float((portfolio_returns > 0).sum()) / len(portfolio_returns), 4),
                "avg_return": round(float(portfolio_returns.mean()), 6),
                "volatility": round(float(portfolio_returns.std()), 6),
                "sharpe": round(float(portfolio_returns.mean() / portfolio_returns.std()) * np.sqrt(252) if portfolio_returns.std() > 1e-10 else 0.0, 4),
                "max_drawdown": round(float(self._max_drawdown(cumulative_p)), 4),
            },
        )

    def _regression(self, y: pd.Series, x: pd.Series) -> FactorExposure:
        x_vals = x.values.astype(float)
        y_vals = y.values.astype(float)
        n = len(y_vals)
        x_mean = x_vals.mean()
        y_mean = y_vals.mean()
        cov_xy = np.cov(x_vals, y_vals, ddof=1)[0, 1]
        var_x = np.var(x_vals, ddof=1)
        if var_x < 1e-12:
            return FactorExposure(beta=0.0, alpha=0.0, r_squared=0.0, residual_vol=0.0)
        beta = cov_xy / var_x
        alpha = y_mean - beta * x_mean
        y_pred = alpha + beta * x_vals
        ss_res = np.sum((y_vals - y_pred) ** 2)
        ss_tot = np.sum((y_vals - y_mean) ** 2)
        r_squared = 1 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0
        residual_vol = float(np.sqrt(ss_res / (n - 2))) if n > 2 else 0.0
        return FactorExposure(
            beta=round(float(beta), 4),
            alpha=round(float(alpha), 4),
            r_squared=round(float(r_squared), 4),
            residual_vol=round(residual_vol, 6),
        )

    def _brinson(
        self,
        portfolio_returns: pd.Series,
        benchmark_returns: pd.Series,
        sector_map: dict[str, str] | None,
        symbols: pd.Index | None,
    ) -> tuple[float, float, float]:
        if symbols is None or sector_map is None or portfolio_returns.index.nlevels < 2:
            return 0.0, float(portfolio_returns.mean() * len(portfolio_returns)), 0.0

        p_weights = self._infer_weights(portfolio_returns)
        b_weights = self._infer_weights(benchmark_returns)
        all_symbols = set(p_weights.keys()) | set(b_weights.keys())

        sector_weights_p: dict[str, float] = {}
        sector_weights_b: dict[str, float] = {}
        sector_returns_p: dict[str, float] = {}
        sector_returns_b: dict[str, float] = {}

        for sym in all_symbols:
            sector = sector_map.get(sym, "OTHER")
            p_w = p_weights.get(sym, 0.0)
            b_w = b_weights.get(sym, 0.0)
            p_r = float(portfolio_returns.xs(sym, level=0).mean()) if sym in portfolio_returns.index.get_level_values(0) else 0.0
            b_r = float(benchmark_returns.xs(sym, level=0).mean()) if sym in benchmark_returns.index.get_level_values(0) else 0.0
            sector_weights_p[sector] = sector_weights_p.get(sector, 0.0) + p_w
            sector_weights_b[sector] = sector_weights_b.get(sector, 0.0) + b_w
            sector_returns_p[sector] = p_r
            sector_returns_b[sector] = b_r

        sector_alloc = 0.0
        stock_sel = 0.0
        interact = 0.0

        all_sectors = set(sector_weights_p.keys()) | set(sector_weights_b.keys())
        for sec in all_sectors:
            w_p = sector_weights_p.get(sec, 0.0)
            w_b = sector_weights_b.get(sec, 0.0)
            r_p = sector_returns_p.get(sec, 0.0)
            r_b = sector_returns_b.get(sec, 0.0)
            sector_alloc += (w_p - w_b) * r_b
            stock_sel += w_b * (r_p - r_b)
            interact += (w_p - w_b) * (r_p - r_b)

        return sector_alloc, stock_sel, interact

    def _infer_weights(self, returns: pd.Series) -> dict[str, float]:
        if returns.index.nlevels > 1:
            level_0 = returns.index.get_level_values(0)
            counts = level_0.value_counts()
            total = counts.sum()
            return {sym: count / total for sym, count in counts.items()}
        return {"portfolio": 1.0}

    def _max_drawdown(self, cumulative: pd.Series) -> float:
        peak = cumulative.cummax()
        drawdown = (cumulative - peak) / peak
        return float(drawdown.min())
