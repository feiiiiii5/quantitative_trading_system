import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional



logger = logging.getLogger(__name__)


class NodeType(Enum):
    INDICATOR = "indicator"
    CONDITION = "condition"
    ACTION = "action"
    LOGIC = "logic"
    VALUE = "value"


@dataclass
class StrategyNode:
    id: str
    type: NodeType
    name: str
    params: Dict[str, Any] = field(default_factory=dict)
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    position: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = {"id": self.id, "type": self.type.value, "name": self.name, "params": self.params,
             "inputs": self.inputs, "outputs": self.outputs, "position": self.position}
        return d


@dataclass
class StrategyEdge:
    source_id: str
    source_output: str
    target_id: str
    target_input: str

    def to_dict(self) -> dict:
        return {"source_id": self.source_id, "source_output": self.source_output,
                "target_id": self.target_id, "target_input": self.target_input}


@dataclass
class VisualStrategy:
    name: str
    description: str
    nodes: List[StrategyNode] = field(default_factory=list)
    edges: List[StrategyEdge] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name, "description": self.description,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "created_at": self.created_at, "updated_at": self.updated_at,
        }


INDICATOR_CATALOG = {
    "SMA": {"name": "简单移动平均", "params": {"period": 20}, "outputs": ["value"]},
    "EMA": {"name": "指数移动平均", "params": {"span": 20}, "outputs": ["value"]},
    "RSI": {"name": "相对强弱指标", "params": {"period": 14}, "outputs": ["value"]},
    "MACD": {"name": "MACD", "params": {"fast": 12, "slow": 26, "signal": 9}, "outputs": ["dif", "dea", "hist"]},
    "BOLL": {"name": "布林带", "params": {"period": 20, "nbdev": 2}, "outputs": ["upper", "mid", "lower"]},
    "ATR": {"name": "平均真实波幅", "params": {"period": 14}, "outputs": ["value"]},
    "KDJ": {"name": "KDJ随机指标", "params": {"n": 9, "m1": 3, "m2": 3}, "outputs": ["k", "d", "j"]},
    "CCI": {"name": "商品通道指标", "params": {"period": 14}, "outputs": ["value"]},
    "SUPERTREND": {"name": "超级趋势", "params": {"period": 10, "multiplier": 3}, "outputs": ["value", "direction"]},
    "VWAP": {"name": "成交量加权平均价", "params": {}, "outputs": ["value"]},
    "OBV": {"name": "能量潮", "params": {}, "outputs": ["value"]},
    "WILLIAMS_R": {"name": "威廉指标", "params": {"period": 14}, "outputs": ["value"]},
    "ROC": {"name": "变动率", "params": {"period": 10}, "outputs": ["value"]},
    "TRIX": {"name": "三重指数平滑", "params": {"period": 12}, "outputs": ["value"]},
    "DMI": {"name": "动向指标", "params": {"period": 14}, "outputs": ["pdi", "mdi", "adx"]},
    "SAR": {"name": "抛物线指标", "params": {"step": 0.02, "max_step": 0.2}, "outputs": ["value"]},
    "ICHIMOKU": {"name": "一目均衡", "params": {}, "outputs": ["tenkan", "kijun", "senkou_a", "senkou_b"]},
    "BBANDS_WIDTH": {"name": "布林带宽度", "params": {"period": 20, "nbdev": 2}, "outputs": ["value"]},
    "MFI": {"name": "资金流量指标", "params": {"period": 14}, "outputs": ["value"]},
    "STOCH": {"name": "随机振荡器", "params": {"k_period": 14, "d_period": 3}, "outputs": ["k", "d"]},
}

CONDITION_CATALOG = {
    "CROSS_ABOVE": {"name": "上穿", "params": {}, "inputs": ["line_a", "line_b"], "outputs": ["signal"]},
    "CROSS_BELOW": {"name": "下穿", "params": {}, "inputs": ["line_a", "line_b"], "outputs": ["signal"]},
    "ABOVE": {"name": "大于", "params": {}, "inputs": ["line_a", "line_b"], "outputs": ["signal"]},
    "BELOW": {"name": "小于", "params": {}, "inputs": ["line_a", "line_b"], "outputs": ["signal"]},
    "IN_RANGE": {"name": "区间内", "params": {"lower": 0, "upper": 100}, "inputs": ["value"], "outputs": ["signal"]},
    "OUT_RANGE": {"name": "区间外", "params": {"lower": 0, "upper": 100}, "inputs": ["value"], "outputs": ["signal"]},
}

ACTION_CATALOG = {
    "BUY": {"name": "买入", "params": {"position_pct": 0.3}, "inputs": ["signal"], "outputs": []},
    "SELL": {"name": "卖出", "params": {}, "inputs": ["signal"], "outputs": []},
    "SET_STOP_LOSS": {"name": "设置止损", "params": {"type": "percentage", "value": 0.05}, "inputs": ["price"], "outputs": []},
    "SET_TAKE_PROFIT": {"name": "设置止盈", "params": {"type": "percentage", "value": 0.10}, "inputs": ["price"], "outputs": []},
}

LOGIC_CATALOG = {
    "AND": {"name": "与", "params": {}, "inputs": ["a", "b"], "outputs": ["result"]},
    "OR": {"name": "或", "params": {}, "inputs": ["a", "b"], "outputs": ["result"]},
    "NOT": {"name": "非", "params": {}, "inputs": ["a"], "outputs": ["result"]},
    "DELAY": {"name": "延迟", "params": {"bars": 1}, "inputs": ["signal"], "outputs": ["signal"]},
}


class VisualStrategyBuilder:
    def __init__(self):
        self._strategies: Dict[str, VisualStrategy] = {}

    def create_strategy(self, name: str, description: str = "") -> VisualStrategy:
        strategy = VisualStrategy(
            name=name, description=description,
            created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            updated_at=time.strftime("%Y-%m-%d %H:%M:%S"),
        )
        self._strategies[name] = strategy
        return strategy

    def add_node(self, strategy_name: str, node_type: str, node_name: str,
                 params: Optional[Dict] = None, position: Optional[Dict] = None) -> Optional[StrategyNode]:
        strategy = self._strategies.get(strategy_name)
        if not strategy:
            return None

        try:
            nt = NodeType(node_type)
        except ValueError:
            return None

        node_id = f"node_{len(strategy.nodes)}_{int(time.time() * 1000)}"
        node = StrategyNode(
            id=node_id, type=nt, name=node_name,
            params=params or {}, position=position or {},
        )
        strategy.nodes.append(node)
        strategy.updated_at = time.strftime("%Y-%m-%d %H:%M:%S")
        return node

    def add_edge(self, strategy_name: str, source_id: str, source_output: str,
                 target_id: str, target_input: str) -> Optional[StrategyEdge]:
        strategy = self._strategies.get(strategy_name)
        if not strategy:
            return None

        edge = StrategyEdge(source_id, source_output, target_id, target_input)
        strategy.edges.append(edge)
        strategy.updated_at = time.strftime("%Y-%m-%d %H:%M:%S")
        return edge

    def remove_node(self, strategy_name: str, node_id: str):
        strategy = self._strategies.get(strategy_name)
        if not strategy:
            return
        strategy.nodes = [n for n in strategy.nodes if n.id != node_id]
        strategy.edges = [e for e in strategy.edges
                          if e.source_id != node_id and e.target_id != node_id]

    def remove_edge(self, strategy_name: str, source_id: str, target_id: str):
        strategy = self._strategies.get(strategy_name)
        if not strategy:
            return
        strategy.edges = [e for e in strategy.edges
                          if not (e.source_id == source_id and e.target_id == target_id)]

    def get_strategy(self, name: str) -> Optional[dict]:
        strategy = self._strategies.get(name)
        return strategy.to_dict() if strategy else None

    def list_strategies(self) -> List[dict]:
        return [s.to_dict() for s in self._strategies.values()]

    def delete_strategy(self, name: str):
        self._strategies.pop(name, None)

    def export_to_python(self, strategy_name: str) -> Optional[str]:
        strategy = self._strategies.get(strategy_name)
        if not strategy:
            return None

        lines = [
            "import numpy as np",
            "import pandas as pd",
            "from core.strategies import BaseStrategy, SignalType, TradeSignal, StrategyResult",
            "",
            f"class {strategy_name.replace(' ', '')}Strategy(BaseStrategy):",
            "    def __init__(self):",
            f'        super().__init__("{strategy_name}", "{strategy.description}")',
            "",
            "    def get_default_params(self) -> dict:",
            "        return {}",
            "",
            "    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:",
            "        if df is None or len(df) < 30:",
            "            return StrategyResult(name=self.name)",
            "        c = df['close'].values.astype(float)",
            "        h = df['high'].values.astype(float)",
            "        l = df['low'].values.astype(float)",
            "",
        ]

        for node in strategy.nodes:
            if node.type == NodeType.INDICATOR:
                if node.name == "SMA":
                    lines.append(f"        {node.id}_val = pd.Series(c).rolling({node.params.get('period', 20)}).mean().values")
                elif node.name == "EMA":
                    lines.append(f"        {node.id}_val = pd.Series(c).ewm(span={node.params.get('span', 20)}).mean().values")
                elif node.name == "RSI":
                    lines.append("        # RSI calculation")
                    lines.append("        delta = np.diff(c, prepend=c[0])")
                    lines.append("        gain = np.where(delta > 0, delta, 0)")
                    lines.append("        loss = np.where(delta < 0, -delta, 0)")
                    lines.append(f"        avg_gain = pd.Series(gain).ewm(alpha=1/{node.params.get('period', 14)}, min_periods={node.params.get('period', 14)}).mean().values")
                    lines.append(f"        avg_loss = pd.Series(loss).ewm(alpha=1/{node.params.get('period', 14)}, min_periods={node.params.get('period', 14)}).mean().values")
                    lines.append("        rs = np.where(avg_loss != 0, avg_gain / avg_loss, 100)")
                    lines.append(f"        {node.id}_val = 100 - 100 / (1 + rs)")
            elif node.type == NodeType.CONDITION:
                if node.name == "CROSS_ABOVE":
                    lines.append(f"        {node.id}_val = np.zeros(len(c))")
                    lines.append("        for i in range(1, len(c)):")
                    lines.append(f"            if {node.inputs[0]}[i-1] < {node.inputs[1]}[i-1] and {node.inputs[0]}[i] > {node.inputs[1]}[i]:")
                    lines.append(f"                {node.id}_val[i] = 1")

        lines.extend([
            "        signals = []",
            "        current_signal = None",
            "        score = 0.0",
            "        return StrategyResult(",
            "            name=self.name, signals=signals,",
            "            current_signal=current_signal, score=score,",
            "        )",
        ])

        return "\n".join(lines)

    def get_catalog(self) -> dict:
        return {
            "indicators": INDICATOR_CATALOG,
            "conditions": CONDITION_CATALOG,
            "actions": ACTION_CATALOG,
            "logic": LOGIC_CATALOG,
        }
