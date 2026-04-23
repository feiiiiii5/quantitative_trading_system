import logging
import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ParsedStrategy:
    name: str
    description: str
    entry_conditions: List[str] = field(default_factory=list)
    exit_conditions: List[str] = field(default_factory=list)
    position_management: List[str] = field(default_factory=list)
    risk_rules: List[str] = field(default_factory=list)
    code: str = ""
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "name": self.name, "description": self.description,
            "entry_conditions": self.entry_conditions,
            "exit_conditions": self.exit_conditions,
            "position_management": self.position_management,
            "risk_rules": self.risk_rules,
            "code": self.code, "confidence": round(self.confidence, 4),
        }


STRATEGY_TEMPLATES = {
    "双均线交叉": {
        "entry": ["fast_ma crosses above slow_ma"],
        "exit": ["fast_ma crosses below slow_ma"],
        "params": {"fast": 5, "slow": 20},
    },
    "RSI超卖反弹": {
        "entry": ["RSI crosses above oversold_level from below"],
        "exit": ["RSI crosses above overbought_level"],
        "params": {"period": 14, "oversold": 30, "overbought": 70},
    },
    "布林带突破": {
        "entry": ["close crosses above upper_band"],
        "exit": ["close crosses below middle_band"],
        "params": {"period": 20, "nbdev": 2},
    },
    "MACD金叉": {
        "entry": ["MACD line crosses above signal line"],
        "exit": ["MACD line crosses below signal line"],
        "params": {"fast": 12, "slow": 26, "signal": 9},
    },
}


class NLStrategyGenerator:
    def __init__(self):
        self._keyword_map = {
            "均线": "ma", "移动平均": "ma", "MA": "ma",
            "金叉": "golden_cross", "死叉": "death_cross",
            "RSI": "rsi", "超卖": "oversold", "超买": "overbought",
            "布林带": "bollinger", "布林": "bollinger",
            "MACD": "macd",
            "突破": "breakout", "跌破": "breakdown",
            "止损": "stop_loss", "止盈": "take_profit",
            "仓位": "position", "加仓": "add_position", "减仓": "reduce_position",
            "趋势": "trend", "震荡": "range",
            "买入": "buy", "卖出": "sell",
        }

    def parse(self, description: str) -> ParsedStrategy:
        strategy = ParsedStrategy(
            name=self._extract_name(description),
            description=description,
        )

        matched_template = None
        for template_name, template in STRATEGY_TEMPLATES.items():
            keywords = template_name.split("交叉") if "交叉" in template_name else [template_name]
            if any(kw in description for kw in keywords):
                matched_template = template_name
                strategy.entry_conditions = template["entry"]
                strategy.exit_conditions = template["exit"]
                break

        if not matched_template:
            strategy.entry_conditions = self._parse_conditions(description, "entry")
            strategy.exit_conditions = self._parse_conditions(description, "exit")

        strategy.position_management = self._parse_position_rules(description)
        strategy.risk_rules = self._parse_risk_rules(description)
        strategy.code = self._generate_code(strategy, matched_template)
        strategy.confidence = self._estimate_confidence(description, matched_template)

        return strategy

    def _extract_name(self, description: str) -> str:
        patterns = [
            r"策略[名称为：:]+[\"']?([^\"',，。]+)[\"']?",
            r"名为[\"']?([^\"',，。]+)[\"']?的?策略",
            r"([^,，。]+)策略",
        ]
        for pattern in patterns:
            match = re.search(pattern, description)
            if match:
                return match.group(1).strip()
        return "自定义策略"

    def _parse_conditions(self, description: str, direction: str) -> List[str]:
        conditions = []
        if direction == "entry":
            buy_patterns = [r"当(.+?)时买入", r"买入条件[为：:](.+?)(?:[，,]|$)", r"(.+?)金叉"]
            for pattern in buy_patterns:
                match = re.search(pattern, description)
                if match:
                    conditions.append(match.group(1).strip())
        elif direction == "exit":
            sell_patterns = [r"当(.+?)时卖出", r"卖出条件[为：:](.+?)(?:[，,]|$)", r"(.+?)死叉"]
            for pattern in sell_patterns:
                match = re.search(pattern, description)
                if match:
                    conditions.append(match.group(1).strip())

        if not conditions:
            for kw, tag in self._keyword_map.items():
                if kw in description:
                    if direction == "entry" and tag in ("golden_cross", "oversold", "breakout", "buy"):
                        conditions.append(f"{kw}触发")
                    elif direction == "exit" and tag in ("death_cross", "overbought", "breakdown", "sell"):
                        conditions.append(f"{kw}触发")

        return conditions[:5]

    def _parse_position_rules(self, description: str) -> List[str]:
        rules = []
        if "仓位" in description or "比例" in description:
            match = re.search(r"(\d+)%?仓位", description)
            if match:
                rules.append(f"仓位比例: {match.group(1)}%")
            else:
                rules.append("仓位比例: 30%")
        if "加仓" in description:
            rules.append("盈利加仓")
        if "减仓" in description:
            rules.append("亏损减仓")
        return rules

    def _parse_risk_rules(self, description: str) -> List[str]:
        rules = []
        stop_match = re.search(r"止损[为：:]*(\d+)%?", description)
        if stop_match:
            rules.append(f"止损: {stop_match.group(1)}%")
        tp_match = re.search(r"止盈[为：:]*(\d+)%?", description)
        if tp_match:
            rules.append(f"止盈: {tp_match.group(1)}%")
        if "最大回撤" in description:
            dd_match = re.search(r"最大回撤[不超过：:]*(\d+)%?", description)
            if dd_match:
                rules.append(f"最大回撤限制: {dd_match.group(1)}%")
        return rules

    def _generate_code(self, strategy: ParsedStrategy, template_name: Optional[str]) -> str:
        if template_name and template_name in STRATEGY_TEMPLATES:
            params = STRATEGY_TEMPLATES[template_name].get("params", {})
            params_str = ", ".join(f"{k}={v}" for k, v in params.items())
            return f"""from core.strategies import BaseStrategy, SignalType, TradeSignal, StrategyResult
import numpy as np
import pandas as pd

class {strategy.name.replace(' ', '')}Strategy(BaseStrategy):
    def __init__(self, {params_str}):
        super().__init__("{strategy.name}", "{strategy.description}")
        self.params = {{"{template_name}": {params}}}

    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        c = df['close'].values.astype(float)
        signals = []
        # TODO: 实现策略逻辑
        return StrategyResult(name=self.name, signals=signals)
"""
        return f"""# {strategy.name}
# {strategy.description}
# 入场条件: {', '.join(strategy.entry_conditions)}
# 出场条件: {', '.join(strategy.exit_conditions)}
# 风险规则: {', '.join(strategy.risk_rules)}
# 请根据以上条件实现策略逻辑
"""

    def generate(self, description: str) -> dict:
        parsed = self.parse(description)
        return {
            "success": True,
            "strategy": parsed.to_dict(),
        }

    def get_templates(self) -> list:
        return [
            {"name": name, **template}
            for name, template in STRATEGY_TEMPLATES.items()
        ]

    def validate_code(self, code: str) -> dict:
        try:
            compile(code, "<strategy>", "exec")
            return {"valid": True, "error": None}
        except SyntaxError as e:
            return {"valid": False, "error": f"SyntaxError: {e.msg} (line {e.lineno})"}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    def _estimate_confidence(self, description: str, matched_template: Optional[str]) -> float:
        score = 0.3
        if matched_template:
            score += 0.4
        keyword_count = sum(1 for kw in self._keyword_map if kw in description)
        score += min(keyword_count * 0.05, 0.2)
        if len(description) > 50:
            score += 0.1
        return min(score, 1.0)
