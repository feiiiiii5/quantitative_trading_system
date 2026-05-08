import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

from core.orders import Order, OrderSide

logger = logging.getLogger(__name__)


@dataclass
class PositionInfo:
    symbol: str
    quantity: int
    avg_cost: float
    market_value: float
    sector: str = ""
    buy_date: str = ""


@dataclass
class Portfolio:
    cash: float
    positions: dict[str, PositionInfo] = field(default_factory=dict)
    total_value: float = 0.0
    peak_value: float = 0.0
    daily_pnl: float = 0.0

    @property
    def current_drawdown(self) -> float:
        if self.peak_value > 0:
            return (self.peak_value - self.total_value) / self.peak_value
        return 0.0

    def position_weight(self, symbol: str) -> float:
        if self.total_value <= 0:
            return 0.0
        pos = self.positions.get(symbol)
        if pos is None:
            return 0.0
        return pos.market_value / self.total_value

    def sector_exposure(self, sector: str) -> float:
        if self.total_value <= 0:
            return 0.0
        sector_value = sum(
            p.market_value for p in self.positions.values() if p.sector == sector
        )
        return sector_value / self.total_value

    @property
    def position_count(self) -> int:
        return len(self.positions)


@dataclass
class RuleResult:
    rule_name: str
    is_violated: bool
    message: str = ""
    severity: str = "info"


@dataclass
class RiskCheckResult:
    approved: bool
    results: list[RuleResult] = field(default_factory=list)
    violations: list[RuleResult] = field(default_factory=list)

    @property
    def has_critical(self) -> bool:
        return any(v.severity == "critical" for v in self.violations)


class RiskRule(ABC):
    @abstractmethod
    def evaluate(self, order: Order, portfolio: Portfolio) -> RuleResult: ...


class ConcentrationRule(RiskRule):
    def __init__(self, max_weight: float = 0.10) -> None:
        self._max_weight = max_weight

    def evaluate(self, order: Order, portfolio: Portfolio) -> RuleResult:
        if order.side != OrderSide.BUY:
            return RuleResult(rule_name="ConcentrationRule", is_violated=False)
        if portfolio.total_value <= 0 or order.price is None or order.price <= 0:
            return RuleResult(
                rule_name="ConcentrationRule",
                is_violated=True,
                message="Invalid portfolio value or order price",
                severity="critical",
            )
        current_weight = portfolio.position_weight(order.symbol)
        order_value = order.quantity * order.price
        projected_weight = current_weight + order_value / portfolio.total_value
        if projected_weight > self._max_weight:
            return RuleResult(
                rule_name="ConcentrationRule",
                is_violated=True,
                message=(
                    f"Position {order.symbol} would reach "
                    f"{projected_weight:.1%} exceeding limit {self._max_weight:.1%}"
                ),
                severity="critical",
            )
        return RuleResult(rule_name="ConcentrationRule", is_violated=False)


class DrawdownCircuitBreaker(RiskRule):
    def __init__(self, max_drawdown: float = 0.15) -> None:
        self._max_drawdown = max_drawdown

    def evaluate(self, order: Order, portfolio: Portfolio) -> RuleResult:
        dd = portfolio.current_drawdown
        if dd > self._max_drawdown:
            return RuleResult(
                rule_name="DrawdownCircuitBreaker",
                is_violated=True,
                message=(
                    f"Drawdown {dd:.1%} exceeds circuit breaker "
                    f"threshold {self._max_drawdown:.1%}, all trading halted"
                ),
                severity="critical",
            )
        if dd > self._max_drawdown * 0.8:
            return RuleResult(
                rule_name="DrawdownCircuitBreaker",
                is_violated=False,
                message=f"Drawdown {dd:.1%} approaching circuit breaker threshold",
                severity="warning",
            )
        return RuleResult(rule_name="DrawdownCircuitBreaker", is_violated=False)


class DailyLossLimit(RiskRule):
    def __init__(self, max_daily_loss: float = 50000) -> None:
        self._max_daily_loss = max_daily_loss

    def evaluate(self, order: Order, portfolio: Portfolio) -> RuleResult:
        if portfolio.daily_pnl < -self._max_daily_loss:
            return RuleResult(
                rule_name="DailyLossLimit",
                is_violated=True,
                message=(
                    f"Daily loss {portfolio.daily_pnl:,.0f} exceeds "
                    f"limit {self._max_daily_loss:,.0f}"
                ),
                severity="critical",
            )
        if portfolio.daily_pnl < -self._max_daily_loss * 0.8:
            return RuleResult(
                rule_name="DailyLossLimit",
                is_violated=False,
                message="Daily loss approaching limit",
                severity="warning",
            )
        return RuleResult(rule_name="DailyLossLimit", is_violated=False)


class SectorExposureRule(RiskRule):
    def __init__(self, max_sector_pct: float = 0.30) -> None:
        self._max_sector_pct = max_sector_pct

    def evaluate(self, order: Order, portfolio: Portfolio) -> RuleResult:
        if order.side != OrderSide.BUY:
            return RuleResult(rule_name="SectorExposureRule", is_violated=False)
        order_sector = ""
        existing_pos = portfolio.positions.get(order.symbol)
        if existing_pos is not None:
            order_sector = existing_pos.sector
        if not order_sector:
            return RuleResult(rule_name="SectorExposureRule", is_violated=False)
        current_exposure = portfolio.sector_exposure(order_sector)
        if portfolio.total_value <= 0 or order.price is None or order.price <= 0:
            return RuleResult(
                rule_name="SectorExposureRule",
                is_violated=True,
                message="Invalid portfolio value or order price",
                severity="critical",
            )
        order_value = order.quantity * order.price
        projected_exposure = current_exposure + order_value / portfolio.total_value
        if projected_exposure > self._max_sector_pct:
            return RuleResult(
                rule_name="SectorExposureRule",
                is_violated=True,
                message=(
                    f"Sector '{order_sector}' exposure would reach "
                    f"{projected_exposure:.1%} exceeding limit {self._max_sector_pct:.1%}"
                ),
                severity="critical",
            )
        return RuleResult(rule_name="SectorExposureRule", is_violated=False)


class OrderSizeRule(RiskRule):
    def __init__(self, max_order_pct: float = 0.05) -> None:
        self._max_order_pct = max_order_pct

    def evaluate(self, order: Order, portfolio: Portfolio) -> RuleResult:
        if portfolio.total_value <= 0 or order.price is None or order.price <= 0:
            return RuleResult(
                rule_name="OrderSizeRule",
                is_violated=True,
                message="Invalid portfolio value or order price",
                severity="critical",
            )
        order_value = order.quantity * order.price
        order_pct = order_value / portfolio.total_value
        if order_pct > self._max_order_pct:
            return RuleResult(
                rule_name="OrderSizeRule",
                is_violated=True,
                message=(
                    f"Order size {order_pct:.1%} of portfolio exceeds "
                    f"limit {self._max_order_pct:.1%}"
                ),
                severity="warning",
            )
        return RuleResult(rule_name="OrderSizeRule", is_violated=False)


class PositionLimitRule(RiskRule):
    def __init__(self, max_positions: int = 20) -> None:
        self._max_positions = max_positions

    def evaluate(self, order: Order, portfolio: Portfolio) -> RuleResult:
        if order.side != OrderSide.BUY:
            return RuleResult(rule_name="PositionLimitRule", is_violated=False)
        if order.symbol in portfolio.positions:
            return RuleResult(rule_name="PositionLimitRule", is_violated=False)
        projected_count = portfolio.position_count + 1
        if projected_count > self._max_positions:
            return RuleResult(
                rule_name="PositionLimitRule",
                is_violated=True,
                message=(
                    f"Opening new position would reach {projected_count} "
                    f"exceeding limit {self._max_positions}"
                ),
                severity="critical",
            )
        return RuleResult(rule_name="PositionLimitRule", is_violated=False)


class PreTradeRiskEngine:
    def __init__(self, rules: list[RiskRule] | None = None) -> None:
        if rules is None:
            self.rules: list[RiskRule] = [
                ConcentrationRule(),
                DrawdownCircuitBreaker(),
                DailyLossLimit(),
                SectorExposureRule(),
                OrderSizeRule(),
                PositionLimitRule(),
            ]
        else:
            self.rules = list(rules)

    def check(self, order: Order, portfolio: Portfolio) -> RiskCheckResult:
        results: list[RuleResult] = []
        violations: list[RuleResult] = []
        for rule in self.rules:
            result = rule.evaluate(order, portfolio)
            results.append(result)
            if result.is_violated:
                violations.append(result)
                logger.warning(
                    "Risk rule violated: %s - %s", result.rule_name, result.message
                )
        approved = len(violations) == 0
        if not approved:
            logger.info(
                "Order %s rejected: %d rule(s) violated",
                order.order_id,
                len(violations),
            )
        return RiskCheckResult(approved=approved, results=results, violations=violations)

    def add_rule(self, rule: RiskRule) -> None:
        self.rules.append(rule)

    def remove_rule(self, rule_name: str) -> None:
        self.rules = [r for r in self.rules if r.__class__.__name__ != rule_name]


def historical_var(
    returns: np.ndarray | pd.Series,
    confidence: float = 0.95,
    horizon: int = 1,
) -> float:
    if len(returns) < 2:
        return 0.0
    arr = np.asarray(returns, dtype=float)
    alpha = 1.0 - confidence
    var_level = float(np.percentile(arr, alpha * 100))
    scaled_var = var_level * np.sqrt(horizon)
    return float(abs(scaled_var))


def historical_cvar(
    returns: np.ndarray | pd.Series,
    confidence: float = 0.95,
    horizon: int = 1,
) -> float:
    if len(returns) < 2:
        return 0.0
    arr = np.asarray(returns, dtype=float)
    alpha = 1.0 - confidence
    var_level = float(np.percentile(arr, alpha * 100))
    tail_losses = arr[arr <= var_level]
    if len(tail_losses) == 0:
        return float(abs(var_level * np.sqrt(horizon)))
    cvar_level = float(np.mean(tail_losses))
    return float(abs(cvar_level * np.sqrt(horizon)))


def parametric_var(
    returns: np.ndarray | pd.Series,
    confidence: float = 0.95,
    horizon: int = 1,
) -> float:
    if len(returns) < 2:
        return 0.0
    arr = np.asarray(returns, dtype=float)
    mu = float(np.mean(arr))
    sigma = float(np.std(arr, ddof=1))
    if sigma < 1e-12:
        return 0.0
    z_score = float(scipy_stats.norm.ppf(1.0 - confidence))
    var_level = mu + z_score * sigma
    return float(abs(var_level * np.sqrt(horizon)))


def parametric_cvar(
    returns: np.ndarray | pd.Series,
    confidence: float = 0.95,
    horizon: int = 1,
) -> float:
    if len(returns) < 2:
        return 0.0
    arr = np.asarray(returns, dtype=float)
    mu = float(np.mean(arr))
    sigma = float(np.std(arr, ddof=1))
    if sigma < 1e-12:
        return 0.0
    alpha = 1.0 - confidence
    z = float(scipy_stats.norm.ppf(alpha))
    pdf_val = float(scipy_stats.norm.pdf(z))
    cvar_level = mu - sigma * pdf_val / alpha
    return float(abs(cvar_level * np.sqrt(horizon)))


def monte_carlo_var(
    returns: np.ndarray | pd.Series,
    confidence: float = 0.95,
    horizon: int = 1,
    n_simulations: int = 10000,
) -> float:
    if len(returns) < 2:
        return 0.0
    arr = np.asarray(returns, dtype=float)
    mu = float(np.mean(arr))
    sigma = float(np.std(arr, ddof=1))
    if sigma < 1e-12:
        return 0.0
    rng = np.random.default_rng()
    simulated = rng.normal(mu, sigma, size=n_simulations)
    alpha = 1.0 - confidence
    var_level = float(np.percentile(simulated, alpha * 100))
    return float(abs(var_level * np.sqrt(horizon)))


def monte_carlo_cvar(
    returns: np.ndarray | pd.Series,
    confidence: float = 0.95,
    horizon: int = 1,
    n_simulations: int = 10000,
) -> float:
    if len(returns) < 2:
        return 0.0
    arr = np.asarray(returns, dtype=float)
    mu = float(np.mean(arr))
    sigma = float(np.std(arr, ddof=1))
    if sigma < 1e-12:
        return 0.0
    rng = np.random.default_rng()
    simulated = rng.normal(mu, sigma, size=n_simulations)
    alpha = 1.0 - confidence
    var_level = float(np.percentile(simulated, alpha * 100))
    tail = simulated[simulated <= var_level]
    if len(tail) == 0:
        return float(abs(var_level * np.sqrt(horizon)))
    cvar_level = float(np.mean(tail))
    return float(abs(cvar_level * np.sqrt(horizon)))


@dataclass
class StressScenario:
    name: str
    date_range: tuple[str, str]
    description: str
    market_shock: float


STRESS_SCENARIOS: list[StressScenario] = [
    StressScenario(
        "2008_financial_crisis",
        ("2008-09-01", "2009-03-01"),
        "Global Financial Crisis",
        -0.45,
    ),
    StressScenario(
        "2015_a_share_crash",
        ("2015-06-12", "2015-08-26"),
        "A-share market crash & circuit breaker",
        -0.40,
    ),
    StressScenario(
        "2020_covid",
        ("2020-02-19", "2020-03-23"),
        "COVID-19 market shock",
        -0.34,
    ),
    StressScenario(
        "2022_rate_hike",
        ("2022-01-01", "2022-10-31"),
        "Fed aggressive rate hikes",
        -0.25,
    ),
]


@dataclass
class StressTestResult:
    scenario_name: str
    projected_loss: float
    projected_loss_pct: float
    position_impacts: dict[str, float] = field(default_factory=dict)
    description: str = ""
    scenario_shock: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_name": self.scenario_name,
            "projected_loss": round(self.projected_loss, 2),
            "projected_loss_pct": round(self.projected_loss_pct, 4),
            "position_impacts": {k: round(v, 2) for k, v in self.position_impacts.items()},
            "description": self.description,
            "scenario_shock": self.scenario_shock,
        }


def run_stress_test(
    portfolio: Portfolio, scenario: StressScenario
) -> StressTestResult:
    total_projected_loss = 0.0
    position_impacts: dict[str, float] = {}
    for symbol, pos in portfolio.positions.items():
        position_loss = pos.market_value * scenario.market_shock
        total_projected_loss += position_loss
        position_impacts[symbol] = position_loss
    projected_loss_pct = (
        total_projected_loss / portfolio.total_value
        if portfolio.total_value > 0
        else 0.0
    )
    return StressTestResult(
        scenario_name=scenario.name,
        projected_loss=total_projected_loss,
        projected_loss_pct=projected_loss_pct,
        position_impacts=position_impacts,
        description=scenario.description,
        scenario_shock=scenario.market_shock,
    )


def run_all_stress_tests(
    portfolio: Portfolio,
    scenarios: list[StressScenario] | None = None,
) -> list[StressTestResult]:
    if scenarios is None:
        scenarios = STRESS_SCENARIOS
    return [run_stress_test(portfolio, s) for s in scenarios]


@dataclass
class CorrelationState:
    avg_correlation: float
    max_correlation: float
    min_correlation: float
    high_corr_pairs: list[tuple[str, str, float]] = field(default_factory=list)
    reduction_factor: float = 1.0
    is_mutation_detected: bool = False


class CorrelationMonitor:
    def __init__(self, lookback: int = 60, threshold: float = 0.7) -> None:
        self._lookback = lookback
        self._threshold = threshold
        self._history: list[pd.DataFrame] = []

    def update(self, returns_matrix: pd.DataFrame) -> CorrelationState:
        if len(returns_matrix.columns) < 2:
            return CorrelationState(
                avg_correlation=0.0,
                max_correlation=0.0,
                min_correlation=0.0,
            )
        window = returns_matrix.tail(self._lookback) if len(returns_matrix) > self._lookback else returns_matrix
        window = window.dropna()
        if len(window) < 10:
            return CorrelationState(
                avg_correlation=0.0,
                max_correlation=0.0,
                min_correlation=0.0,
            )
        corr_matrix = window.corr()
        symbols = list(corr_matrix.columns)
        n = len(symbols)
        if n < 2:
            return CorrelationState(
                avg_correlation=0.0,
                max_correlation=0.0,
                min_correlation=0.0,
            )
        pairwise_corrs: list[float] = []
        high_corr_pairs: list[tuple[str, str, float]] = []
        max_corr = -2.0
        min_corr = 2.0
        for i in range(n):
            for j in range(i + 1, n):
                val = float(corr_matrix.iloc[i, j])
                if not np.isfinite(val):
                    continue
                pairwise_corrs.append(val)
                if val > max_corr:
                    max_corr = val
                if val < min_corr:
                    min_corr = val
                if val > self._threshold:
                    high_corr_pairs.append((symbols[i], symbols[j], val))
        if not pairwise_corrs:
            return CorrelationState(
                avg_correlation=0.0,
                max_correlation=0.0,
                min_correlation=0.0,
            )
        avg_corr = float(np.mean(pairwise_corrs))
        reduction = self.compute_reduction_factor(avg_corr)
        is_mutation = avg_corr > self._threshold
        if is_mutation:
            logger.warning(
                "Correlation mutation detected: avg_corr=%.3f exceeds threshold=%.3f, "
                "reduction_factor=%.2f",
                avg_corr,
                self._threshold,
                reduction,
            )
        self._history.append(corr_matrix)
        if len(self._history) > 252:
            self._history = self._history[-252:]
        return CorrelationState(
            avg_correlation=avg_corr,
            max_correlation=max_corr,
            min_correlation=min_corr,
            high_corr_pairs=high_corr_pairs,
            reduction_factor=reduction,
            is_mutation_detected=is_mutation,
        )

    def compute_reduction_factor(self, avg_correlation: float) -> float:
        if avg_correlation <= self._threshold:
            return 1.0
        excess = (avg_correlation - self._threshold) / (1.0 - self._threshold)
        factor = 1.0 - min(excess, 1.0)
        return max(factor, 0.0)
