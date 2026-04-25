import logging
from typing import Optional

from fastapi import APIRouter, Query, Request


logger = logging.getLogger(__name__)
platform_router = APIRouter(prefix="/platform", tags=["平台工程"])


def _resp(success: bool, data=None, msg: str = ""):
    return {"code": 0 if success else 1, "data": data, "msg": msg}


@platform_router.post("/microservice/start")
async def start_microservices(request: Request):
    result = await request.app.state.microservice_mgr.start()
    return _resp(result["code"] == 0, data=result.get("data"), msg=result.get("msg", ""))


@platform_router.post("/microservice/stop")
async def stop_microservices(request: Request):
    result = await request.app.state.microservice_mgr.stop()
    return _resp(result["code"] == 0, data=result.get("data"), msg=result.get("msg", ""))


@platform_router.get("/microservice/status")
async def get_microservice_status(request: Request):
    result = request.app.state.microservice_mgr.get_status()
    return _resp(result["code"] == 0, data=result.get("data"), msg=result.get("msg", ""))


@platform_router.get("/microservice/topology")
async def get_service_topology(request: Request):
    result = request.app.state.microservice_mgr.get_topology()
    return _resp(result["code"] == 0, data=result.get("data"), msg=result.get("msg", ""))


@platform_router.post("/microservice/heartbeat/{service_name}")
async def service_heartbeat(request: Request, service_name: str):
    result = request.app.state.microservice_mgr.heartbeat(service_name)
    return _resp(result["code"] == 0, data=result.get("data"), msg=result.get("msg", ""))


@platform_router.post("/microservice/send-message")
async def send_service_message(
    request: Request,
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
    result = request.app.state.microservice_mgr.send_message(source, target, topic, data)
    return _resp(result["code"] == 0, data=result.get("data"), msg=result.get("msg", ""))


@platform_router.get("/microservice/messages")
async def get_service_messages(request: Request, topic: str = Query(""), limit: int = Query(100)):
    result = request.app.state.microservice_mgr.get_message_log(topic, limit)
    return _resp(result["code"] == 0, data=result.get("data"), msg=result.get("msg", ""))


@platform_router.post("/scheduler/add")
async def add_task(
    request: Request,
    name: str = Query(...),
    interval_seconds: float = Query(0),
    cron: str = Query(""),
    max_retries: int = Query(3),
    timeout_seconds: float = Query(300),
    dependencies: str = Query("", description="逗号分隔的依赖任务ID"),
):
    deps = [d.strip() for d in dependencies.split(",") if d.strip()]
    async with request.app.state.write_lock:
        task_id = request.app.state.scheduler.add_task(
            name=name, interval_seconds=interval_seconds, cron=cron,
            max_retries=max_retries, timeout_seconds=timeout_seconds, dependencies=deps,
        )
    return _resp(True, data={"task_id": task_id}, msg="任务已添加")


@platform_router.post("/scheduler/run/{task_id}")
async def run_task(request: Request, task_id: str):
    result = await request.app.state.scheduler.run_task(task_id)
    success = result.get("success", False)
    return _resp(success, data=result, msg="" if success else result.get("error", ""))


@platform_router.post("/scheduler/run-pending")
async def run_pending_tasks(request: Request):
    results = await request.app.state.scheduler.run_pending()
    return _resp(True, data=results)


@platform_router.get("/scheduler/list")
async def list_tasks(request: Request):
    tasks = request.app.state.scheduler.list_tasks()
    return _resp(True, data=tasks)


@platform_router.get("/scheduler/status/{task_id}")
async def get_task_status(request: Request, task_id: str):
    status = request.app.state.scheduler.get_task_status(task_id)
    if status:
        return _resp(True, data=status)
    return _resp(False, msg="任务不存在")


@platform_router.delete("/scheduler/remove/{task_id}")
async def remove_task(request: Request, task_id: str):
    async with request.app.state.write_lock:
        result = request.app.state.scheduler.remove_task(task_id)
    return _resp(result.get("success", False), data=result)


@platform_router.post("/scheduler/reset/{task_id}")
async def reset_task(request: Request, task_id: str):
    async with request.app.state.write_lock:
        result = request.app.state.scheduler.reset_task(task_id)
    return _resp(result.get("success", False), data=result)


@platform_router.get("/env/list")
async def list_environments(request: Request):
    envs = request.app.state.env_manager.list_envs()
    return _resp(True, data=envs)


@platform_router.get("/env/config/{env_name}")
async def get_env_config(request: Request, env_name: str):
    config = request.app.state.env_manager.get_env_config(env_name)
    if config:
        return _resp(True, data=config.to_dict())
    return _resp(False, msg="环境不存在")


@platform_router.post("/env/create")
async def create_environment(
    request: Request,
    env_name: str = Query(...),
    database_url: str = Query(""),
    redis_url: str = Query(""),
    log_level: str = Query("INFO"),
):
    async with request.app.state.write_lock:
        result = request.app.state.env_manager.create_env(env_name, database_url, redis_url, log_level)
    return _resp(result.get("success", False), data=result)


@platform_router.post("/env/set-config")
async def set_env_config(
    request: Request,
    env_name: str = Query(...),
    key: str = Query(...),
    value: str = Query(...),
):
    async with request.app.state.write_lock:
        result = request.app.state.env_manager.set_config(env_name, key, value)
    return _resp(result.get("success", False), data=result)


@platform_router.post("/env/promote")
async def promote_environment(
    request: Request,
    from_env: str = Query(...),
    to_env: str = Query(...),
):
    async with request.app.state.write_lock:
        result = request.app.state.env_manager.promote(from_env, to_env)
    return _resp(result.get("success", False), data=result)


@platform_router.post("/env/checklist")
async def update_promotion_checklist(
    request: Request,
    from_env: str = Query(...),
    to_env: str = Query(...),
    checklist: str = Query(..., description="JSON格式检查清单"),
):
    import json
    try:
        data = json.loads(checklist)
        result = request.app.state.env_manager.update_checklist(from_env, to_env, data)
        return _resp(result.get("success", False), data=result)
    except Exception as e:
        return _resp(False, msg=str(e))


@platform_router.post("/env/load-vars/{env_name}")
async def load_env_vars(request: Request, env_name: str):
    result = request.app.state.env_manager.load_env_vars(env_name)
    return _resp(result.get("success", False), data=result)


@platform_router.post("/auth/create-user")
async def create_user(request: Request, username: str = Query(...), role: str = Query("observer")):
    async with request.app.state.write_lock:
        result = request.app.state.auth_manager.create_user(username, role)
    if result:
        return _resp(True, data=result, msg="用户已创建")
    return _resp(False, msg="用户创建失败")


@platform_router.post("/auth/authenticate")
async def authenticate(request: Request, api_key: str = Query(...)):
    user = request.app.state.auth_manager.authenticate(api_key)
    if user:
        return _resp(True, data={
            "username": user.username, "role": user.role.value,
            "is_active": user.is_active, "last_login": user.last_login,
        })
    return _resp(False, msg="认证失败")


@platform_router.post("/auth/check-permission")
async def check_permission(request: Request, username: str = Query(...), permission: str = Query(...)):
    has_perm = request.app.state.auth_manager.check_permission(username, permission)
    return _resp(True, data={"has_permission": has_perm})


@platform_router.post("/auth/rotate-key")
async def rotate_api_key(request: Request, username: str = Query(...)):
    async with request.app.state.write_lock:
        result = request.app.state.auth_manager.rotate_api_key(username)
    return _resp(result.get("success", False), data=result)


@platform_router.post("/auth/set-active")
async def set_user_active(request: Request, username: str = Query(...), active: bool = Query(True)):
    async with request.app.state.write_lock:
        result = request.app.state.auth_manager.set_user_active(username, active)
    return _resp(result.get("success", False), data=result)


@platform_router.get("/auth/roles")
async def get_roles():
    from core.platform.auth_security import ROLE_PERMISSIONS
    roles = {}
    for role, perms in ROLE_PERMISSIONS.items():
        roles[role.value] = perms
    return _resp(True, data=roles)


@platform_router.get("/auth/audit-log")
async def get_auth_audit_log(request: Request, limit: int = Query(100)):
    log = request.app.state.auth_manager.get_audit_log(limit)
    return _resp(True, data=log)


@platform_router.post("/auth/encrypt")
async def encrypt_data(request: Request, data: str = Query(...)):
    encrypted = request.app.state.auth_manager.encrypt(data)
    return _resp(True, data={"encrypted": encrypted})


@platform_router.post("/auth/decrypt")
async def decrypt_data(request: Request, data: str = Query(...)):
    decrypted = request.app.state.auth_manager.decrypt(data)
    return _resp(True, data={"decrypted": decrypted})


@platform_router.get("/workspace/presets")
async def get_workspace_presets(request: Request):
    result = request.app.state.workspace_mgr.get_presets()
    return _resp(result["code"] == 0, data=result.get("data"), msg=result.get("msg", ""))


@platform_router.post("/workspace/create")
async def create_workspace(request: Request, name: str = Query(...), preset: str = Query("")):
    result = request.app.state.workspace_mgr.create_layout(name, preset)
    return _resp(result["code"] == 0, data=result.get("data"), msg=result.get("msg", ""))


@platform_router.get("/workspace/list")
async def list_workspaces(request: Request):
    result = request.app.state.workspace_mgr.list_layouts()
    return _resp(result["code"] == 0, data=result.get("data"), msg=result.get("msg", ""))


@platform_router.get("/workspace/{layout_id}")
async def get_workspace(request: Request, layout_id: str):
    result = request.app.state.workspace_mgr.get_layout(layout_id)
    return _resp(result["code"] == 0, data=result.get("data"), msg=result.get("msg", ""))


@platform_router.delete("/workspace/{layout_id}")
async def delete_workspace(request: Request, layout_id: str):
    result = request.app.state.workspace_mgr.delete_layout(layout_id)
    return _resp(result["code"] == 0, data=result.get("data"), msg=result.get("msg", ""))


@platform_router.post("/workspace/add-panel")
async def add_workspace_panel(
    request: Request,
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
    result = request.app.state.workspace_mgr.add_panel(layout_id, panel_type, title, x, y, width, height, cfg)
    return _resp(result["code"] == 0, data=result.get("data"), msg=result.get("msg", ""))


@platform_router.delete("/workspace/{layout_id}/panel/{panel_id}")
async def remove_workspace_panel(request: Request, layout_id: str, panel_id: str):
    result = request.app.state.workspace_mgr.remove_panel(layout_id, panel_id)
    return _resp(result["code"] == 0, data=result.get("data"), msg=result.get("msg", ""))


@platform_router.post("/workspace/move-panel")
async def move_workspace_panel(
    request: Request,
    layout_id: str = Query(...),
    panel_id: str = Query(...),
    x: int = Query(...),
    y: int = Query(...),
    width: Optional[int] = Query(None),
    height: Optional[int] = Query(None),
):
    result = request.app.state.workspace_mgr.move_panel(layout_id, panel_id, x, y, width, height)
    return _resp(result["code"] == 0, data=result.get("data"), msg=result.get("msg", ""))


@platform_router.post("/workspace/user-layout")
async def set_user_workspace(request: Request, user_id: str = Query(...), layout_id: str = Query(...)):
    result = request.app.state.workspace_mgr.set_user_layout(user_id, layout_id)
    return _resp(result["code"] == 0, data=result.get("data"), msg=result.get("msg", ""))


@platform_router.get("/workspace/user/{user_id}")
async def get_user_workspace(request: Request, user_id: str):
    result = request.app.state.workspace_mgr.get_user_layout(user_id)
    return _resp(result["code"] == 0, data=result.get("data"), msg=result.get("msg", ""))


@platform_router.get("/workspace/shortcuts")
async def get_shortcuts(request: Request):
    result = request.app.state.workspace_mgr.get_shortcuts()
    return _resp(result["code"] == 0, data=result.get("data"), msg=result.get("msg", ""))


@platform_router.post("/workspace/set-shortcut")
async def set_shortcut(
    request: Request,
    key: str = Query(...),
    action: str = Query(...),
    description: str = Query(""),
    scope: str = Query("global"),
):
    result = request.app.state.workspace_mgr.set_shortcut(key, action, description, scope)
    return _resp(result["code"] == 0, data=result.get("data"), msg=result.get("msg", ""))


@platform_router.delete("/workspace/shortcut/{key}")
async def remove_shortcut(request: Request, key: str):
    result = request.app.state.workspace_mgr.remove_shortcut(key)
    return _resp(result["code"] == 0, data=result.get("data"), msg=result.get("msg", ""))


@platform_router.post("/workspace/reset-shortcuts")
async def reset_shortcuts(request: Request):
    result = request.app.state.workspace_mgr.reset_shortcuts()
    return _resp(result["code"] == 0, data=result.get("data"), msg=result.get("msg", ""))
