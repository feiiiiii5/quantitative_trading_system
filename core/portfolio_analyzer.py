__all__ = ["RebalanceFrequency", "PortfolioBacktestResult", "PortfolioBacktester"]

"""
QuantCore Portfolio Backtest Analyzer
Analyzes multi-asset portfolio backtest results
"""
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class RebalanceFrequency(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


@dataclass
class PortfolioBacktestResult:
    initial_capital: float
    final_capital: float
    total_return: float
    annualized_return: float
    annualized_volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    max_drawdown_duration: int
    win_rate: float
    total_trades: int
    turnover: float
    equity_curve: pd.Series = field(repr=False)
    drawdown_curve: pd.Series = field(repr=False)
    monthly_returns: pd.Series = field(repr=False)
    rebalance_dates: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "initial_capital": self.initial_capital,
            "final_capital": self.final_capital,
            "total_return": round(self.total_return, 4),
            "annualized_return": round(self.annualized_return, 4),
            "annualized_volatility": round(self.annualized_volatility, 4),
            "sharpe_ratio": round(self.sharpe_ratio, 4),
            "sortino_ratio": round(self.sortino_ratio, 4),
            "max_drawdown": round(self.max_drawdown, 4),
            "max_drawdown_duration": self.max_drawdown_duration,
            "win_rate": round(self.win_rate, 4),
            "total_trades": self.total_trades,
            "turnover": round(self.turnover, 4),
            "equity_curve": self.equity_curve.to_dict(),
            "drawdown_curve": self.drawdown_curve.to_dict(),
            "monthly_returns": self.monthly_returns.to_dict(),
            "rebalance_dates": self.rebalance_dates,
        }


class PortfolioBacktester:

    def __init__(
        self,
        initial_capital: float = 100000.0,
        rebalance_frequency: RebalanceFrequency = RebalanceFrequency.MONTHLY,
        commission_rate: float = 0.0003,
        slippage_rate: float = 0.001,
        risk_free_rate: float = 0.03,
    ):
        self.initial_capital = initial_capital
        self.rebalance_frequency = rebalance_frequency
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
        self.risk_free_rate = risk_free_rate

        self._price_data: pd.DataFrame | None = None
        self._weights: dict[str, float] | None = None
        self._rebalance_dates: list[pd.Timestamp] = []

    def load_price_data(self, price_data: pd.DataFrame) -> "PortfolioBacktester":
        self._price_data = price_data.copy()
        return self

    def set_static_weights(self, weights: dict[str, float]) -> "PortfolioBacktester":
        total_weight = sum(weights.values())
        if abs(total_weight - 1.0) > 1e-6:
            logger.warning("Weight sum is %s, normalizing to 1.0", total_weight)
            self._weights = {s: w / total_weight for s, w in weights.items()}
        else:
            self._weights = weights.copy()
        return self

    def _get_rebalance_dates(self) -> list[pd.Timestamp]:
        if self._price_data is None or len(self._price_data) == 0:
            return []

        dates = self._price_data.index
        rebalance_dates: list[pd.Timestamp] = []

        if self.rebalance_frequency == RebalanceFrequency.DAILY:
            rebalance_dates = list(dates)
        elif self.rebalance_frequency == RebalanceFrequency.WEEKLY:
            for idx, date in enumerate(dates):
                if idx == 0 or date.weekday() == 0:
                    rebalance_dates.append(date)
        elif self.rebalance_frequency == RebalanceFrequency.MONTHLY:
            prev_month = None
            for date in dates:
                month = (date.year, date.month)
                if prev_month is None or month != prev_month:
                    rebalance_dates.append(date)
                    prev_month = month
        elif self.rebalance_frequency == RebalanceFrequency.QUARTERLY:
            prev_quarter = None
            for date in dates:
                quarter = (date.year, (date.month - 1) // 3)
                if prev_quarter is None or quarter != prev_quarter:
                    rebalance_dates.append(date)
                    prev_quarter = quarter
        elif self.rebalance_frequency == RebalanceFrequency.YEARLY:
            prev_year = None
            for date in dates:
                if prev_year is None or date.year != prev_year:
                    rebalance_dates.append(date)
                    prev_year = date.year

        if len(rebalance_dates) == 0 or rebalance_dates[0] != dates[0]:
            rebalance_dates.insert(0, dates[0])
        if rebalance_dates[-1] != dates[-1]:
            rebalance_dates.append(dates[-1])

        self._rebalance_dates = rebalance_dates
        return rebalance_dates

    def run_backtest(self) -> PortfolioBacktestResult:
        if self._price_data is None:
            raise ValueError("No price data loaded. Call load_price_data first.")

        if self._weights is None:
            raise ValueError("No weights set. Call set_static_weights first.")

        available_symbols = set(self._price_data.columns)
        required_symbols = set(self._weights.keys())
        if not required_symbols.issubset(available_symbols):
            missing = required_symbols - available_symbols
            raise ValueError(f"Missing price data for symbols: {missing}")

        rebalance_dates = self._get_rebalance_dates()
        rebalance_set = set(rebalance_dates)

        symbols = list(self._weights.keys())
        prices = self._price_data[symbols].copy()

        current_capital = self.initial_capital
        positions: dict[str, float] = dict.fromkeys(symbols, 0.0)
        equity_curve = pd.Series(index=prices.index, dtype=float)
        trades_count = 0
        total_turnover = 0.0

        prev_weights = dict.fromkeys(symbols, 0.0)
        rebalance_dates_list: list[str] = []

        for date in prices.index:
            if date in rebalance_set:
                rebalance_dates_list.append(date.strftime("%Y-%m-%d"))

                current_prices = prices.loc[date]
                target_weights = self._weights

                portfolio_value = current_capital
                for s in symbols:
                    portfolio_value += abs(positions[s]) * current_prices[s]

                target_positions: dict[str, float] = {}
                for s in symbols:
                    target_value = portfolio_value * target_weights[s]
                    target_positions[s] = target_value / current_prices[s] if current_prices[s] > 0 else 0.0

                trade_cost = 0.0
                for s in symbols:
                    shares_change = target_positions[s] - positions[s]
                    if abs(shares_change) > 0.01:
                        slippage = abs(shares_change * current_prices[s] * self.slippage_rate)
                        commission = abs(shares_change * current_prices[s] * self.commission_rate)
                        trade_cost += slippage + commission
                        trades_count += 1

                turnover = sum(
                    abs(target_weights[s] - prev_weights[s]) for s in symbols
                )
                total_turnover += turnover / 2
                prev_weights = dict(target_weights)

                current_capital -= trade_cost
                positions = target_positions

            current_prices = prices.loc[date]
            position_value = sum(positions[s] * current_prices[s] for s in symbols)
            total_value = current_capital + position_value
            equity_curve.loc[date] = total_value

        return self._calculate_metrics(
            equity_curve=equity_curve,
            total_trades=trades_count,
            turnover=total_turnover / max(len(rebalance_dates_list), 1),
            rebalance_dates=rebalance_dates_list,
        )

    def _calculate_metrics(
        self,
        equity_curve: pd.Series,
        total_trades: int,
        turnover: float,
        rebalance_dates: list[str],
    ) -> PortfolioBacktestResult:
        returns = equity_curve.pct_change().dropna()
        if len(returns) == 0:
            return PortfolioBacktestResult(
                initial_capital=self.initial_capital,
                final_capital=self.initial_capital,
                total_return=0.0, annualized_return=0.0,
                annualized_volatility=0.0, sharpe_ratio=0.0,
                sortino_ratio=0.0, max_drawdown=0.0,
                max_drawdown_duration=0, win_rate=0.0,
                total_trades=total_trades, turnover=turnover,
                equity_curve=equity_curve,
                drawdown_curve=pd.Series(0.0, index=equity_curve.index),
                monthly_returns=pd.Series(dtype=float),
                rebalance_dates=rebalance_dates,
            )

        total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1

        if isinstance(equity_curve.index, pd.DatetimeIndex):
            days = (equity_curve.index[-1] - equity_curve.index[0]).days
        else:
            days = len(equity_curve) - 1
        years = max(days / 365.25, 1e-6)
        annualized_return = (1 + total_return) ** (1 / years) - 1

        annualized_volatility = returns.std() * np.sqrt(252)

        excess_return = annualized_return - self.risk_free_rate
        sharpe_ratio = excess_return / annualized_volatility if annualized_volatility > 0 else 0.0

        downside_returns = returns[returns < 0]
        downside_risk = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0.0
        sortino_ratio = excess_return / downside_risk if downside_risk > 0 else 0.0

        cummax = equity_curve.cummax()
        drawdown = equity_curve.copy()
        nonzero_mask = cummax > 0
        drawdown[nonzero_mask] = (equity_curve[nonzero_mask] - cummax[nonzero_mask]) / cummax[nonzero_mask]
        drawdown[~nonzero_mask] = 0.0
        max_drawdown = float(drawdown.min())

        drawdown_duration = 0
        current_duration = 0
        for d in drawdown:
            if d < 0:
                current_duration += 1
            else:
                drawdown_duration = max(drawdown_duration, current_duration)
                current_duration = 0
        max_drawdown_duration = max(drawdown_duration, current_duration)

        win_rate = float((returns > 0).sum() / len(returns))

        monthly_returns = equity_curve.resample('ME').last().pct_change().dropna()

        return PortfolioBacktestResult(
            initial_capital=self.initial_capital,
            final_capital=float(equity_curve.iloc[-1]),
            total_return=total_return,
            annualized_return=annualized_return,
            annualized_volatility=float(annualized_volatility),
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown=max_drawdown,
            max_drawdown_duration=max_drawdown_duration,
            win_rate=win_rate,
            total_trades=total_trades,
            turnover=turnover,
            equity_curve=equity_curve,
            drawdown_curve=drawdown,
            monthly_returns=monthly_returns,
            rebalance_dates=rebalance_dates,
        )
