import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_WORKSPACE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "workspaces")


class PanelType(Enum):
    CHART = "chart"
    TABLE = "table"
    METRIC = "metric"
    LOG = "log"
    HEATMAP = "heatmap"
    TREE = "tree"
    EDITOR = "editor"
    TERMINAL = "terminal"
    CUSTOM = "custom"


class PresetWorkspace(Enum):
    RESEARCH = "research"
    TRADING = "trading"
    MONITORING = "monitoring"


@dataclass
class Panel:
    panel_id: str
    panel_type: PanelType
    title: str = ""
    x: int = 0
    y: int = 0
    width: int = 6
    height: int = 4
    config: Dict[str, Any] = field(default_factory=dict)
    data_source: str = ""

    def to_dict(self) -> dict:
        return {
            "panel_id": self.panel_id,
            "panel_type": self.panel_type.value,
            "title": self.title,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "config": self.config,
            "data_source": self.data_source,
        }


@dataclass
class WorkspaceLayout:
    layout_id: str
    name: str
    preset: str = ""
    panels: List[Panel] = field(default_factory=list)
    grid_cols: int = 12
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "layout_id": self.layout_id,
            "name": self.name,
            "preset": self.preset,
            "panels": [p.to_dict() for p in self.panels],
            "grid_cols": self.grid_cols,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class ShortcutBinding:
    key: str
    action: str
    description: str = ""
    scope: str = "global"

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "action": self.action,
            "description": self.description,
            "scope": self.scope,
        }


RESEARCH_PRESET = WorkspaceLayout(
    layout_id="preset_research",
    name="研究工作台",
    preset=PresetWorkspace.RESEARCH.value,
    panels=[
        Panel("r_chart", PanelType.CHART, "K线图表", 0, 0, 8, 5, {"chart_type": "candlestick"}),
        Panel("r_indicators", PanelType.TABLE, "技术指标", 8, 0, 4, 5),
        Panel("r_factor", PanelType.HEATMAP, "因子分析", 0, 5, 6, 4),
        Panel("r_sentiment", PanelType.METRIC, "市场情绪", 6, 5, 3, 4),
        Panel("r_news", PanelType.LOG, "新闻资讯", 9, 5, 3, 4),
        Panel("r_notebook", PanelType.EDITOR, "研究笔记", 0, 9, 12, 4),
    ],
)

TRADING_PRESET = WorkspaceLayout(
    layout_id="preset_trading",
    name="交易工作台",
    preset=PresetWorkspace.TRADING.value,
    panels=[
        Panel("t_chart", PanelType.CHART, "实时行情", 0, 0, 8, 5, {"chart_type": "candlestick", "realtime": True}),
        Panel("t_orderbook", PanelType.TABLE, "订单簿", 8, 0, 4, 3),
        Panel("t_position", PanelType.TABLE, "持仓管理", 8, 3, 4, 2),
        Panel("t_orders", PanelType.TABLE, "委托单", 0, 5, 6, 3),
        Panel("t_pnl", PanelType.METRIC, "盈亏统计", 6, 5, 3, 3),
        Panel("t_risk", PanelType.METRIC, "风控指标", 9, 5, 3, 3),
        Panel("t_algo", PanelType.TERMINAL, "算法交易", 0, 8, 12, 3),
    ],
)

MONITORING_PRESET = WorkspaceLayout(
    layout_id="preset_monitoring",
    name="监控工作台",
    preset=PresetWorkspace.MONITORING.value,
    panels=[
        Panel("m_equity", PanelType.CHART, "资金曲线", 0, 0, 8, 4, {"chart_type": "line"}),
        Panel("m_drawdown", PanelType.CHART, "回撤监控", 0, 4, 6, 3, {"chart_type": "area"}),
        Panel("m_risk", PanelType.METRIC, "风险指标", 6, 4, 3, 3),
        Panel("m_alerts", PanelType.LOG, "告警日志", 9, 4, 3, 3),
        Panel("m_perf", PanelType.HEATMAP, "性能热力图", 0, 7, 6, 3),
        Panel("m_heartbeat", PanelType.TABLE, "策略心跳", 6, 7, 6, 3),
        Panel("m_audit", PanelType.LOG, "审计日志", 0, 10, 12, 3),
    ],
)

DEFAULT_SHORTCUTS = [
    ShortcutBinding("Ctrl+K", "search", "全局搜索"),
    ShortcutBinding("Ctrl+B", "buy", "快速买入"),
    ShortcutBinding("Ctrl+S", "sell", "快速卖出"),
    ShortcutBinding("Ctrl+R", "refresh", "刷新数据"),
    ShortcutBinding("Ctrl+1", "switch_research", "切换到研究工作台"),
    ShortcutBinding("Ctrl+2", "switch_trading", "切换到交易工作台"),
    ShortcutBinding("Ctrl+3", "switch_monitoring", "切换到监控工作台"),
    ShortcutBinding("Ctrl+P", "panel_add", "添加面板"),
    ShortcutBinding("Delete", "panel_remove", "删除面板"),
    ShortcutBinding("Ctrl+Z", "undo", "撤销操作"),
    ShortcutBinding("Ctrl+Shift+S", "save_layout", "保存布局"),
    ShortcutBinding("F5", "run_backtest", "运行回测"),
    ShortcutBinding("F6", "run_strategy", "运行策略"),
    ShortcutBinding("Escape", "close_modal", "关闭弹窗"),
]


class WorkspaceManager:
    def __init__(self):
        self._layouts: Dict[str, WorkspaceLayout] = {}
        self._user_layouts: Dict[str, str] = {}
        self._shortcuts: Dict[str, ShortcutBinding] = {}
        self._init_presets()
        self._init_shortcuts()
        os.makedirs(_WORKSPACE_DIR, exist_ok=True)
        self._load_from_disk()

    def _init_presets(self):
        for preset in [RESEARCH_PRESET, TRADING_PRESET, MONITORING_PRESET]:
            self._layouts[preset.layout_id] = preset

    def _init_shortcuts(self):
        for sc in DEFAULT_SHORTCUTS:
            self._shortcuts[sc.key] = sc

    def _load_from_disk(self):
        layout_file = os.path.join(_WORKSPACE_DIR, "layouts.json")
        if os.path.exists(layout_file):
            try:
                with open(layout_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for item in data.get("layouts", []):
                    panels = [
                        Panel(
                            panel_id=p["panel_id"],
                            panel_type=PanelType(p["panel_type"]),
                            title=p.get("title", ""),
                            x=p.get("x", 0), y=p.get("y", 0),
                            width=p.get("width", 6), height=p.get("height", 4),
                            config=p.get("config", {}),
                            data_source=p.get("data_source", ""),
                        )
                        for p in item.get("panels", [])
                    ]
                    layout = WorkspaceLayout(
                        layout_id=item["layout_id"],
                        name=item["name"],
                        preset=item.get("preset", ""),
                        panels=panels,
                        grid_cols=item.get("grid_cols", 12),
                        created_at=item.get("created_at", ""),
                        updated_at=item.get("updated_at", ""),
                    )
                    self._layouts[layout.layout_id] = layout
                for key, sc in data.get("shortcuts", {}).items():
                    self._shortcuts[key] = ShortcutBinding(**sc)
                self._user_layouts = data.get("user_layouts", {})
                logger.info(f"已加载{len(self._layouts)}个工作台布局")
            except Exception as e:
                logger.warning(f"加载工作台配置失败: {e}")

    def _save_to_disk(self):
        layout_file = os.path.join(_WORKSPACE_DIR, "layouts.json")
        try:
            data = {
                "layouts": [
                    {**layout.to_dict()}
                    for lid, layout in self._layouts.items()
                    if not lid.startswith("preset_")
                ],
                "shortcuts": {k: v.to_dict() for k, v in self._shortcuts.items()},
                "user_layouts": self._user_layouts,
            }
            with open(layout_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存工作台配置失败: {e}")

    def create_layout(self, name: str, preset: str = "") -> dict:
        layout_id = f"custom_{int(time.time()*1000)}"
        panels = []
        if preset:
            preset_layout = self._layouts.get(f"preset_{preset}")
            if preset_layout:
                panels = [
                    Panel(
                        panel_id=f"{layout_id}_{p.panel_id}",
                        panel_type=p.panel_type,
                        title=p.title,
                        x=p.x, y=p.y,
                        width=p.width, height=p.height,
                        config=p.config.copy(),
                        data_source=p.data_source,
                    )
                    for p in preset_layout.panels
                ]
        layout = WorkspaceLayout(
            layout_id=layout_id,
            name=name,
            preset=preset,
            panels=panels,
            created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            updated_at=time.strftime("%Y-%m-%d %H:%M:%S"),
        )
        self._layouts[layout_id] = layout
        self._save_to_disk()
        return {"code": 0, "data": layout.to_dict(), "msg": "工作台已创建"}

    def get_layout(self, layout_id: str) -> dict:
        layout = self._layouts.get(layout_id)
        if not layout:
            return {"code": 1, "data": None, "msg": "工作台不存在"}
        return {"code": 0, "data": layout.to_dict(), "msg": ""}

    def list_layouts(self) -> dict:
        layouts = []
        for lid, layout in self._layouts.items():
            layouts.append({
                "layout_id": lid,
                "name": layout.name,
                "preset": layout.preset,
                "panel_count": len(layout.panels),
                "created_at": layout.created_at,
                "updated_at": layout.updated_at,
            })
        return {"code": 0, "data": layouts, "msg": ""}

    def delete_layout(self, layout_id: str) -> dict:
        if layout_id.startswith("preset_"):
            return {"code": 1, "data": None, "msg": "预设工作台不可删除"}
        if layout_id not in self._layouts:
            return {"code": 1, "data": None, "msg": "工作台不存在"}
        del self._layouts[layout_id]
        self._save_to_disk()
        return {"code": 0, "data": None, "msg": "工作台已删除"}

    def add_panel(
        self, layout_id: str, panel_type: str, title: str = "",
        x: int = 0, y: int = 0, width: int = 6, height: int = 4,
        config: Optional[dict] = None,
    ) -> dict:
        layout = self._layouts.get(layout_id)
        if not layout:
            return {"code": 1, "data": None, "msg": "工作台不存在"}
        try:
            pt = PanelType(panel_type)
        except ValueError:
            return {"code": 1, "data": None, "msg": f"不支持的面板类型: {panel_type}"}
        panel_id = f"{layout_id}_p{len(layout.panels)}"
        panel = Panel(
            panel_id=panel_id, panel_type=pt, title=title,
            x=x, y=y, width=width, height=height,
            config=config or {},
        )
        layout.panels.append(panel)
        layout.updated_at = time.strftime("%Y-%m-%d %H:%M:%S")
        self._save_to_disk()
        return {"code": 0, "data": panel.to_dict(), "msg": "面板已添加"}

    def remove_panel(self, layout_id: str, panel_id: str) -> dict:
        layout = self._layouts.get(layout_id)
        if not layout:
            return {"code": 1, "data": None, "msg": "工作台不存在"}
        original_len = len(layout.panels)
        layout.panels = [p for p in layout.panels if p.panel_id != panel_id]
        if len(layout.panels) == original_len:
            return {"code": 1, "data": None, "msg": "面板不存在"}
        layout.updated_at = time.strftime("%Y-%m-%d %H:%M:%S")
        self._save_to_disk()
        return {"code": 0, "data": None, "msg": "面板已移除"}

    def move_panel(
        self, layout_id: str, panel_id: str,
        x: int, y: int, width: Optional[int] = None, height: Optional[int] = None,
    ) -> dict:
        layout = self._layouts.get(layout_id)
        if not layout:
            return {"code": 1, "data": None, "msg": "工作台不存在"}
        for panel in layout.panels:
            if panel.panel_id == panel_id:
                panel.x = x
                panel.y = y
                if width is not None:
                    panel.width = width
                if height is not None:
                    panel.height = height
                layout.updated_at = time.strftime("%Y-%m-%d %H:%M:%S")
                self._save_to_disk()
                return {"code": 0, "data": panel.to_dict(), "msg": "面板已移动"}
        return {"code": 1, "data": None, "msg": "面板不存在"}

    def update_panel_config(self, layout_id: str, panel_id: str, config: dict) -> dict:
        layout = self._layouts.get(layout_id)
        if not layout:
            return {"code": 1, "data": None, "msg": "工作台不存在"}
        for panel in layout.panels:
            if panel.panel_id == panel_id:
                panel.config.update(config)
                layout.updated_at = time.strftime("%Y-%m-%d %H:%M:%S")
                self._save_to_disk()
                return {"code": 0, "data": panel.to_dict(), "msg": "面板配置已更新"}
        return {"code": 1, "data": None, "msg": "面板不存在"}

    def get_presets(self) -> dict:
        presets = []
        for preset in PresetWorkspace:
            layout = self._layouts.get(f"preset_{preset.value}")
            if layout:
                presets.append({
                    "id": preset.value,
                    "name": layout.name,
                    "panel_count": len(layout.panels),
                    "panels": [p.to_dict() for p in layout.panels],
                })
        return {"code": 0, "data": presets, "msg": ""}

    def set_user_layout(self, user_id: str, layout_id: str) -> dict:
        if layout_id not in self._layouts:
            return {"code": 1, "data": None, "msg": "工作台不存在"}
        self._user_layouts[user_id] = layout_id
        self._save_to_disk()
        return {"code": 0, "data": {"layout_id": layout_id}, "msg": "用户工作台已设置"}

    def get_user_layout(self, user_id: str) -> dict:
        layout_id = self._user_layouts.get(user_id)
        if not layout_id:
            return {"code": 0, "data": {"layout_id": "preset_research"}, "msg": "使用默认工作台"}
        layout = self._layouts.get(layout_id)
        if not layout:
            return {"code": 0, "data": {"layout_id": "preset_research"}, "msg": "工作台不存在，使用默认"}
        return {"code": 0, "data": layout.to_dict(), "msg": ""}

    def get_shortcuts(self) -> dict:
        shortcuts = [sc.to_dict() for sc in self._shortcuts.values()]
        return {"code": 0, "data": shortcuts, "msg": ""}

    def set_shortcut(self, key: str, action: str, description: str = "", scope: str = "global") -> dict:
        for k, sc in list(self._shortcuts.items()):
            if sc.action == action and k != key:
                del self._shortcuts[k]
                break
        self._shortcuts[key] = ShortcutBinding(
            key=key, action=action, description=description, scope=scope,
        )
        self._save_to_disk()
        return {"code": 0, "data": self._shortcuts[key].to_dict(), "msg": "快捷键已设置"}

    def remove_shortcut(self, key: str) -> dict:
        if key in self._shortcuts:
            del self._shortcuts[key]
            self._save_to_disk()
            return {"code": 0, "data": None, "msg": "快捷键已移除"}
        return {"code": 1, "data": None, "msg": "快捷键不存在"}

    def reset_shortcuts(self) -> dict:
        self._shortcuts.clear()
        self._init_shortcuts()
        self._save_to_disk()
        return {"code": 0, "data": None, "msg": "快捷键已重置为默认"}
