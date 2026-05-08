import logging
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class RiskMetrics:
    var_historic_95: float = 0.0
    var_historic_99: float = 0.0
    var_monte_carlo_95: float = 0.0
    var_monte_carlo_99: float = 0.0
    cvar_95: float = 0.0
    cvar_99: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    calmar_ratio: float = 0.0
    sortino_ratio: float = 0.0
    omega_ratio: float = 0.0
    annual_volatility: float = 0.0
    sharpe_ratio: float = 0.0
    skewness: float = 0.0
    kurtosis: float = 0.0


@dataclass
class DrawdownInfo:
    peak_value: float
    trough_value: float
    peak_date_idx: int
    trough_date_idx: int
    recovery_date_idx: int | None
    drawdown_pct: float
    duration_days: int | None


def calc_max_drawdown(equity_curve: list[float] | np.ndarray) -> tuple[float, float, DrawdownInfo | None]:
    if isinstance(equity_curve, list):
        equity_curve = np.array(equity_curve)
    if len(equity_curve) < 2:
        return 0.0, 0.0, None

    running_max = np.maximum.accumulate(equity_curve)
    drawdowns = (running_max - equity_curve) / running_max
    max_dd = float(np.max(drawdowns))
    max_dd_idx = int(np.argmax(drawdowns))
    peak_idx = int(np.argmax(equity_curve[: max_dd_idx + 1]))

    trough_value = float(equity_curve[max_dd_idx])
    peak_value = float(equity_curve[peak_idx])

    recovery_idx = None
    if max_dd_idx < len(equity_curve) - 1:
        post_trough = equity_curve[max_dd_idx:]
        if np.any(post_trough >= peak_value):
            recovery_idx = max_dd_idx + int(np.argmax(post_trough >= peak_value))

    drawdown_info = DrawdownInfo(
        peak_value=peak_value,
        trough_value=trough_value,
        peak_date_idx=peak_idx,
        trough_date_idx=max_dd_idx,
        recovery_date_idx=recovery_idx,
        drawdown_pct=max_dd,
        duration_days=(recovery_idx - max_dd_idx) if recovery_idx else None,
    )

    return float(np.max(equity_curve) - float(np.min(equity_curve))), max_dd, drawdown_info


def calc_calmar_ratio(returns: list[float] | np.ndarray, annual_return: float, equity_curve: list[float] | np.ndarray) -> float:
    if isinstance(returns, list):
        returns = np.array(returns)
    _, max_dd_pct, _ = calc_max_drawdown(equity_curve)
    if max_dd_pct < 1e-10:
        return 0.0
    return annual_return / max_dd_pct


def calc_sortino_ratio(returns: list[float] | np.ndarray, target_return: float = 0.0, risk_free_rate: float = 0.0, periods_per_year: int = 252) -> float:
    if isinstance(returns, list):
        returns = np.array(returns)
    if len(returns) < 5:
        return 0.0

    excess_returns = returns - risk_free_rate / periods_per_year
    downside_returns = excess_returns[excess_returns < target_return]

    if len(downside_returns) == 0 or np.std(downside_returns) < 1e-12:
        return 0.0

    downside_std = float(np.std(downside_returns, ddof=1)) * np.sqrt(periods_per_year)
    if downside_std < 1e-12:
        return 0.0

    annual_excess_return = float(np.mean(excess_returns)) * periods_per_year
    return annual_excess_return / downside_std


def calc_omega_ratio(returns: list[float] | np.ndarray, threshold: float = 0.0) -> float:
    if isinstance(returns, list):
        returns = np.array(returns)
    if len(returns) < 2:
        return 1.0

    gains = returns[returns > threshold]
    losses = abs(returns[returns < threshold])

    if len(losses) == 0:
        return float("inf") if len(gains) > 0 else 1.0

    gain_sum = float(np.sum(gains))
    loss_sum = float(np.sum(losses))

    if loss_sum < 1e-12:
        return float("inf") if gain_sum > 0 else 1.0

    return gain_sum / loss_sum


def calc_monte_carlo_var(
    returns: list[float] | np.ndarray,
    portfolio_value: float,
    confidence_level: float = 0.95,
    n_simulations: int = 10000,
    seed: int = 42,
) -> float:
    if isinstance(returns, list):
        returns = np.array(returns)
    if len(returns) < 10:
        return 0.0

    rng = np.random.RandomState(seed)
    mean_ret = float(np.mean(returns))
    std_ret = float(np.std(returns, ddof=1))
    if std_ret < 1e-12:
        return 0.0

    simulated_returns = rng.normal(mean_ret, std_ret, n_simulations)
    var_percentile = np.percentile(simulated_returns, (1 - confidence_level) * 100)
    return float(abs(var_percentile * portfolio_value))


def calc_historic_var(returns: list[float] | np.ndarray, portfolio_value: float, confidence_level: float = 0.95) -> float:
    if isinstance(returns, list):
        returns = np.array(returns)
    if len(returns) < 5:
        return 0.0

    var_percentile = np.percentile(returns, (1 - confidence_level) * 100)
    return float(abs(var_percentile * portfolio_value))


def calc_cvar(
    returns: list[float] | np.ndarray,
    portfolio_value: float,
    confidence_level: float = 0.95,
) -> float:
    if isinstance(returns, list):
        returns = np.array(returns)
    if len(returns) < 5:
        return 0.0

    var_threshold = np.percentile(returns, (1 - confidence_level) * 100)
    tail_losses = returns[returns <= var_threshold]

    if len(tail_losses) == 0:
        return calc_historic_var(returns, portfolio_value, confidence_level)

    return float(abs(float(np.mean(tail_losses)) * portfolio_value))


def calc_all_risk_metrics(
    returns: list[float] | np.ndarray,
    equity_curve: list[float] | np.ndarray,
    portfolio_value: float,
    annual_return: float,
    risk_free_rate: float = 0.03,
    periods_per_year: int = 252,
) -> RiskMetrics:
    if isinstance(returns, list):
        returns = np.array(returns)
    if isinstance(equity_curve, list):
        equity_curve = np.array(equity_curve)

    n = len(returns)
    if n < 5:
        return RiskMetrics()

    annual_vol = float(np.std(returns, ddof=1)) * np.sqrt(periods_per_year)
    daily_rf = risk_free_rate / periods_per_year
    excess_returns = returns - daily_rf
    annual_excess = float(np.mean(excess_returns)) * periods_per_year
    sharpe = annual_excess / annual_vol if annual_vol > 1e-12 else 0.0

    var_95 = calc_historic_var(returns, portfolio_value, 0.95)
    var_99 = calc_historic_var(returns, portfolio_value, 0.99)
    mc_var_95 = calc_monte_carlo_var(returns, portfolio_value, 0.95)
    mc_var_99 = calc_monte_carlo_var(returns, portfolio_value, 0.99)
    cvar_95 = calc_cvar(returns, portfolio_value, 0.95)
    cvar_99 = calc_cvar(returns, portfolio_value, 0.99)

    _, max_dd_pct, drawdown_info = calc_max_drawdown(equity_curve)
    calmar = calc_calmar_ratio(returns, annual_return, equity_curve)
    sortino = calc_sortino_ratio(returns, 0.0, risk_free_rate, periods_per_year)
    omega = calc_omega_ratio(returns, 0.0)

    skewness = float(np.mean(((returns - np.mean(returns)) / (np.std(returns, ddof=1) + 1e-12)) ** 3)) if np.std(returns, ddof=1) > 1e-12 else 0.0
    kurt = float(np.mean(((returns - np.mean(returns)) / (np.std(returns, ddof=1) + 1e-12)) ** 4)) - 3 if np.std(returns, ddof=1) > 1e-12 else 0.0

    return RiskMetrics(
        var_historic_95=round(var_95, 2),
        var_historic_99=round(var_99, 2),
        var_monte_carlo_95=round(mc_var_95, 2),
        var_monte_carlo_99=round(mc_var_99, 2),
        cvar_95=round(cvar_95, 2),
        cvar_99=round(cvar_99, 2),
        max_drawdown=round(float(np.max(equity_curve) - float(np.min(equity_curve))), 2),
        max_drawdown_pct=round(max_dd_pct * 100, 2),
        calmar_ratio=round(calmar, 3),
        sortino_ratio=round(sortino, 3),
        omega_ratio=round(omega, 3),
        annual_volatility=round(annual_vol * 100, 2),
        sharpe_ratio=round(sharpe, 3),
        skewness=round(skewness, 3),
        kurtosis=round(kurt, 3),
    )


def generate_risk_report(metrics: RiskMetrics, portfolio_value: float) -> dict:
    return {
        "portfolio_value": round(portfolio_value, 2),
        "value_at_risk": {
            "historic_95": metrics.var_historic_95,
            "historic_99": metrics.var_historic_99,
            "monte_carlo_95": metrics.var_monte_carlo_95,
            "monte_carlo_99": metrics.var_monte_carlo_99,
        },
        "conditional_var": {
            "cvar_95": metrics.cvar_95,
            "cvar_99": metrics.cvar_99,
        },
        "drawdown": {
            "max_drawdown": metrics.max_drawdown,
            "max_drawdown_pct": metrics.max_drawdown_pct,
        },
        "risk_adjusted_returns": {
            "calmar_ratio": metrics.calmar_ratio,
            "sortino_ratio": metrics.sortino_ratio,
            "omega_ratio": metrics.omega_ratio,
            "sharpe_ratio": metrics.sharpe_ratio,
        },
        "distribution": {
            "annual_volatility_pct": metrics.annual_volatility,
            "skewness": metrics.skewness,
            "kurtosis": metrics.kurtosis,
        },
    }
