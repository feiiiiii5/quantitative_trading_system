import logging
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional

import numpy as np
import pandas as pd

from core.strategies import BaseStrategy

logger = logging.getLogger(__name__)


class EventType(Enum):
    BAR = "bar"
    TICK = "tick"
    ORDERBOOK = "orderbook"
    SIGNAL = "signal"
    ORDER = "order"
    FILL = "fill"
    TIMER = "timer"


@dataclass
class Event:
    type: EventType
    data: dict
    timestamp: float = 0.0


@dataclass
class Order:
    symbol: str
    direction: str
    quantity: int
    price: float = 0.0
    order_type: str = "market"
    timestamp: float = 0.0
    filled_price: float = 0.0
    filled_quantity: int = 0
    status: str = "pending"
    commission: float = 0.0
    slippage: float = 0.0

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol, "direction": self.direction,
            "quantity": self.quantity, "price": self.price,
            "order_type": self.order_type, "filled_price": self.filled_price,
            "filled_quantity": self.filled_quantity, "status": self.status,
            "commission": self.commission, "slippage": self.slippage,
        }


@dataclass
class Position:
    symbol: str
    quantity: int = 0
    avg_price: float = 0.0
    entry_date: str = ""
    unrealized_pnl: float = 0.0

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol, "quantity": self.quantity,
            "avg_price": self.avg_price, "entry_date": self.entry_date,
            "unrealized_pnl": round(self.unrealized_pnl, 2),
        }


@dataclass
class BacktestAccount:
    initial_capital: float = 100000.0
    cash: float = 100000.0
    positions: Dict[str, Position] = field(default_factory=dict)
    equity_curve: List[float] = field(default_factory=list)
    trades: List[dict] = field(default_factory=list)
    commission_rate: float = 0.0003
    slippage_rate: float = 0.001

    @property
    def total_equity(self) -> float:
        pos_value = sum(p.quantity * p.avg_price for p in self.positions.values())
        return self.cash + pos_value

    def to_dict(self) -> dict:
        return {
            "cash": round(self.cash, 2),
            "total_equity": round(self.total_equity, 2),
            "positions": {s: p.to_dict() for s, p in self.positions.items()},
            "trade_count": len(self.trades),
        }


class EventBacktestEngine:
    def __init__(
        self,
        initial_capital: float = 100000.0,
        commission_rate: float = 0.0003,
        slippage_rate: float = 0.001,
        risk_free_rate: float = 0.03,
    ):
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
        self.risk_free_rate = risk_free_rate
        self._event_queue: deque = deque()
        self._handlers: Dict[EventType, List[Callable]] = {}
        self._account: Optional[BacktestAccount] = None
        self._strategy: Optional[BaseStrategy] = None
        self._bar_data: List[dict] = []
        self._current_prices: Dict[str, float] = {}

    def register_handler(self, event_type: EventType, handler: Callable):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def _emit(self, event: Event):
        handlers = self._handlers.get(event.type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.debug(f"Handler error: {e}")

    def _on_bar(self, event: Event):
        data = event.data
        symbol = data.get("symbol", "")
        price = data.get("close", 0)
        self._current_prices[symbol] = price

        for sym, pos in self._account.positions.items():
            if sym in self._current_prices:
                pos.unrealized_pnl = (self._current_prices[sym] - pos.avg_price) * pos.quantity

        self._account.equity_curve.append(self._account.total_equity)

    def _on_signal(self, event: Event):
        data = event.data
        symbol = data.get("symbol", "")
        signal_type = data.get("signal_type", "hold")

        if signal_type == "buy" and symbol not in self._account.positions:
            price = self._current_prices.get(symbol, 0)
            if price <= 0:
                return
            max_invest = self._account.cash * 0.3
            fill_price = price * (1 + self.slippage_rate)
            shares = int(max_invest / fill_price / 100) * 100
            if shares <= 0:
                shares = int(max_invest / fill_price)
            if shares <= 0:
                return
            cost = shares * fill_price * (1 + self.commission_rate)
            if cost > self._account.cash:
                return
            self._account.cash -= cost
            self._account.positions[symbol] = Position(
                symbol=symbol, quantity=shares, avg_price=fill_price,
                entry_date=data.get("date", ""),
            )
            self._emit(Event(EventType.FILL, {
                "symbol": symbol, "direction": "buy",
                "quantity": shares, "price": fill_price,
                "commission": shares * fill_price * self.commission_rate,
            }))

        elif signal_type == "sell" and symbol in self._account.positions:
            pos = self._account.positions[symbol]
            price = self._current_prices.get(symbol, 0)
            if price <= 0:
                return
            fill_price = price * (1 - self.slippage_rate)
            revenue = pos.quantity * fill_price * (1 - self.commission_rate)
            pnl = (fill_price - pos.avg_price) * pos.quantity
            pnl_pct = (fill_price / pos.avg_price - 1) * 100 if pos.avg_price > 0 else 0

            self._account.cash += revenue
            self._account.trades.append({
                "symbol": symbol, "direction": "long",
                "entry_price": pos.avg_price, "exit_price": fill_price,
                "shares": pos.quantity, "pnl": round(pnl, 2),
                "pnl_pct": round(pnl_pct, 2),
                "entry_date": pos.entry_date,
                "exit_date": data.get("date", ""),
            })
            del self._account.positions[symbol]
            self._emit(Event(EventType.FILL, {
                "symbol": symbol, "direction": "sell",
                "quantity": pos.quantity, "price": fill_price,
                "commission": pos.quantity * fill_price * self.commission_rate,
            }))

    def run(self, strategy: BaseStrategy, df: pd.DataFrame, symbol: str = "") -> dict:
        self._account = BacktestAccount(
            initial_capital=self.initial_capital,
            commission_rate=self.commission_rate,
            slippage_rate=self.slippage_rate,
        )
        self._strategy = strategy
        self._current_prices = {}

        self.register_handler(EventType.BAR, self._on_bar)
        self.register_handler(EventType.SIGNAL, self._on_signal)

        if df is None or len(df) < 30:
            return self._empty_result(symbol)

        c = df["close"].values.astype(float)
        h = df["high"].values.astype(float)
        low_arr = df["low"].values.astype(float)
        dates = df["date"].values if "date" in df.columns else np.arange(len(df))
        date_strs = [str(pd.Timestamp(d).date()) if not isinstance(d, str) else d for d in dates]

        strategy_result = strategy.generate_signals(df)

        signal_map: Dict[int, dict] = {}
        for sig in strategy_result.signals:
            best_idx = -1
            best_diff = float("inf")
            for i in range(len(c)):
                diff = abs(c[i] - sig.price)
                if diff < best_diff:
                    best_diff = diff
                    best_idx = i
            if best_idx >= 0 and best_diff < c[best_idx] * 0.02:
                if best_idx not in signal_map or sig.strength > signal_map[best_idx].get("strength", 0):
                    signal_map[best_idx] = {
                        "symbol": symbol, "signal_type": sig.signal_type.value,
                        "strength": sig.strength, "price": sig.price,
                        "stop_loss": sig.stop_loss, "take_profit": sig.take_profit,
                    }

        for i in range(len(c)):
            bar_event = Event(EventType.BAR, {
                "symbol": symbol, "close": c[i], "high": h[i], "low": low_arr[i],
                "open": df["open"].values[i] if "open" in df.columns else c[i],
                "date": date_strs[i] if i < len(date_strs) else "",
            })
            self._emit(bar_event)

            if i in signal_map:
                sig_data = signal_map[i]
                sig_data["date"] = date_strs[i] if i < len(date_strs) else ""
                self._emit(Event(EventType.SIGNAL, sig_data))

        if self._account.positions:
            for sym, pos in list(self._account.positions.items()):
                price = self._current_prices.get(sym, c[-1])
                fill_price = price * (1 - self.slippage_rate)
                revenue = pos.quantity * fill_price * (1 - self.commission_rate)
                pnl = (fill_price - pos.avg_price) * pos.quantity
                pnl_pct = (fill_price / pos.avg_price - 1) * 100 if pos.avg_price > 0 else 0
                self._account.cash += revenue
                self._account.trades.append({
                    "symbol": sym, "direction": "long",
                    "entry_price": pos.avg_price, "exit_price": fill_price,
                    "shares": pos.quantity, "pnl": round(pnl, 2),
                    "pnl_pct": round(pnl_pct, 2),
                    "entry_date": pos.entry_date, "exit_date": date_strs[-1],
                    "exit_reason": "end_of_data",
                })
                del self._account.positions[sym]

        return self._calculate_result(symbol, c)

    def _calculate_result(self, symbol: str, prices: np.ndarray) -> dict:
        eq = self._account.equity_curve
        trades = self._account.trades

        if not eq:
            return {"symbol": symbol, "total_return": 0, "sharpe_ratio": 0}

        total_return = (eq[-1] / self.initial_capital - 1) * 100
        n_days = len(eq)
        annual_return = ((eq[-1] / self.initial_capital) ** (252 / max(n_days, 1)) - 1) * 100

        daily_returns = np.diff(eq) / np.maximum(eq[:-1], 1)
        daily_returns = daily_returns[np.isfinite(daily_returns)]

        sharpe = 0.0
        if len(daily_returns) > 10 and np.std(daily_returns) > 0:
            sharpe = (np.mean(daily_returns) - self.risk_free_rate / 252) / np.std(daily_returns) * np.sqrt(252)

        peak = eq[0]
        max_dd = 0.0
        for e in eq:
            peak = max(peak, e)
            dd = (peak - e) / peak * 100 if peak > 0 else 0
            max_dd = max(max_dd, dd)

        win_trades = [t for t in trades if t.get("pnl", 0) > 0]
        loss_trades = [t for t in trades if t.get("pnl", 0) <= 0]
        total_profit = sum(t.get("pnl_pct", 0) for t in win_trades)
        total_loss = abs(sum(t.get("pnl_pct", 0) for t in loss_trades)) if loss_trades else 1

        benchmark_return = (prices[-1] / prices[0] - 1) * 100 if len(prices) > 1 else 0
        alpha = annual_return - benchmark_return

        return {
            "symbol": symbol,
            "total_return": round(total_return, 2),
            "annual_return": round(annual_return, 2),
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown": round(max_dd, 2),
            "win_rate": round(len(win_trades) / len(trades) * 100, 2) if trades else 0,
            "profit_factor": round(total_profit / total_loss, 2) if total_loss > 0 else 0,
            "total_trades": len(trades),
            "win_trades": len(win_trades),
            "loss_trades": len(loss_trades),
            "avg_profit": round(np.mean([t["pnl_pct"] for t in win_trades]), 2) if win_trades else 0,
            "avg_loss": round(np.mean([t["pnl_pct"] for t in loss_trades]), 2) if loss_trades else 0,
            "benchmark_return": round(benchmark_return, 2),
            "alpha": round(alpha, 2),
            "equity_curve": [round(e, 2) for e in eq[-200:]],
            "trades": trades[-50:],
        }

    def _empty_result(self, symbol: str) -> dict:
        return {
            "symbol": symbol, "total_return": 0, "annual_return": 0,
            "sharpe_ratio": 0, "max_drawdown": 0, "win_rate": 0,
            "profit_factor": 0, "total_trades": 0, "win_trades": 0,
            "loss_trades": 0, "avg_profit": 0, "avg_loss": 0,
            "benchmark_return": 0, "alpha": 0, "equity_curve": [], "trades": [],
        }
