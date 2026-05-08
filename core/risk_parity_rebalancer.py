import logging
from dataclasses import dataclass, field

import numpy as np

from core.portfolio_optimizer import risk_parity_optimize

logger = logging.getLogger(__name__)


@dataclass
class RebalanceTrade:
    symbol: str
    name: str
    current_weight: float
    target_weight: float
    weight_delta: float
    action: str
    shares: int = 0
    price: float = 0.0


@dataclass
class RebalanceResult:
    trades: list[RebalanceTrade] = field(default_factory=list)
    total_turnover: float = 0.0
    max_drift: float = 0.0
    needs_rebalance: bool = False
    reason: str = ""


class RiskParityRebalancer:
    """风险平价再平衡引擎

    比较当前持仓权重与风险平价最优权重，
    当偏离超过阈值时生成调仓建议。
    """

    DRIFT_THRESHOLD = 0.05
    TURNOVER_CAP = 0.30

    def __init__(
        self,
        drift_threshold: float = 0.05,
        turnover_cap: float = 0.30,
    ):
        self._drift_threshold = drift_threshold
        self._turnover_cap = turnover_cap

    def analyze(
        self,
        positions: list[dict],
        cov_matrix: np.ndarray,
        prices: dict[str, float] | None = None,
        capital: float = 100000,
    ) -> RebalanceResult:
        if not positions or len(positions) < 2:
            return RebalanceResult(reason="持仓不足2只，无法再平衡")

        n = len(positions)
        if cov_matrix.shape != (n, n):
            return RebalanceResult(reason="协方差矩阵维度不匹配")

        symbols = [p["symbol"] for p in positions]
        names = [p.get("name", p["symbol"]) for p in positions]
        current_weights = np.array([p.get("weight", 0) for p in positions], dtype=float)

        weight_sum = np.sum(current_weights)
        if weight_sum < 1e-10:
            return RebalanceResult(reason="当前权重总和为零")
        current_weights = current_weights / weight_sum

        try:
            target_weights = risk_parity_optimize(cov_matrix)
        except Exception as e:
            logger.debug("风险平价优化失败: %s", e)
            return RebalanceResult(reason=f"优化失败: {e}")

        if len(target_weights) != n:
            return RebalanceResult(reason="优化结果维度不匹配")

        drifts = np.abs(current_weights - target_weights)
        max_drift = float(np.max(drifts))
        needs_rebalance = max_drift >= self._drift_threshold

        trades = []
        total_turnover = 0.0
        for i in range(n):
            delta = float(target_weights[i] - current_weights[i])
            if abs(delta) < 0.001:
                continue
            action = "buy" if delta > 0 else "sell"
            price = (prices or {}).get(symbols[i], 0)
            shares = 0
            if price > 0 and capital > 0:
                shares = int(abs(delta) * capital / price / 100) * 100
            trades.append(RebalanceTrade(
                symbol=symbols[i],
                name=names[i],
                current_weight=round(float(current_weights[i]), 4),
                target_weight=round(float(target_weights[i]), 4),
                weight_delta=round(delta, 4),
                action=action,
                shares=shares,
                price=price,
            ))
            total_turnover += abs(delta)

        if total_turnover > self._turnover_cap:
            scale = self._turnover_cap / total_turnover
            for t in trades:
                t.weight_delta = round(t.weight_delta * scale, 4)
                t.shares = int(t.shares * scale / 100) * 100
            total_turnover = self._turnover_cap

        return RebalanceResult(
            trades=trades,
            total_turnover=round(total_turnover, 4),
            max_drift=round(max_drift, 4),
            needs_rebalance=needs_rebalance,
            reason=f"最大偏离{max_drift:.1%}" + ("，需调仓" if needs_rebalance else "，暂无需调仓"),
        )
