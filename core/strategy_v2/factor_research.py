import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class FactorResult:
    name: str
    ic: float = 0.0
    ir: float = 0.0
    ic_pvalue: float = 1.0
    turnover: float = 0.0
    monotonicity: float = 0.0
    decay_curve: List[float] = field(default_factory=list)
    layer_returns: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "ic": round(self.ic, 4),
            "ir": round(self.ir, 4),
            "ic_pvalue": round(self.ic_pvalue, 4),
            "turnover": round(self.turnover, 4),
            "monotonicity": round(self.monotonicity, 4),
            "decay_curve": [round(d, 4) for d in self.decay_curve[:20]],
            "layer_returns": {k: round(v, 4) for k, v in self.layer_returns.items()},
        }


class FactorResearchWorkbench:
    def __init__(self, n_layers: int = 5):
        self.n_layers = n_layers
        self._factor_results: Dict[str, FactorResult] = {}

    def calculate_ic(
        self,
        factor_values: np.ndarray,
        forward_returns: np.ndarray,
    ) -> Tuple[float, float, float]:
        valid = np.isfinite(factor_values) & np.isfinite(forward_returns)
        if valid.sum() < 10:
            return 0.0, 0.0, 1.0

        fv = factor_values[valid]
        fr = forward_returns[valid]

        if np.std(fv) == 0 or np.std(fr) == 0:
            return 0.0, 0.0, 1.0

        ic = np.corrcoef(fv, fr)[0, 1]

        try:
            from scipy import stats
            _, pvalue = stats.pearsonr(fv, fr)
        except (ImportError, Exception):
            pvalue = 1.0

        return float(ic), 0.0, float(pvalue)

    def calculate_rolling_ic(
        self,
        factor_values: np.ndarray,
        forward_returns: np.ndarray,
        window: int = 20,
    ) -> List[float]:
        n = len(factor_values)
        if n < window:
            return []

        rolling_ics = []
        for i in range(window, n):
            fv = factor_values[i - window:i]
            fr = forward_returns[i - window:i]
            valid = np.isfinite(fv) & np.isfinite(fr)
            if valid.sum() < 5:
                rolling_ics.append(0)
                continue
            fv_v = fv[valid]
            fr_v = fr[valid]
            if np.std(fv_v) > 0 and np.std(fr_v) > 0:
                rolling_ics.append(float(np.corrcoef(fv_v, fr_v)[0, 1]))
            else:
                rolling_ics.append(0)

        return rolling_ics

    def calculate_ir(self, rolling_ics: List[float]) -> float:
        if not rolling_ics or len(rolling_ics) < 5:
            return 0.0
        arr = np.array(rolling_ics)
        if np.std(arr) == 0:
            return 0.0
        return float(np.mean(arr) / np.std(arr))

    def layered_backtest(
        self,
        factor_values: np.ndarray,
        forward_returns: np.ndarray,
    ) -> Dict[str, float]:
        valid = np.isfinite(factor_values) & np.isfinite(forward_returns)
        if valid.sum() < self.n_layers * 10:
            return {}

        fv = factor_values[valid]
        fr = forward_returns[valid]

        sorted_idx = np.argsort(fv)
        n = len(sorted_idx)
        layer_size = n // self.n_layers

        layer_returns = {}
        for i in range(self.n_layers):
            start = i * layer_size
            end = start + layer_size if i < self.n_layers - 1 else n
            layer_idx = sorted_idx[start:end]
            layer_ret = np.mean(fr[layer_idx])
            layer_name = f"L{i + 1}"
            layer_returns[layer_name] = float(layer_ret)

        return layer_returns

    def calculate_decay(
        self,
        factor_values: np.ndarray,
        returns: np.ndarray,
        max_lag: int = 20,
    ) -> List[float]:
        decay = []
        for lag in range(1, max_lag + 1):
            if lag >= len(returns):
                decay.append(0)
                continue
            fv = factor_values[:-lag]
            fr = returns[lag:]
            n = min(len(fv), len(fr))
            if n < 10:
                decay.append(0)
                continue
            fv = fv[:n]
            fr = fr[:n]
            valid = np.isfinite(fv) & np.isfinite(fr)
            if valid.sum() < 5:
                decay.append(0)
                continue
            fv_v = fv[valid]
            fr_v = fr[valid]
            if np.std(fv_v) > 0 and np.std(fr_v) > 0:
                decay.append(float(np.corrcoef(fv_v, fr_v)[0, 1]))
            else:
                decay.append(0)
        return decay

    def calculate_monotonicity(self, layer_returns: Dict[str, float]) -> float:
        if len(layer_returns) < 3:
            return 0.0
        values = list(layer_returns.values())
        n = len(values)
        concordant = 0
        discordant = 0
        for i in range(n):
            for j in range(i + 1, n):
                if values[i] < values[j]:
                    concordant += 1
                elif values[i] > values[j]:
                    discordant += 1
        total = concordant + discordant
        if total == 0:
            return 0.0
        return (concordant - discordant) / total

    def research_factor(
        self,
        name: str,
        factor_values: np.ndarray,
        returns: np.ndarray,
        forward_period: int = 5,
    ) -> FactorResult:
        forward_returns = np.zeros(len(returns))
        if len(returns) > forward_period:
            forward_returns[:len(returns) - forward_period] = (
                returns[forward_period:] / np.maximum(returns[:-forward_period], 1e-8) - 1
            )

        ic, _, pvalue = self.calculate_ic(factor_values, forward_returns)
        rolling_ics = self.calculate_rolling_ic(factor_values, forward_returns)
        ir = self.calculate_ir(rolling_ics)
        layer_returns = self.layered_backtest(factor_values, forward_returns)
        decay = self.calculate_decay(factor_values, returns)
        monotonicity = self.calculate_monotonicity(layer_returns)

        turnover = 0.0
        if len(factor_values) > 1:
            rank_changes = np.diff(np.argsort(factor_values))
            turnover = float(np.mean(np.abs(rank_changes)) / len(factor_values))

        result = FactorResult(
            name=name, ic=ic, ir=ir, ic_pvalue=pvalue,
            turnover=turnover, monotonicity=monotonicity,
            decay_curve=decay, layer_returns=layer_returns,
        )
        self._factor_results[name] = result
        return result

    def multi_factor_composite(
        self,
        factors: Dict[str, np.ndarray],
        returns: np.ndarray,
        method: str = "equal_weight",
        weights: Optional[Dict[str, float]] = None,
    ) -> dict:
        if not factors:
            return {}

        results = {}
        for name, fv in factors.items():
            results[name] = self.research_factor(name, fv, returns)

        if method == "equal_weight":
            w = {name: 1.0 / len(factors) for name in factors}
        elif method == "ic_weight":
            total_ic = sum(abs(r.ic) for r in results.values())
            w = {name: abs(r.ic) / total_ic if total_ic > 0 else 1.0 / len(factors) for name, r in results.items()}
        elif method == "ir_weight":
            total_ir = sum(abs(r.ir) for r in results.values())
            w = {name: abs(r.ir) / total_ir if total_ir > 0 else 1.0 / len(factors) for name, r in results.items()}
        elif weights:
            w = weights
        else:
            w = {name: 1.0 / len(factors) for name in factors}

        min_len = min(len(fv) for fv in factors.values())
        composite = np.zeros(min_len)
        for name, fv in factors.items():
            composite += w.get(name, 0) * fv[:min_len]

        composite_result = self.research_factor("composite", composite, returns[:min_len])

        return {
            "composite": composite_result.to_dict(),
            "individual": {name: r.to_dict() for name, r in results.items()},
            "weights": {k: round(v, 4) for k, v in w.items()},
        }

    def get_results(self) -> Dict[str, dict]:
        return {name: r.to_dict() for name, r in self._factor_results.items()}
