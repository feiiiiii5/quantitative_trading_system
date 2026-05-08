import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

import numpy as np
import pandas as pd
from scipy.optimize import minimize

logger = logging.getLogger(__name__)


class FactorCategory(Enum):
    VALUE = "value"
    GROWTH = "growth"
    QUALITY = "quality"
    MOMENTUM = "momentum"
    LOW_VOLATILITY = "low_volatility"
    LIQUIDITY = "liquidity"
    TECHNICAL = "technical"


@dataclass
class FactorDefinition:
    name: str
    category: FactorCategory
    description: str
    compute_fn: Callable[[pd.DataFrame], pd.Series]


def _pe_ratio(df: pd.DataFrame) -> pd.Series:
    return df.get("pe_ratio", pd.Series(np.nan, index=df.index))


def _pb_ratio(df: pd.DataFrame) -> pd.Series:
    return df.get("pb_ratio", pd.Series(np.nan, index=df.index))


def _ps_ratio(df: pd.DataFrame) -> pd.Series:
    return df.get("ps_ratio", pd.Series(np.nan, index=df.index))


def _pcf_ratio(df: pd.DataFrame) -> pd.Series:
    return df.get("pcf_ratio", pd.Series(np.nan, index=df.index))


def _ev_ebitda(df: pd.DataFrame) -> pd.Series:
    ev = df.get("ev", pd.Series(np.nan, index=df.index))
    ebitda = df.get("ebitda", pd.Series(np.nan, index=df.index))
    result = ev / ebitda.replace(0, np.nan)
    return result


def _dividend_yield(df: pd.DataFrame) -> pd.Series:
    dividend = df.get("dividend", pd.Series(0.0, index=df.index))
    price = df.get("close", pd.Series(np.nan, index=df.index))
    result = dividend / price.replace(0, np.nan)
    return result


def _book_to_market(df: pd.DataFrame) -> pd.Series:
    bv = df.get("book_value", pd.Series(np.nan, index=df.index))
    mv = df.get("market_cap", pd.Series(np.nan, index=df.index))
    result = bv / mv.replace(0, np.nan)
    return result


def _revenue_growth(df: pd.DataFrame) -> pd.Series:
    rev = df.get("revenue", pd.Series(np.nan, index=df.index))
    rev_prev = df.get("revenue_prev", pd.Series(np.nan, index=df.index))
    result = (rev - rev_prev) / rev_prev.replace(0, np.nan)
    return result


def _earnings_growth(df: pd.DataFrame) -> pd.Series:
    earnings = df.get("earnings", pd.Series(np.nan, index=df.index))
    earnings_prev = df.get("earnings_prev", pd.Series(np.nan, index=df.index))
    result = (earnings - earnings_prev) / earnings_prev.replace(0, np.nan)
    return result


def _roe_change(df: pd.DataFrame) -> pd.Series:
    roe = df.get("roe", pd.Series(np.nan, index=df.index))
    roe_prev = df.get("roe_prev", pd.Series(np.nan, index=df.index))
    return roe - roe_prev


def _eps_growth(df: pd.DataFrame) -> pd.Series:
    eps = df.get("eps", pd.Series(np.nan, index=df.index))
    eps_prev = df.get("eps_prev", pd.Series(np.nan, index=df.index))
    result = (eps - eps_prev) / eps_prev.replace(0, np.nan)
    return result


def _roe(df: pd.DataFrame) -> pd.Series:
    return df.get("roe", pd.Series(np.nan, index=df.index))


def _roa(df: pd.DataFrame) -> pd.Series:
    return df.get("roa", pd.Series(np.nan, index=df.index))


def _gross_margin(df: pd.DataFrame) -> pd.Series:
    gp = df.get("gross_profit", pd.Series(np.nan, index=df.index))
    rev = df.get("revenue", pd.Series(np.nan, index=df.index))
    result = gp / rev.replace(0, np.nan)
    return result


def _current_ratio(df: pd.DataFrame) -> pd.Series:
    ca = df.get("current_assets", pd.Series(np.nan, index=df.index))
    cl = df.get("current_liabilities", pd.Series(np.nan, index=df.index))
    result = ca / cl.replace(0, np.nan)
    return result


def _debt_to_equity(df: pd.DataFrame) -> pd.Series:
    td = df.get("total_debt", pd.Series(np.nan, index=df.index))
    te = df.get("total_equity", pd.Series(np.nan, index=df.index))
    result = td / te.replace(0, np.nan)
    return result


def _accruals(df: pd.DataFrame) -> pd.Series:
    ni = df.get("net_income", pd.Series(np.nan, index=df.index))
    ocf = df.get("operating_cash_flow", pd.Series(np.nan, index=df.index))
    ta = df.get("total_assets", pd.Series(np.nan, index=df.index))
    result = (ni - ocf) / ta.replace(0, np.nan)
    return result


def _return_1m(df: pd.DataFrame) -> pd.Series:
    close = df.get("close", pd.Series(np.nan, index=df.index))
    close_prev_1m = df.get("close_prev_1m", pd.Series(np.nan, index=df.index))
    result = close / close_prev_1m.replace(0, np.nan) - 1.0
    return result


def _return_3m(df: pd.DataFrame) -> pd.Series:
    close = df.get("close", pd.Series(np.nan, index=df.index))
    close_prev_3m = df.get("close_prev_3m", pd.Series(np.nan, index=df.index))
    result = close / close_prev_3m.replace(0, np.nan) - 1.0
    return result


def _return_6m(df: pd.DataFrame) -> pd.Series:
    close = df.get("close", pd.Series(np.nan, index=df.index))
    close_prev_6m = df.get("close_prev_6m", pd.Series(np.nan, index=df.index))
    result = close / close_prev_6m.replace(0, np.nan) - 1.0
    return result


def _return_12m(df: pd.DataFrame) -> pd.Series:
    close = df.get("close", pd.Series(np.nan, index=df.index))
    close_prev_12m = df.get("close_prev_12m", pd.Series(np.nan, index=df.index))
    result = close / close_prev_12m.replace(0, np.nan) - 1.0
    return result


def _price_momentum(df: pd.DataFrame) -> pd.Series:
    r6 = _return_6m(df)
    r1 = _return_1m(df)
    return r6 - r1


def _earnings_momentum(df: pd.DataFrame) -> pd.Series:
    eps_surprise = df.get("eps_surprise", pd.Series(np.nan, index=df.index))
    return eps_surprise


def _vol_20d(df: pd.DataFrame) -> pd.Series:
    return df.get("vol_20d", pd.Series(np.nan, index=df.index))


def _vol_60d(df: pd.DataFrame) -> pd.Series:
    return df.get("vol_60d", pd.Series(np.nan, index=df.index))


def _vol_120d(df: pd.DataFrame) -> pd.Series:
    return df.get("vol_120d", pd.Series(np.nan, index=df.index))


def _beta_factor(df: pd.DataFrame) -> pd.Series:
    return df.get("beta", pd.Series(np.nan, index=df.index))


def _downside_deviation(df: pd.DataFrame) -> pd.Series:
    returns = df.get("daily_returns", pd.Series(np.nan, index=df.index))
    if returns.isna().all():
        return pd.Series(np.nan, index=df.index)
    negative = returns.where(returns < 0, np.nan)
    result = negative.std()
    return pd.Series(result, index=df.index) if np.isscalar(result) else negative.std()


def _turnover_rate(df: pd.DataFrame) -> pd.Series:
    vol = df.get("volume", pd.Series(np.nan, index=df.index))
    shares = df.get("shares_outstanding", pd.Series(np.nan, index=df.index))
    result = vol / shares.replace(0, np.nan)
    return result


def _amihud_illiquidity(df: pd.DataFrame) -> pd.Series:
    returns = df.get("daily_returns", pd.Series(np.nan, index=df.index))
    dollar_vol = df.get("dollar_volume", pd.Series(np.nan, index=df.index))
    if returns.isna().all() or dollar_vol.isna().all():
        return pd.Series(np.nan, index=df.index)
    abs_ret = returns.abs()
    safe_dv = dollar_vol.replace(0, np.nan)
    result = (abs_ret / safe_dv).mean() if not (abs_ret / safe_dv).isna().all() else np.nan
    return pd.Series(result, index=df.index) if np.isscalar(result) else (abs_ret / safe_dv).mean()


def _volume_ratio(df: pd.DataFrame) -> pd.Series:
    vol = df.get("volume", pd.Series(np.nan, index=df.index))
    vol_avg = df.get("volume_avg_20d", pd.Series(np.nan, index=df.index))
    result = vol / vol_avg.replace(0, np.nan)
    return result


def _bid_ask_spread_proxy(df: pd.DataFrame) -> pd.Series:
    high = df.get("high", pd.Series(np.nan, index=df.index))
    low = df.get("low", pd.Series(np.nan, index=df.index))
    close = df.get("close", pd.Series(np.nan, index=df.index))
    result = (high - low) / close.replace(0, np.nan)
    return result


def _rsi_factor(df: pd.DataFrame) -> pd.Series:
    return df.get("rsi_14", pd.Series(np.nan, index=df.index))


def _macd_signal(df: pd.DataFrame) -> pd.Series:
    return df.get("macd", pd.Series(np.nan, index=df.index))


def _bollinger_position(df: pd.DataFrame) -> pd.Series:
    close = df.get("close", pd.Series(np.nan, index=df.index))
    upper = df.get("bollinger_upper", pd.Series(np.nan, index=df.index))
    lower = df.get("bollinger_lower", pd.Series(np.nan, index=df.index))
    result = (close - lower) / (upper - lower).replace(0, np.nan)
    return result


def _atr_ratio(df: pd.DataFrame) -> pd.Series:
    atr = df.get("atr_14", pd.Series(np.nan, index=df.index))
    close = df.get("close", pd.Series(np.nan, index=df.index))
    result = atr / close.replace(0, np.nan)
    return result


def _obv_trend(df: pd.DataFrame) -> pd.Series:
    return df.get("obv_slope", pd.Series(np.nan, index=df.index))


FACTOR_REGISTRY: dict[str, FactorDefinition] = {
    "pe_ratio": FactorDefinition("pe_ratio", FactorCategory.VALUE, "Price-to-earnings ratio", _pe_ratio),
    "pb_ratio": FactorDefinition("pb_ratio", FactorCategory.VALUE, "Price-to-book ratio", _pb_ratio),
    "ps_ratio": FactorDefinition("ps_ratio", FactorCategory.VALUE, "Price-to-sales ratio", _ps_ratio),
    "pcf_ratio": FactorDefinition("pcf_ratio", FactorCategory.VALUE, "Price-to-cash-flow ratio", _pcf_ratio),
    "ev_ebitda": FactorDefinition("ev_ebitda", FactorCategory.VALUE, "EV/EBITDA", _ev_ebitda),
    "dividend_yield": FactorDefinition("dividend_yield", FactorCategory.VALUE, "Dividend yield", _dividend_yield),
    "book_to_market": FactorDefinition("book_to_market", FactorCategory.VALUE, "Book-to-market ratio", _book_to_market),
    "revenue_growth": FactorDefinition("revenue_growth", FactorCategory.GROWTH, "YoY revenue growth", _revenue_growth),
    "earnings_growth": FactorDefinition("earnings_growth", FactorCategory.GROWTH, "YoY earnings growth", _earnings_growth),
    "roe_change": FactorDefinition("roe_change", FactorCategory.GROWTH, "Change in ROE", _roe_change),
    "eps_growth": FactorDefinition("eps_growth", FactorCategory.GROWTH, "YoY EPS growth", _eps_growth),
    "roe": FactorDefinition("roe", FactorCategory.QUALITY, "Return on equity", _roe),
    "roa": FactorDefinition("roa", FactorCategory.QUALITY, "Return on assets", _roa),
    "gross_margin": FactorDefinition("gross_margin", FactorCategory.QUALITY, "Gross profit margin", _gross_margin),
    "current_ratio": FactorDefinition("current_ratio", FactorCategory.QUALITY, "Current ratio", _current_ratio),
    "debt_to_equity": FactorDefinition("debt_to_equity", FactorCategory.QUALITY, "Debt-to-equity ratio", _debt_to_equity),
    "accruals": FactorDefinition("accruals", FactorCategory.QUALITY, "Accruals / total assets", _accruals),
    "return_1m": FactorDefinition("return_1m", FactorCategory.MOMENTUM, "1-month return", _return_1m),
    "return_3m": FactorDefinition("return_3m", FactorCategory.MOMENTUM, "3-month return", _return_3m),
    "return_6m": FactorDefinition("return_6m", FactorCategory.MOMENTUM, "6-month return", _return_6m),
    "return_12m": FactorDefinition("return_12m", FactorCategory.MOMENTUM, "12-month return", _return_12m),
    "price_momentum": FactorDefinition("price_momentum", FactorCategory.MOMENTUM, "6m-1m momentum", _price_momentum),
    "earnings_momentum": FactorDefinition("earnings_momentum", FactorCategory.MOMENTUM, "Earnings surprise", _earnings_momentum),
    "vol_20d": FactorDefinition("vol_20d", FactorCategory.LOW_VOLATILITY, "20-day realized volatility", _vol_20d),
    "vol_60d": FactorDefinition("vol_60d", FactorCategory.LOW_VOLATILITY, "60-day realized volatility", _vol_60d),
    "vol_120d": FactorDefinition("vol_120d", FactorCategory.LOW_VOLATILITY, "120-day realized volatility", _vol_120d),
    "beta_factor": FactorDefinition("beta_factor", FactorCategory.LOW_VOLATILITY, "Market beta", _beta_factor),
    "downside_deviation": FactorDefinition("downside_deviation", FactorCategory.LOW_VOLATILITY, "Downside deviation", _downside_deviation),
    "turnover_rate": FactorDefinition("turnover_rate", FactorCategory.LIQUIDITY, "Share turnover rate", _turnover_rate),
    "amihud_illiquidity": FactorDefinition("amihud_illiquidity", FactorCategory.LIQUIDITY, "Amihud illiquidity measure", _amihud_illiquidity),
    "volume_ratio": FactorDefinition("volume_ratio", FactorCategory.LIQUIDITY, "Volume / 20d avg volume", _volume_ratio),
    "bid_ask_spread_proxy": FactorDefinition("bid_ask_spread_proxy", FactorCategory.LIQUIDITY, "High-low spread proxy", _bid_ask_spread_proxy),
    "rsi_factor": FactorDefinition("rsi_factor", FactorCategory.TECHNICAL, "14-day RSI", _rsi_factor),
    "macd_signal": FactorDefinition("macd_signal", FactorCategory.TECHNICAL, "MACD signal line", _macd_signal),
    "bollinger_position": FactorDefinition("bollinger_position", FactorCategory.TECHNICAL, "Bollinger band position", _bollinger_position),
    "atr_ratio": FactorDefinition("atr_ratio", FactorCategory.TECHNICAL, "ATR / price", _atr_ratio),
    "obv_trend": FactorDefinition("obv_trend", FactorCategory.TECHNICAL, "OBV trend slope", _obv_trend),
}


@dataclass
class FactorTestResult:
    factor_name: str
    mean_ic: float
    icir: float
    ic_decay: list[float]
    turnover: float
    long_short_return: float
    long_short_sharpe: float
    monotonicity: float


def factor_ic_analysis(
    factor_values: pd.Series,
    forward_returns: pd.Series,
    max_lag: int = 20,
    n_quintiles: int = 5,
    risk_free_rate: float = 0.03,
) -> FactorTestResult:
    valid = factor_values.notna() & forward_returns.notna()
    if valid.sum() < 10:
        logger.warning("Insufficient valid observations for IC analysis: %d", valid.sum())
        return FactorTestResult(
            factor_name=factor_values.name or "unknown",
            mean_ic=0.0, icir=0.0, ic_decay=[0.0] * min(max_lag, 20),
            turnover=0.0, long_short_return=0.0, long_short_sharpe=0.0, monotonicity=0.0,
        )

    fv = factor_values[valid]
    fr = forward_returns[valid]

    from scipy.stats import spearmanr
    ic_val, _ = spearmanr(fv, fr)
    ic_val = float(ic_val) if not np.isnan(ic_val) else 0.0

    ic_series = _compute_rolling_ic(fv, fr)
    mean_ic = float(ic_series.mean()) if len(ic_series) > 0 else ic_val
    ic_std = float(ic_series.std()) if len(ic_series) > 1 else 1.0
    icir = mean_ic / ic_std if abs(ic_std) > 1e-12 else 0.0

    ic_decay = _compute_ic_decay(fv, fr, max_lag)

    quintile_result = quintile_return_test(fv, fr, n_quintiles)

    top_ret = quintile_result.get(n_quintiles - 1, 0.0)
    bottom_ret = quintile_result.get(0, 0.0)
    ls_ret = top_ret - bottom_ret

    ls_sharpe = ls_ret / (abs(ls_ret) * 0.5 + 1e-12) if abs(ls_ret) > 1e-12 else 0.0
    if abs(ls_ret) > 1e-12:
        ls_sharpe = (ls_ret - risk_free_rate) / (abs(ls_ret) * 0.3 + 1e-12)

    monotonicity = _compute_monotonicity(quintile_result)

    turnover = _compute_factor_turnover(fv)

    return FactorTestResult(
        factor_name=factor_values.name or "unknown",
        mean_ic=mean_ic,
        icir=icir,
        ic_decay=ic_decay,
        turnover=turnover,
        long_short_return=ls_ret,
        long_short_sharpe=ls_sharpe,
        monotonicity=monotonicity,
    )


def _compute_rolling_ic(
    factor_values: pd.Series,
    forward_returns: pd.Series,
    window: int = 20,
) -> pd.Series:
    from scipy.stats import spearmanr
    n = len(factor_values)
    if n < window:
        ic_val, _ = spearmanr(factor_values, forward_returns)
        return pd.Series([float(ic_val)] if not np.isnan(ic_val) else [0.0])

    ics: list[float] = []
    for i in range(0, n - window + 1, max(1, window // 4)):
        chunk_fv = factor_values.iloc[i : i + window]
        chunk_fr = forward_returns.iloc[i : i + window]
        valid = chunk_fv.notna() & chunk_fr.notna()
        if valid.sum() < 5:
            ics.append(0.0)
            continue
        ic_val, _ = spearmanr(chunk_fv[valid], chunk_fr[valid])
        ics.append(float(ic_val) if not np.isnan(ic_val) else 0.0)

    return pd.Series(ics)


def _compute_ic_decay(
    factor_values: pd.Series,
    forward_returns: pd.Series,
    max_lag: int,
) -> list[float]:
    from scipy.stats import spearmanr
    decay: list[float] = []
    n = len(forward_returns)
    for lag in range(1, min(max_lag + 1, n)):
        if lag >= n:
            decay.append(0.0)
            continue
        shifted_fr = forward_returns.shift(-lag)
        valid = factor_values.notna() & shifted_fr.notna()
        if valid.sum() < 5:
            decay.append(0.0)
            continue
        ic_val, _ = spearmanr(factor_values[valid], shifted_fr[valid])
        decay.append(float(ic_val) if not np.isnan(ic_val) else 0.0)
    return decay


def _compute_monotonicity(quintile_returns: dict[int, float]) -> float:
    if len(quintile_returns) < 2:
        return 0.0
    sorted_rets = [quintile_returns[k] for k in sorted(quintile_returns.keys())]
    n = len(sorted_rets)
    concordant = 0
    discordant = 0
    for i in range(n):
        for j in range(i + 1, n):
            diff = sorted_rets[j] - sorted_rets[i]
            if diff > 0:
                concordant += 1
            elif diff < 0:
                discordant += 1
    total = concordant + discordant
    if total == 0:
        return 0.0
    return (concordant - discordant) / total


def _compute_factor_turnover(factor_values: pd.Series) -> float:
    ranked = factor_values.rank(pct=True)
    top_mask = ranked >= 0.8
    if top_mask.sum() < 2:
        return 1.0
    return 0.5


def quintile_return_test(
    factor_values: pd.Series,
    forward_returns: pd.Series,
    n_quintiles: int = 5,
) -> dict[int, float]:
    valid = factor_values.notna() & forward_returns.notna()
    if valid.sum() < n_quintiles:
        return dict.fromkeys(range(n_quintiles), 0.0)

    fv = factor_values[valid].copy()
    fr = forward_returns[valid].copy()

    try:
        quantile_labels = pd.qcut(fv.rank(method="first"), n_quintiles, labels=False)
    except ValueError:
        return dict.fromkeys(range(n_quintiles), 0.0)

    result: dict[int, float] = {}
    for q in range(n_quintiles):
        mask = quantile_labels == q
        if mask.sum() == 0:
            result[q] = 0.0
        else:
            result[q] = float(fr[mask].mean())

    return result


def barra_neutralize(
    factor_values: pd.Series,
    industry_labels: pd.Series,
    market_cap: pd.Series,
    style_factors: pd.DataFrame | None = None,
) -> pd.Series:
    valid = factor_values.notna() & industry_labels.notna() & market_cap.notna() & (market_cap > 0)
    if valid.sum() < 20:
        logger.warning("Insufficient observations for Barra neutralization: %d", valid.sum())
        return factor_values.copy()

    fv = factor_values[valid].copy()
    ind = industry_labels[valid].copy()
    mc = market_cap[valid].copy()

    industries = ind.unique()
    n_industries = len(industries)

    industry_dummies = pd.DataFrame(0, index=fv.index, columns=[f"ind_{i}" for i in range(n_industries)], dtype=float)
    for i, ind_val in enumerate(industries):
        industry_dummies.loc[ind == ind_val, f"ind_{i}"] = 1.0

    log_mc = np.log(mc)
    log_mc_z = (log_mc - log_mc.mean()) / (log_mc.std() + 1e-12)

    x_parts: list[pd.DataFrame] = [industry_dummies, pd.DataFrame({"log_mc": log_mc_z.values}, index=fv.index)]
    if style_factors is not None:
        style_valid = style_factors.reindex(fv.index)
        for col in style_valid.columns:
            col_vals = style_valid[col]
            if col_vals.notna().sum() > 0:
                col_z = (col_vals - col_vals.mean()) / (col_vals.std() + 1e-12)
                x_parts.append(pd.DataFrame({col: col_z.fillna(0).values}, index=fv.index))

    x = pd.concat(x_parts, axis=1)
    x["intercept"] = 1.0

    weights = mc.values
    weights = weights / weights.sum()

    x_w = x.values * np.sqrt(weights)[:, np.newaxis]
    y_w = fv.values * np.sqrt(weights)

    try:
        beta, _, _, _ = np.linalg.lstsq(x_w, y_w, rcond=None)
        fitted = x.values @ beta
        residuals = fv.values - fitted
    except np.linalg.LinAlgError:
        logger.warning("WLS regression failed in Barra neutralization")
        return factor_values.copy()

    result = factor_values.copy().astype(float)
    result[valid] = residuals
    return result


def optimize_with_factor_exposure(
    expected_returns: np.ndarray,
    cov_matrix: np.ndarray,
    factor_exposures: np.ndarray,
    factor_constraints: np.ndarray,
    max_weight: float = 0.05,
    min_weight: float = 0.0,
    risk_free_rate: float = 0.03,
    lambda_risk: float = 1.0,
) -> np.ndarray:
    n = len(expected_returns)
    if n == 0:
        return np.array([])
    if n == 1:
        return np.array([min(max_weight, 1.0)])

    cov = cov_matrix.copy()
    if cov.shape != (n, n):
        cov = np.eye(n) * 0.01
    eigvals = np.linalg.eigvalsh(cov)
    if np.min(eigvals) < 1e-10:
        cov += np.eye(n) * 1e-8

    if factor_exposures.ndim == 1:
        factor_exposures = factor_exposures.reshape(1, -1)

    if len(factor_constraints) != factor_exposures.shape[0]:
        logger.warning("factor_constraints length mismatch with factor_exposures rows, ignoring constraints")
        factor_constraints = np.zeros(factor_exposures.shape[0])

    bounds = [(min_weight, max_weight)] * n
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]

    for i in range(factor_exposures.shape[0]):
        target = float(factor_constraints[i])
        exposures_i = factor_exposures[i]
        constraints.append({
            "type": "eq",
            "fun": lambda w, exp=exposures_i, t=target: float(w @ exp) - t,
        })

    def objective(w: np.ndarray) -> float:
        port_ret = w @ expected_returns
        port_var = w @ cov @ w
        return -port_ret + lambda_risk * port_var

    best_obj = np.inf
    best_weights = np.ones(n) / n

    starting_points = [np.ones(n) / n]
    rng = np.random.RandomState(42)
    for _ in range(5):
        perturbed = np.ones(n) / n + rng.normal(0, 0.01, n)
        perturbed = np.clip(perturbed, min_weight, max_weight)
        if np.sum(perturbed) > 0:
            perturbed = perturbed / np.sum(perturbed)
        starting_points.append(perturbed)

    for w0 in starting_points:
        try:
            result = minimize(
                objective, w0, method="SLSQP",
                bounds=bounds, constraints=constraints,
                options={"maxiter": 300, "ftol": 1e-10},
            )
            if result.success or result.fun < best_obj:
                w = np.clip(result.x, min_weight, max_weight)
                if np.sum(w) > 0:
                    w = w / np.sum(w)
                obj_val = objective(w)
                if obj_val < best_obj:
                    best_obj = obj_val
                    best_weights = w.copy()
        except Exception as e:
            logger.debug("Factor-constrained optimization iteration failed: %s", e)
            continue

    best_weights = np.clip(best_weights, min_weight, max_weight)
    best_weights = best_weights / np.sum(best_weights) if np.sum(best_weights) > 0 else np.ones(n) / n

    return best_weights


@dataclass
class RotationSignal:
    factor_name: str
    recent_ic: float
    long_term_ic: float
    ic_change: float
    recommendation: str


class FactorRotationDetector:
    def __init__(
        self,
        recent_window: int = 60,
        long_term_window: int = 252,
        ic_threshold: float = 0.02,
    ) -> None:
        self._recent_window = recent_window
        self._long_term_window = long_term_window
        self._ic_threshold = ic_threshold

    def detect_rotation(
        self,
        factor_name: str,
        factor_values_ts: pd.DataFrame,
        forward_returns_ts: pd.DataFrame,
    ) -> RotationSignal:
        recent_ic = self._compute_period_ic(
            factor_values_ts, forward_returns_ts,
            min(len(factor_values_ts), self._recent_window),
        )
        long_term_ic = self._compute_period_ic(
            factor_values_ts, forward_returns_ts,
            min(len(factor_values_ts), self._long_term_window),
        )

        ic_change = recent_ic - long_term_ic

        if ic_change > self._ic_threshold:
            recommendation = "overweight"
        elif ic_change < -self._ic_threshold:
            recommendation = "underweight"
        else:
            recommendation = "neutral"

        return RotationSignal(
            factor_name=factor_name,
            recent_ic=recent_ic,
            long_term_ic=long_term_ic,
            ic_change=ic_change,
            recommendation=recommendation,
        )

    def detect_rotation_multi(
        self,
        factor_names: list[str],
        factor_values_ts: pd.DataFrame,
        forward_returns_ts: pd.DataFrame,
    ) -> list[RotationSignal]:
        signals: list[RotationSignal] = []
        for name in factor_names:
            if name not in factor_values_ts.columns:
                logger.warning("Factor '%s' not found in factor_values_ts", name)
                continue
            signal = self.detect_rotation(name, factor_values_ts, forward_returns_ts)
            signals.append(signal)
        return signals

    def _compute_period_ic(
        self,
        factor_values_ts: pd.DataFrame,
        forward_returns_ts: pd.DataFrame,
        period: int,
    ) -> float:
        from scipy.stats import spearmanr

        n_periods = len(factor_values_ts)
        start = max(0, n_periods - period)
        fv_slice = factor_values_ts.iloc[start:]
        fr_slice = forward_returns_ts.iloc[start:]

        ics: list[float] = []
        for i in range(len(fv_slice)):
            fv_row = fv_slice.iloc[i]
            fr_row = fr_slice.iloc[i]
            valid = fv_row.notna() & fr_row.notna()
            if valid.sum() < 5:
                continue
            ic_val, _ = spearmanr(fv_row[valid], fr_row[valid])
            if not np.isnan(ic_val):
                ics.append(float(ic_val))

        if len(ics) == 0:
            return 0.0
        return float(np.mean(ics))
