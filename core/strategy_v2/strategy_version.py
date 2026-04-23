import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

VERSION_DIR = Path(os.environ.get("STRATEGY_VERSION_DIR", str(Path(__file__).parent.parent.parent / "data" / "strategy_versions")))


@dataclass
class StrategyVersion:
    strategy_name: str
    version_id: str
    params: dict
    code_hash: str = ""
    commit_message: str = ""
    author: str = ""
    status: str = "draft"
    created_at: str = ""
    backtest_summary: dict = field(default_factory=dict)
    parent_version: str = ""

    def to_dict(self) -> dict:
        return {
            "strategy_name": self.strategy_name,
            "version_id": self.version_id,
            "params": self.params,
            "code_hash": self.code_hash,
            "commit_message": self.commit_message,
            "author": self.author,
            "status": self.status,
            "created_at": self.created_at,
            "backtest_summary": self.backtest_summary,
            "parent_version": self.parent_version,
        }


class StrategyVersionControl:
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir) if base_dir else VERSION_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._versions: Dict[str, List[StrategyVersion]] = {}
        self._load_versions()

    def _load_versions(self):
        for strategy_dir in self.base_dir.iterdir():
            if strategy_dir.is_dir():
                name = strategy_dir.name
                self._versions[name] = []
                for f in sorted(strategy_dir.glob("v_*.json")):
                    try:
                        with open(f, "r", encoding="utf-8") as fh:
                            data = json.load(fh)
                        self._versions[name].append(StrategyVersion(**data))
                    except Exception as e:
                        logger.debug(f"Failed to load version {f}: {e}")

    def _save_version(self, version: StrategyVersion):
        strategy_dir = self.base_dir / version.strategy_name
        strategy_dir.mkdir(parents=True, exist_ok=True)
        filepath = strategy_dir / f"v_{version.version_id}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(version.to_dict(), f, ensure_ascii=False, indent=2)

    def commit(
        self,
        strategy_name: str,
        params: dict,
        commit_message: str = "",
        author: str = "",
        backtest_summary: Optional[dict] = None,
    ) -> StrategyVersion:
        if strategy_name not in self._versions:
            self._versions[strategy_name] = []

        version_num = len(self._versions[strategy_name]) + 1
        version_id = f"{version_num:04d}"

        parent = ""
        if self._versions[strategy_name]:
            parent = self._versions[strategy_name][-1].version_id

        code_hash = self._simple_hash(str(params))

        version = StrategyVersion(
            strategy_name=strategy_name,
            version_id=version_id,
            params=params,
            code_hash=code_hash,
            commit_message=commit_message,
            author=author,
            status="draft",
            created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            backtest_summary=backtest_summary or {},
            parent_version=parent,
        )

        self._versions[strategy_name].append(version)
        self._save_version(version)
        return version

    def get_versions(self, strategy_name: str) -> List[dict]:
        versions = self._versions.get(strategy_name, [])
        return [v.to_dict() for v in versions]

    def get_version(self, strategy_name: str, version_id: str) -> Optional[dict]:
        for v in self._versions.get(strategy_name, []):
            if v.version_id == version_id:
                return v.to_dict()
        return None

    def get_latest(self, strategy_name: str) -> Optional[dict]:
        versions = self._versions.get(strategy_name, [])
        return versions[-1].to_dict() if versions else None

    def diff_versions(self, strategy_name: str, v1: str, v2: str) -> dict:
        ver1 = None
        ver2 = None
        for v in self._versions.get(strategy_name, []):
            if v.version_id == v1:
                ver1 = v
            if v.version_id == v2:
                ver2 = v

        if not ver1 or not ver2:
            return {"error": "版本未找到"}

        params_diff = {}
        all_keys = set(list(ver1.params.keys()) + list(ver2.params.keys()))
        for key in all_keys:
            val1 = ver1.params.get(key)
            val2 = ver2.params.get(key)
            if val1 != val2:
                params_diff[key] = {"from": val1, "to": val2}

        bt_diff = {}
        if ver1.backtest_summary and ver2.backtest_summary:
            for key in set(list(ver1.backtest_summary.keys()) + list(ver2.backtest_summary.keys())):
                v1_val = ver1.backtest_summary.get(key)
                v2_val = ver2.backtest_summary.get(key)
                if v1_val != v2_val:
                    bt_diff[key] = {"from": v1_val, "to": v2_val}

        return {
            "version_from": v1,
            "version_to": v2,
            "params_diff": params_diff,
            "backtest_diff": bt_diff,
        }

    def update_status(self, strategy_name: str, version_id: str, status: str) -> bool:
        valid_statuses = ["draft", "review", "live", "archived"]
        if status not in valid_statuses:
            return False

        for v in self._versions.get(strategy_name, []):
            if v.version_id == version_id:
                v.status = status
                self._save_version(v)
                return True
        return False

    def promote(self, strategy_name: str, version_id: str) -> dict:
        current = None
        for v in self._versions.get(strategy_name, []):
            if v.version_id == version_id:
                current = v
                break

        if not current:
            return {"success": False, "error": "版本未找到"}

        if current.status == "draft":
            current.status = "review"
        elif current.status == "review":
            current.status = "live"
        elif current.status == "live":
            return {"success": False, "error": "已上线版本无法再晋升"}
        else:
            return {"success": False, "error": f"无法从{current.status}状态晋升"}

        self._save_version(current)
        return {"success": True, "new_status": current.status}

    def list_strategies(self) -> List[dict]:
        result = []
        for name, versions in self._versions.items():
            latest = versions[-1] if versions else None
            result.append({
                "name": name,
                "version_count": len(versions),
                "latest_version": latest.version_id if latest else "",
                "latest_status": latest.status if latest else "",
                "latest_params": latest.params if latest else {},
            })
        return result

    def delete_version(self, strategy_name: str, version_id: str) -> bool:
        versions = self._versions.get(strategy_name, [])
        for i, v in enumerate(versions):
            if v.version_id == version_id:
                filepath = self.base_dir / strategy_name / f"v_{version_id}.json"
                if filepath.exists():
                    filepath.unlink()
                versions.pop(i)
                return True
        return False

    def _simple_hash(self, s: str) -> str:
        h = 0
        for c in s:
            h = (h * 31 + ord(c)) & 0xFFFFFFFF
        return f"{h:08x}"
