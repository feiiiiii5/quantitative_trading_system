import gzip
import hashlib
import json
import logging
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_CACHE_DIR = Path(__file__).parent.parent / "data" / "file_cache"
_MAX_FILES = 500
_DEFAULT_TTL = 300
_INDEX: OrderedDict = OrderedDict()
_INDEX_PATH = _CACHE_DIR / "_index.json"
_INDEX_LOADED = False


def _ensure_dir():
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _load_index():
    global _INDEX, _INDEX_LOADED
    if _INDEX_LOADED:
        return
    _INDEX_LOADED = True
    if not _INDEX_PATH.exists():
        return
    try:
        data = json.loads(_INDEX_PATH.read_text(encoding="utf-8"))
        for k, v in data.items():
            _INDEX[k] = v
    except Exception:
        _INDEX.clear()


def _save_index():
    _ensure_dir()
    try:
        _INDEX_PATH.write_text(json.dumps(dict(_INDEX), ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _key_hash(key: str) -> str:
    return hashlib.md5(key.encode()).hexdigest()


def get(key: str) -> Optional[Any]:
    _load_index()
    entry = _INDEX.get(key)
    if not entry:
        return None
    if time.time() - entry.get("ts", 0) > entry.get("ttl", _DEFAULT_TTL):
        delete(key)
        return None
    path = _CACHE_DIR / f"{_key_hash(key)}.gz"
    if not path.exists():
        delete(key)
        return None
    try:
        data = gzip.decompress(path.read_bytes())
        _INDEX.move_to_end(key)
        return json.loads(data)
    except Exception:
        delete(key)
        return None


def set(key: str, value: Any, ttl: int = _DEFAULT_TTL) -> None:
    _load_index()
    _ensure_dir()
    h = _key_hash(key)
    try:
        compressed = gzip.compress(json.dumps(value, ensure_ascii=False).encode("utf-8"))
        path = _CACHE_DIR / f"{h}.gz"
        path.write_bytes(compressed)
        _INDEX[key] = {"ts": time.time(), "ttl": ttl, "hash": h}
        _INDEX.move_to_end(key)
        while len(_INDEX) > _MAX_FILES:
            oldest_key, oldest_entry = _INDEX.popitem(last=False)
            try:
                (_CACHE_DIR / f"{oldest_entry['hash']}.gz").unlink(missing_ok=True)
            except Exception:
                pass
        _save_index()
    except Exception as e:
        logger.debug(f"FileCache set error for {key}: {e}")


def delete(key: str) -> None:
    entry = _INDEX.pop(key, None)
    if entry:
        try:
            (_CACHE_DIR / f"{entry['hash']}.gz").unlink(missing_ok=True)
        except Exception:
            pass


def clear() -> int:
    _load_index()
    count = len(_INDEX)
    for entry in _INDEX.values():
        try:
            (_CACHE_DIR / f"{entry['hash']}.gz").unlink(missing_ok=True)
        except Exception:
            pass
    _INDEX.clear()
    _save_index()
    return count
