import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent / "data"

_COMMISSION_RATE = 0.0003
_MIN_COMMISSION = 5.0
_STAMP_TAX_RATE = 0.001
_SLIPPAGE_BPS = 2


@dataclass
class Position:
    symbol: str
    name: str
    market: str
    shares: int
    cost_price: float
    current_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    buy_time: str = ""
    strategy: str = "manual"

    @property
    def market_value(self) -> float:
        return self.current_price * self.shares if self.current_price > 0 else self.cost_price * self.shares

    @property
    def profit(self) -> float:
        return (self.current_price - self.cost_price) * self.shares if self.current_price > 0 else 0

    @property
    def profit_pct(self) -> float:
        if self.cost_price <= 0:
            return 0
        return (self.current_price - self.cost_price) / self.cost_price * 100 if self.current_price > 0 else 0

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol, "name": self.name, "market": self.market,
            "shares": self.shares, "cost_price": self.cost_price,
            "current_price": self.current_price, "stop_loss": self.stop_loss,
            "take_profit": self.take_profit, "buy_time": self.buy_time,
            "strategy": self.strategy,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Position":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class TradeRecord:
    id: str
    symbol: str
    name: str
    market: str
    action: str
    price: float
    shares: int
    amount: float
    fee: float
    time: str
    strategy: str = "manual"
    signal_strength: float = 0
    reason: str = ""
    pnl: float = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id, "symbol": self.symbol, "name": self.name,
            "market": self.market, "action": self.action, "price": self.price,
            "shares": self.shares, "amount": round(self.amount, 2),
            "fee": round(self.fee, 2), "time": self.time,
            "strategy": self.strategy, "signal_strength": self.signal_strength,
            "reason": self.reason, "pnl": round(self.pnl, 2),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TradeRecord":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class PendingOrder:
    id: str
    symbol: str
    name: str
    market: str
    action: str
    order_type: str
    price: float
    shares: int
    trigger_price: float
    strategy: str
    created_time: str
    expire_time: str = ""
    status: str = "pending"

    def to_dict(self) -> dict:
        return {
            "id": self.id, "symbol": self.symbol, "name": self.name,
            "market": self.market, "action": self.action,
            "order_type": self.order_type, "price": self.price,
            "shares": self.shares, "trigger_price": self.trigger_price,
            "strategy": self.strategy, "created_time": self.created_time,
            "expire_time": self.expire_time, "status": self.status,
        }


@dataclass
class WatchItem:
    symbol: str
    name: str
    added_time: str = ""


def _calc_commission(amount: float, market: str, action: str) -> float:
    commission = max(amount * _COMMISSION_RATE, _MIN_COMMISSION)
    if market == "A" and action == "sell":
        commission += amount * _STAMP_TAX_RATE
    return round(commission, 2)


def _apply_slippage(price: float, action: str, market: str) -> float:
    slip = price * _SLIPPAGE_BPS / 10000
    if action == "buy":
        return round(price + slip, 2)
    return round(price - slip, 2)


class SimulatedTrading:
    def __init__(self, initial_capital: float = 1000000):
        self._initial_capital = initial_capital
        self._cash = initial_capital
        self._positions: dict[str, Position] = {}
        self._trades: list[TradeRecord] = []
        self._pending_orders: list[PendingOrder] = []
        self._watchlist: list[WatchItem] = []
        self._auto_running = False
        self._auto_strategy = ""
        self._auto_task: Optional[asyncio.Task] = None
        self._fetcher = None
        self._load_state()

    def _state_path(self) -> Path:
        return _DATA_DIR / "trading_state.json"

    def _load_state(self) -> None:
        path = self._state_path()
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self._cash = data.get("cash", self._initial_capital)
            self._initial_capital = data.get("initial_capital", self._initial_capital)
            self._positions = {k: Position.from_dict(v) for k, v in data.get("positions", {}).items()}
            self._trades = [TradeRecord.from_dict(t) for t in data.get("trades", [])]
            self._watchlist = [WatchItem(**w) for w in data.get("watchlist", [])]
            logger.info(f"Trading state loaded: cash={self._cash}, positions={len(self._positions)}, trades={len(self._trades)}")
        except Exception as e:
            logger.warning(f"Failed to load trading state: {e}")

    def _save_state(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        path = self._state_path()
        try:
            data = {
                "cash": self._cash,
                "initial_capital": self._initial_capital,
                "positions": {k: v.to_dict() for k, v in self._positions.items()},
                "trades": [t.to_dict() for t in self._trades[-500:]],
                "watchlist": [{"symbol": w.symbol, "name": w.name, "added_time": w.added_time} for w in self._watchlist],
                "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to save trading state: {e}")

    def execute_buy(self, symbol: str, name: str, market: str, price: float,
                    strategy: str = "manual", stop_loss: float = 0, take_profit: float = 0,
                    order_type: str = "market", shares: int = 0) -> dict:
        if price <= 0:
            return {"success": False, "error": "价格必须大于0"}

        fill_price = _apply_slippage(price, "buy", market)

        if shares <= 0:
            max_shares = int(self._cash * 0.95 / fill_price / 100) * 100
            if market == "US":
                max_shares = int(self._cash * 0.95 / fill_price)
            if max_shares <= 0:
                return {"success": False, "error": "资金不足"}
            shares = max_shares

        amount = fill_price * shares
        fee = _calc_commission(amount, market, "buy")
        total_cost = amount + fee

        if total_cost > self._cash:
            return {"success": False, "error": f"资金不足，需要 {total_cost:.2f}，可用 {self._cash:.2f}"}

        self._cash -= total_cost

        if symbol in self._positions:
            pos = self._positions[symbol]
            total_cost_basis = pos.cost_price * pos.shares + amount
            total_shares = pos.shares + shares
            pos.cost_price = total_cost_basis / total_shares
            pos.shares = total_shares
            pos.stop_loss = stop_loss if stop_loss > 0 else pos.stop_loss
            pos.take_profit = take_profit if take_profit > 0 else pos.take_profit
        else:
            self._positions[symbol] = Position(
                symbol=symbol, name=name, market=market, shares=shares,
                cost_price=fill_price, stop_loss=stop_loss, take_profit=take_profit,
                buy_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), strategy=strategy,
            )

        trade = TradeRecord(
            id=str(uuid.uuid4())[:8], symbol=symbol, name=name, market=market,
            action="buy", price=fill_price, shares=shares, amount=amount,
            fee=fee, time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), strategy=strategy,
        )
        self._trades.append(trade)
        self._save_state()

        return {
            "success": True, "action": "buy", "symbol": symbol, "name": name,
            "price": fill_price, "shares": shares, "amount": round(amount, 2),
            "fee": fee, "cash": round(self._cash, 2),
        }

    def execute_sell(self, symbol: str, price: float, reason: str = "manual", shares: int = 0) -> dict:
        if symbol not in self._positions:
            return {"success": False, "error": f"未持有 {symbol}"}

        pos = self._positions[symbol]
        if shares <= 0 or shares >= pos.shares:
            shares = pos.shares

        fill_price = _apply_slippage(price, "sell", pos.market)
        amount = fill_price * shares
        fee = _calc_commission(amount, pos.market, "sell")
        net_amount = amount - fee

        pnl = (fill_price - pos.cost_price) * shares - fee

        self._cash += net_amount

        trade = TradeRecord(
            id=str(uuid.uuid4())[:8], symbol=symbol, name=pos.name, market=pos.market,
            action="sell", price=fill_price, shares=shares, amount=amount,
            fee=fee, time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            strategy=reason, reason=reason, pnl=pnl,
        )
        self._trades.append(trade)

        if shares >= pos.shares:
            del self._positions[symbol]
        else:
            pos.shares -= shares

        self._save_state()

        return {
            "success": True, "action": "sell", "symbol": symbol, "name": pos.name,
            "price": fill_price, "shares": shares, "amount": round(amount, 2),
            "fee": fee, "pnl": round(pnl, 2), "cash": round(self._cash, 2), "reason": reason,
        }

    def place_order(self, symbol: str, name: str, market: str, action: str,
                    order_type: str, price: float, shares: int,
                    trigger_price: float = 0, strategy: str = "manual",
                    expire_minutes: int = 1440) -> dict:
        if action not in ("buy", "sell"):
            return {"success": False, "error": "无效的交易方向"}
        if order_type not in ("limit", "stop", "stop_limit"):
            return {"success": False, "error": "无效的订单类型"}
        if price <= 0:
            return {"success": False, "error": "价格必须大于0"}
        if shares <= 0:
            return {"success": False, "error": "数量必须大于0"}

        if action == "sell" and symbol not in self._positions:
            return {"success": False, "error": f"未持有 {symbol}"}
        if action == "sell" and shares > self._positions[symbol].shares:
            return {"success": False, "error": "卖出数量超过持仓"}

        expire_time = ""
        if expire_minutes > 0:
            expire_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        order = PendingOrder(
            id=str(uuid.uuid4())[:8], symbol=symbol, name=name, market=market,
            action=action, order_type=order_type, price=price, shares=shares,
            trigger_price=trigger_price, strategy=strategy,
            created_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            expire_time=expire_time,
        )
        self._pending_orders.append(order)
        self._save_state()

        return {
            "success": True, "order_id": order.id, "action": action,
            "order_type": order_type, "symbol": symbol, "price": price,
            "shares": shares, "trigger_price": trigger_price,
        }

    def cancel_order(self, order_id: str) -> dict:
        for i, order in enumerate(self._pending_orders):
            if order.id == order_id:
                if order.status != "pending":
                    return {"success": False, "error": "订单已处理，无法取消"}
                self._pending_orders.pop(i)
                self._save_state()
                return {"success": True, "message": f"订单 {order_id} 已取消"}
        return {"success": False, "error": "订单不存在"}

    def get_pending_orders(self) -> list:
        return [o.to_dict() for o in self._pending_orders if o.status == "pending"]

    def check_pending_orders(self, current_prices: dict[str, float]) -> list:
        executed = []
        remaining = []
        now = datetime.now()

        for order in self._pending_orders:
            if order.status != "pending":
                continue

            if order.expire_time:
                try:
                    expire_dt = datetime.strptime(order.expire_time, "%Y-%m-%d %H:%M:%S")
                    if now > expire_dt:
                        order.status = "expired"
                        continue
                except ValueError:
                    pass

            current_price = current_prices.get(order.symbol)
            if current_price is None or current_price <= 0:
                remaining.append(order)
                continue

            should_execute = False
            if order.order_type == "limit":
                if order.action == "buy" and current_price <= order.price:
                    should_execute = True
                elif order.action == "sell" and current_price >= order.price:
                    should_execute = True
            elif order.order_type == "stop":
                if order.action == "buy" and current_price >= order.trigger_price:
                    should_execute = True
                elif order.action == "sell" and current_price <= order.trigger_price:
                    should_execute = True
            elif order.order_type == "stop_limit":
                if order.action == "buy" and current_price >= order.trigger_price and current_price <= order.price:
                    should_execute = True
                elif order.action == "sell" and current_price <= order.trigger_price and current_price >= order.price:
                    should_execute = True

            if should_execute:
                order.status = "filled"
                if order.action == "buy":
                    result = self.execute_buy(
                        order.symbol, order.name, order.market, current_price,
                        strategy=order.strategy, shares=order.shares,
                    )
                else:
                    result = self.execute_sell(
                        order.symbol, current_price, reason=order.strategy, shares=order.shares,
                    )
                executed.append({"order": order.to_dict(), "result": result})
            else:
                remaining.append(order)

        self._pending_orders = remaining
        if executed:
            self._save_state()
        return executed

    def update_position_prices(self, price_map: dict[str, float]) -> int:
        updated = 0
        for symbol, price in price_map.items():
            if symbol in self._positions and price > 0:
                self._positions[symbol].current_price = price
                updated += 1
        return updated

    def get_account_info(self) -> dict:
        total_market_value = sum(p.market_value for p in self._positions.values())
        total_cost = sum(p.cost_price * p.shares for p in self._positions.values())
        total_assets = self._cash + total_market_value
        total_profit = total_assets - self._initial_capital
        total_profit_pct = (total_profit / self._initial_capital * 100) if self._initial_capital > 0 else 0

        positions = []
        for p in self._positions.values():
            positions.append({
                "symbol": p.symbol, "name": p.name, "market": p.market,
                "shares": p.shares, "cost_price": round(p.cost_price, 2),
                "current_price": round(p.current_price, 2) if p.current_price > 0 else None,
                "market_value": round(p.market_value, 2),
                "profit": round(p.profit, 2), "profit_pct": round(p.profit_pct, 2),
                "stop_loss": p.stop_loss, "take_profit": p.take_profit,
                "strategy": p.strategy, "buy_time": p.buy_time,
            })

        return {
            "initial_capital": self._initial_capital,
            "cash": round(self._cash, 2),
            "total_market_value": round(total_market_value, 2),
            "total_cost": round(total_cost, 2),
            "total_assets": round(total_assets, 2),
            "total_profit": round(total_profit, 2),
            "total_profit_pct": round(total_profit_pct, 2),
            "position_count": len(self._positions),
            "positions": positions,
        }

    def get_performance(self) -> dict:
        return self.get_detailed_stats()

    def get_detailed_stats(self) -> dict:
        account = self.get_account_info()
        total_profit = account["total_profit"]
        total_profit_pct = account["total_profit_pct"]

        buy_trades = [t for t in self._trades if t.action == "buy"]
        sell_trades = [t for t in self._trades if t.action == "sell"]

        win_trades = []
        loss_trades = []
        for sell in sell_trades:
            buy_for_same = [t for t in buy_trades if t.symbol == sell.symbol and t.time < sell.time]
            if buy_for_same:
                buy = buy_for_same[-1]
                pnl = (sell.price - buy.price) * sell.shares - sell.fee - buy.fee
                if pnl > 0:
                    win_trades.append(pnl)
                else:
                    loss_trades.append(abs(pnl))

        total_trades = len(sell_trades)
        win_count = len(win_trades)
        loss_count = len(loss_trades)
        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0
        avg_win = np.mean(win_trades) if win_trades else 0
        avg_loss = np.mean(loss_trades) if loss_trades else 0
        profit_factor = (sum(win_trades) / sum(loss_trades)) if loss_trades and sum(loss_trades) > 0 else float('inf') if win_trades else 0

        total_fees = sum(t.fee for t in self._trades)

        equity_curve = [self._initial_capital]
        for t in self._trades:
            last = equity_curve[-1]
            if t.action == "buy":
                equity_curve.append(last - t.amount - t.fee)
            else:
                equity_curve.append(last + t.amount - t.fee)

        max_drawdown = 0
        peak = equity_curve[0]
        for val in equity_curve:
            if val > peak:
                peak = val
            dd = (peak - val) / peak * 100 if peak > 0 else 0
            if dd > max_drawdown:
                max_drawdown = dd

        daily_returns = []
        for i in range(1, len(equity_curve)):
            if equity_curve[i - 1] > 0:
                daily_returns.append((equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1])

        sharpe = 0
        if daily_returns:
            avg_ret = np.mean(daily_returns)
            std_ret = np.std(daily_returns)
            if std_ret > 0:
                sharpe = avg_ret / std_ret * np.sqrt(252)

        avg_hold_days = 0
        hold_days_list = []
        for sell in sell_trades:
            buy_for_same = [t for t in buy_trades if t.symbol == sell.symbol and t.time < sell.time]
            if buy_for_same:
                buy = buy_for_same[-1]
                try:
                    b = datetime.strptime(buy.time, "%Y-%m-%d %H:%M:%S")
                    s = datetime.strptime(sell.time, "%Y-%m-%d %H:%M:%S")
                    hold_days_list.append((s - b).days)
                except Exception:
                    pass
        if hold_days_list:
            avg_hold_days = np.mean(hold_days_list)

        return {
            "total_return": round(total_profit_pct, 2),
            "total_profit": round(total_profit, 2),
            "max_drawdown": round(max_drawdown, 2),
            "sharpe_ratio": round(sharpe, 2),
            "win_rate": round(win_rate, 2),
            "profit_factor": round(profit_factor, 2) if profit_factor != float('inf') else 999,
            "total_trades": total_trades,
            "win_trades": win_count,
            "loss_trades": loss_count,
            "avg_profit": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "avg_hold_days": round(avg_hold_days, 1),
            "total_fees": round(total_fees, 2),
            "cash": account["cash"],
            "total_assets": account["total_assets"],
            "position_count": account["position_count"],
        }

    def get_trade_history(self, limit: int = 50, page: int = 1) -> dict:
        total = len(self._trades)
        start = (page - 1) * limit
        end = start + limit
        trades = self._trades[start:end]

        return {
            "total": total, "page": page, "limit": limit,
            "trades": [t.to_dict() for t in reversed(trades)],
        }

    def reset_account(self) -> dict:
        self.stop_auto_trading()
        self._cash = self._initial_capital
        self._positions.clear()
        self._trades.clear()
        self._pending_orders.clear()
        self._watchlist.clear()
        self._save_state()
        return {"success": True, "message": "账户已重置", "initial_capital": self._initial_capital}

    def add_to_watchlist(self, symbol: str, name: str) -> dict:
        for w in self._watchlist:
            if w.symbol == symbol:
                return {"success": True, "message": f"{symbol} 已在监控池中"}
        self._watchlist.append(WatchItem(
            symbol=symbol, name=name,
            added_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ))
        self._save_state()
        return {"success": True, "message": f"{symbol} 已添加到监控池", "watchlist_count": len(self._watchlist)}

    def remove_from_watchlist(self, symbol: str) -> dict:
        self._watchlist = [w for w in self._watchlist if w.symbol != symbol]
        self._save_state()
        return {"success": True, "message": f"{symbol} 已从监控池移除", "watchlist_count": len(self._watchlist)}

    def get_watchlist(self) -> list:
        return [
            {"symbol": w.symbol, "name": w.name, "added_time": w.added_time}
            for w in self._watchlist
        ]

    def start_auto_trading(self, strategy_name: str, fetcher) -> dict:
        if self._auto_running:
            return {"success": False, "error": "自动交易已在运行中"}

        from core.strategies import CompositeStrategy
        strategy_map = {s.name: s for s in CompositeStrategy().strategies}
        if strategy_name not in strategy_map:
            available = list(strategy_map.keys())
            return {"success": False, "error": f"策略 {strategy_name} 不存在", "available": available}

        self._auto_running = True
        self._auto_strategy = strategy_name
        self._fetcher = fetcher

        try:
            loop = asyncio.get_event_loop()
            self._auto_task = loop.create_task(self._auto_trading_loop())
        except RuntimeError:
            self._auto_running = False
            return {"success": False, "error": "无法启动异步任务"}

        return {"success": True, "message": f"自动策略交易已启动，策略: {strategy_name}"}

    def stop_auto_trading(self) -> dict:
        if not self._auto_running:
            return {"success": True, "message": "自动交易未在运行"}

        self._auto_running = False
        if self._auto_task and not self._auto_task.done():
            self._auto_task.cancel()
        self._auto_task = None
        self._auto_strategy = ""
        return {"success": True, "message": "自动策略交易已停止"}

    def get_auto_trading_status(self) -> dict:
        return {
            "running": self._auto_running,
            "strategy": self._auto_strategy,
            "watchlist_count": len(self._watchlist),
            "position_count": len(self._positions),
            "pending_orders": len(self._pending_orders),
            "watchlist": [
                {"symbol": w.symbol, "name": w.name} for w in self._watchlist
            ],
        }

    async def _auto_trading_loop(self):
        from core.strategies import CompositeStrategy
        from core.market_detector import MarketDetector

        composite = CompositeStrategy()
        strategy_map = {s.name: s for s in composite.strategies}

        while self._auto_running:
            try:
                if not self._watchlist:
                    await asyncio.sleep(30)
                    continue

                price_map = {}
                for item in list(self._watchlist):
                    if not self._auto_running:
                        break

                    try:
                        symbol = item.symbol
                        market = MarketDetector.detect(symbol)

                        realtime = await self._fetcher.get_realtime(symbol)
                        if not realtime or not realtime.get("price") or realtime["price"] <= 0:
                            continue

                        current_price = realtime["price"]
                        price_map[symbol] = current_price

                        if symbol in self._positions:
                            pos = self._positions[symbol]
                            pos.current_price = current_price

                            if pos.stop_loss > 0 and current_price <= pos.stop_loss:
                                self.execute_sell(symbol, current_price, reason=f"止损-{self._auto_strategy}")
                                continue
                            if pos.take_profit > 0 and current_price >= pos.take_profit:
                                self.execute_sell(symbol, current_price, reason=f"止盈-{self._auto_strategy}")
                                continue

                        df = await self._fetcher.get_history(symbol, "1y", "daily")
                        if df.empty or len(df) < 30:
                            continue

                        strategy = strategy_map.get(self._auto_strategy)
                        if not strategy:
                            continue

                        result = strategy.generate_signals(df)
                        if result and result.current_signal:
                            signal = result.current_signal
                            if signal.signal_type.value == "buy" and symbol not in self._positions:
                                stop_loss = signal.stop_loss if signal.stop_loss > 0 else current_price * 0.95
                                take_profit = signal.take_profit if signal.take_profit > 0 else current_price * 1.10
                                self.execute_buy(
                                    symbol, item.name, market, current_price,
                                    strategy=self._auto_strategy, stop_loss=stop_loss,
                                    take_profit=take_profit,
                                )
                            elif signal.signal_type.value == "sell" and symbol in self._positions:
                                self.execute_sell(symbol, current_price, reason=f"策略卖出-{self._auto_strategy}")

                    except Exception as e:
                        logger.debug(f"Auto trading error for {item.symbol}: {e}")

                self.check_pending_orders(price_map)

                await asyncio.sleep(30)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Auto trading loop error: {e}")
                await asyncio.sleep(30)
