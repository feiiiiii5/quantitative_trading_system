import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from core.strategies import CompositeStrategy, SignalType

logger = logging.getLogger(__name__)

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
_POSITIONS_FILE = os.path.join(_DATA_DIR, "positions.json")
_TRADES_FILE = os.path.join(_DATA_DIR, "trades.json")
_ACCOUNT_FILE = os.path.join(_DATA_DIR, "account.json")


@dataclass
class Position:
    symbol: str
    name: str
    market: str
    shares: int
    entry_price: float
    entry_date: str
    stop_loss: float = 0.0
    take_profit: float = 0.0
    strategy: str = ""


@dataclass
class SimTrade:
    symbol: str
    name: str
    market: str
    direction: str
    shares: int
    entry_price: float
    exit_price: float
    entry_date: str
    exit_date: str
    pnl: float
    pnl_pct: float
    commission: float
    slippage: float
    strategy: str
    exit_reason: str


@dataclass
class SimAccount:
    initial_capital: float = 1000000.0
    cash: float = 1000000.0
    created_at: str = ""
    updated_at: str = ""


class SimulatedTrading:
    def __init__(self):
        self.composite = CompositeStrategy()
        self.commission_rate = 0.0003
        self.slippage_rate = 0.001
        self.max_position_pct = 0.3
        self.max_daily_loss_pct = 0.03
        self._ensure_data_dir()
        self.account = self._load_account()
        self.positions: Dict[str, Position] = self._load_positions()
        self.trades: List[SimTrade] = self._load_trades()

    def _ensure_data_dir(self):
        os.makedirs(_DATA_DIR, exist_ok=True)

    def _load_account(self) -> SimAccount:
        try:
            if os.path.exists(_ACCOUNT_FILE):
                with open(_ACCOUNT_FILE, "r") as f:
                    d = json.load(f)
                return SimAccount(**d)
        except Exception:
            pass
        acc = SimAccount(created_at=time.strftime("%Y-%m-%d %H:%M:%S"))
        self._save_account(acc)
        return acc

    def _save_account(self, acc: SimAccount = None):
        if acc is None:
            acc = self.account
        acc.updated_at = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(_ACCOUNT_FILE, "w") as f:
            json.dump(acc.__dict__, f, ensure_ascii=False, indent=2)

    def _load_positions(self) -> Dict[str, Position]:
        try:
            if os.path.exists(_POSITIONS_FILE):
                with open(_POSITIONS_FILE, "r") as f:
                    data = json.load(f)
                return {k: Position(**v) for k, v in data.items()}
        except Exception:
            pass
        return {}

    def _save_positions(self):
        data = {k: v.__dict__ for k, v in self.positions.items()}
        with open(_POSITIONS_FILE, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_trades(self) -> List[SimTrade]:
        try:
            if os.path.exists(_TRADES_FILE):
                with open(_TRADES_FILE, "r") as f:
                    data = json.load(f)
                return [SimTrade(**t) for t in data]
        except Exception:
            pass
        return []

    def _save_trades(self):
        data = [t.__dict__ for t in self.trades]
        with open(_TRADES_FILE, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_account_info(self) -> dict:
        total_value = self.account.cash
        position_values = {}
        for sym, pos in self.positions.items():
            position_values[sym] = {
                "symbol": pos.symbol,
                "name": pos.name,
                "market": pos.market,
                "shares": pos.shares,
                "entry_price": pos.entry_price,
                "entry_date": pos.entry_date,
                "stop_loss": pos.stop_loss,
                "take_profit": pos.take_profit,
                "strategy": pos.strategy,
            }
        return {
            "initial_capital": self.account.initial_capital,
            "cash": round(self.account.cash, 2),
            "positions": position_values,
            "position_count": len(self.positions),
            "total_value": round(total_value, 2),
            "updated_at": self.account.updated_at,
        }

    def get_trade_history(self, limit: int = 50) -> list:
        recent = self.trades[-limit:] if len(self.trades) > limit else self.trades
        return [t.__dict__ for t in reversed(recent)]

    def execute_buy(
        self, symbol: str, name: str, market: str, price: float,
        strategy: str = "manual", stop_loss: float = 0.0, take_profit: float = 0.0,
        order_type: str = "market", shares: int = 0,
    ) -> dict:
        if symbol in self.positions:
            return {"success": False, "error": "已有持仓，不可重复买入"}

        if order_type == "limit" and price <= 0:
            return {"success": False, "error": "限价单价格必须大于0"}

        if shares > 0:
            total_cost = shares * price * (1 + self.commission_rate + self.slippage_rate)
            if total_cost > self.account.cash:
                return {"success": False, "error": "资金不足"}
        else:
            max_invest = self.account.cash * self.max_position_pct
            commission_cost = price * (1 + self.commission_rate + self.slippage_rate)
            shares = int(max_invest / commission_cost / 100) * 100
            if shares <= 0:
                shares = int(max_invest / commission_cost)
            if shares <= 0:
                return {"success": False, "error": "资金不足"}
            total_cost = shares * price * (1 + self.commission_rate + self.slippage_rate)
            if total_cost > self.account.cash:
                return {"success": False, "error": "资金不足"}

        self.account.cash -= total_cost
        self.positions[symbol] = Position(
            symbol=symbol, name=name, market=market,
            shares=shares, entry_price=price,
            entry_date=time.strftime("%Y-%m-%d %H:%M:%S"),
            stop_loss=stop_loss, take_profit=take_profit,
            strategy=strategy,
        )
        self._save_account()
        self._save_positions()

        return {
            "success": True,
            "action": "buy",
            "order_type": order_type,
            "symbol": symbol,
            "name": name,
            "shares": shares,
            "price": price,
            "total_cost": round(total_cost, 2),
            "commission": round(shares * price * self.commission_rate, 2),
            "slippage": round(shares * price * self.slippage_rate, 2),
        }

    def execute_sell(self, symbol: str, price: float, reason: str = "manual") -> dict:
        if symbol not in self.positions:
            return {"success": False, "error": "无持仓"}

        pos = self.positions[symbol]
        revenue = pos.shares * price * (1 - self.commission_rate - self.slippage_rate)
        pnl = revenue - pos.shares * pos.entry_price
        pnl_pct = (price - pos.entry_price) / pos.entry_price * 100

        self.account.cash += revenue

        trade = SimTrade(
            symbol=symbol, name=pos.name, market=pos.market,
            direction="long", shares=pos.shares,
            entry_price=pos.entry_price, exit_price=price,
            entry_date=pos.entry_date, exit_date=time.strftime("%Y-%m-%d"),
            pnl=round(pnl, 2), pnl_pct=round(pnl_pct, 2),
            commission=round(pos.shares * price * self.commission_rate, 2),
            slippage=round(pos.shares * price * self.slippage_rate, 2),
            strategy=pos.strategy, exit_reason=reason,
        )
        self.trades.append(trade)
        del self.positions[symbol]

        self._save_account()
        self._save_positions()
        self._save_trades()

        return {
            "success": True,
            "action": "sell",
            "symbol": symbol,
            "name": trade.name,
            "shares": trade.shares,
            "entry_price": trade.entry_price,
            "exit_price": price,
            "pnl": trade.pnl,
            "pnl_pct": trade.pnl_pct,
            "reason": reason,
        }

    def check_stop_loss_take_profit(self, symbol: str, current_price: float) -> Optional[dict]:
        if symbol not in self.positions:
            return None
        pos = self.positions[symbol]
        if pos.stop_loss > 0 and current_price <= pos.stop_loss:
            return self.execute_sell(symbol, current_price, "stop_loss")
        if pos.take_profit > 0 and current_price >= pos.take_profit:
            return self.execute_sell(symbol, current_price, "take_profit")
        return None

    def get_performance(self) -> dict:
        if not self.trades:
            return {
                "total_trades": 0,
                "win_rate": 0,
                "total_pnl": 0,
                "avg_pnl_pct": 0,
                "max_win": 0,
                "max_loss": 0,
                "profit_factor": 0,
                "sharpe_ratio": 0,
            }

        pnls = [t.pnl for t in self.trades]
        pnl_pcts = [t.pnl_pct for t in self.trades]
        wins = [t for t in self.trades if t.pnl > 0]
        losses = [t for t in self.trades if t.pnl <= 0]

        total_profit = sum(t.pnl for t in wins)
        total_loss = abs(sum(t.pnl for t in losses)) if losses else 1

        sharpe = 0.0
        if len(pnl_pcts) > 5:
            arr = np.array(pnl_pcts)
            if np.std(arr) > 0:
                sharpe = float(np.mean(arr) / np.std(arr) * np.sqrt(252))

        return {
            "total_trades": len(self.trades),
            "win_trades": len(wins),
            "loss_trades": len(losses),
            "win_rate": round(len(wins) / len(self.trades) * 100, 2),
            "total_pnl": round(sum(pnls), 2),
            "avg_pnl_pct": round(np.mean(pnl_pcts), 2),
            "max_win": round(max(pnls), 2) if pnls else 0,
            "max_loss": round(min(pnls), 2) if pnls else 0,
            "profit_factor": round(total_profit / total_loss, 2) if total_loss > 0 else 0,
            "sharpe_ratio": round(sharpe, 2),
        }

    def reset_account(self) -> dict:
        self.account = SimAccount(created_at=time.strftime("%Y-%m-%d %H:%M:%S"))
        self.positions = {}
        self.trades = []
        self._save_account()
        self._save_positions()
        self._save_trades()
        return {"success": True, "message": "账户已重置"}
