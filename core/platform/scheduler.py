import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class ScheduledTask:
    task_id: str
    name: str
    func: Optional[Callable] = None
    cron: str = ""
    interval_seconds: float = 0.0
    next_run: float = 0.0
    last_run: float = 0.0
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: float = 300.0
    dependencies: List[str] = field(default_factory=list)
    result: Optional[dict] = None
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id, "name": self.name,
            "cron": self.cron, "interval_seconds": self.interval_seconds,
            "next_run": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.next_run)) if self.next_run > 0 else "",
            "last_run": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.last_run)) if self.last_run > 0 else "",
            "status": self.status.value,
            "retry_count": self.retry_count, "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds,
            "dependencies": self.dependencies,
            "error": self.error,
        }


class TaskScheduler:
    def __init__(self):
        self._tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._task_counter = 0

    def add_task(
        self,
        name: str,
        func: Optional[Callable] = None,
        cron: str = "",
        interval_seconds: float = 0.0,
        max_retries: int = 3,
        timeout_seconds: float = 300.0,
        dependencies: Optional[List[str]] = None,
    ) -> str:
        self._task_counter += 1
        task_id = f"task_{self._task_counter:04d}"
        next_run = time.time() + interval_seconds if interval_seconds > 0 else time.time()

        task = ScheduledTask(
            task_id=task_id, name=name, func=func,
            cron=cron, interval_seconds=interval_seconds,
            next_run=next_run, max_retries=max_retries,
            timeout_seconds=timeout_seconds,
            dependencies=dependencies or [],
        )
        self._tasks[task_id] = task
        return task_id

    def remove_task(self, task_id: str) -> dict:
        if task_id in self._tasks:
            del self._tasks[task_id]
            return {"success": True, "task_id": task_id, "msg": "任务已删除"}
        return {"success": False, "task_id": task_id, "error": "任务不存在"}

    async def run_task(self, task_id: str) -> dict:
        task = self._tasks.get(task_id)
        if not task:
            return {"success": False, "error": "任务不存在"}

        deps_ok = True
        for dep_id in task.dependencies:
            dep = self._tasks.get(dep_id)
            if not dep or dep.status != TaskStatus.COMPLETED:
                deps_ok = False
                break

        if not deps_ok:
            return {"success": False, "error": "依赖任务未完成"}

        task.status = TaskStatus.RUNNING
        task.last_run = time.time()

        if task.func:
            try:
                if asyncio.iscoroutinefunction(task.func):
                    result = await asyncio.wait_for(
                        task.func(), timeout=task.timeout_seconds,
                    )
                else:
                    loop = asyncio.get_event_loop()
                    result = await asyncio.wait_for(
                        loop.run_in_executor(None, task.func),
                        timeout=task.timeout_seconds,
                    )
                task.status = TaskStatus.COMPLETED
                task.result = result if isinstance(result, dict) else {"result": str(result)}
                return {"success": True, "task_id": task_id, "result": task.result}
            except asyncio.TimeoutError:
                task.status = TaskStatus.TIMEOUT
                task.error = "任务超时"
                return {"success": False, "error": "任务超时"}
            except Exception as e:
                task.retry_count += 1
                if task.retry_count < task.max_retries:
                    task.status = TaskStatus.PENDING
                    task.next_run = time.time() + 5
                    return {"success": False, "error": str(e), "will_retry": True}
                else:
                    task.status = TaskStatus.FAILED
                    task.error = str(e)
                    return {"success": False, "error": str(e)}
        else:
            task.status = TaskStatus.COMPLETED
            return {"success": True, "task_id": task_id}

    async def run_pending(self):
        now = time.time()
        for task_id, task in self._tasks.items():
            if task.status == TaskStatus.PENDING and task.next_run <= now:
                await self.run_task(task_id)

    def list_tasks(self) -> List[dict]:
        return [t.to_dict() for t in self._tasks.values()]

    def get_tasks(self) -> List[dict]:
        return self.list_tasks()

    def get_task(self, task_id: str) -> Optional[dict]:
        task = self._tasks.get(task_id)
        return task.to_dict() if task else None

    def get_task_status(self, task_id: str) -> Optional[dict]:
        return self.get_task(task_id)

    def reset_task(self, task_id: str) -> dict:
        task = self._tasks.get(task_id)
        if task:
            task.status = TaskStatus.PENDING
            task.retry_count = 0
            task.error = ""
            task.next_run = time.time()
            return {"success": True, "task_id": task_id, "status": "pending"}
        return {"success": False, "task_id": task_id, "error": "任务不存在"}
