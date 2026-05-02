import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def mean_variance_optimize(
    expected_returns: np.ndarray,
    cov_matrix: np.ndarray,
    risk_free_rate: float = 0.03,
    max_weight: float = 0.05,
    min_weight: float = 0.0,
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

    best_sharpe = -np.inf
    best_weights = np.ones(n) / n

    for _ in range(200):
        try:
            inv_cov = np.linalg.inv(cov)
            excess = expected_returns - risk_free_rate / 252
            raw = inv_cov @ excess
            if np.sum(raw) < 1e-12:
                continue
            w = raw / np.sum(np.abs(raw))
            for _clip_iter in range(20):
                w = np.clip(w, min_weight, max_weight)
                s = np.sum(w)
                if s > 0 and abs(s - 1.0) > 1e-8:
                    w = w / s
                else:
                    break
                if np.all(w <= max_weight + 1e-10):
                    break
            w = np.clip(w, min_weight, max_weight)
            if np.sum(w) > 0:
                w = w / np.sum(w)

            port_ret = w @ expected_returns
            port_vol = np.sqrt(w @ cov @ w)
            if port_vol < 1e-12:
                continue
            sharpe = (port_ret - risk_free_rate / 252) / port_vol
            if sharpe > best_sharpe:
                best_sharpe = sharpe
                best_weights = w.copy()
        except np.linalg.LinAlgError:
            continue

    best_weights = np.clip(best_weights, min_weight, max_weight)
    if np.sum(best_weights) > 0:
        best_weights = best_weights / np.sum(best_weights)
    else:
        best_weights = np.ones(n) / n

    return best_weights


def risk_parity_optimize(
    cov_matrix: np.ndarray,
    risk_budget: np.ndarray = None,
    max_weight: float = 0.05,
    min_weight: float = 0.0,
) -> np.ndarray:
    n = cov_matrix.shape[0]
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

    if risk_budget is None:
        risk_budget = np.ones(n) / n
    risk_budget = risk_budget / np.sum(risk_budget)

    weights = np.ones(n) / n
    for iteration in range(1000):
        port_var = weights @ cov @ weights
        if port_var < 1e-20:
            break
        marginal_contrib = cov @ weights
        risk_contrib = weights * marginal_contrib / port_var
        risk_diff = risk_contrib - risk_budget
        if np.max(np.abs(risk_diff)) < 1e-8:
            break

        grad = 2 * (cov @ weights) / port_var - 2 * weights * (marginal_contrib @ weights) / (port_var ** 2)
        step = 0.01
        new_weights = weights - step * grad
        for _clip_iter in range(20):
            new_weights = np.clip(new_weights, min_weight, max_weight)
            s = np.sum(new_weights)
            if s > 0 and abs(s - 1.0) > 1e-8:
                new_weights = new_weights / s
            else:
                break
            if np.all(new_weights <= max_weight + 1e-10):
                break
        new_weights = np.clip(new_weights, min_weight, max_weight)
        if np.sum(new_weights) > 0:
            new_weights = new_weights / np.sum(new_weights)
        else:
            new_weights = np.ones(n) / n
        weights = new_weights

    weights = np.clip(weights, min_weight, max_weight)
    if np.sum(weights) > 0:
        weights = weights / np.sum(weights)
    else:
        weights = np.ones(n) / n

    return weights


def ic_weighted_optimize(
    ics: np.ndarray,
    vols: np.ndarray,
    max_weight: float = 0.05,
    min_weight: float = 0.0,
) -> np.ndarray:
    n = len(ics)
    if n == 0:
        return np.array([])

    abs_ics = np.abs(ics)
    safe_vols = np.where(vols > 1e-10, vols, 1e-10)
    raw = abs_ics / safe_vols
    if np.sum(raw) < 1e-12:
        return np.ones(n) / n

    weights = raw / np.sum(raw)
    weights = np.clip(weights, min_weight, max_weight)
    if np.sum(weights) > 0:
        weights = weights / np.sum(weights)
    else:
        weights = np.ones(n) / n

    return weights


class PortfolioOptimizer:
    def __init__(
        self,
        max_weight: float = 0.05,
        min_weight: float = 0.0,
        risk_free_rate: float = 0.03,
    ):
        self._max_weight = max_weight
        self._min_weight = min_weight
        self._risk_free_rate = risk_free_rate

    def optimize(
        self,
        expected_returns: np.ndarray,
        cov_matrix: np.ndarray,
        method: str = "mean_variance",
        risk_budget: np.ndarray = None,
    ) -> np.ndarray:
        if method == "mean_variance":
            return mean_variance_optimize(
                expected_returns, cov_matrix,
                self._risk_free_rate, self._max_weight, self._min_weight,
            )
        elif method == "risk_parity":
            return risk_parity_optimize(
                cov_matrix, risk_budget,
                self._max_weight, self._min_weight,
            )
        else:
            return mean_variance_optimize(
                expected_returns, cov_matrix,
                self._risk_free_rate, self._max_weight, self._min_weight,
            )

    def optimize_from_alphas(
        self,
        alpha_results: Dict[str, "AlphaResult"],
        returns_df: pd.DataFrame,
        method: str = "ic_weighted",
    ) -> Dict[str, float]:
        names = list(alpha_results.keys())
        n = len(names)
        if n == 0:
            return {}

        ics = np.array([alpha_results[name].ic for name in names])
        values_df = pd.DataFrame({name: alpha_results[name].values for name in names})
        vols = values_df.std().values
        expected_returns = ics * vols

        if method == "ic_weighted":
            weights = ic_weighted_optimize(ics, vols, self._max_weight, self._min_weight)
        elif method == "mean_variance":
            cov = values_df.cov().values
            weights = mean_variance_optimize(
                expected_returns, cov,
                self._risk_free_rate, self._max_weight, self._min_weight,
            )
        elif method == "risk_parity":
            cov = values_df.cov().values
            weights = risk_parity_optimize(cov, max_weight=self._max_weight, min_weight=self._min_weight)
        else:
            weights = ic_weighted_optimize(ics, vols, self._max_weight, self._min_weight)

        return {name: round(float(w), 6) for name, w in zip(names, weights)}

    def get_portfolio_report(
        self,
        weights: np.ndarray,
        expected_returns: np.ndarray,
        cov_matrix: np.ndarray,
        names: List[str] = None,
    ) -> Dict:
        n = len(weights)
        port_ret = float(weights @ expected_returns)
        port_vol = float(np.sqrt(weights @ cov_matrix @ weights))
        sharpe = (port_ret - self._risk_free_rate / 252) / port_vol if port_vol > 1e-12 else 0.0

        marginal_contrib = cov_matrix @ weights
        port_var = float(weights @ cov_matrix @ weights)
        risk_contrib = weights * marginal_contrib / port_var if port_var > 1e-20 else np.zeros(n)

        report = {
            "expected_return": round(port_ret, 6),
            "volatility": round(port_vol, 6),
            "sharpe_ratio": round(sharpe, 4),
            "weights": {},
            "risk_contribution": {},
        }
        if names is None:
            names = [f"asset_{i}" for i in range(n)]
        for i, name in enumerate(names):
            report["weights"][name] = round(float(weights[i]), 6)
            report["risk_contribution"][name] = round(float(risk_contrib[i]), 6)

        return report
