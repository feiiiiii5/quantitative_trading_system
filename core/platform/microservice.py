import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    DEGRADED = "degraded"
    FAILED = "failed"
    RESTARTING = "restarting"


class MessageType(Enum):
    REQUEST = "request"
    RESPONSE = "response"
    EVENT = "event"
    COMMAND = "command"


@dataclass
class ServiceEndpoint:
    name: str
    host: str = "localhost"
    port: int = 8000
    protocol: str = "http"
    health_path: str = "/health"

    @property
    def base_url(self) -> str:
        return f"{self.protocol}://{self.host}:{self.port}"


@dataclass
class ServiceInfo:
    name: str
    endpoint: ServiceEndpoint
    status: ServiceStatus = ServiceStatus.STOPPED
    dependencies: List[str] = field(default_factory=list)
    restart_count: int = 0
    max_restarts: int = 5
    last_heartbeat: float = 0.0
    health_check_interval: float = 10.0
    metadata: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "endpoint": {
                "name": self.endpoint.name,
                "host": self.endpoint.host,
                "port": self.endpoint.port,
                "protocol": self.endpoint.protocol,
                "base_url": self.endpoint.base_url,
            },
            "status": self.status.value,
            "dependencies": self.dependencies,
            "restart_count": self.restart_count,
            "last_heartbeat": self.last_heartbeat,
            "metadata": self.metadata,
        }


@dataclass
class Message:
    msg_id: str
    msg_type: MessageType
    source: str
    target: str
    topic: str = ""
    payload: Any = None
    timestamp: float = field(default_factory=time.time)
    correlation_id: str = ""

    def to_dict(self) -> dict:
        return {
            "msg_id": self.msg_id,
            "msg_type": self.msg_type.value,
            "source": self.source,
            "target": self.target,
            "topic": self.topic,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
        }


class ServiceRegistry:
    def __init__(self):
        self._services: Dict[str, ServiceInfo] = {}
        self._message_handlers: Dict[str, List[Callable]] = {}
        self._message_log: List[Message] = []
        self._max_log_size = 10000

    def register(self, service: ServiceInfo) -> dict:
        if service.name in self._services:
            return {"code": 1, "data": None, "msg": f"服务{service.name}已注册"}
        self._services[service.name] = service
        logger.info(f"服务注册: {service.name} -> {service.endpoint.base_url}")
        return {"code": 0, "data": service.to_dict(), "msg": "注册成功"}

    def deregister(self, name: str) -> dict:
        if name not in self._services:
            return {"code": 1, "data": None, "msg": f"服务{name}未注册"}
        del self._services[name]
        return {"code": 0, "data": None, "msg": "注销成功"}

    def get_service(self, name: str) -> Optional[ServiceInfo]:
        return self._services.get(name)

    def list_services(self) -> List[dict]:
        return [s.to_dict() for s in self._services.values()]

    def update_status(self, name: str, status: ServiceStatus) -> dict:
        svc = self._services.get(name)
        if not svc:
            return {"code": 1, "data": None, "msg": f"服务{name}未注册"}
        svc.status = status
        svc.last_heartbeat = time.time()
        return {"code": 0, "data": svc.to_dict(), "msg": "状态已更新"}

    def subscribe(self, topic: str, handler: Callable) -> dict:
        if topic not in self._message_handlers:
            self._message_handlers[topic] = []
        self._message_handlers[topic].append(handler)
        return {"code": 0, "data": {"topic": topic}, "msg": "订阅成功"}

    def publish(self, message: Message) -> dict:
        self._message_log.append(message)
        if len(self._message_log) > self._max_log_size:
            self._message_log = self._message_log[-self._max_log_size:]

        handlers = self._message_handlers.get(message.topic, [])
        for handler in handlers:
            try:
                handler(message)
            except Exception as e:
                logger.error(f"消息处理错误: topic={message.topic}, error={e}")

        return {"code": 0, "data": {"delivered": len(handlers)}, "msg": "消息已发布"}

    def get_message_log(self, topic: str = "", limit: int = 100) -> List[dict]:
        logs = self._message_log
        if topic:
            logs = [m for m in logs if m.topic == topic]
        return [m.to_dict() for m in logs[-limit:]]


class MicroserviceManager:
    def __init__(self):
        self.registry = ServiceRegistry()
        self._health_task: Optional[asyncio.Task] = None
        self._running = False
        self._init_default_services()

    def _init_default_services(self):
        default_services = [
            ServiceInfo(
                name="data-service",
                endpoint=ServiceEndpoint(name="data", port=8001),
                dependencies=[],
            ),
            ServiceInfo(
                name="backtest-service",
                endpoint=ServiceEndpoint(name="backtest", port=8002),
                dependencies=["data-service"],
            ),
            ServiceInfo(
                name="execution-service",
                endpoint=ServiceEndpoint(name="execution", port=8003),
                dependencies=["data-service"],
            ),
            ServiceInfo(
                name="risk-service",
                endpoint=ServiceEndpoint(name="risk", port=8004),
                dependencies=["data-service", "execution-service"],
            ),
            ServiceInfo(
                name="strategy-service",
                endpoint=ServiceEndpoint(name="strategy", port=8005),
                dependencies=["data-service", "backtest-service"],
            ),
            ServiceInfo(
                name="monitor-service",
                endpoint=ServiceEndpoint(name="monitor", port=8006),
                dependencies=[],
            ),
            ServiceInfo(
                name="ai-service",
                endpoint=ServiceEndpoint(name="ai", port=8007),
                dependencies=["data-service"],
            ),
            ServiceInfo(
                name="platform-service",
                endpoint=ServiceEndpoint(name="platform", port=8008),
                dependencies=[],
            ),
        ]
        for svc in default_services:
            self.registry.register(svc)

    async def start(self) -> dict:
        self._running = True
        for name, svc in self.registry._services.items():
            deps_ok = all(
                self.registry.get_service(d) and
                self.registry.get_service(d).status in (ServiceStatus.RUNNING, ServiceStatus.DEGRADED)
                for d in svc.dependencies
            )
            if deps_ok or not svc.dependencies:
                svc.status = ServiceStatus.RUNNING
            else:
                svc.status = ServiceStatus.STOPPED
            svc.last_heartbeat = time.time()

        self._health_task = asyncio.create_task(self._health_check_loop())
        return {"code": 0, "data": {"services": len(self.registry._services)}, "msg": "微服务管理器已启动"}

    async def stop(self) -> dict:
        self._running = False
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
        for svc in self.registry._services.values():
            svc.status = ServiceStatus.STOPPED
        return {"code": 0, "data": None, "msg": "微服务管理器已停止"}

    async def _health_check_loop(self):
        while self._running:
            try:
                await asyncio.sleep(10)
                for name, svc in self.registry._services.items():
                    if svc.status == ServiceStatus.RUNNING:
                        elapsed = time.time() - svc.last_heartbeat
                        if elapsed > svc.health_check_interval * 3:
                            logger.warning(f"服务{name}心跳超时，标记为DEGRADED")
                            svc.status = ServiceStatus.DEGRADED
                    elif svc.status == ServiceStatus.FAILED:
                        if svc.restart_count < svc.max_restarts:
                            svc.status = ServiceStatus.RESTARTING
                            svc.restart_count += 1
                            logger.info(f"服务{name}自动重启({svc.restart_count}/{svc.max_restarts})")
                            await asyncio.sleep(2)
                            svc.status = ServiceStatus.RUNNING
                            svc.last_heartbeat = time.time()
                        else:
                            logger.error(f"服务{name}重启次数超限，保持FAILED")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"健康检查异常: {e}")

    def heartbeat(self, service_name: str) -> dict:
        svc = self.registry.get_service(service_name)
        if not svc:
            return {"code": 1, "data": None, "msg": f"服务{service_name}未注册"}
        svc.last_heartbeat = time.time()
        if svc.status in (ServiceStatus.DEGRADED, ServiceStatus.RESTARTING):
            svc.status = ServiceStatus.RUNNING
        return {"code": 0, "data": {"status": svc.status.value}, "msg": "心跳已更新"}

    def get_topology(self) -> dict:
        nodes = []
        edges = []
        for name, svc in self.registry._services.items():
            nodes.append({
                "id": name,
                "status": svc.status.value,
                "port": svc.endpoint.port,
            })
            for dep in svc.dependencies:
                edges.append({"source": dep, "target": name})
        return {"code": 0, "data": {"nodes": nodes, "edges": edges}, "msg": ""}

    def get_status(self) -> dict:
        services = self.registry.list_services()
        running = sum(1 for s in services if s["status"] == "running")
        return {
            "code": 0,
            "data": {
                "total": len(services),
                "running": running,
                "stopped": sum(1 for s in services if s["status"] == "stopped"),
                "degraded": sum(1 for s in services if s["status"] == "degraded"),
                "failed": sum(1 for s in services if s["status"] == "failed"),
                "services": services,
            },
            "msg": "",
        }

    def send_message(self, source: str, target: str, topic: str, payload: Any) -> dict:
        msg_id = f"{source}-{int(time.time()*1000)}"
        message = Message(
            msg_id=msg_id,
            msg_type=MessageType.EVENT,
            source=source,
            target=target,
            topic=topic,
            payload=payload,
        )
        return self.registry.publish(message)

    def get_message_log(self, topic: str = "", limit: int = 100) -> dict:
        logs = self.registry.get_message_log(topic, limit)
        return {"code": 0, "data": logs, "msg": ""}
