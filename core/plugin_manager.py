import importlib
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass
class PluginInfo:
    name: str
    version: str
    strategy_class: type
    source: str
    loaded_at: float
    enabled: bool = True
    health_status: str = "unknown"
    last_error: str | None = None
    load_time_ms: float | None = None


@dataclass
class PluginHealthReport:
    total_plugins: int
    healthy: int
    degraded: int
    failed: int
    plugins: list[dict]


class PluginManager:
    _instance: "PluginManager | None" = None

    def __init__(self, plugin_dirs: list[str] | None = None):
        self._plugins: dict[str, PluginInfo] = {}
        self._plugin_dirs = plugin_dirs or []
        self._class_registry: dict[str, type] = {}
        self._lock = __import__("threading").Lock()
        self._discovery_cache: dict[str, list[str]] = {}
        self._cache_ttl = 300.0
        self._last_discovery = 0.0
        self._static_strategy_classes: dict[str, type] = {}
        self._initialized = False

    @classmethod
    def get_instance(cls) -> "PluginManager":
        if cls._instance is None:
            cls._instance = PluginManager()
        return cls._instance

    def register_static_strategy(self, name: str, strategy_class: type) -> None:
        self._static_strategy_classes[name] = strategy_class

    def register_from_registry(self, registry: dict) -> None:
        for name, cls in registry.items():
            self._static_strategy_classes[name] = cls
            self._class_registry[name] = cls
            self._plugins[name] = PluginInfo(
                name=name,
                version="1.0.0",
                strategy_class=cls,
                source="static_registry",
                loaded_at=time.time(),
                enabled=True,
                health_status="healthy",
            )

    def discover_plugins(self) -> list[str]:
        now = time.monotonic()
        if now - self._last_discovery < self._cache_ttl and self._discovery_cache:
            return list(self._discovery_cache.keys())

        discovered: list[str] = []
        for plugin_dir in self._plugin_dirs:
            try:
                dir_path = Path(plugin_dir)
                if not dir_path.exists():
                    continue
                for py_file in dir_path.glob("strategy_*.py"):
                    if py_file.stem.startswith("_"):
                        continue
                    discovered.append(str(py_file))
            except Exception as e:
                logger.warning("Plugin discovery failed for %s: %s", plugin_dir, e)

        self._discovery_cache = {p: p for p in discovered}
        self._last_discovery = now
        return discovered

    def load_plugin_from_path(self, path: str) -> PluginInfo | None:
        path_obj = Path(path)
        module_name = f"plugins.{path_obj.stem}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, path_obj)
            if spec is None or spec.loader is None:
                return None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            strategy_class = self._extract_strategy_class(module)
            if strategy_class is None:
                return None
            name = getattr(strategy_class, "name", path_obj.stem)
            version = getattr(strategy_class, "version", "1.0.0")
            plugin_info = PluginInfo(
                name=name,
                version=version,
                strategy_class=strategy_class,
                source=path,
                loaded_at=time.time(),
                enabled=True,
                health_status="healthy",
            )
            with self._lock:
                self._plugins[name] = plugin_info
                self._class_registry[name] = strategy_class
            logger.info("Loaded plugin: %s v%s from %s", name, version, path)
            return plugin_info
        except Exception as e:
            logger.error("Failed to load plugin from %s: %s", path, e)
            return None

    def _extract_strategy_class(self, module) -> type | None:
        for attr_name in dir(module):
            if attr_name.startswith("_"):
                continue
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and hasattr(attr, "generate_signals") and attr_name not in ("BaseStrategy",):
                    return attr
        return None

    def get_strategy_class(self, name: str) -> type | None:
        if name in self._class_registry:
            return self._class_registry[name]
        if name in self._static_strategy_classes:
            return self._static_strategy_classes[name]
        return None

    def list_plugins(self) -> list[dict]:
        result = []
        for _name, info in self._plugins.items():
            result.append({
                "name": info.name,
                "version": info.version,
                "source": info.source,
                "enabled": info.enabled,
                "health": info.health_status,
                "loaded_at": info.loaded_at,
                "last_error": info.last_error,
            })
        for name, _cls in self._static_strategy_classes.items():
            if name not in self._plugins:
                result.append({
                    "name": name,
                    "version": "1.0.0",
                    "source": "static_registry",
                    "enabled": True,
                    "health": "healthy",
                    "loaded_at": time.time(),
                    "last_error": None,
                })
        return result

    def get_health_report(self) -> PluginHealthReport:
        plugins = []
        healthy = degraded = failed = 0
        for name, info in self._plugins.items():
            status = info.health_status
            if status == "healthy":
                healthy += 1
            elif status == "degraded":
                degraded += 1
            else:
                failed += 1
            plugins.append({
                "name": name,
                "version": info.version,
                "health": status,
                "last_error": info.last_error,
                "enabled": info.enabled,
            })
        for name in self._static_strategy_classes:
            if name not in self._plugins:
                plugins.append({
                    "name": name,
                    "version": "1.0.0",
                    "health": "healthy",
                    "last_error": None,
                    "enabled": True,
                })
                healthy += 1
        return PluginHealthReport(
            total_plugins=len(plugins),
            healthy=healthy,
            degraded=degraded,
            failed=failed,
            plugins=plugins,
        )

    def reload_plugin(self, name: str) -> bool:
        with self._lock:
            if name in self._plugins:
                old_info = self._plugins[name]
                if old_info.source.startswith("plugins."):
                    return False
                old_info.health_status = "reloading"
        if name in self._plugins:
            old_info = self._plugins[name]
            plugin_info = self.load_plugin_from_path(old_info.source)
            return plugin_info is not None
        return False

    def validate_plugin_interface(self, strategy_class: type) -> tuple[bool, list[str]]:
        errors = []
        required_methods = ["generate_signals"]
        for method in required_methods:
            if not hasattr(strategy_class, method):
                errors.append(f"Missing required method: {method}")
        required_attrs = ["name"]
        for attr in required_attrs:
            if not hasattr(strategy_class, attr):
                errors.append(f"Missing required attribute: {attr}")
        return len(errors) == 0, errors

    def __len__(self) -> int:
        return len(self._class_registry) + len(self._static_strategy_classes)

    def get_all_strategy_names(self) -> list[str]:
        names = set(self._static_strategy_classes.keys()) | set(self._class_registry.keys())
        return sorted(names)
