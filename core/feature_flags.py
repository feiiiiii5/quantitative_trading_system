"""
QuantCore 功能开关模块
支持运行时动态控制功能启用/禁用状态
"""
import contextlib
import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class FeatureFlag:
    """功能开关定义"""
    name: str
    description: str
    enabled: bool = True
    rollout_percentage: float = 100.0
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class FeatureFlagManager:
    """功能开关管理器"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance

    def _init(self):
        self._flags: dict[str, FeatureFlag] = {}
        self._callbacks: list[Callable[[str, bool], None]] = []
        self._lock = threading.Lock()
        self._load_default_flags()

    def _load_default_flags(self):
        """加载默认功能开关"""
        default_flags = [
            FeatureFlag(
                name="vectorized_backtest",
                description="启用向量化回测引擎",
                enabled=True,
                tags=["backtest", "performance"]
            ),
            FeatureFlag(
                name="real_time_data",
                description="启用实时数据推送",
                enabled=True,
                tags=["data", "realtime"]
            ),
            FeatureFlag(
                name="ml_factor_scoring",
                description="启用机器学习因子评分",
                enabled=True,
                tags=["ml", "factor"]
            ),
            FeatureFlag(
                name="auto_risk_management",
                description="启用自动风险管理",
                enabled=True,
                tags=["risk", "automation"]
            ),
            FeatureFlag(
                name="advanced_analytics",
                description="启用高级分析功能",
                enabled=True,
                tags=["analytics"]
            ),
            FeatureFlag(
                name="news_sentiment",
                description="启用新闻情感分析",
                enabled=True,
                tags=["news", "alternative_data"]
            ),
            FeatureFlag(
                name="walk_forward_optimization",
                description="启用滚动优化",
                enabled=True,
                tags=["optimization", "backtest"]
            ),
            FeatureFlag(
                name="monte_carlo_var",
                description="启用蒙特卡洛VaR计算",
                enabled=True,
                tags=["risk", "analytics"]
            ),
        ]
        for flag in default_flags:
            self._flags[flag.name] = flag

    def register_flag(self, name: str, description: str, enabled: bool = True, **kwargs) -> None:
        """注册新的功能开关"""
        with self._lock:
            if name in self._flags:
                logger.warning("Feature flag '%s' already exists, updating", name)
            self._flags[name] = FeatureFlag(
                name=name,
                description=description,
                enabled=enabled,
                **kwargs
            )
        self._notify_callbacks(name, enabled)

    def is_enabled(self, name: str) -> bool:
        """检查功能开关是否启用"""
        with self._lock:
            flag = self._flags.get(name)
            if flag is None:
                logger.debug("Feature flag '%s' not found, returning False", name)
                return False
            return flag.enabled

    def set_enabled(self, name: str, enabled: bool) -> None:
        """设置功能开关状态"""
        with self._lock:
            flag = self._flags.get(name)
            if flag is None:
                raise ValueError(f"Feature flag '{name}' not found")
            old_value = flag.enabled
            flag.enabled = enabled
        if old_value != enabled:
            self._notify_callbacks(name, enabled)
            logger.info("Feature flag '%s' changed from %s to %s", name, old_value, enabled)

    def toggle(self, name: str) -> bool:
        """切换功能开关状态"""
        with self._lock:
            flag = self._flags.get(name)
            if flag is None:
                raise ValueError(f"Feature flag '{name}' not found")
            flag.enabled = not flag.enabled
            new_value = flag.enabled
        self._notify_callbacks(name, new_value)
        logger.info("Feature flag '%s' toggled to %s", name, new_value)
        return new_value

    def get_flag(self, name: str) -> FeatureFlag | None:
        """获取功能开关详情"""
        with self._lock:
            return self._flags.get(name)

    def list_flags(self, tags: list[str] | None = None) -> list[FeatureFlag]:
        """列出所有功能开关"""
        with self._lock:
            flags = list(self._flags.values())
            if tags:
                flags = [f for f in flags if any(t in f.tags for t in tags)]
            return flags

    def register_callback(self, callback: Callable[[str, bool], None]) -> None:
        """注册状态变更回调"""
        with self._lock:
            self._callbacks.append(callback)

    def unregister_callback(self, callback: Callable[[str, bool], None]) -> None:
        """注销状态变更回调"""
        with self._lock, contextlib.suppress(ValueError):
            self._callbacks.remove(callback)

    def _notify_callbacks(self, name: str, enabled: bool) -> None:
        """通知所有回调"""
        for callback in self._callbacks:
            try:
                callback(name, enabled)
            except Exception as e:
                logger.error("Error in feature flag callback for '%s': %s", name, e)

    def export_flags(self) -> dict[str, dict[str, Any]]:
        """导出所有功能开关状态"""
        with self._lock:
            return {
                name: {
                    "description": flag.description,
                    "enabled": flag.enabled,
                    "rollout_percentage": flag.rollout_percentage,
                    "tags": flag.tags,
                    "metadata": flag.metadata
                }
                for name, flag in self._flags.items()
            }

    def import_flags(self, data: dict[str, dict[str, Any]]) -> None:
        """导入功能开关状态"""
        with self._lock:
            for name, info in data.items():
                if name in self._flags:
                    self._flags[name].enabled = info.get("enabled", self._flags[name].enabled)
                    if "rollout_percentage" in info:
                        self._flags[name].rollout_percentage = info["rollout_percentage"]
                    if "metadata" in info:
                        self._flags[name].metadata.update(info["metadata"])

    def reset_all(self) -> None:
        """重置所有功能开关到默认状态"""
        with self._lock:
            self._flags.clear()
        self._load_default_flags()
        logger.info("All feature flags reset to default")


def get_feature_flag_manager() -> FeatureFlagManager:
    """获取功能开关管理器实例"""
    return FeatureFlagManager()


def feature_enabled(name: str) -> bool:
    """检查功能是否启用（便捷函数）"""
    return get_feature_flag_manager().is_enabled(name)


def require_feature(name: str):
    """装饰器：要求功能开关启用"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not feature_enabled(name):
                raise RuntimeError(f"Feature '{name}' is not enabled")
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_feature_async(name: str):
    """装饰器：要求功能开关启用（异步版本）"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            if not feature_enabled(name):
                raise RuntimeError(f"Feature '{name}' is not enabled")
            return await func(*args, **kwargs)
        return wrapper
    return decorator
