import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Query

from core.platform.microservice import MicroserviceManager, ServiceStatus
from core.platform.scheduler import TaskScheduler, TaskStatus
from core.platform.env_manager import EnvironmentManager
from core.platform.auth_security import AuthSecurityManager, Role
from core.platform.workspace import WorkspaceManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/platform", tags=["平台工程"])

microservice_mgr = MicroserviceManager()
scheduler = TaskScheduler()
env_manager = EnvironmentManager()
auth_mgr = AuthSecurityManager()
workspace_mgr = WorkspaceManager()


def _resp(success: bool, data=None, msg: str = ""):
    return {"code": 0 if success else 1, "data": data, "msg": msg}


# ==================== 46 微服务架构 ====================

@router.post("/microservice/start")
async def start_microservices():
    result = await microservice_mgr.start()
    return _resp(result["code"] == 0, data=result.get("data"), msg=result.get("msg", ""))


@router.post("/microservice/stop")
async def stop_microservices():
    result = await microservice_mgr.stop()
    return _resp(result["code"] == 0, data=result.get("data"), msg=result.get("msg", ""))


@router.get("/microservice/status")
async def get_microservice_status():
    result = microservice_mgr.get_status()
    return _resp(result["code"] == 0, data=result.get("data"), msg=result.get("msg", ""))


@router.get("/microservice/topology")
async def get_service_topology():
    result = microservice_mgr.get_topology()
    return _resp(result["code"] == 0, data=result.get("data"), msg=result.get("msg", ""))


@router.post("/microservice/heartbeat/{service_name}")
async def service_heartbeat(service_name: str):
    result = microservice_mgr.heartbeat(service_name)
    return _resp(result["code"] == 0, data=result.get("data"), msg=result.get("msg", ""))


@router.post("/microservice/send-message")
async def send_service_message(
    source: str = Query(...),
    target: str = Query(...),
    topic: str = Query(...),
    payload: str = Query("{}"),
):
    import json
    try:
        data = json.loads(payload)
    except Exception:
        data = {}
    result = microservice_mgr.send_message(source, target, topic, data)
    return _resp(result["code"] == 0, data=result.get("data"), msg=result.get("msg", ""))


@router.get("/microservice/messages")
async def get_service_messages(topic: str = Query(""), limit: int = Query(100)):
    result = microservice_mgr.get_message_log(topic, limit)
    return _resp(result["code"] == 0, data=result.get("data"), msg=result.get("msg", ""))


# ==================== 47 任务调度系统 ====================

@router.post("/scheduler/add")
async def add_task(
    name: str = Query(...),
    interval_seconds: float = Query(0),
    cron: str = Query(""),
    max_retries: int = Query(3),
    timeout_seconds: float = Query(300),
    dependencies: str = Query("", description="逗号分隔的依赖任务ID"),
):
    deps = [d.strip() for d in dependencies.split(",") if d.strip()]
    task_id = scheduler.add_task(
        name=name,
        interval_seconds=interval_seconds,
        cron=cron,
        max_retries=max_retries,
        timeout_seconds=timeout_seconds,
        dependencies=deps,
    )
    return _resp(True, data={"task_id": task_id}, msg="任务已添加")


@router.post("/scheduler/run/{task_id}")
async def run_task(task_id: str):
    result = await scheduler.run_task(task_id)
    success = result.get("success", False)
    return _resp(success, data=result, msg="" if success else result.get("error", ""))


@router.post("/scheduler/run-pending")
async def run_pending_tasks():
    results = await scheduler.run_pending()
    return _resp(True, data=results)


@router.get("/scheduler/list")
async def list_tasks():
    tasks = scheduler.list_tasks()
    return _resp(True, data=tasks)


@router.get("/scheduler/status/{task_id}")
async def get_task_status(task_id: str):
    status = scheduler.get_task_status(task_id)
    if status:
        return _resp(True, data=status)
    return _resp(False, msg="任务不存在")


@router.delete("/scheduler/remove/{task_id}")
async def remove_task(task_id: str):
    result = scheduler.remove_task(task_id)
    return _resp(result.get("success", False), data=result)


@router.post("/scheduler/reset/{task_id}")
async def reset_task(task_id: str):
    result = scheduler.reset_task(task_id)
    return _resp(result.get("success", False), data=result)


# ==================== 48 多环境管理 ====================

@router.get("/env/list")
async def list_environments():
    envs = env_manager.list_envs()
    return _resp(True, data=envs)


@router.get("/env/config/{env_name}")
async def get_env_config(env_name: str):
    config = env_manager.get_env_config(env_name)
    if config:
        return _resp(True, data=config.to_dict())
    return _resp(False, msg="环境不存在")


@router.post("/env/create")
async def create_environment(
    env_name: str = Query(...),
    database_url: str = Query(""),
    redis_url: str = Query(""),
    log_level: str = Query("INFO"),
):
    result = env_manager.create_env(env_name, database_url, redis_url, log_level)
    return _resp(result.get("success", False), data=result)


@router.post("/env/set-config")
async def set_env_config(
    env_name: str = Query(...),
    key: str = Query(...),
    value: str = Query(...),
):
    result = env_manager.set_config(env_name, key, value)
    return _resp(result.get("success", False), data=result)


@router.post("/env/promote")
async def promote_environment(
    from_env: str = Query(...),
    to_env: str = Query(...),
):
    result = env_manager.promote(from_env, to_env)
    return _resp(result.get("success", False), data=result)


@router.post("/env/checklist")
async def update_promotion_checklist(
    from_env: str = Query(...),
    to_env: str = Query(...),
    checklist: str = Query(..., description="JSON格式检查清单"),
):
    import json
    try:
        data = json.loads(checklist)
        result = env_manager.update_checklist(from_env, to_env, data)
        return _resp(result.get("success", False), data=result)
    except Exception as e:
        return _resp(False, msg=str(e))


@router.post("/env/load-vars/{env_name}")
async def load_env_vars(env_name: str):
    result = env_manager.load_env_vars(env_name)
    return _resp(result.get("success", False), data=result)


# ==================== 49 权限与安全体系 ====================

@router.post("/auth/create-user")
async def create_user(username: str = Query(...), role: str = Query("observer")):
    result = auth_mgr.create_user(username, role)
    if result:
        return _resp(True, data=result, msg="用户已创建")
    return _resp(False, msg="用户创建失败，可能用户名已存在或角色无效")


@router.post("/auth/authenticate")
async def authenticate(api_key: str = Query(...)):
    user = auth_mgr.authenticate(api_key)
    if user:
        return _resp(True, data={
            "username": user.username,
            "role": user.role.value,
            "is_active": user.is_active,
            "last_login": user.last_login,
        })
    return _resp(False, msg="认证失败")


@router.post("/auth/check-permission")
async def check_permission(
    username: str = Query(...),
    permission: str = Query(...),
):
    has_perm = auth_mgr.check_permission(username, permission)
    return _resp(True, data={"has_permission": has_perm})


@router.post("/auth/rotate-key")
async def rotate_api_key(username: str = Query(...)):
    result = auth_mgr.rotate_api_key(username)
    if result:
        return _resp(True, data=result, msg="API密钥已轮换")
    return _resp(False, msg="密钥轮换失败")


@router.post("/auth/set-active")
async def set_user_active(username: str = Query(...), active: bool = Query(True)):
    result = auth_mgr.set_user_active(username, active)
    return _resp(result.get("success", False), data=result)


@router.get("/auth/roles")
async def get_roles():
    from core.platform.auth_security import ROLE_PERMISSIONS
    roles = {}
    for role, perms in ROLE_PERMISSIONS.items():
        roles[role.value] = perms
    return _resp(True, data=roles)


@router.get("/auth/audit-log")
async def get_auth_audit_log(limit: int = Query(100)):
    log = auth_mgr.get_audit_log(limit)
    return _resp(True, data=log)


@router.post("/auth/encrypt")
async def encrypt_data(data: str = Query(...)):
    encrypted = auth_mgr.encrypt(data)
    return _resp(True, data={"encrypted": encrypted})


@router.post("/auth/decrypt")
async def decrypt_data(data: str = Query(...)):
    decrypted = auth_mgr.decrypt(data)
    return _resp(True, data={"decrypted": decrypted})


# ==================== 50 用户工作台个性化 ====================

@router.get("/workspace/presets")
async def get_workspace_presets():
    result = workspace_mgr.get_presets()
    return _resp(result["code"] == 0, data=result.get("data"), msg=result.get("msg", ""))


@router.post("/workspace/create")
async def create_workspace(name: str = Query(...), preset: str = Query("")):
    result = workspace_mgr.create_layout(name, preset)
    return _resp(result["code"] == 0, data=result.get("data"), msg=result.get("msg", ""))


@router.get("/workspace/list")
async def list_workspaces():
    result = workspace_mgr.list_layouts()
    return _resp(result["code"] == 0, data=result.get("data"), msg=result.get("msg", ""))


@router.get("/workspace/{layout_id}")
async def get_workspace(layout_id: str):
    result = workspace_mgr.get_layout(layout_id)
    return _resp(result["code"] == 0, data=result.get("data"), msg=result.get("msg", ""))


@router.delete("/workspace/{layout_id}")
async def delete_workspace(layout_id: str):
    result = workspace_mgr.delete_layout(layout_id)
    return _resp(result["code"] == 0, data=result.get("data"), msg=result.get("msg", ""))


@router.post("/workspace/add-panel")
async def add_workspace_panel(
    layout_id: str = Query(...),
    panel_type: str = Query(...),
    title: str = Query(""),
    x: int = Query(0),
    y: int = Query(0),
    width: int = Query(6),
    height: int = Query(4),
    config: str = Query("{}"),
):
    import json
    try:
        cfg = json.loads(config)
    except Exception:
        cfg = {}
    result = workspace_mgr.add_panel(layout_id, panel_type, title, x, y, width, height, cfg)
    return _resp(result["code"] == 0, data=result.get("data"), msg=result.get("msg", ""))


@router.delete("/workspace/{layout_id}/panel/{panel_id}")
async def remove_workspace_panel(layout_id: str, panel_id: str):
    result = workspace_mgr.remove_panel(layout_id, panel_id)
    return _resp(result["code"] == 0, data=result.get("data"), msg=result.get("msg", ""))


@router.post("/workspace/move-panel")
async def move_workspace_panel(
    layout_id: str = Query(...),
    panel_id: str = Query(...),
    x: int = Query(...),
    y: int = Query(...),
    width: Optional[int] = Query(None),
    height: Optional[int] = Query(None),
):
    result = workspace_mgr.move_panel(layout_id, panel_id, x, y, width, height)
    return _resp(result["code"] == 0, data=result.get("data"), msg=result.get("msg", ""))


@router.post("/workspace/user-layout")
async def set_user_workspace(user_id: str = Query(...), layout_id: str = Query(...)):
    result = workspace_mgr.set_user_layout(user_id, layout_id)
    return _resp(result["code"] == 0, data=result.get("data"), msg=result.get("msg", ""))


@router.get("/workspace/user/{user_id}")
async def get_user_workspace(user_id: str):
    result = workspace_mgr.get_user_layout(user_id)
    return _resp(result["code"] == 0, data=result.get("data"), msg=result.get("msg", ""))


@router.get("/workspace/shortcuts")
async def get_shortcuts():
    result = workspace_mgr.get_shortcuts()
    return _resp(result["code"] == 0, data=result.get("data"), msg=result.get("msg", ""))


@router.post("/workspace/set-shortcut")
async def set_shortcut(
    key: str = Query(...),
    action: str = Query(...),
    description: str = Query(""),
    scope: str = Query("global"),
):
    result = workspace_mgr.set_shortcut(key, action, description, scope)
    return _resp(result["code"] == 0, data=result.get("data"), msg=result.get("msg", ""))


@router.delete("/workspace/shortcut/{key}")
async def remove_shortcut(key: str):
    result = workspace_mgr.remove_shortcut(key)
    return _resp(result["code"] == 0, data=result.get("data"), msg=result.get("msg", ""))


@router.post("/workspace/reset-shortcuts")
async def reset_shortcuts():
    result = workspace_mgr.reset_shortcuts()
    return _resp(result["code"] == 0, data=result.get("data"), msg=result.get("msg", ""))
