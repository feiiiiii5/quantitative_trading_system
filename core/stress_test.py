"""
QuantCore 组合压力测试模块
提供蒙特卡洛模拟、历史情景回放、自定义情景分析
评估组合在不同市场环境下的风险暴露和潜在损失
"""
import logging
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class StressScenario:
    name: str
    description: str
    equity_shock: float = 0.0
    bond_shock: float = 0.0
    commodity_shock: float = 0.0
    volatility_mult: float = 1.0
    correlation_shift: float = 0.0


@dataclass
class MonteCarloResult:
    n_simulations: int
    horizon_days: int
    initial_value: float
    final_values: np.ndarray
    var_95: float
    var_99: float
    cvar_95: float
    cvar_99: float
    max_loss: float
    max_gain: float
    prob_loss: float
    expected_shortfall: float

    def summary(self) -> dict:
        return {
            "n_simulations": self.n_simulations,
            "horizon_days": self.horizon_days,
            "initial_value": round(self.initial_value, 2),
            "var_95": round(self.var_95, 2),
            "var_99": round(self.var_99, 2),
            "cvar_95": round(self.cvar_95, 2),
            "cvar_99": round(self.cvar_99, 2),
            "max_loss_pct": round(self.max_loss / self.initial_value * 100, 2) if self.initial_value > 0 else 0,
            "max_gain_pct": round(self.max_gain / self.initial_value * 100, 2) if self.initial_value > 0 else 0,
            "prob_loss_pct": round(self.prob_loss * 100, 1),
            "expected_shortfall_pct": round(self.expected_shortfall / self.initial_value * 100, 2) if self.initial_value > 0 else 0,
        }


@dataclass
class ScenarioResult:
    scenario_name: str
    portfolio_impact_pct: float
    position_impacts: dict = field(default_factory=dict)
    description: str = ""

    def summary(self) -> dict:
        return {
            "scenario_name": self.scenario_name,
            "portfolio_impact_pct": round(self.portfolio_impact_pct, 2),
            "position_impacts": {k: round(v, 2) for k, v in self.position_impacts.items()},
            "description": self.description,
        }


PREDEFINED_SCENARIOS = [
    StressScenario(
        name="2008金融危机",
        description="模拟2008年全球金融危机：股市暴跌、波动率飙升、相关性趋同",
        equity_shock=-0.45,
        bond_shock=0.05,
        commodity_shock=-0.30,
        volatility_mult=3.5,
        correlation_shift=0.4,
    ),
    StressScenario(
        name="2020疫情冲击",
        description="模拟2020年3月新冠疫情冲击：快速下跌后V型反弹",
        equity_shock=-0.35,
        bond_shock=-0.02,
        commodity_shock=-0.25,
        volatility_mult=4.0,
        correlation_shift=0.3,
    ),
    StressScenario(
        name="利率骤升",
        description="模拟利率快速上升：债券大跌、成长股承压",
        equity_shock=-0.15,
        bond_shock=-0.20,
        commodity_shock=0.05,
        volatility_mult=2.0,
        correlation_shift=0.1,
    ),
    StressScenario(
        name="黑天鹅事件",
        description="极端尾部风险：单日大幅下跌、流动性枯竭",
        equity_shock=-0.25,
        bond_shock=-0.10,
        commodity_shock=-0.20,
        volatility_mult=5.0,
        correlation_shift=0.5,
    ),
    StressScenario(
        name="温和回调",
        description="正常市场回调：10%修正、波动率适度上升",
        equity_shock=-0.10,
        bond_shock=0.02,
        commodity_shock=-0.05,
        volatility_mult=1.5,
        correlation_shift=0.1,
    ),
]


class PortfolioStressTester:
    """组合压力测试引擎"""

    def __init__(self, seed: int = 42):
        self._rng = np.random.default_rng(seed)

    def monte_carlo(
        self,
        returns: np.ndarray,
        weights: np.ndarray,
        portfolio_value: float,
        horizon_days: int = 20,
        n_simulations: int = 10000,
    ) -> MonteCarloResult:
        """蒙特卡洛模拟

        Args:
            returns: 历史收益率矩阵 (n_days, n_assets)
            weights: 资产权重向量 (n_assets,)
            portfolio_value: 当前组合市值
            horizon_days: 模拟天数
            n_simulations: 模拟次数

        Returns:
            MonteCarloResult
        """
        if len(returns) < 30 or len(weights) == 0:
            return MonteCarloResult(
                n_simulations=0, horizon_days=horizon_days,
                initial_value=portfolio_value, final_values=np.array([]),
                var_95=0, var_99=0, cvar_95=0, cvar_99=0,
                max_loss=0, max_gain=0, prob_loss=0, expected_shortfall=0,
            )

        mean_ret = np.mean(returns, axis=0)
        cov_matrix = np.cov(returns, rowvar=False)
        if cov_matrix.ndim == 0:
            cov_matrix = np.array([[float(cov_matrix)]])

        n_assets = len(weights)
        if len(mean_ret) != n_assets or cov_matrix.shape[0] != n_assets:
            return MonteCarloResult(
                n_simulations=0, horizon_days=horizon_days,
                initial_value=portfolio_value, final_values=np.array([]),
                var_95=0, var_99=0, cvar_95=0, cvar_99=0,
                max_loss=0, max_gain=0, prob_loss=0, expected_shortfall=0,
            )

        try:
            chol_mat = np.linalg.cholesky(cov_matrix + np.eye(n_assets) * 1e-8)
        except np.linalg.LinAlgError:
            chol_mat = np.linalg.cholesky(np.eye(n_assets) * np.mean(np.diag(cov_matrix)))

        z = self._rng.standard_normal((horizon_days, n_simulations, n_assets))
        correlated = z @ chol_mat.T
        daily_returns = mean_ret + correlated

        port_daily = daily_returns @ weights
        cum_returns = np.cumprod(1 + port_daily, axis=0)
        final_values = portfolio_value * cum_returns[-1]

        pnl = final_values - portfolio_value
        pnl_pct = pnl / portfolio_value if portfolio_value > 0 else pnl

        sorted_pnl = np.sort(pnl_pct)
        n = len(sorted_pnl)
        var_95_idx = max(int(n * 0.05), 0)
        var_99_idx = max(int(n * 0.01), 0)

        var_95 = abs(sorted_pnl[var_95_idx]) * portfolio_value
        var_99 = abs(sorted_pnl[var_99_idx]) * portfolio_value
        cvar_95 = abs(np.mean(sorted_pnl[:var_95_idx + 1])) * portfolio_value if var_95_idx > 0 else var_95
        cvar_99 = abs(np.mean(sorted_pnl[:var_99_idx + 1])) * portfolio_value if var_99_idx > 0 else var_99

        max_loss = float(np.min(pnl))
        max_gain = float(np.max(pnl))
        prob_loss = float(np.mean(pnl < 0))
        expected_shortfall = cvar_95

        return MonteCarloResult(
            n_simulations=n_simulations,
            horizon_days=horizon_days,
            initial_value=portfolio_value,
            final_values=final_values,
            var_95=var_95,
            var_99=var_99,
            cvar_95=cvar_95,
            cvar_99=cvar_99,
            max_loss=max_loss,
            max_gain=max_gain,
            prob_loss=prob_loss,
            expected_shortfall=expected_shortfall,
        )

    def run_scenario(
        self,
        positions: list[dict],
        scenario: StressScenario,
    ) -> ScenarioResult:
        """运行单个压力情景

        Args:
            positions: 持仓列表 [{"symbol": ..., "value": ..., "type": "equity"/"bond"/"commodity"}]
            scenario: 压力情景

        Returns:
            ScenarioResult
        """
        total_impact = 0.0
        total_value = 0.0
        position_impacts = {}

        shock_map = {
            "equity": scenario.equity_shock,
            "bond": scenario.bond_shock,
            "commodity": scenario.commodity_shock,
        }

        for pos in positions:
            symbol = pos.get("symbol", "?")
            value = float(pos.get("value", 0))
            asset_type = pos.get("type", "equity")
            shock = shock_map.get(asset_type, scenario.equity_shock)
            impact = value * shock
            total_impact += impact
            total_value += value
            position_impacts[symbol] = impact / value * 100 if value > 0 else 0

        portfolio_impact_pct = total_impact / total_value * 100 if total_value > 0 else 0

        return ScenarioResult(
            scenario_name=scenario.name,
            portfolio_impact_pct=portfolio_impact_pct,
            position_impacts=position_impacts,
            description=scenario.description,
        )

    def run_all_scenarios(
        self,
        positions: list[dict],
        scenarios: list[StressScenario] | None = None,
    ) -> list[dict]:
        """运行所有预定义压力情景

        Args:
            positions: 持仓列表
            scenarios: 自定义情景列表，默认使用预定义情景

        Returns:
            情景结果列表
        """
        if scenarios is None:
            scenarios = PREDEFINED_SCENARIOS
        results = []
        for scenario in scenarios:
            result = self.run_scenario(positions, scenario)
            results.append(result.summary())
        return results

    def custom_scenario(
        self,
        positions: list[dict],
        equity_shock: float = 0.0,
        bond_shock: float = 0.0,
        commodity_shock: float = 0.0,
        name: str = "自定义情景",
    ) -> ScenarioResult:
        """创建并运行自定义压力情景

        Args:
            positions: 持仓列表
            equity_shock: 股票冲击比例
            bond_shock: 债券冲击比例
            commodity_shock: 商品冲击比例
            name: 情景名称

        Returns:
            ScenarioResult
        """
        scenario = StressScenario(
            name=name,
            description=f"自定义情景: 股票{equity_shock*100:+.0f}%, 债券{bond_shock*100:+.0f}%, 商品{commodity_shock*100:+.0f}%",
            equity_shock=equity_shock,
            bond_shock=bond_shock,
            commodity_shock=commodity_shock,
        )
        return self.run_scenario(positions, scenario)


_stress_tester: PortfolioStressTester | None = None


def get_stress_tester() -> PortfolioStressTester:
    global _stress_tester
    if _stress_tester is None:
        _stress_tester = PortfolioStressTester()
    return _stress_tester
