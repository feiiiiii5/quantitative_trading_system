import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

ACCOUNT_DIR = Path(os.environ.get("ACCOUNT_DATA_DIR", str(Path(__file__).parent.parent.parent / "data" / "accounts")))


@dataclass
class SubAccount:
    account_id: str
    name: str
    allocated_capital: float = 0.0
    current_capital: float = 0.0
    strategy: str = ""
    pnl: float = 0.0
    pnl_pct: float = 0.0
    positions: Dict[str, dict] = field(default_factory=dict)
    trades: List[dict] = field(default_factory=list)
    created_at: str = ""
    is_active: bool = True

    def to_dict(self) -> dict:
        return {
            "account_id": self.account_id, "name": self.name,
            "allocated_capital": round(self.allocated_capital, 2),
            "current_capital": round(self.current_capital, 2),
            "strategy": self.strategy,
            "pnl": round(self.pnl, 2), "pnl_pct": round(self.pnl_pct, 4),
            "position_count": len(self.positions),
            "trade_count": len(self.trades),
            "created_at": self.created_at,
            "is_active": self.is_active,
        }


@dataclass
class MasterAccount:
    total_capital: float = 1000000.0
    cash: float = 1000000.0
    sub_accounts: Dict[str, SubAccount] = field(default_factory=dict)
    risk_params: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "total_capital": round(self.total_capital, 2),
            "cash": round(self.cash, 2),
            "sub_account_count": len(self.sub_accounts),
            "total_pnl": round(sum(sa.pnl for sa in self.sub_accounts.values()), 2),
            "sub_accounts": {k: v.to_dict() for k, v in self.sub_accounts.items()},
        }


class MultiAccountManager:
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir) if base_dir else ACCOUNT_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._master = MasterAccount()
        self._load_accounts()

    def _load_accounts(self):
        filepath = self.base_dir / "master.json"
        if filepath.exists():
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._master.total_capital = data.get("total_capital", 1000000)
                self._master.cash = data.get("cash", 1000000)
                for sa_id, sa_data in data.get("sub_accounts", {}).items():
                    self._master.sub_accounts[sa_id] = SubAccount(
                        account_id=sa_id,
                        name=sa_data.get("name", ""),
                        allocated_capital=sa_data.get("allocated_capital", 0),
                        current_capital=sa_data.get("current_capital", 0),
                        strategy=sa_data.get("strategy", ""),
                        pnl=sa_data.get("pnl", 0),
                        pnl_pct=sa_data.get("pnl_pct", 0),
                        created_at=sa_data.get("created_at", ""),
                    )
            except Exception as e:
                logger.debug(f"Failed to load accounts: {e}")

    def _save_accounts(self):
        filepath = self.base_dir / "master.json"
        data = {
            "total_capital": self._master.total_capital,
            "cash": self._master.cash,
            "sub_accounts": {k: v.to_dict() for k, v in self._master.sub_accounts.items()},
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def create_sub_account(self, name: str, allocated_capital: float, strategy: str = "") -> Optional[SubAccount]:
        total_allocated = sum(sa.allocated_capital for sa in self._master.sub_accounts.values())
        if total_allocated + allocated_capital > self._master.total_capital:
            return None

        account_id = f"sub_{len(self._master.sub_accounts) + 1:04d}"
        sub = SubAccount(
            account_id=account_id, name=name,
            allocated_capital=allocated_capital,
            current_capital=allocated_capital,
            strategy=strategy,
            created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
        )
        self._master.sub_accounts[account_id] = sub
        self._master.cash -= allocated_capital
        self._save_accounts()
        return sub

    def delete_sub_account(self, account_id: str) -> bool:
        sub = self._master.sub_accounts.get(account_id)
        if not sub:
            return False
        self._master.cash += sub.current_capital
        del self._master.sub_accounts[account_id]
        self._save_accounts()
        return True

    def get_sub_account(self, account_id: str) -> Optional[dict]:
        sub = self._master.sub_accounts.get(account_id)
        return sub.to_dict() if sub else None

    def list_sub_accounts(self) -> List[dict]:
        return [sa.to_dict() for sa in self._master.sub_accounts.values()]

    def get_master_account(self) -> dict:
        return self._master.to_dict()

    def allocate_capital(self, account_id: str, amount: float) -> bool:
        sub = self._master.sub_accounts.get(account_id)
        if not sub:
            return False
        if amount > 0 and amount > self._master.cash:
            return False
        if amount < 0 and abs(amount) > sub.current_capital:
            return False
        self._master.cash -= amount
        sub.allocated_capital += amount
        sub.current_capital += amount
        self._save_accounts()
        return True

    def copy_trade(self, from_account_id: str, to_account_id: str,
                   symbol: str, quantity: int, price: float, side: str) -> dict:
        from_sub = self._master.sub_accounts.get(from_account_id)
        to_sub = self._master.sub_accounts.get(to_account_id)
        if not from_sub or not to_sub:
            return {"success": False, "error": "账户不存在"}

        ratio = to_sub.allocated_capital / from_sub.allocated_capital if from_sub.allocated_capital > 0 else 1.0
        copy_qty = int(quantity * ratio / 100) * 100
        if copy_qty <= 0:
            copy_qty = int(quantity * ratio)
        if copy_qty <= 0:
            return {"success": False, "error": "跟单数量为0"}

        cost = copy_qty * price * 1.001
        if side == "buy" and cost > to_sub.current_capital:
            return {"success": False, "error": "子账户资金不足"}

        if side == "buy":
            to_sub.current_capital -= cost
            to_sub.positions[symbol] = {"quantity": copy_qty, "avg_price": price}
        else:
            if symbol in to_sub.positions:
                pos = to_sub.positions[symbol]
                pnl = (price - pos.get("avg_price", price)) * pos.get("quantity", 0)
                to_sub.current_capital += copy_qty * price * 0.999
                to_sub.pnl += pnl
                del to_sub.positions[symbol]

        to_sub.trades.append({
            "symbol": symbol, "side": side, "quantity": copy_qty,
            "price": price, "type": "copy_trade",
            "from_account": from_account_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        })

        self._save_accounts()
        return {"success": True, "copied_quantity": copy_qty, "ratio": round(ratio, 4)}

    def mirror_trade(self, from_account_id: str, symbol: str, quantity: int,
                     price: float, side: str) -> dict:
        results = {}
        for sa_id, sub in self._master.sub_accounts.items():
            if sa_id == from_account_id:
                continue
            result = self.copy_trade(from_account_id, sa_id, symbol, quantity, price, side)
            results[sa_id] = result
        return results
