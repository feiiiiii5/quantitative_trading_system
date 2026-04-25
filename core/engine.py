"""
QuantCore 异步事件总线主控引擎
"""
import asyncio
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from core.logger import logger


class EventType(Enum):
    """事件类型"""
    TICK = "tick"  # Tick数据
    BAR = "bar"  # K线数据
    ORDER = "order"  # 订单事件
    FILL = "fill"  # 成交事件
    SIGNAL = "signal"  # 策略信号
    RISK_ALERT = "risk_alert"  # 风控告警
    MARKET_REGIME = "market_regime"  # 市场状态变化
    PORTFOLIO_UPDATE = "portfolio_update"  # 组合更新
    SYSTEM = "system"  # 系统事件


@dataclass
class Event:
    """事件对象"""
    type: EventType
    timestamp: datetime
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = ""
    priority: int = 0  # 优先级，数字越小优先级越高


class EventBus:
    """
    异步事件总线
    支持发布-订阅模式，处理所有模块间通信
    """

    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {et: [] for et in EventType}
        self._event_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._metrics: Dict[str, int] = {"published": 0, "processed": 0, "dropped": 0}

    async def start(self):
        """启动事件总线"""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._process_events())
        logger.info("事件总线已启动")

    async def stop(self):
        """停止事件总线"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("事件总线已停止")

    def subscribe(self, event_type: EventType, handler: Callable[[Event], Any]):
        """订阅事件"""
        if handler not in self._subscribers[event_type]:
            self._subscribers[event_type].append(handler)
            logger.debug(f"订阅事件: {event_type.value}, 处理器: {handler.__name__}")

    def unsubscribe(self, event_type: EventType, handler: Callable[[Event], Any]):
        """取消订阅"""
        if handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)

    async def publish(self, event: Event):
        """发布事件到队列"""
        if not self._running:
            logger.warning("事件总线未运行，事件被丢弃")
            self._metrics["dropped"] += 1
            return

        # 使用优先级队列: (priority, timestamp, event)
        await self._event_queue.put((event.priority, event.timestamp.timestamp(), event))
        self._metrics["published"] += 1

    async def publish_immediate(self, event: Event):
        """立即处理事件（不经过队列）"""
        await self._dispatch(event)

    async def _process_events(self):
        """事件处理循环"""
        while self._running:
            try:
                # 等待事件，超时1秒检查running状态
                priority, ts, event = await asyncio.wait_for(
                    self._event_queue.get(), timeout=1.0
                )
                await self._dispatch(event)
                self._metrics["processed"] += 1
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"事件处理错误: {e}")

    async def _dispatch(self, event: Event):
        """分发事件到所有订阅者"""
        handlers = self._subscribers.get(event.type, [])
        if not handlers:
            return

        # 并行调用所有处理器
        tasks = []
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    tasks.append(handler(event))
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"事件处理器错误 [{handler.__name__}]: {e}")

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def get_metrics(self) -> Dict[str, int]:
        """获取事件统计"""
        return self._metrics.copy()


class Clock:
    """
    统一时钟系统
    支持实盘时间和回测时间
    """

    def __init__(self):
        self._backtest_mode = False
        self._current_time: Optional[datetime] = None
        self._speed: float = 1.0  # 回测速度倍率

    def set_backtest_mode(self, start_time: datetime, speed: float = 1.0):
        """设置回测模式"""
        self._backtest_mode = True
        self._current_time = start_time
        self._speed = speed

    def set_realtime_mode(self):
        """设置实盘模式"""
        self._backtest_mode = False
        self._current_time = None

    def now(self) -> datetime:
        """获取当前时间"""
        if self._backtest_mode:
            return self._current_time or datetime.now()
        return datetime.now()

    def tick(self, delta: Optional[Any] = None):
        """回测时间推进"""
        if self._backtest_mode and self._current_time:
            from datetime import timedelta
            self._current_time += delta or timedelta(seconds=1)

    def is_backtest(self) -> bool:
        """是否回测模式"""
        return self._backtest_mode


# 全局事件总线实例
event_bus = EventBus()


def get_event_bus() -> EventBus:
    """获取事件总线实例"""
    return event_bus
