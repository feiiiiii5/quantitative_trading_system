import asyncio
import logging
import time
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"


@dataclass
class StreamMessage:
    symbol: str
    data: dict
    timestamp: float = 0.0
    seq: int = 0
    source: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Subscription:
    symbol: str
    callback: Optional[Callable] = None
    last_seq: int = 0
    last_update: float = 0.0
    msg_count: int = 0


class ReconnectPolicy:
    def __init__(self, base_delay: float = 1.0, max_delay: float = 60.0, multiplier: float = 2.0):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self._current_delay = base_delay
        self._attempt = 0

    def next_delay(self) -> float:
        delay = min(self.base_delay * (self.multiplier ** self._attempt), self.max_delay)
        self._attempt += 1
        return delay

    def reset(self):
        self._attempt = 0
        self._current_delay = self.base_delay


class RealtimeStreamManager:
    def __init__(self, max_subscriptions: int = 1000):
        self._subscriptions: Dict[str, Subscription] = {}
        self._state = ConnectionState.DISCONNECTED
        self._reconnect_policy = ReconnectPolicy()
        self._seq_counter = 0
        self._heartbeat_interval = 30.0
        self._last_heartbeat = 0.0
        self._max_subscriptions = max_subscriptions
        self._message_queue: asyncio.Queue = asyncio.Queue(maxsize=10000)
        self._callbacks: List[Callable] = []
        self._running = False
        self._tasks: List[asyncio.Task] = []
        self._missed_messages: Dict[str, int] = {}

    @property
    def state(self) -> ConnectionState:
        return self._state

    def subscribe(self, symbol: str, callback: Optional[Callable] = None) -> bool:
        if len(self._subscriptions) >= self._max_subscriptions:
            logger.warning(f"Max subscriptions ({self._max_subscriptions}) reached")
            return False
        if symbol in self._subscriptions:
            if callback:
                self._subscriptions[symbol].callback = callback
            return True
        self._subscriptions[symbol] = Subscription(symbol=symbol, callback=callback)
        logger.info(f"Subscribed to {symbol}, total: {len(self._subscriptions)}")
        return True

    def unsubscribe(self, symbol: str):
        if symbol in self._subscriptions:
            del self._subscriptions[symbol]
            logger.info(f"Unsubscribed from {symbol}")

    def add_global_callback(self, callback: Callable):
        self._callbacks.append(callback)

    def remove_global_callback(self, callback: Callable):
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    async def push_data(self, symbol: str, data: dict, source: str = ""):
        if symbol not in self._subscriptions:
            return

        self._seq_counter += 1
        msg = StreamMessage(
            symbol=symbol, data=data,
            timestamp=time.time(), seq=self._seq_counter,
            source=source,
        )

        sub = self._subscriptions[symbol]
        if sub.last_seq > 0 and msg.seq > sub.last_seq + 1:
            gap = msg.seq - sub.last_seq - 1
            self._missed_messages[symbol] = self._missed_messages.get(symbol, 0) + gap
            logger.warning(f"Message gap detected for {symbol}: {gap} messages missed")

        sub.last_seq = msg.seq
        sub.last_update = time.time()
        sub.msg_count += 1

        try:
            self._message_queue.put_nowait(msg)
        except asyncio.QueueFull:
            logger.warning("Message queue full, dropping oldest")
            try:
                self._message_queue.get_nowait()
                self._message_queue.put_nowait(msg)
            except asyncio.QueueEmpty:
                pass

        if sub.callback:
            try:
                if asyncio.iscoroutinefunction(sub.callback):
                    await sub.callback(msg)
                else:
                    sub.callback(msg)
            except Exception as e:
                logger.debug(f"Callback error for {symbol}: {e}")

        for cb in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(msg)
                else:
                    cb(msg)
            except Exception as e:
                logger.debug(f"Global callback error: {e}")

    async def _dispatch_loop(self):
        while self._running:
            try:
                await asyncio.wait_for(self._message_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except Exception:
                continue

    async def _heartbeat_loop(self):
        while self._running:
            await asyncio.sleep(self._heartbeat_interval)
            now = time.time()
            stale_symbols = []
            for symbol, sub in self._subscriptions.items():
                if now - sub.last_update > self._heartbeat_interval * 2:
                    stale_symbols.append(symbol)
            for symbol in stale_symbols:
                logger.warning(f"Heartbeat timeout for {symbol}")

    async def start(self):
        if self._running:
            return
        self._running = True
        self._state = ConnectionState.CONNECTED
        self._reconnect_policy.reset()
        self._tasks.append(asyncio.create_task(self._dispatch_loop()))
        self._tasks.append(asyncio.create_task(self._heartbeat_loop()))
        logger.info("RealtimeStreamManager started")

    async def stop(self):
        self._running = False
        self._state = ConnectionState.DISCONNECTED
        for task in self._tasks:
            task.cancel()
        self._tasks.clear()
        logger.info("RealtimeStreamManager stopped")

    async def _reconnect(self):
        self._state = ConnectionState.RECONNECTING
        while self._running:
            delay = self._reconnect_policy.next_delay()
            logger.info(f"Reconnecting in {delay:.1f}s...")
            await asyncio.sleep(delay)
            try:
                self._state = ConnectionState.CONNECTED
                self._reconnect_policy.reset()
                logger.info("Reconnected successfully")
                return
            except Exception as e:
                logger.error(f"Reconnect failed: {e}")

    def get_status(self) -> dict:
        return {
            "state": self._state.value,
            "subscriptions": len(self._subscriptions),
            "max_subscriptions": self._max_subscriptions,
            "total_messages": self._seq_counter,
            "missed_messages": dict(self._missed_messages),
            "queue_size": self._message_queue.qsize(),
            "symbols": list(self._subscriptions.keys()),
        }

    def get_subscription_info(self, symbol: str) -> Optional[dict]:
        sub = self._subscriptions.get(symbol)
        if not sub:
            return None
        return {
            "symbol": sub.symbol,
            "last_seq": sub.last_seq,
            "last_update": sub.last_update,
            "msg_count": sub.msg_count,
            "has_callback": sub.callback is not None,
        }

    def get_all_subscriptions(self) -> List[dict]:
        return [
            {
                "symbol": sub.symbol,
                "last_seq": sub.last_seq,
                "last_update": sub.last_update,
                "msg_count": sub.msg_count,
            }
            for sub in self._subscriptions.values()
        ]
