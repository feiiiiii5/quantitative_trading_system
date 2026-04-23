import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

ENV_DIR = Path(os.environ.get("ENV_CONFIG_DIR", str(Path(__file__).parent.parent.parent.parent / "data" / "envs")))


@dataclass
class EnvironmentConfig:
    env_name: str
    api_keys: Dict[str, str] = field(default_factory=dict)
    database_url: str = ""
    redis_url: str = ""
    log_level: str = "INFO"
    custom_config: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        masked_keys = {k: v[:4] + "****" if len(v) > 4 else "****" for k, v in self.api_keys.items()}
        return {
            "env_name": self.env_name,
            "api_keys": list(self.api_keys.keys()),
            "database_url": self.database_url[:20] + "****" if self.database_url else "",
            "redis_url": self.redis_url[:20] + "****" if self.redis_url else "",
            "log_level": self.log_level,
            "custom_keys": list(self.custom_config.keys()),
        }


@dataclass
class PromotionChecklist:
    backtest_passed: bool = False
    stress_test_passed: bool = False
    risk_params_set: bool = False
    api_endpoints_tested: bool = False
    data_sources_verified: bool = False
    monitoring_configured: bool = False

    @property
    def all_passed(self) -> bool:
        return all([
            self.backtest_passed, self.stress_test_passed,
            self.risk_params_set, self.api_endpoints_tested,
            self.data_sources_verified, self.monitoring_configured,
        ])

    def to_dict(self) -> dict:
        return {
            "backtest_passed": self.backtest_passed,
            "stress_test_passed": self.stress_test_passed,
            "risk_params_set": self.risk_params_set,
            "api_endpoints_tested": self.api_endpoints_tested,
            "data_sources_verified": self.data_sources_verified,
            "monitoring_configured": self.monitoring_configured,
            "all_passed": self.all_passed,
        }


class EnvironmentManager:
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir) if base_dir else ENV_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._envs: Dict[str, EnvironmentConfig] = {}
        self._checklists: Dict[str, PromotionChecklist] = {}
        self._load_envs()

    def _load_envs(self):
        for env_name in ["dev", "paper", "prod"]:
            filepath = self.base_dir / f"{env_name}.json"
            if filepath.exists():
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    self._envs[env_name] = EnvironmentConfig(
                        env_name=data.get("env_name", env_name),
                        api_keys=data.get("api_keys", {}),
                        database_url=data.get("database_url", ""),
                        redis_url=data.get("redis_url", ""),
                        log_level=data.get("log_level", "INFO"),
                        custom_config=data.get("custom_config", {}),
                    )
                except Exception as e:
                    logger.debug(f"Failed to load env {env_name}: {e}")

        for env_name in ["dev", "paper", "prod"]:
            if env_name not in self._envs:
                self._envs[env_name] = EnvironmentConfig(env_name=env_name)

    def _save_env(self, env_name: str):
        config = self._envs.get(env_name)
        if not config:
            return
        filepath = self.base_dir / f"{env_name}.json"
        data = {
            "env_name": config.env_name,
            "api_keys": config.api_keys,
            "database_url": config.database_url,
            "redis_url": config.redis_url,
            "log_level": config.log_level,
            "custom_config": config.custom_config,
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_env(self, env_name: str) -> Optional[dict]:
        config = self._envs.get(env_name)
        return config.to_dict() if config else None

    def get_env_config(self, env_name: str) -> Optional[EnvironmentConfig]:
        return self._envs.get(env_name)

    def list_envs(self) -> List[dict]:
        return [config.to_dict() for config in self._envs.values()]

    def create_env(self, env_name: str, database_url: str = "", redis_url: str = "", log_level: str = "INFO") -> dict:
        if env_name in self._envs:
            return {"success": False, "error": f"环境{env_name}已存在"}
        config = EnvironmentConfig(
            env_name=env_name,
            database_url=database_url,
            redis_url=redis_url,
            log_level=log_level,
        )
        self._envs[env_name] = config
        self._save_env(env_name)
        return {"success": True, "env_name": env_name}

    def set_config(self, env_name: str, key: str, value: str) -> dict:
        config = self._envs.get(env_name)
        if not config:
            return {"success": False, "error": f"环境{env_name}不存在"}
        config.custom_config[key] = value
        self._save_env(env_name)
        return {"success": True, "env_name": env_name, "key": key}

    def update_env(self, env_name: str, updates: dict) -> bool:
        config = self._envs.get(env_name)
        if not config:
            return False

        if "api_keys" in updates:
            config.api_keys.update(updates["api_keys"])
        if "database_url" in updates:
            config.database_url = updates["database_url"]
        if "redis_url" in updates:
            config.redis_url = updates["redis_url"]
        if "log_level" in updates:
            config.log_level = updates["log_level"]
        if "custom_config" in updates:
            config.custom_config.update(updates["custom_config"])

        self._save_env(env_name)
        return True

    def load_env_vars(self, env_name: str) -> dict:
        config = self._envs.get(env_name)
        if not config:
            return {"success": False, "error": f"环境{env_name}不存在"}

        loaded = []
        for key, value in config.api_keys.items():
            os.environ[key] = value
            loaded.append(key)
        for key, value in config.custom_config.items():
            os.environ[key] = value
            loaded.append(key)
        if config.database_url:
            os.environ["DATABASE_URL"] = config.database_url
            loaded.append("DATABASE_URL")
        if config.redis_url:
            os.environ["REDIS_URL"] = config.redis_url
            loaded.append("REDIS_URL")

        return {"success": True, "env_name": env_name, "loaded_vars": loaded}

    def promote(self, from_env: str, to_env: str) -> dict:
        checklist = self._checklists.get(f"{from_env}->{to_env}", PromotionChecklist())
        if not checklist.all_passed:
            return {"success": False, "error": "预检清单未通过", "checklist": checklist.to_dict()}

        from_config = self._envs.get(from_env)
        if not from_config:
            return {"success": False, "error": f"源环境{from_env}不存在"}

        to_config = self._envs.get(to_env)
        if not to_config:
            to_config = EnvironmentConfig(env_name=to_env)

        to_config.custom_config = from_config.custom_config.copy()
        to_config.log_level = "WARNING" if to_env == "prod" else from_config.log_level

        self._envs[to_env] = to_config
        self._save_env(to_env)

        return {"success": True, "from": from_env, "to": to_env}

    def update_checklist(self, from_env: str, to_env: str, data: dict) -> dict:
        key = f"{from_env}->{to_env}"
        if key not in self._checklists:
            self._checklists[key] = PromotionChecklist()

        checklist = self._checklists[key]
        updated = []
        for item, passed in data.items():
            if hasattr(checklist, item):
                setattr(checklist, item, bool(passed))
                updated.append(item)

        return {"success": True, "updated_items": updated, "checklist": checklist.to_dict()}

    def get_checklist(self, from_env: str, to_env: str) -> dict:
        key = f"{from_env}->{to_env}"
        checklist = self._checklists.get(key, PromotionChecklist())
        return checklist.to_dict()
