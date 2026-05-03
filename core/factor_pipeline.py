import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def winsorize(series: pd.Series, lower: float = 0.025, upper: float = 0.975) -> pd.Series:
    clipped = series.copy()
    valid = clipped.dropna()
    if len(valid) < 3:
        return clipped
    q_low = float(valid.quantile(lower))
    q_high = float(valid.quantile(upper))
    clipped = clipped.clip(lower=q_low, upper=q_high)
    return clipped


def winsorize_df(df: pd.DataFrame, lower: float = 0.025, upper: float = 0.975) -> pd.DataFrame:
    return df.apply(lambda col: winsorize(col, lower, upper) if np.issubdtype(col.dtype, np.number) else col)


def zscore_normalize(series: pd.Series) -> pd.Series:
    valid = series.dropna()
    if len(valid) < 2:
        return series.copy()
    mean = float(valid.mean())
    std = float(valid.std())
    if std < 1e-12:
        return pd.Series(0.0, index=series.index)
    return (series - mean) / std


def zscore_normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    return df.apply(lambda col: zscore_normalize(col) if np.issubdtype(col.dtype, np.number) else col)


def rank_normalize(series: pd.Series) -> pd.Series:
    valid_mask = series.notna()
    ranked = series.copy().astype(float)
    if valid_mask.sum() < 2:
        return ranked
    ranked[valid_mask] = series[valid_mask].rank(pct=True)
    return ranked


def rank_normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    return df.apply(lambda col: rank_normalize(col) if np.issubdtype(col.dtype, np.number) else col)


def industry_neutralize(
    factor_series: pd.Series,
    industry_labels: pd.Series,
) -> pd.Series:
    if len(factor_series) != len(industry_labels):
        logger.warning("factor_series and industry_labels length mismatch")
        return factor_series.copy()
    result = factor_series.copy()
    groups = industry_labels.groupby(industry_labels)
    for name, idx in groups.groups.items():
        if len(idx) < 2:
            continue
        group_vals = factor_series.loc[idx]
        mean_val = group_vals.mean()
        if group_vals.std() < 1e-12:
            result.loc[idx] = 0.0
        else:
            result.loc[idx] = group_vals - mean_val
    return result


def market_cap_neutralize(
    factor_series: pd.Series,
    market_cap: pd.Series,
) -> pd.Series:
    valid = factor_series.notna() & market_cap.notna() & (market_cap > 0)
    if valid.sum() < 5:
        return factor_series.copy()
    result = factor_series.copy()
    log_mc = np.log(market_cap[valid])
    x = log_mc.values
    y = factor_series[valid].values
    x_mean = x.mean()
    y_mean = y.mean()
    denom = np.sum((x - x_mean) ** 2)
    if denom < 1e-12:
        return result
    beta = np.sum((x - x_mean) * (y - y_mean)) / denom
    alpha = y_mean - beta * x_mean
    residuals = y - (alpha + beta * x)
    result[valid] = residuals
    return result


def orthogonalize(
    factor_df: pd.DataFrame,
    reference_col: str = None,
) -> pd.DataFrame:
    if factor_df.empty or len(factor_df.columns) < 2:
        return factor_df.copy()
    result = factor_df.copy()
    numeric_cols = [c for c in result.columns if np.issubdtype(result[c].dtype, np.number)]
    if len(numeric_cols) < 2:
        return result

    if reference_col is None:
        reference_col = numeric_cols[0]
    if reference_col not in numeric_cols:
        return result

    ref = result[reference_col].fillna(0).values
    ref_mean = ref.mean()
    ref_centered = ref - ref_mean
    ref_ss = np.dot(ref_centered, ref_centered)
    if ref_ss < 1e-12:
        return result

    for col in numeric_cols:
        if col == reference_col:
            continue
        target = result[col].fillna(0).values
        target_mean = target.mean()
        target_centered = target - target_mean
        proj = np.dot(target_centered, ref_centered) / ref_ss
        orthogonalized = target - proj * ref_centered
        result[col] = orthogonalized
    return result


def full_factor_pipeline(
    factor_df: pd.DataFrame,
    industry_labels: pd.Series = None,
    market_cap: pd.Series = None,
    winsorize_bounds: Tuple[float, float] = (0.025, 0.975),
    neutralize_method: str = "zscore",
) -> pd.DataFrame:
    if factor_df.empty:
        return factor_df

    result = factor_df.copy()
    numeric_cols = [c for c in result.columns if np.issubdtype(result[c].dtype, np.number)]

    for col in numeric_cols:
        result[col] = winsorize(result[col], winsorize_bounds[0], winsorize_bounds[1])

    if neutralize_method == "zscore":
        for col in numeric_cols:
            result[col] = zscore_normalize(result[col])
    elif neutralize_method == "rank":
        for col in numeric_cols:
            result[col] = rank_normalize(result[col])

    if industry_labels is not None:
        for col in numeric_cols:
            result[col] = industry_neutralize(result[col], industry_labels)

    if market_cap is not None:
        for col in numeric_cols:
            result[col] = market_cap_neutralize(result[col], market_cap)

    if len(numeric_cols) >= 2:
        result = orthogonalize(result, numeric_cols[0])

    return result
