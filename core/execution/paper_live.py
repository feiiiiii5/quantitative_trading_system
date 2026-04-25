import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


logger = logging.getLogger(__name__)

PAPER_DIR = Path(os.environ.get("PAPER_DATA_DIR", str(Path(__file__).parent.parent.parent / "data" / "paper_trading")))


@dataclass
class PaperPosition:
    symbol: str
    name: str
    market: str
    shares: int
    entry_price: float
    entry_date: str
    stop_loss: float = 0.0
    take_profit: float = 0.0
    strategy: str = "manual"

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol, "name": self.name, "market": self.market,
            "shares": self.shares, "entry_price": self.entry_price,
            "entry_date": self.entry_date, "stop_loss": self.stop_loss,
            "take_profit": self.take_profit, "strategy": self.strategy,
        }


@dataclass
class PaperAccount:
    cash: float = 100000.0
    initial_capital: float = 100000.0
    positions: Dict[str, PaperPosition] = field(default_factory=dict)
    trades: List[dict] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    commission_rate: float = 0.0003
    slippage_rate: float = 0.001

    def to_dict(self) -> dict:
        return {
            "cash": round(self.cash, 2),
            "initial_capital": round(self.initial_capital, 2),
            "positions": {k: v.to_dict() for k, v in self.positions.items()},
            "trade_count": len(self.trades),
            "equity_curve_len": len(self.equity_curve),
        }


class PaperLiveSwitch:
    def __init__(self):
        self._paper_account = PaperAccount()
        self._live_account: Optional[dict] = None
        self._mode = "paper"
        self._pre_live_checklist: Dict[str, bool] = {
            "backtest_passed": False,
            "stress_test_passed": False,
            "risk_params_set": False,
            "stop_loss_configured": False,
            "capital_verified": False,
        }
        self._data_dir = PAPER_DIR
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._load_paper_account()

    def _load_paper_account(self):
        filepath = self._data_dir / "paper_account.json"
        if filepath.exists():
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._paper_account.cash = data.get("cash", 100000)
                self._paper_account.initial_capital = data.get("initial_capital", 100000)
                self._paper_account.trades = data.get("trades", [])
                self._paper_account.equity_curve = data.get("equity_curve", [])
            except Exception as e:
                logger.debug(f"Failed to load paper account: {e}")

    def _save_paper_account(self):
        filepath = self._data_dir / "paper_account.json"
        data = {
            "cash": self._paper_account.cash,
            "initial_capital": self._paper_account.initial_capital,
            "trades": self._paper_account.trades[-100:],
            "equity_curve": self._paper_account.equity_curve[-500:],
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def paper_buy(self, symbol: str, name: str, market: str, price: float,
                  strategy: str = "manual", stop_loss: float = 0.0, take_profit: float = 0.0) -> dict:
        if symbol in self._paper_account.positions:
            return {"success": False, "error": "已有持仓"}

        max_invest = self._paper_account.cash * 0.3
        fill_price = price * (1 + self._paper_account.slippage_rate)
        shares = int(max_invest / fill_price / 100) * 100
        if shares <= 0:
            shares = int(max_invest / fill_price)
        if shares <= 0:
            return {"success": False, "error": "资金不足"}

        cost = shares * fill_price * (1 + self._paper_account.commission_rate)
        if cost > self._paper_account.cash:
            return {"success": False, "error": "资金不足"}

        self._paper_account.cash -= cost
        self._paper_account.positions[symbol] = PaperPosition(
            symbol=symbol, name=name, market=market,
            shares=shares, entry_price=fill_price,
            entry_date=time.strftime("%Y-%m-%d"),
            stop_loss=stop_loss, take_profit=take_profit,
            strategy=strategy,
        )
        self._save_paper_account()
        return {"success": True, "shares": shares, "fill_price": round(fill_price, 2), "cost": round(cost, 2)}

    def paper_sell(self, symbol: str, price: float, reason: str = "manual") -> dict:
        if symbol not in self._paper_account.positions:
            return {"success": False, "error": "无持仓"}

        pos = self._paper_account.positions[symbol]
        fill_price = price * (1 - self._paper_account.slippage_rate)
        revenue = pos.shares * fill_price * (1 - self._paper_account.commission_rate)
        pnl = revenue - pos.shares * pos.entry_price
        pnl_pct = (fill_price / pos.entry_price - 1) * 100

        self._paper_account.cash += revenue
        self._paper_account.trades.append({
            "symbol": symbol, "name": pos.name, "direction": "long",
            "shares": pos.shares, "entry_price": pos.entry_price,
            "exit_price": round(fill_price, 2), "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2), "strategy": pos.strategy,
            "exit_reason": reason,
            "entry_date": pos.entry_date,
            "exit_date": time.strftime("%Y-%m-%d"),
        })
        del self._paper_account.positions[symbol]
        self._save_paper_account()
        return {"success": True, "pnl": round(pnl, 2), "pnl_pct": round(pnl_pct, 2)}

    def reset_paper_account(self, capital: float = 100000.0):
        self._paper_account = PaperAccount(initial_capital=capital, cash=capital)
        self._save_paper_account()

    def get_paper_status(self) -> dict:
        total_value = self._paper_account.cash
        for pos in self._paper_account.positions.values():
            total_value += pos.shares * pos.entry_price

        return {
            "mode": self._mode,
            "cash": round(self._paper_account.cash, 2),
            "total_value": round(total_value, 2),
            "initial_capital": round(self._paper_account.initial_capital, 2),
            "total_pnl": round(total_value - self._paper_account.initial_capital, 2),
            "total_pnl_pct": round((total_value / self._paper_account.initial_capital - 1) * 100, 2),
            "position_count": len(self._paper_account.positions),
            "trade_count": len(self._paper_account.trades),
            "positions": {k: v.to_dict() for k, v in self._paper_account.positions.items()},
        }

    def get_equity_curve(self) -> List[float]:
        return self._paper_account.equity_curve[-200:]

    def check_pre_live_checklist(self) -> dict:
        all_passed = all(self._pre_live_checklist.values())
        return {
            "all_passed": all_passed,
            "items": dict(self._pre_live_checklist),
            "can_go_live": all_passed,
        }

    def update_checklist(self, item: str, passed: bool) -> bool:
        if item in self._pre_live_checklist:
            self._pre_live_checklist[item] = passed
            return True
        return False

    def switch_to_live(self) -> dict:
        checklist = self.check_pre_live_checklist()
        if not checklist["can_go_live"]:
            return {"success": False, "error": "预检查未通过", "checklist": checklist["items"]}
        self._mode = "live"
        return {"success": True, "mode": "live"}

    def switch_to_paper(self) -> dict:
        self._mode = "paper"
        return {"success": True, "mode": "paper"}

    def compare_equity_curves(self, live_curve: Optional[List[float]] = None) -> dict:
        paper_curve = self._paper_account.equity_curve
        if not paper_curve:
            return {"paper": [], "live": live_curve or []}

        if live_curve is None:
            return {"paper": paper_curve[-200:], "live": []}

        min_len = min(len(paper_curve), len(live_curve))
        return {
            "paper": paper_curve[-min_len:],
            "live": live_curve[-min_len:],
            "paper_return": round((paper_curve[-1] / paper_curve[0] - 1) * 100, 2) if len(paper_curve) > 1 else 0,
            "live_return": round((live_curve[-1] / live_curve[0] - 1) * 100, 2) if len(live_curve) > 1 else 0,
        }
