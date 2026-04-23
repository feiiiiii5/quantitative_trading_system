import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class StopLossType(Enum):
    FIXED_AMOUNT = "fixed_amount"
    PERCENTAGE = "percentage"
    ATR_TRAILING = "atr_trailing"
    TIME = "time"
    BREAKEVEN = "breakeven"


@dataclass
class StopLossOrder:
    symbol: str
    stop_loss_type: StopLossType
    trigger_price: float = 0.0
    current_stop: float = 0.0
    entry_price: float = 0.0
    entry_date: str = ""
    params: dict = field(default_factory=dict)
    is_active: bool = True
    triggered: bool = False

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "stop_loss_type": self.stop_loss_type.value,
            "trigger_price": round(self.trigger_price, 2),
            "current_stop": round(self.current_stop, 2),
            "entry_price": round(self.entry_price, 2),
            "entry_date": self.entry_date,
            "params": self.params,
            "is_active": self.is_active,
            "triggered": self.triggered,
        }


@dataclass
class TakeProfitOrder:
    symbol: str
    take_profit_price: float = 0.0
    entry_price: float = 0.0
    is_active: bool = True
    triggered: bool = False

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "take_profit_price": round(self.take_profit_price, 2),
            "entry_price": round(self.entry_price, 2),
            "is_active": self.is_active,
            "triggered": self.triggered,
        }


@dataclass
class CircuitBreaker:
    max_portfolio_drawdown: float = 0.15
    max_daily_loss: float = 0.05
    max_consecutive_losses: int = 5
    is_triggered: bool = False
    triggered_reason: str = ""
    triggered_time: str = ""

    def to_dict(self) -> dict:
        return {
            "max_portfolio_drawdown": self.max_portfolio_drawdown,
            "max_daily_loss": self.max_daily_loss,
            "max_consecutive_losses": self.max_consecutive_losses,
            "is_triggered": self.is_triggered,
            "triggered_reason": self.triggered_reason,
            "triggered_time": self.triggered_time,
        }


class MultiDimensionStopLoss:
    def __init__(
        self,
        default_stop_pct: float = 0.05,
        atr_period: int = 14,
        atr_multiplier: float = 2.0,
        max_hold_days: int = 30,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ):
        self.default_stop_pct = default_stop_pct
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier
        self.max_hold_days = max_hold_days
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self._stop_orders: Dict[str, StopLossOrder] = {}
        self._tp_orders: Dict[str, TakeProfitOrder] = {}
        self._consecutive_losses = 0
        self._peak_equity = 0.0
        self._daily_start_equity = 0.0

    def set_stop_loss(
        self,
        symbol: str,
        entry_price: float,
        entry_date: str,
        stop_type: StopLossType = StopLossType.PERCENTAGE,
        params: Optional[dict] = None,
    ) -> StopLossOrder:
        params = params or {}

        if stop_type == StopLossType.FIXED_AMOUNT:
            amount = params.get("amount", entry_price * self.default_stop_pct)
            stop_price = entry_price - amount

        elif stop_type == StopLossType.PERCENTAGE:
            pct = params.get("percentage", self.default_stop_pct)
            stop_price = entry_price * (1 - pct)

        elif stop_type == StopLossType.ATR_TRAILING:
            atr = params.get("atr", entry_price * 0.02)
            stop_price = entry_price - atr * self.atr_multiplier

        elif stop_type == StopLossType.TIME:
            stop_price = entry_price * (1 - self.default_stop_pct)

        elif stop_type == StopLossType.BREAKEVEN:
            stop_price = entry_price

        else:
            stop_price = entry_price * (1 - self.default_stop_pct)

        order = StopLossOrder(
            symbol=symbol,
            stop_loss_type=stop_type,
            trigger_price=stop_price,
            current_stop=stop_price,
            entry_price=entry_price,
            entry_date=entry_date,
            params=params,
        )
        self._stop_orders[symbol] = order
        return order

    def set_take_profit(
        self,
        symbol: str,
        entry_price: float,
        take_profit_pct: float = 0.10,
    ) -> TakeProfitOrder:
        tp_price = entry_price * (1 + take_profit_pct)
        order = TakeProfitOrder(
            symbol=symbol,
            take_profit_price=tp_price,
            entry_price=entry_price,
        )
        self._tp_orders[symbol] = order
        return order

    def check_stop_loss(self, symbol: str, current_price: float, current_date: str = "") -> Optional[dict]:
        order = self._stop_orders.get(symbol)
        if not order or not order.is_active:
            return None

        if order.stop_loss_type == StopLossType.ATR_TRAILING:
            self._update_trailing_stop(order, current_price)

        if order.stop_loss_type == StopLossType.TIME:
            if self._check_time_stop(order, current_date):
                order.triggered = True
                order.is_active = False
                return {
                    "symbol": symbol,
                    "action": "sell",
                    "reason": f"时间止损: 持仓超过{self.max_hold_days}天",
                    "price": current_price,
                    "stop_type": "time",
                }

        if current_price <= order.current_stop:
            order.triggered = True
            order.is_active = False
            loss_pct = (current_price - order.entry_price) / order.entry_price * 100
            return {
                "symbol": symbol,
                "action": "sell",
                "reason": f"止损触发: {order.stop_loss_type.value}, 亏损{loss_pct:.2f}%",
                "price": current_price,
                "stop_type": order.stop_loss_type.value,
            }

        return None

    def check_take_profit(self, symbol: str, current_price: float) -> Optional[dict]:
        order = self._tp_orders.get(symbol)
        if not order or not order.is_active:
            return None

        if current_price >= order.take_profit_price:
            order.triggered = True
            order.is_active = False
            profit_pct = (current_price - order.entry_price) / order.entry_price * 100
            return {
                "symbol": symbol,
                "action": "sell",
                "reason": f"止盈触发: 盈利{profit_pct:.2f}%",
                "price": current_price,
                "stop_type": "take_profit",
            }

        return None

    def check_circuit_breaker(
        self,
        current_equity: float,
        trade_pnl: float = 0.0,
    ) -> Optional[dict]:
        if self._peak_equity == 0 or self._daily_start_equity == 0:
            self._peak_equity = current_equity
            self._daily_start_equity = current_equity

        self._peak_equity = max(self._peak_equity, current_equity)

        drawdown = (self._peak_equity - current_equity) / self._peak_equity
        if drawdown >= self.circuit_breaker.max_portfolio_drawdown:
            self.circuit_breaker.is_triggered = True
            self.circuit_breaker.triggered_reason = f"组合最大回撤{drawdown:.2%}触发熔断"
            self.circuit_breaker.triggered_time = time.strftime("%Y-%m-%d %H:%M:%S")
            return {
                "action": "halt_all",
                "reason": self.circuit_breaker.triggered_reason,
                "drawdown": round(drawdown, 4),
            }

        daily_loss = (current_equity - self._daily_start_equity) / self._daily_start_equity
        if daily_loss < -self.circuit_breaker.max_daily_loss:
            self.circuit_breaker.is_triggered = True
            self.circuit_breaker.triggered_reason = f"单日亏损{daily_loss:.2%}触发熔断"
            self.circuit_breaker.triggered_time = time.strftime("%Y-%m-%d %H:%M:%S")
            return {
                "action": "halt_all",
                "reason": self.circuit_breaker.triggered_reason,
                "daily_loss": round(daily_loss, 4),
            }

        if trade_pnl < 0:
            self._consecutive_losses += 1
        elif trade_pnl > 0:
            self._consecutive_losses = 0

        if self._consecutive_losses >= self.circuit_breaker.max_consecutive_losses:
            self.circuit_breaker.is_triggered = True
            self.circuit_breaker.triggered_reason = f"连续{self._consecutive_losses}次亏损触发熔断"
            self.circuit_breaker.triggered_time = time.strftime("%Y-%m-%d %H:%M:%S")
            return {
                "action": "halt_all",
                "reason": self.circuit_breaker.triggered_reason,
                "consecutive_losses": self._consecutive_losses,
            }

        return None

    def _update_trailing_stop(self, order: StopLossOrder, current_price: float):
        if current_price > order.entry_price:
            atr = order.params.get("atr", order.entry_price * 0.02)
            new_stop = current_price - atr * self.atr_multiplier
            if new_stop > order.current_stop:
                order.current_stop = new_stop

    def _check_time_stop(self, order: StopLossOrder, current_date: str) -> bool:
        if not order.entry_date or not current_date:
            return False
        try:
            from datetime import datetime
            entry = datetime.strptime(order.entry_date, "%Y-%m-%d")
            current = datetime.strptime(current_date, "%Y-%m-%d")
            hold_days = (current - entry).days
            return hold_days >= self.max_hold_days
        except (ValueError, TypeError):
            return False

    def remove_order(self, symbol: str):
        self._stop_orders.pop(symbol, None)
        self._tp_orders.pop(symbol, None)

    def get_active_orders(self) -> Dict[str, dict]:
        result = {}
        for sym, order in self._stop_orders.items():
            if order.is_active:
                result[f"sl:{sym}"] = order.to_dict()
        for sym, order in self._tp_orders.items():
            if order.is_active:
                result[f"tp:{sym}"] = order.to_dict()
        return result

    def reset_daily(self):
        self._daily_start_equity = 0.0
        self.circuit_breaker.is_triggered = False
        self.circuit_breaker.triggered_reason = ""
