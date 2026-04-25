"""
QuantCore 策略抽象基类
所有策略必须继承此类
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class SignalType(Enum):
    """信号类型"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE = "close"


@dataclass
class Signal:
    """交易信号"""
    type: SignalType
    symbol: str
    strength: float = 0.0  # 信号强度 0-100
    reason: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Bar:
    """K线数据"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float = 0.0


@dataclass
class Tick:
    """Tick数据"""
    symbol: str
    timestamp: datetime
    price: float
    volume: int
    bid: float = 0.0
    ask: float = 0.0


@dataclass
class Fill:
    """成交记录"""
    order_id: str
    symbol: str
    side: str
    price: float
    quantity: int
    timestamp: datetime
    commission: float = 0.0


class Strategy(ABC):
    """
    策略抽象基类
    所有自定义策略必须继承此类并实现相关方法
    """

    # 策略参数 - 子类可覆盖
    params: Dict[str, Any] = field(default_factory=dict)

    # 策略元数据
    name: str = "BaseStrategy"
    description: str = ""
    version: str = "1.0.0"
    author: str = ""
    risk_level: str = "medium"  # low/medium/high
    supported_markets: List[str] = field(default_factory=lambda: ["A"])

    def __init__(self, **kwargs):
        """初始化策略"""
        self.params.update(kwargs)
        self._initialized = False
        self._data_buffer: List[Bar] = []
        self._max_buffer_size = 1000

    async def initialize(self):
        """策略初始化 - 可覆盖"""
        self._initialized = True

    async def on_bar(self, bar: Bar) -> Optional[Signal]:
        """
        K线回调 - 必须实现
        每根K线触发一次
        """
        # 维护数据缓冲区
        self._data_buffer.append(bar)
        if len(self._data_buffer) > self._max_buffer_size:
            self._data_buffer.pop(0)
        return None

    async def on_tick(self, tick: Tick) -> Optional[Signal]:
        """
        Tick回调 - 可选实现
        每个Tick触发一次（实盘模式）
        """
        return None

    async def on_fill(self, fill: Fill):
        """
        成交回调 - 可选实现
        订单成交时触发
        """
        pass

    async def on_market_regime_change(self, regime: str):
        """
        市场状态变化回调 - 可选实现
        regime: bull/bear/sideways
        """
        pass

    def get_param(self, key: str, default=None):
        """获取策略参数"""
        return self.params.get(key, default)

    def set_param(self, key: str, value: Any):
        """设置策略参数"""
        self.params[key] = value

    def get_indicators(self) -> Dict[str, Any]:
        """
        获取策略指标 - 用于前端展示
        返回Dict，key为指标名，value为指标值
        """
        return {}

    def get_state(self) -> Dict[str, Any]:
        """获取策略状态"""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "risk_level": self.risk_level,
            "params": self.params,
            "initialized": self._initialized,
        }

    def reset(self):
        """重置策略状态"""
        self._data_buffer.clear()
        self._initialized = False


class PortfolioStrategy(ABC):
    """
    组合策略基类
    用于多因子选股和组合优化
    """

    name: str = "BasePortfolio"
    description: str = ""

    def __init__(self, **kwargs):
        self.params = kwargs
        self._holdings: Dict[str, float] = {}  # 目标权重

    @abstractmethod
    async def generate_weights(self, universe: List[str], data: Dict[str, Any]) -> Dict[str, float]:
        """
        生成目标权重
        返回: {symbol: weight}
        """
        pass

    def get_holdings(self) -> Dict[str, float]:
        """获取当前目标持仓权重"""
        return self._holdings.copy()


class ExecutionStrategy(ABC):
    """
    执行策略基类
    用于订单执行算法（TWAP/VWAP等）
    """

    name: str = "BaseExecution"

    @abstractmethod
    async def execute(self, order: Dict[str, Any], market_data: Any) -> List[Dict]:
        """
        执行订单
        返回: 子订单列表
        """
        pass
