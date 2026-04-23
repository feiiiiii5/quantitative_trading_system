import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class Role(Enum):
    ADMIN = "admin"
    STRATEGIST = "strategist"
    RISK_MANAGER = "risk_manager"
    OBSERVER = "observer"


ROLE_PERMISSIONS = {
    Role.ADMIN: ["read", "write", "delete", "manage_users", "manage_system", "execute_trades", "view_audit"],
    Role.STRATEGIST: ["read", "write", "execute_trades", "view_backtest"],
    Role.RISK_MANAGER: ["read", "manage_risk", "view_audit", "halt_trading"],
    Role.OBSERVER: ["read", "view_backtest"],
}


@dataclass
class User:
    username: str
    role: Role = Role.OBSERVER
    api_key_hash: str = ""
    created_at: str = ""
    last_login: str = ""
    is_active: bool = True

    def to_dict(self) -> dict:
        return {
            "username": self.username, "role": self.role.value,
            "created_at": self.created_at, "last_login": self.last_login,
            "is_active": self.is_active,
            "permissions": ROLE_PERMISSIONS.get(self.role, []),
        }


@dataclass
class AuditRecord:
    username: str
    action: str
    resource: str
    timestamp: str = ""
    details: dict = field(default_factory=dict)
    ip_address: str = ""

    def to_dict(self) -> dict:
        return {
            "username": self.username, "action": self.action,
            "resource": self.resource, "timestamp": self.timestamp,
            "details": self.details, "ip_address": self.ip_address,
        }


class AuthSecurityManager:
    def __init__(self):
        self._users: Dict[str, User] = {}
        self._api_keys: Dict[str, str] = {}
        self._audit_log: List[AuditRecord] = []
        self._audit_log_max = 10000
        self._encryption_key = os.environ.get("ENCRYPTION_KEY", "default_key_change_me")
        self._fernet = None
        self._init_encryption()

    def _init_encryption(self):
        try:
            from cryptography.fernet import Fernet
            import base64
            key = hashlib.sha256(self._encryption_key.encode()).digest()
            self._fernet = Fernet(base64.urlsafe_b64encode(key))
        except ImportError:
            logger.warning("cryptography库未安装，使用基础加密（不推荐生产环境）")
            self._fernet = None

    def create_user(self, username: str, role: str = "observer") -> Optional[dict]:
        try:
            r = Role(role)
        except ValueError:
            return None

        if username in self._users:
            return None

        api_key = self._generate_api_key(username)
        api_key_hash = self._hash(api_key)

        user = User(
            username=username, role=r,
            api_key_hash=api_key_hash,
            created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
        )
        self._users[username] = user
        self._api_keys[api_key] = username

        return {"username": username, "role": r.value, "api_key": api_key}

    def authenticate(self, api_key: str) -> Optional[User]:
        username = self._api_keys.get(api_key)
        if not username:
            return None
        user = self._users.get(username)
        if not user or not user.is_active:
            return None
        user.last_login = time.strftime("%Y-%m-%d %H:%M:%S")
        return user

    def check_permission(self, username: str, permission: str) -> bool:
        user = self._users.get(username)
        if not user:
            return False
        permissions = ROLE_PERMISSIONS.get(user.role, [])
        return permission in permissions

    def set_user_active(self, username: str, active: bool = True) -> dict:
        user = self._users.get(username)
        if not user:
            return {"success": False, "error": f"用户{username}不存在"}
        user.is_active = active
        return {"success": True, "username": username, "is_active": active}

    def rotate_api_key(self, username: str) -> dict:
        user = self._users.get(username)
        if not user:
            return {"success": False, "error": f"用户{username}不存在"}

        for key, name in list(self._api_keys.items()):
            if name == username:
                del self._api_keys[key]

        new_key = self._generate_api_key(username)
        user.api_key_hash = self._hash(new_key)
        self._api_keys[new_key] = username
        return {"success": True, "username": username, "new_api_key": new_key}

    def encrypt(self, value: str) -> str:
        return self.encrypt_field(value)

    def decrypt(self, encrypted: str) -> str:
        return self.decrypt_field(encrypted)

    def encrypt_field(self, value: str) -> str:
        if self._fernet:
            try:
                return self._fernet.encrypt(value.encode()).decode()
            except Exception:
                pass
        import base64
        key_bytes = self._encryption_key.encode()[:32].ljust(32, b'0')
        value_bytes = value.encode()
        xored = bytes(a ^ b for a, b in zip(value_bytes, key_bytes[:len(value_bytes)] * (len(value_bytes) // len(key_bytes[:len(value_bytes)]) + 1)))
        return base64.b64encode(xored).decode()

    def decrypt_field(self, encrypted: str) -> str:
        if self._fernet:
            try:
                return self._fernet.decrypt(encrypted.encode()).decode()
            except Exception:
                pass
        import base64
        key_bytes = self._encryption_key.encode()[:32].ljust(32, b'0')
        try:
            xored = base64.b64decode(encrypted)
            value_bytes = bytes(a ^ b for a, b in zip(xored, key_bytes[:len(xored)] * (len(xored) // len(key_bytes[:len(xored)]) + 1)))
            return value_bytes.decode()
        except Exception:
            return ""

    def audit(self, username: str, action: str, resource: str, details: Optional[dict] = None):
        record = AuditRecord(
            username=username, action=action, resource=resource,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            details=details or {},
        )
        self._audit_log.append(record)
        if len(self._audit_log) > self._audit_log_max:
            self._audit_log = self._audit_log[-self._audit_log_max:]

    def get_users(self) -> List[dict]:
        return [u.to_dict() for u in self._users.values()]

    def get_audit_log(self, limit: int = 100) -> List[dict]:
        return [r.to_dict() for r in self._audit_log[-limit:]]

    def get_roles(self) -> List[dict]:
        return [{"name": r.value, "permissions": perms} for r, perms in ROLE_PERMISSIONS.items()]

    def _generate_api_key(self, username: str) -> str:
        raw = f"{username}:{time.time()}:{os.urandom(16).hex()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    def _hash(self, value: str) -> str:
        return hashlib.sha256((value + self._encryption_key).encode()).hexdigest()
