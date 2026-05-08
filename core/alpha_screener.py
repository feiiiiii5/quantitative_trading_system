import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from core.alpha_engine import AlphaResult

logger = logging.getLogger(__name__)


@dataclass
class AlphaScreeningConfig:
    ic_threshold: float = 0.02
    ic_ir_threshold: float = 0.3
    turnover_max: float = 0.8
    decay_max: float = 0.5
    ic_window: int = 20
    forward_periods: list[int] = field(default_factory=lambda: [1, 5, 10])


def calc_ic(
    factor_values: pd.Series,
    forward_returns: pd.Series,
    method: str = "pearson",
) -> float:
    valid = factor_values.notna() & forward_returns.notna()
    if valid.sum() < 10:
        return 0.0
    x = factor_values[valid].values
    y = forward_returns[valid].values
    if method == "spearman":
        try:
            from scipy.stats import spearmanr
            corr, _ = spearmanr(x, y)
            return float(corr) if np.isfinite(corr) else 0.0
        except Exception as e:
            logger.debug("Spearman相关计算失败: %s", e)
            return 0.0
    else:
        std_x = np.std(x)
        std_y = np.std(y)
        if std_x < 1e-12 or std_y < 1e-12:
            return 0.0
        return float(np.corrcoef(x, y)[0, 1])


def calc_rolling_ic(
    factor_values: pd.Series,
    forward_returns: pd.Series,
    window: int = 20,
) -> tuple[float, float]:
    valid = factor_values.notna() & forward_returns.notna()
    if valid.sum() < window * 2:
        ic = calc_ic(factor_values, forward_returns)
        return ic, 0.0 if abs(ic) < 1e-12 else 999.0

    f_vals = factor_values.values.astype(float)
    r_vals = forward_returns.values.astype(float)
    mask = np.isfinite(f_vals) & np.isfinite(r_vals)

    ic_arr = _vectorized_rolling_corr(f_vals, r_vals, mask, window)
    if ic_arr is None or len(ic_arr) == 0:
        return 0.0, 0.0

    mean_ic = float(np.nanmean(ic_arr))
    std_ic = float(np.nanstd(ic_arr))
    ic_ir = mean_ic / std_ic if std_ic > 1e-12 else 0.0
    return mean_ic, ic_ir


def _vectorized_rolling_corr(
    x: np.ndarray,
    y: np.ndarray,
    mask: np.ndarray,
    window: int,
) -> np.ndarray:
    n = len(x)
    if n < window * 2:
        return np.array([])

    result = np.full(n, np.nan)
    min_valid = 5

    cumsum_x = np.zeros(n + 1)
    cumsum_y = np.zeros(n + 1)
    cumsum_xy = np.zeros(n + 1)
    cumsum_x2 = np.zeros(n + 1)
    cumsum_y2 = np.zeros(n + 1)
    cumsum_count = np.zeros(n + 1, dtype=int)

    for i in range(n):
        cumsum_x[i + 1] = cumsum_x[i] + (x[i] if mask[i] else 0.0)
        cumsum_y[i + 1] = cumsum_y[i] + (y[i] if mask[i] else 0.0)
        cumsum_xy[i + 1] = cumsum_xy[i] + (x[i] * y[i] if mask[i] else 0.0)
        cumsum_x2[i + 1] = cumsum_x2[i] + (x[i] ** 2 if mask[i] else 0.0)
        cumsum_y2[i + 1] = cumsum_y2[i] + (y[i] ** 2 if mask[i] else 0.0)
        cumsum_count[i + 1] = cumsum_count[i] + (1 if mask[i] else 0)

    for i in range(window, n):
        count = cumsum_count[i] - cumsum_count[i - window]
        if count < min_valid:
            continue

        x_sum = cumsum_x[i] - cumsum_x[i - window]
        y_sum = cumsum_y[i] - cumsum_y[i - window]
        xy_sum = cumsum_xy[i] - cumsum_xy[i - window]
        x2_sum = cumsum_x2[i] - cumsum_x2[i - window]
        y2_sum = cumsum_y2[i] - cumsum_y2[i - window]

        var_x = x2_sum - x_sum ** 2 / count
        var_y = y2_sum - y_sum ** 2 / count
        if var_x < 0 or var_y < 0:
            continue
        denom_sq = var_x * var_y
        if denom_sq < 1e-24:
            continue
        corr = (xy_sum - x_sum * y_sum / count) / np.sqrt(denom_sq)
        result[i] = corr if np.isfinite(corr) else 0.0

    return result


def calc_turnover(factor_values: pd.Series, period: int = 1) -> float:
    ranked = factor_values.rank(pct=True)
    valid = ranked.notna() & ranked.shift(period).notna()
    if valid.sum() < 5:
        return 0.0
    current = ranked[valid]
    previous = ranked.shift(period)[valid]
    changed = (current - previous).abs() > 0.01
    return float(changed.sum() / len(current))


def calc_decay(
    factor_values: pd.Series,
    forward_returns: pd.Series,
    max_lag: int = 10,
) -> float:
    if factor_values.notna().sum() < max_lag + 10:
        return 0.0
    ics = []
    for lag in range(1, max_lag + 1):
        shifted_returns = forward_returns.shift(-lag)
        ic = calc_ic(factor_values, shifted_returns)
        ics.append(abs(ic))
    if not ics or ics[0] < 1e-12:
        return 0.0
    half_life = 0
    for i, ic_val in enumerate(ics):
        if ic_val < ics[0] / 2:
            half_life = i + 1
            break
    if half_life == 0:
        half_life = max_lag
    decay_rate = 1.0 / half_life
    return float(decay_rate)


class AlphaScreener:
    def __init__(self, config: AlphaScreeningConfig | None = None):
        self._config = config or AlphaScreeningConfig()

    def screen_alpha(
        self,
        name: str,
        factor_values: pd.Series,
        close: pd.Series,
        category: str = "",
        description: str = "",
    ) -> AlphaResult:
        forward_returns = close.pct_change(self._config.forward_periods[0]).shift(-1)

        ic, ic_ir = calc_rolling_ic(
            factor_values, forward_returns, self._config.ic_window
        )
        turnover = calc_turnover(factor_values)
        decay = calc_decay(factor_values, forward_returns)

        passed = (
            abs(ic) >= self._config.ic_threshold
            and abs(ic_ir) >= self._config.ic_ir_threshold
            and turnover <= self._config.turnover_max
            and decay <= self._config.decay_max
        )

        return AlphaResult(
            name=name,
            values=factor_values,
            ic=round(ic, 4),
            ic_ir=round(ic_ir, 4),
            turnover=round(turnover, 4),
            decay=round(decay, 4),
            passed=passed,
            category=category,
            description=description,
        )

    def screen_all(
        self,
        alpha_values: dict[str, pd.Series],
        close: pd.Series,
        alpha_meta: dict[str, dict] = None,
    ) -> dict[str, AlphaResult]:
        results = {}
        for name, values in alpha_values.items():
            meta = (alpha_meta or {}).get(name, {})
            result = self.screen_alpha(
                name=name,
                factor_values=values,
                close=close,
                category=meta.get("category", ""),
                description=meta.get("description", ""),
            )
            results[name] = result
        return results

    def filter_passed(self, results: dict[str, AlphaResult]) -> dict[str, AlphaResult]:
        return {k: v for k, v in results.items() if v.passed}

    def rank_by_ic_ir(self, results: dict[str, AlphaResult]) -> list[tuple[str, AlphaResult]]:
        sorted_results = sorted(
            results.items(),
            key=lambda x: abs(x[1].ic_ir),
            reverse=True,
        )
        return sorted_results

    def get_screening_report(self, results: dict[str, AlphaResult]) -> dict:
        total = len(results)
        passed = sum(1 for r in results.values() if r.passed)
        by_category = {}
        for _name, r in results.items():
            cat = r.category or "uncategorized"
            if cat not in by_category:
                by_category[cat] = {"total": 0, "passed": 0}
            by_category[cat]["total"] += 1
            if r.passed:
                by_category[cat]["passed"] += 1

        top_alphas = self.rank_by_ic_ir(results)[:10]
        return {
            "total_alphas": total,
            "passed_alphas": passed,
            "pass_rate": round(passed / max(total, 1), 4),
            "by_category": by_category,
            "top_alphas": [
                {
                    "name": name,
                    "ic": r.ic,
                    "ic_ir": r.ic_ir,
                    "turnover": r.turnover,
                    "decay": r.decay,
                    "passed": r.passed,
                }
                for name, r in top_alphas
            ],
        }
