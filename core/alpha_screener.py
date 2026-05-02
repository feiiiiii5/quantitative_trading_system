import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

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
    forward_periods: List[int] = field(default_factory=lambda: [1, 5, 10])


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
        except Exception:
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
) -> Tuple[float, float]:
    valid = factor_values.notna() & forward_returns.notna()
    if valid.sum() < window * 2:
        ic = calc_ic(factor_values, forward_returns)
        return ic, 0.0 if abs(ic) < 1e-12 else float("inf")

    ic_list = []
    f_vals = factor_values.values.astype(float)
    r_vals = forward_returns.values.astype(float)
    mask = np.isfinite(f_vals) & np.isfinite(r_vals)

    for i in range(window, len(f_vals)):
        m = mask[i - window:i]
        if m.sum() < 5:
            ic_list.append(0.0)
            continue
        x = f_vals[i - window:i][m]
        y = r_vals[i - window:i][m]
        std_x = np.std(x)
        std_y = np.std(y)
        if std_x < 1e-12 or std_y < 1e-12:
            ic_list.append(0.0)
            continue
        corr = np.corrcoef(x, y)[0, 1]
        ic_list.append(float(corr) if np.isfinite(corr) else 0.0)

    if not ic_list:
        return 0.0, 0.0

    ic_arr = np.array(ic_list)
    mean_ic = float(np.mean(ic_arr))
    std_ic = float(np.std(ic_arr))
    ic_ir = mean_ic / std_ic if std_ic > 1e-12 else 0.0
    return mean_ic, ic_ir


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
    def __init__(self, config: AlphaScreeningConfig = None):
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
        alpha_values: Dict[str, pd.Series],
        close: pd.Series,
        alpha_meta: Dict[str, Dict] = None,
    ) -> Dict[str, AlphaResult]:
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

    def filter_passed(self, results: Dict[str, AlphaResult]) -> Dict[str, AlphaResult]:
        return {k: v for k, v in results.items() if v.passed}

    def rank_by_ic_ir(self, results: Dict[str, AlphaResult]) -> List[Tuple[str, AlphaResult]]:
        sorted_results = sorted(
            results.items(),
            key=lambda x: abs(x[1].ic_ir),
            reverse=True,
        )
        return sorted_results

    def get_screening_report(self, results: Dict[str, AlphaResult]) -> Dict:
        total = len(results)
        passed = sum(1 for r in results.values() if r.passed)
        by_category = {}
        for name, r in results.items():
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
