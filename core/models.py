from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# 枚举类型的规范定义位置：
#   SignalType  → core.strategies.SignalType
#   OrderSide   → core.orders.OrderSide
#   OrderStatus → core.orders.OrderStatus
#   MarketRegime (通用7态) → core.regime_detector.MarketRegime
#   MarketRegime (策略8态) → core.adaptive_strategy.MarketRegime


class SignalStrength(Enum):
    WEAK = 0.2
    MODERATE = 0.5
    STRONG = 0.8
    VERY_STRONG = 1.0


@dataclass(frozen=True)
class TradeSignal:
    signal_type: str
    strength: float = 0.0
    reason: str = ""

    @property
    def strength_category(self) -> SignalStrength:
        """Get strength category based on strength value"""
        if self.strength >= 0.8:
            return SignalStrength.VERY_STRONG
        elif self.strength >= 0.5:
            return SignalStrength.STRONG
        elif self.strength >= 0.2:
            return SignalStrength.MODERATE
        return SignalStrength.WEAK

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "signal_type": self.signal_type,
            "strength": self.strength,
            "reason": self.reason,
            "strength_category": self.strength_category.name.lower()
        }


@dataclass(frozen=True)
class KlineBar:
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float = 0.0

    @property
    def typical_price(self) -> float:
        return (self.high + self.low + self.close) / 3.0

    @property
    def range(self) -> float:
        return self.high - self.low

    @property
    def body(self) -> float:
        return abs(self.close - self.open)

    @property
    def is_bullish(self) -> bool:
        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        return self.close < self.open

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "date": self.date,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "amount": self.amount,
            "typical_price": self.typical_price,
            "range": self.range,
            "body": self.body,
            "is_bullish": self.is_bullish
        }


@dataclass(frozen=True)
class Position:
    symbol: str
    entry_price: float
    shares: int
    entry_date: str = ""
    stop_loss: float = 0.0
    take_profit: float = 0.0

    @property
    def cost(self) -> float:
        return self.entry_price * self.shares

    @property
    def risk_per_share(self) -> float:
        if self.stop_loss > 0:
            return self.entry_price - self.stop_loss
        return 0.0

    @property
    def has_stop_loss(self) -> bool:
        return self.stop_loss > 0

    @property
    def has_take_profit(self) -> bool:
        return self.take_profit > 0

    def calculate_pnl(self, current_price: float) -> float:
        """Calculate PnL based on current price"""
        return (current_price - self.entry_price) * self.shares

    def calculate_pnl_pct(self, current_price: float) -> float:
        """Calculate PnL percentage based on current price"""
        if self.entry_price <= 0:
            return 0.0
        return (current_price - self.entry_price) / self.entry_price * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "symbol": self.symbol,
            "entry_price": self.entry_price,
            "shares": self.shares,
            "entry_date": self.entry_date,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "cost": self.cost,
            "risk_per_share": self.risk_per_share,
            "has_stop_loss": self.has_stop_loss,
            "has_take_profit": self.has_take_profit
        }


@dataclass(frozen=True)
class PortfolioSnapshot:
    cash: float
    positions: dict[str, Position] = field(default_factory=dict)
    timestamp: float = 0.0

    @property
    def total_position_value(self) -> float:
        """持仓成本总额（非市值），因frozen dataclass无法存储实时价格"""
        return sum(p.entry_price * p.shares for p in self.positions.values())

    @property
    def total_value(self) -> float:
        return self.cash + self.total_position_value

    @property
    def position_count(self) -> int:
        return len(self.positions)

    @property
    def is_empty(self) -> bool:
        return self.cash <= 0 and self.position_count == 0

    def get_position(self, symbol: str) -> Position | None:
        """Get position by symbol"""
        return self.positions.get(symbol)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "cash": self.cash,
            "positions": {k: v.to_dict() for k, v in self.positions.items()},
            "timestamp": self.timestamp,
            "total_position_value": self.total_position_value,
            "total_value": self.total_value,
            "position_count": self.position_count
        }


@dataclass(frozen=True)
class BacktestMetrics:
    total_return: float = 0.0
    annual_return: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    avg_trade_return: float = 0.0
    calmar_ratio: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "total_return": self.total_return,
            "annual_return": self.annual_return,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "max_drawdown": self.max_drawdown,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "total_trades": self.total_trades,
            "avg_trade_return": self.avg_trade_return,
            "calmar_ratio": self.calmar_ratio
        }


@dataclass(frozen=True)
class PortfolioRiskMetrics:
    """组合风险指标（与risk_monitor.RiskMetrics互补）"""
    var_95: float = 0.0
    cvar_95: float = 0.0
    daily_volatility: float = 0.0
    annual_volatility: float = 0.0
    beta: float = 0.0
    concentration: dict[str, float] = field(default_factory=dict)
    max_concentration: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "var_95": self.var_95,
            "cvar_95": self.cvar_95,
            "daily_volatility": self.daily_volatility,
            "annual_volatility": self.annual_volatility,
            "beta": self.beta,
            "concentration": self.concentration,
            "max_concentration": self.max_concentration
        }


@dataclass(frozen=True)
class MarketDataPoint:
    symbol: str
    price: float
    change_pct: float = 0.0
    volume: float = 0.0
    amount: float = 0.0
    high: float = 0.0
    low: float = 0.0
    open: float = 0.0
    timestamp: float = 0.0
    market: str = ""

    @property
    def is_valid(self) -> bool:
        return self.price > 0 and self.symbol != ""

    @property
    def is_up(self) -> bool:
        return self.change_pct > 0

    @property
    def is_down(self) -> bool:
        return self.change_pct < 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "symbol": self.symbol,
            "price": self.price,
            "change_pct": self.change_pct,
            "volume": self.volume,
            "amount": self.amount,
            "high": self.high,
            "low": self.low,
            "open": self.open,
            "timestamp": self.timestamp,
            "market": self.market,
            "is_valid": self.is_valid,
            "is_up": self.is_up,
            "is_down": self.is_down
        }


@dataclass(frozen=True)
class StrategyPerformance:
    name: str
    total_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    total_trades: int = 0
    profit_factor: float = 0.0
    avg_pnl: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "name": self.name,
            "total_return": self.total_return,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "win_rate": self.win_rate,
            "total_trades": self.total_trades,
            "profit_factor": self.profit_factor,
            "avg_pnl": self.avg_pnl
        }


@dataclass(frozen=True)
class WalkForwardSplitResult:
    split_index: int
    train: BacktestMetrics = field(default_factory=BacktestMetrics)
    validation: BacktestMetrics = field(default_factory=BacktestMetrics)
    test: BacktestMetrics = field(default_factory=BacktestMetrics)
    overfitting_score: float = 0.0

    @property
    def has_overfitting(self) -> bool:
        """Check if there's significant overfitting"""
        return self.overfitting_score > 0.3

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "split_index": self.split_index,
            "train": self.train.to_dict(),
            "validation": self.validation.to_dict(),
            "test": self.test.to_dict(),
            "overfitting_score": self.overfitting_score,
            "has_overfitting": self.has_overfitting
        }


@dataclass(frozen=True)
class CorrelationResult:
    symbol_a: str
    symbol_b: str
    correlation: float
    is_significant: bool = False

    @property
    def is_highly_correlated(self) -> bool:
        return abs(self.correlation) > 0.7

    @property
    def is_positively_correlated(self) -> bool:
        return self.correlation > 0

    @property
    def is_negatively_correlated(self) -> bool:
        return self.correlation < 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "symbol_a": self.symbol_a,
            "symbol_b": self.symbol_b,
            "correlation": self.correlation,
            "is_significant": self.is_significant,
            "is_highly_correlated": self.is_highly_correlated,
            "is_positively_correlated": self.is_positively_correlated,
            "is_negatively_correlated": self.is_negatively_correlated
        }
