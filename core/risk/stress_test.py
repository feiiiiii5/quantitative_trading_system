import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class StressScenario:
    name: str
    description: str
    equity_shock: float = 0.0
    volatility_mult: float = 1.0
    correlation_break: bool = False
    liquidity_shock: float = 0.0
    duration_days: int = 30

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "equity_shock": self.equity_shock,
            "volatility_mult": self.volatility_mult,
            "correlation_break": self.correlation_break,
            "liquidity_shock": self.liquidity_shock,
            "duration_days": self.duration_days,
        }


BUILTIN_SCENARIOS = {
    "2008_financial_crisis": StressScenario(
        name="2008金融危机", description="雷曼兄弟破产引发的全球金融危机",
        equity_shock=-0.40, volatility_mult=3.5, correlation_break=True,
        liquidity_shock=0.3, duration_days=90,
    ),
    "2015_china_crash": StressScenario(
        name="2015中国股灾", description="A股异常波动与熔断机制",
        equity_shock=-0.35, volatility_mult=3.0, correlation_break=True,
        liquidity_shock=0.2, duration_days=30,
    ),
    "2020_covid": StressScenario(
        name="2020新冠疫情", description="COVID-19全球大流行导致的市场暴跌",
        equity_shock=-0.35, volatility_mult=2.8, correlation_break=False,
        liquidity_shock=0.15, duration_days=20,
    ),
    "flash_crash": StressScenario(
        name="闪电崩盘", description="2010年5月6日美股闪电崩盘",
        equity_shock=-0.10, volatility_mult=5.0, correlation_break=True,
        liquidity_shock=0.5, duration_days=1,
    ),
    "rate_hike_shock": StressScenario(
        name="加息冲击", description="超预期加息引发的市场调整",
        equity_shock=-0.15, volatility_mult=2.0, correlation_break=False,
        liquidity_shock=0.1, duration_days=60,
    ),
    "liquidity_crisis": StressScenario(
        name="流动性危机", description="市场流动性枯竭",
        equity_shock=-0.25, volatility_mult=2.5, correlation_break=True,
        liquidity_shock=0.6, duration_days=45,
    ),
}


@dataclass
class StressTestResult:
    scenario_name: str
    portfolio_loss: float = 0.0
    portfolio_loss_pct: float = 0.0
    max_drawdown: float = 0.0
    recovery_days: int = 0
    var_breach: bool = False
    liquidity_impact: float = 0.0
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "scenario_name": self.scenario_name,
            "portfolio_loss": round(self.portfolio_loss, 2),
            "portfolio_loss_pct": round(self.portfolio_loss_pct, 4),
            "max_drawdown": round(self.max_drawdown, 4),
            "recovery_days": self.recovery_days,
            "var_breach": self.var_breach,
            "liquidity_impact": round(self.liquidity_impact, 4),
            "details": self.details,
        }


class RiskStressTest:
    def __init__(self, confidence_level: float = 0.95):
        self.confidence_level = confidence_level
        self._custom_scenarios: Dict[str, StressScenario] = {}

    def add_scenario(self, scenario: StressScenario):
        self._custom_scenarios[scenario.name] = scenario

    def get_scenarios(self) -> Dict[str, dict]:
        all_scenarios = {**BUILTIN_SCENARIOS, **self._custom_scenarios}
        return {k: v.to_dict() for k, v in all_scenarios.items()}

    def run_scenario(
        self,
        scenario_name: str,
        positions: Dict[str, dict],
        returns_data: Optional[Dict[str, np.ndarray]] = None,
    ) -> StressTestResult:
        all_scenarios = {**BUILTIN_SCENARIOS, **self._custom_scenarios}
        scenario = all_scenarios.get(scenario_name)
        if not scenario:
            return StressTestResult(scenario_name=scenario_name)

        total_value = sum(p.get("value", 0) for p in positions.values())
        if total_value <= 0:
            return StressTestResult(scenario_name=scenario_name)

        portfolio_loss = 0.0
        position_details = {}

        for symbol, pos in positions.items():
            invested = pos.get("invested", 0)
            weight = invested / total_value if total_value > 0 else 0

            shock = scenario.equity_shock * weight
            vol_adj = 1.0
            if returns_data and symbol in returns_data:
                r = returns_data[symbol]
                if len(r) > 20:
                    current_vol = np.std(r[-20:])
                    base_vol = np.std(r) if len(r) > 60 else current_vol
                    if base_vol > 0:
                        vol_adj = current_vol / base_vol

            adjusted_shock = shock * scenario.volatility_mult * max(vol_adj, 0.5)
            position_loss = invested * adjusted_shock
            portfolio_loss += position_loss

            liquidity_cost = invested * scenario.liquidity_shock * 0.01

            position_details[symbol] = {
                "invested": round(invested, 2),
                "shock_pct": round(adjusted_shock * 100, 2),
                "loss": round(position_loss, 2),
                "liquidity_cost": round(liquidity_cost, 2),
            }

        total_liquidity = total_value * scenario.liquidity_shock * 0.01
        total_loss = portfolio_loss + total_liquidity
        loss_pct = total_loss / total_value if total_value > 0 else 0

        max_dd = abs(loss_pct)
        recovery_days = int(max_dd / 0.005) if max_dd > 0 else 0

        return StressTestResult(
            scenario_name=scenario.name,
            portfolio_loss=round(total_loss, 2),
            portfolio_loss_pct=loss_pct,
            max_drawdown=max_dd,
            recovery_days=recovery_days,
            var_breach=abs(loss_pct) > 0.05,
            liquidity_impact=total_liquidity / total_value if total_value > 0 else 0,
            details=position_details,
        )

    def run_all_scenarios(
        self,
        positions: Dict[str, dict],
        returns_data: Optional[Dict[str, np.ndarray]] = None,
    ) -> Dict[str, StressTestResult]:
        all_scenarios = {**BUILTIN_SCENARIOS, **self._custom_scenarios}
        results = {}
        for name in all_scenarios:
            results[name] = self.run_scenario(name, positions, returns_data)
        return results

    def run_custom_shock(
        self,
        positions: Dict[str, dict],
        shock_pct: float = -0.20,
        volatility_mult: float = 2.0,
        liquidity_shock: float = 0.1,
    ) -> StressTestResult:
        scenario = StressScenario(
            name="custom_shock",
            description=f"自定义冲击: {shock_pct:.0%}跌幅, {volatility_mult}x波动率",
            equity_shock=shock_pct,
            volatility_mult=volatility_mult,
            liquidity_shock=liquidity_shock,
        )
        self._custom_scenarios["custom_shock"] = scenario
        return self.run_scenario("custom_shock", positions)
