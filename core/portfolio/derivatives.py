import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class FuturesPosition:
    symbol: str
    contract: str
    quantity: int
    entry_price: float
    current_price: float = 0.0
    multiplier: float = 1.0
    margin_rate: float = 0.1
    roll_date: str = ""
    days_to_expiry: int = 0

    def to_dict(self) -> dict:
        pnl = (self.current_price - self.entry_price) * self.quantity * self.multiplier
        return {
            "symbol": self.symbol, "contract": self.contract,
            "quantity": self.quantity, "entry_price": self.entry_price,
            "current_price": self.current_price, "multiplier": self.multiplier,
            "margin_rate": self.margin_rate, "roll_date": self.roll_date,
            "days_to_expiry": self.days_to_expiry,
            "unrealized_pnl": round(pnl, 2),
            "margin_required": round(self.entry_price * abs(self.quantity) * self.multiplier * self.margin_rate, 2),
        }


@dataclass
class OptionPosition:
    symbol: str
    option_type: str
    strike: float
    expiry: str
    quantity: int
    entry_price: float
    current_price: float = 0.0
    underlying_price: float = 0.0
    implied_vol: float = 0.3
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol, "option_type": self.option_type,
            "strike": self.strike, "expiry": self.expiry,
            "quantity": self.quantity, "entry_price": self.entry_price,
            "current_price": self.current_price,
            "underlying_price": self.underlying_price,
            "implied_vol": round(self.implied_vol, 4),
            "delta": round(self.delta, 4), "gamma": round(self.gamma, 6),
            "theta": round(self.theta, 4), "vega": round(self.vega, 4),
        }


class DerivativesManager:
    def __init__(self):
        self._futures: Dict[str, FuturesPosition] = {}
        self._options: Dict[str, OptionPosition] = {}
        self._roll_threshold_days = 5

    def add_future(self, position: FuturesPosition):
        self._futures[position.symbol] = position

    def add_option(self, position: OptionPosition):
        self._options[position.symbol] = position

    def add_futures_position(self, symbol: str, quantity: int, entry_price: float,
                             contract_month: str = "", multiplier: float = 1.0,
                             margin_rate: float = 0.1) -> dict:
        pos = FuturesPosition(
            symbol=symbol, contract=contract_month, quantity=quantity,
            entry_price=entry_price, current_price=entry_price,
            multiplier=multiplier, margin_rate=margin_rate,
        )
        self.add_future(pos)
        return pos.to_dict()

    def add_option_position(self, symbol: str, quantity: int, entry_price: float,
                            option_type: str = "call", strike: float = 0.0,
                            expiry: str = "", underlying: str = "",
                            delta: float = 0.0, gamma: float = 0.0,
                            theta: float = 0.0, vega: float = 0.0) -> dict:
        pos = OptionPosition(
            symbol=symbol, option_type=option_type, strike=strike,
            expiry=expiry, quantity=quantity, entry_price=entry_price,
            underlying_price=0.0, delta=delta, gamma=gamma,
            theta=theta, vega=vega,
        )
        self.add_option(pos)
        return pos.to_dict()

    def check_roll_dates(self) -> List[dict]:
        return self.check_roll_reminders()

    def get_greeks_summary(self) -> dict:
        return self.calculate_option_greeks_summary()

    def remove_future(self, symbol: str):
        self._futures.pop(symbol, None)

    def remove_option(self, symbol: str):
        self._options.pop(symbol, None)

    def check_roll_reminders(self) -> List[dict]:
        reminders = []
        for symbol, pos in self._futures.items():
            if pos.days_to_expiry <= self._roll_threshold_days and pos.days_to_expiry >= 0:
                reminders.append({
                    "symbol": symbol, "contract": pos.contract,
                    "days_to_expiry": pos.days_to_expiry,
                    "action": "需要展期",
                    "urgency": "high" if pos.days_to_expiry <= 2 else "medium",
                })
        return reminders

    def auto_roll(self, symbol: str, new_contract: str, new_price: float) -> Optional[dict]:
        pos = self._futures.get(symbol)
        if not pos:
            return None

        old_pnl = (pos.current_price - pos.entry_price) * pos.quantity * pos.multiplier

        rolled = FuturesPosition(
            symbol=symbol, contract=new_contract,
            quantity=pos.quantity, entry_price=new_price,
            current_price=new_price, multiplier=pos.multiplier,
            margin_rate=pos.margin_rate,
        )
        self._futures[symbol] = rolled

        return {
            "symbol": symbol,
            "old_contract": pos.contract, "new_contract": new_contract,
            "old_price": pos.current_price, "new_price": new_price,
            "realized_pnl": round(old_pnl, 2),
            "rolled_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

    def calculate_option_greeks_summary(self) -> dict:
        total_delta = 0.0
        total_gamma = 0.0
        total_theta = 0.0
        total_vega = 0.0

        for pos in self._options.values():
            qty_signed = pos.quantity if pos.option_type == "call" else -pos.quantity
            total_delta += pos.delta * qty_signed
            total_gamma += pos.gamma * abs(pos.quantity)
            total_theta += pos.theta * qty_signed
            total_vega += pos.vega * abs(pos.quantity)

        return {
            "total_delta": round(total_delta, 4),
            "total_gamma": round(total_gamma, 6),
            "total_theta": round(total_theta, 4),
            "total_vega": round(total_vega, 4),
            "option_count": len(self._options),
        }

    def calculate_hedge_ratio(self, target_delta: float = 0.0) -> dict:
        current_delta = sum(
            pos.delta * (pos.quantity if pos.option_type == "call" else -pos.quantity)
            for pos in self._options.values()
        )

        if not self._options:
            return {"current_delta": 0, "target_delta": target_delta, "hedge_needed": 0}

        first_option = next(iter(self._options.values()))
        underlying_price = first_option.underlying_price
        if underlying_price <= 0:
            return {"current_delta": round(current_delta, 4), "target_delta": target_delta, "hedge_needed": 0}

        delta_diff = target_delta - current_delta
        shares_needed = int(delta_diff * 100)

        return {
            "current_delta": round(current_delta, 4),
            "target_delta": target_delta,
            "delta_diff": round(delta_diff, 4),
            "shares_needed": shares_needed,
            "underlying_price": underlying_price,
            "hedge_value": round(abs(shares_needed) * underlying_price, 2),
        }

    def get_all_positions(self) -> dict:
        return {
            "futures": {k: v.to_dict() for k, v in self._futures.items()},
            "options": {k: v.to_dict() for k, v in self._options.items()},
            "greeks_summary": self.calculate_option_greeks_summary(),
            "roll_reminders": self.check_roll_reminders(),
        }
