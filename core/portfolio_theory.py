"""
QuantCore 现代投资组合理论 (MPT) 模块
提供马科维茨有效前沿、夏普比率优化、风险平价等投资组合构建方法
使用 scipy.optimize 进行数学严格优化
"""
import logging
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import minimize

logger = logging.getLogger(__name__)


@dataclass
class PortfolioOptimizationResult:
    """投资组合优化结果"""
    weights: dict[str, float]
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    diversification_ratio: float
    is_valid: bool
    message: str


def _insufficient_result(msg: str) -> PortfolioOptimizationResult:
    return PortfolioOptimizationResult(
        weights={}, expected_return=0.0, expected_volatility=0.0,
        sharpe_ratio=0.0, diversification_ratio=0.0,
        is_valid=False, message=msg,
    )


def _failed_result(exc: Exception) -> PortfolioOptimizationResult:
    return PortfolioOptimizationResult(
        weights={}, expected_return=0.0, expected_volatility=0.0,
        sharpe_ratio=0.0, diversification_ratio=0.0,
        is_valid=False, message=f"Optimization failed: {exc}",
    )


class ModernPortfolioTheory:
    """现代投资组合理论优化器 — 基于 scipy.optimize SLSQP"""

    def __init__(
        self,
        risk_free_rate: float = 0.03,
        min_weight: float = 0.0,
        max_weight: float = 1.0,
    ):
        self.risk_free_rate = risk_free_rate
        self.min_weight = min_weight
        self.max_weight = max_weight

    def calculate_returns(self, prices: pd.DataFrame) -> pd.DataFrame:
        return np.log(prices / prices.shift(1)).dropna()

    def calculate_annual_returns(self, returns: pd.DataFrame) -> pd.Series:
        return returns.mean() * 252

    def calculate_covariance_matrix(self, returns: pd.DataFrame) -> pd.DataFrame:
        return returns.cov() * 252

    def portfolio_return(self, weights: np.ndarray, annual_returns: pd.Series) -> float:
        return float(np.sum(weights * annual_returns))

    def portfolio_volatility(self, weights: np.ndarray, cov_matrix: pd.DataFrame) -> float:
        return float(np.sqrt(np.dot(weights.T, np.dot(cov_matrix.values, weights))))

    def sharpe_ratio(self, weights: np.ndarray, annual_returns: pd.Series,
                     cov_matrix: pd.DataFrame) -> float:
        ret = self.portfolio_return(weights, annual_returns)
        vol = self.portfolio_volatility(weights, cov_matrix)
        if vol <= 0:
            return 0.0
        return (ret - self.risk_free_rate) / vol

    def diversification_ratio(self, weights: np.ndarray, cov_matrix: pd.DataFrame) -> float:
        asset_vols = np.sqrt(np.diag(cov_matrix.values))
        port_vol = self.portfolio_volatility(weights, cov_matrix)
        if port_vol <= 0:
            return 1.0
        return float(np.sum(weights * asset_vols) / port_vol)

    def _build_bounds(
        self,
        n_assets: int,
        fixed_weights: dict[str, float],
        columns: pd.Index,
    ) -> tuple:
        """Build per-asset bounds, pinning fixed-weight assets to their value."""
        bounds = []
        for col in columns:
            if col in fixed_weights:
                w = fixed_weights[col]
                bounds.append((w, w))
            else:
                bounds.append((self.min_weight, self.max_weight))
        return tuple(bounds)

    def _build_constraints(
        self,
        fixed_weights: dict[str, float],
        columns: pd.Index,
        target_return: float | None = None,
        annual_returns: pd.Series | None = None,
    ) -> list[dict[str, Any]]:
        """Build constraint list: weights sum to 1 minus fixed allocation."""
        fixed_sum = sum(fixed_weights.get(col, 0.0) for col in columns)
        target_sum = 1.0 - fixed_sum

        constraints: list[dict[str, Any]] = [
            {"type": "eq", "fun": lambda w: np.sum(w) - target_sum},
        ]

        if target_return is not None and annual_returns is not None:
            constraints.append({
                "type": "eq",
                "fun": lambda w: np.sum(w * annual_returns.values) - target_return,
            })

        return constraints

    def _initial_guess(
        self,
        n_assets: int,
        fixed_weights: dict[str, float],
        columns: pd.Index,
    ) -> np.ndarray:
        """Equal-weight initial guess respecting fixed weights."""
        fixed_sum = sum(fixed_weights.get(col, 0.0) for col in columns)
        n_free = sum(1 for col in columns if col not in fixed_weights)
        free_weight = (1.0 - fixed_sum) / n_free if n_free > 0 else 0.0
        return np.array([fixed_weights.get(col, free_weight) for col in columns])

    def optimize_max_sharpe(
        self,
        prices: pd.DataFrame,
        fixed_weights: dict[str, float] | None = None,
    ) -> PortfolioOptimizationResult:
        try:
            returns = self.calculate_returns(prices)
            if len(returns) < 10:
                return _insufficient_result("Insufficient data, need at least 10 days of data")

            annual_returns = self.calculate_annual_returns(returns)
            cov_matrix = self.calculate_covariance_matrix(returns)
            columns = prices.columns
            fixed_weights = fixed_weights or {}
            n = len(columns)

            cov_arr = cov_matrix.values
            ret_arr = annual_returns.values

            def neg_sharpe(w: np.ndarray) -> float:
                port_ret = np.dot(w, ret_arr)
                port_vol = np.sqrt(np.dot(w.T, np.dot(cov_arr, w)))
                if port_vol < 1e-12:
                    return 0.0
                return float(-(port_ret - self.risk_free_rate) / port_vol)

            bounds = self._build_bounds(n, fixed_weights, columns)
            constraints = self._build_constraints(fixed_weights, columns)
            x0 = self._initial_guess(n, fixed_weights, columns)

            result = minimize(
                neg_sharpe, x0, method="SLSQP",
                bounds=bounds, constraints=constraints,
                options={"maxiter": 500, "ftol": 1e-10},
            )

            weights_arr = result.x if result.success else x0
            weights_arr = np.clip(weights_arr, 0.0, 1.0)
            total = np.sum(weights_arr)
            if total > 0:
                weights_arr = weights_arr / total

            weights_dict = {col: float(weights_arr[i]) for i, col in enumerate(columns)}
            exp_return = self.portfolio_return(weights_arr, annual_returns)
            exp_vol = self.portfolio_volatility(weights_arr, cov_matrix)
            sharpe = self.sharpe_ratio(weights_arr, annual_returns, cov_matrix)
            div_ratio = self.diversification_ratio(weights_arr, cov_matrix)

            return PortfolioOptimizationResult(
                weights=weights_dict, expected_return=exp_return,
                expected_volatility=exp_vol, sharpe_ratio=sharpe,
                diversification_ratio=div_ratio, is_valid=True,
                message="Optimization successful",
            )
        except Exception as e:
            logger.warning("Max Sharpe optimization failed: %s", e)
            return _failed_result(e)

    def optimize_min_volatility(
        self,
        prices: pd.DataFrame,
        fixed_weights: dict[str, float] | None = None,
    ) -> PortfolioOptimizationResult:
        try:
            returns = self.calculate_returns(prices)
            if len(returns) < 10:
                return _insufficient_result("Insufficient data, need at least 10 days of data")

            annual_returns = self.calculate_annual_returns(returns)
            cov_matrix = self.calculate_covariance_matrix(returns)
            columns = prices.columns
            fixed_weights = fixed_weights or {}
            n = len(columns)

            cov_arr = cov_matrix.values

            def port_vol(w: np.ndarray) -> float:
                return float(np.sqrt(np.dot(w.T, np.dot(cov_arr, w))))

            bounds = self._build_bounds(n, fixed_weights, columns)
            constraints = self._build_constraints(fixed_weights, columns)
            x0 = self._initial_guess(n, fixed_weights, columns)

            result = minimize(
                port_vol, x0, method="SLSQP",
                bounds=bounds, constraints=constraints,
                options={"maxiter": 500, "ftol": 1e-10},
            )

            weights_arr = result.x if result.success else x0
            weights_arr = np.clip(weights_arr, 0.0, 1.0)
            total = np.sum(weights_arr)
            if total > 0:
                weights_arr = weights_arr / total

            weights_dict = {col: float(weights_arr[i]) for i, col in enumerate(columns)}
            exp_return = self.portfolio_return(weights_arr, annual_returns)
            exp_vol = self.portfolio_volatility(weights_arr, cov_matrix)
            sharpe = self.sharpe_ratio(weights_arr, annual_returns, cov_matrix)
            div_ratio = self.diversification_ratio(weights_arr, cov_matrix)

            return PortfolioOptimizationResult(
                weights=weights_dict, expected_return=exp_return,
                expected_volatility=exp_vol, sharpe_ratio=sharpe,
                diversification_ratio=div_ratio, is_valid=True,
                message="Optimization successful",
            )
        except Exception as e:
            logger.warning("Min volatility optimization failed: %s", e)
            return _failed_result(e)

    def optimize_equal_weight(
        self,
        prices: pd.DataFrame,
    ) -> PortfolioOptimizationResult:
        try:
            returns = self.calculate_returns(prices)
            if len(returns) < 10:
                return _insufficient_result("Insufficient data, need at least 10 days of data")

            annual_returns = self.calculate_annual_returns(returns)
            cov_matrix = self.calculate_covariance_matrix(returns)
            columns = prices.columns
            n_assets = len(columns)
            weights_dict = dict.fromkeys(columns, 1.0 / n_assets)
            weights_arr = np.array([weights_dict[col] for col in columns])

            exp_return = self.portfolio_return(weights_arr, annual_returns)
            exp_vol = self.portfolio_volatility(weights_arr, cov_matrix)
            sharpe = self.sharpe_ratio(weights_arr, annual_returns, cov_matrix)
            div_ratio = self.diversification_ratio(weights_arr, cov_matrix)

            return PortfolioOptimizationResult(
                weights=weights_dict, expected_return=exp_return,
                expected_volatility=exp_vol, sharpe_ratio=sharpe,
                diversification_ratio=div_ratio, is_valid=True,
                message="Equal weight allocation successful",
            )
        except Exception as e:
            logger.warning("Equal weight allocation failed: %s", e)
            return _failed_result(e)

    def optimize_risk_parity(
        self,
        prices: pd.DataFrame,
        fixed_weights: dict[str, float] | None = None,
    ) -> PortfolioOptimizationResult:
        try:
            returns = self.calculate_returns(prices)
            if len(returns) < 10:
                return _insufficient_result("Insufficient data, need at least 10 days of data")

            annual_returns = self.calculate_annual_returns(returns)
            cov_matrix = self.calculate_covariance_matrix(returns)
            columns = prices.columns
            fixed_weights = fixed_weights or {}
            n = len(columns)

            cov_arr = cov_matrix.values

            def risk_parity_objective(w: np.ndarray) -> float:
                port_vol = np.sqrt(np.dot(w.T, np.dot(cov_arr, w)))
                if port_vol < 1e-12:
                    return 0.0
                marginal_risk = np.dot(cov_arr, w) / port_vol
                risk_contrib = w * marginal_risk
                target_risk = port_vol / n
                return float(np.sum((risk_contrib - target_risk) ** 2))

            bounds = self._build_bounds(n, fixed_weights, columns)
            constraints = self._build_constraints(fixed_weights, columns)
            x0 = self._initial_guess(n, fixed_weights, columns)

            result = minimize(
                risk_parity_objective, x0, method="SLSQP",
                bounds=bounds, constraints=constraints,
                options={"maxiter": 500, "ftol": 1e-12},
            )

            weights_arr = result.x if result.success else x0
            weights_arr = np.clip(weights_arr, 0.0, 1.0)
            total = np.sum(weights_arr)
            if total > 0:
                weights_arr = weights_arr / total

            weights_dict = {col: float(weights_arr[i]) for i, col in enumerate(columns)}
            exp_return = self.portfolio_return(weights_arr, annual_returns)
            exp_vol = self.portfolio_volatility(weights_arr, cov_matrix)
            sharpe = self.sharpe_ratio(weights_arr, annual_returns, cov_matrix)
            div_ratio = self.diversification_ratio(weights_arr, cov_matrix)

            return PortfolioOptimizationResult(
                weights=weights_dict, expected_return=exp_return,
                expected_volatility=exp_vol, sharpe_ratio=sharpe,
                diversification_ratio=div_ratio, is_valid=True,
                message="Risk parity allocation successful",
            )
        except Exception as e:
            logger.warning("Risk parity allocation failed: %s", e)
            return _failed_result(e)

    def generate_efficient_frontier(
        self,
        prices: pd.DataFrame,
        n_points: int = 20,
    ) -> list[dict[str, Any]]:
        try:
            returns = self.calculate_returns(prices)
            if len(returns) < 10:
                return []

            annual_returns = self.calculate_annual_returns(returns)
            cov_matrix = self.calculate_covariance_matrix(returns)
            columns = prices.columns
            n = len(columns)
            cov_arr = cov_matrix.values
            ret_arr = annual_returns.values

            min_vol_result = self.optimize_min_volatility(prices)
            max_sharpe_result = self.optimize_max_sharpe(prices)

            if not min_vol_result.is_valid or not max_sharpe_result.is_valid:
                return []

            min_ret = min(min_vol_result.expected_return, max_sharpe_result.expected_return)
            max_ret = max(min_vol_result.expected_return, max_sharpe_result.expected_return)
            ret_range = max_ret - min_ret
            if ret_range < 1e-8:
                ret_range = abs(max_ret) * 0.1 if abs(max_ret) > 1e-8 else 0.01

            target_returns = np.linspace(min_ret - ret_range * 0.1, max_ret + ret_range * 0.1, n_points)

            frontier_points = []
            bounds = tuple((self.min_weight, self.max_weight) for _ in range(n))
            x0 = np.ones(n) / n

            for target_ret in target_returns:
                constraints = [
                    {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
                    {"type": "eq", "fun": lambda w, tr=target_ret: np.dot(w, ret_arr) - tr},
                ]

                def port_vol(w: np.ndarray) -> float:
                    return float(np.sqrt(np.dot(w.T, np.dot(cov_arr, w))))

                result = minimize(
                    port_vol, x0, method="SLSQP",
                    bounds=bounds, constraints=constraints,
                    options={"maxiter": 300, "ftol": 1e-10},
                )

                if not result.success:
                    continue

                weights = result.x
                weights = np.clip(weights, 0.0, 1.0)
                total = np.sum(weights)
                if total > 0:
                    weights = weights / total

                exp_return = self.portfolio_return(weights, annual_returns)
                exp_vol = self.portfolio_volatility(weights, cov_matrix)
                sharpe = self.sharpe_ratio(weights, annual_returns, cov_matrix)

                frontier_points.append({
                    "return": exp_return,
                    "volatility": exp_vol,
                    "sharpe_ratio": sharpe,
                    "weights": dict(zip(columns, weights, strict=False)),
                })

            return frontier_points
        except Exception as e:
            logger.warning("Efficient frontier generation failed: %s", e)
            return []


def shrink_covariance_matrix(
    returns: pd.DataFrame,
    shrinkage_target: str = "single_factor",
    shrinkage_intensity: float | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, float]:
    """收缩协方差矩阵估计，减少样本误差导致的估计偏差。

    实现三种收缩方法：
    - "single_factor": 向单因子模型收缩 (Ledoit-Wolf风格)
    - "constant_correlation": 向恒定相关结构收缩
    - "diagonal": 向对角矩阵收缩 (简单收缩)

    参数:
        returns: 资产收益率DataFrame (n_samples × n_assets)
        shrinkage_target: 收缩目标结构
        shrinkage_intensity: 手动指定收缩强度 (0=不收缩, 1=完全收缩到目标)
                            如果为None，则自动计算Ledoit-Wolf最优收缩强度

    返回:
        (原始协方差, 收缩后协方差, 收缩强度)

    引用: Ledoit & Wolf (2004) "Honey, I Shrunk the Sample Covariance Matrix"
    """
    prices_or_returns = returns
    if hasattr(returns, "iloc"):
        if len(returns.columns) == 0 or len(returns) == 0:
            n = 1
            k = 1
            x_vals = returns.values
        else:
            x_vals = returns.values
            n, k = x_vals.shape
    else:
        raise TypeError("returns must be a pandas DataFrame")

    if n <= 1 or k <= 0:
        return pd.DataFrame(), pd.DataFrame(), 0.0

    if k == 1:
        var = float(np.var(x_vals, ddof=1))
        cov = np.array([[var]])
    else:
        cov = np.cov(x_vals, rowvar=False, ddof=1)

    if np.any(np.isnan(cov)) or np.any(np.isinf(cov)):
        cov = np.eye(k) * float(np.nanmean(np.diag(cov)))

    if shrinkage_intensity is not None and shrinkage_intensity >= 0.0:
        delta = float(shrinkage_intensity)
    else:
        delta = _lw_shrinkage_intensity(x_vals, cov, shrinkage_target)

    if delta <= 0.0 or delta >= 1.0:
        return pd.DataFrame(cov, index=prices_or_returns.columns, columns=prices_or_returns.columns), \
               pd.DataFrame(cov, index=prices_or_returns.columns, columns=prices_or_returns.columns), \
               delta

    if shrinkage_target == "single_factor":
        target_matrix = _single_factor_target(x_vals, k)
    elif shrinkage_target == "constant_correlation":
        target_matrix = _constant_correlation_target(cov, k)
    else:
        target_matrix = np.eye(k) * np.diag(cov)

    shrunk_cov = delta * target_matrix + (1.0 - delta) * cov
    shrunk_cov = _ensure_positive_definite(shrunk_cov)

    return pd.DataFrame(cov, index=prices_or_returns.columns, columns=prices_or_returns.columns), \
           pd.DataFrame(shrunk_cov, index=prices_or_returns.columns, columns=prices_or_returns.columns), \
           delta


def _lw_shrinkage_intensity(X: np.ndarray, sample_cov: np.ndarray, target: str) -> float:  # noqa: N803
    """Ledoit-Wolf optimal shrinkage intensity for covariance estimation."""
    n, k = X.shape
    if k <= 1 or n <= k:
        return 1.0

    if target == "single_factor":
        target_matrix = _single_factor_target(X, k)
    elif target == "constant_correlation":
        target_matrix = _constant_correlation_target(sample_cov, k)
    else:
        target_matrix = np.eye(k) * np.diag(np.diag(sample_cov))

    x_centered = X - np.mean(X, axis=0)  # noqa: N806
    sample_moment = np.dot(x_centered.T, x_centered) / (n - 1)

    _phi = float(np.sum((sample_cov - sample_moment) ** 2))  # noqa: F841
    gamma = float(np.sum((sample_cov - target_matrix) ** 2))

    if gamma < 1e-12:
        return min(1.0, 0.5)

    omega_sum = 0.0
    for i in range(n):
        xi = x_centered[i]
        outer = np.outer(xi, xi)
        omega_sum += float(np.sum((outer - sample_moment) ** 2))
    omega = omega_sum / (n ** 2)

    delta = max(0.0, min(1.0, omega / max(gamma, 1e-12)))

    return delta


def _single_factor_target(X: np.ndarray, k: int) -> np.ndarray:  # noqa: N803
    """Compute single-factor shrinkage target matrix for covariance estimation."""
    x_vals = X - np.mean(X, axis=0)
    market_returns = np.mean(x_vals, axis=1)
    betas = np.dot(np.linalg.pinv(np.atleast_2d(market_returns).T), x_vals)
    factor_var = float(np.var(market_returns, ddof=1))
    if factor_var < 1e-12:
        diag_vals: np.ndarray = np.var(x_vals, axis=0, ddof=1)
        return np.asarray(np.eye(k) * diag_vals, dtype=np.float64)
    factor_cov = float(factor_var) * np.outer(betas.flatten(), betas.flatten())
    residuals = x_vals - np.outer(market_returns, betas.flatten())
    diag_residual_var: np.ndarray = np.var(residuals, axis=0, ddof=1)
    return factor_cov + np.diag(np.asarray(diag_residual_var, dtype=np.float64))


def _constant_correlation_target(cov: np.ndarray, k: int) -> np.ndarray:
    diag: np.ndarray = np.diag(cov)
    if np.any(diag <= 0):
        return np.eye(k)
    std: np.ndarray = np.sqrt(diag)
    avg_r: float = float((np.sum(cov / np.outer(std, std)) - k) / (k * (k - 1)))
    avg_r = float(np.clip(avg_r, -1.0 + 1e-9, 1.0 - 1e-9))
    target = np.outer(std, std) * avg_r
    np.fill_diagonal(target, diag)
    return target


def _ensure_positive_definite(cov: np.ndarray, min_eigenvalue: float = 1e-10) -> np.ndarray:
    eigenvalues, eigenvectors = np.linalg.eigh(cov)
    eigenvalues = np.maximum(eigenvalues, min_eigenvalue)
    return eigenvectors @ np.diag(eigenvalues) @ eigenvectors.T


def denoise_correlation_matrix(
    returns: pd.DataFrame,
    method: str = "shrinkage",
    n_factors: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, float | str]]:
    """去噪相关矩阵，减少市场噪声对组合优化的影响。

    参数:
        returns: 资产收益率DataFrame
        method: "shrinkage" (收缩估计) | "factor" (因子去噪) | "random_matrix" (Marchenko-Pastur)
        n_factors: 因子数量（仅factor方法）

    返回:
        (原始相关矩阵, 去噪后相关矩阵, 元数据字典)
    """
    prices_or_returns = returns
    x_vals = returns.values
    n, k = x_vals.shape

    if n <= 1 or k <= 0:
        return pd.DataFrame(), pd.DataFrame(), {}

    if k == 1:
        return pd.DataFrame([[1.0]], index=prices_or_returns.columns, columns=prices_or_returns.columns), \
               pd.DataFrame([[1.0]], index=prices_or_returns.columns, columns=prices_or_returns.columns), \
               {"method": "single_asset"}

    std = np.std(x_vals, axis=0, ddof=1)
    std[std < 1e-12] = 1.0
    corr = np.corrcoef(x_vals, rowvar=False)

    if np.any(np.isnan(corr)):
        corr = np.eye(k)
    if np.any(np.abs(corr) > 1.0):
        corr = np.clip(corr, -1.0, 1.0)

    metadata: dict[str, float | str] = {"original_eigenvalues_condition": 0.0}

    if method == "shrinkage":
        _, shrunk_cov, delta = shrink_covariance_matrix(returns, "constant_correlation")
        shrunk_std = np.sqrt(np.maximum(np.diag(shrunk_cov.values), 1e-10))
        denoised_corr = shrunk_cov.values / np.outer(shrunk_std, shrunk_std)
        denoised_corr = np.clip(denoised_corr, -1.0, 1.0)
        np.fill_diagonal(denoised_corr, 1.0)
        denoised_corr = _ensure_positive_definite(denoised_corr)
        denoised_corr = denoised_corr / np.sqrt(np.outer(np.diag(denoised_corr), np.diag(denoised_corr)))
        np.fill_diagonal(denoised_corr, 1.0)
        metadata["shrinkage_intensity"] = delta
        metadata["method"] = "shrinkage"

    elif method == "factor":
        n_factors_int = min(3, k - 1) if n_factors is None else max(1, min(n_factors, k - 1))

        eigenvalues, eigenvectors = np.linalg.eigh(corr)
        idx = np.argsort(eigenvalues)[::-1]
        eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors[:, idx]

        signal_eigenvalues = eigenvalues[:n_factors_int]
        noise_threshold = float(np.mean(eigenvalues[n_factors_int:]))
        noise_eigenvalues = np.maximum(eigenvalues[n_factors_int:], noise_threshold)
        cleaned_eigenvalues = np.concatenate([signal_eigenvalues, noise_eigenvalues])
        denoised_corr = eigenvectors @ np.diag(cleaned_eigenvalues) @ eigenvectors.T
        denoised_corr = denoised_corr / np.sqrt(np.outer(np.diag(denoised_corr), np.diag(denoised_corr)))
        np.fill_diagonal(denoised_corr, 1.0)
        denoised_corr = np.clip(denoised_corr, -1.0, 1.0)
        metadata["n_factors"] = float(n_factors_int)
        metadata["noise_threshold"] = noise_threshold
        metadata["method"] = "factor"

    elif method == "random_matrix":
        eigenvalues, eigenvectors = np.linalg.eigh(corr)
        idx = np.argsort(eigenvalues)[::-1]
        eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors[:, idx]

        q_ratio = float(n / k)
        if q_ratio > 1:
            lambda_max = (1.0 + 1.0 / q_ratio) ** 2
            lambda_min = (1.0 - 1.0 / q_ratio) ** 2
            theoretical_mean = 1.0
        else:
            lambda_max, lambda_min, theoretical_mean = 2.0, 0.0, 1.0

        cleaned_eigenvalues = np.copy(eigenvalues)
        if q_ratio > 1:
            for i in range(k):
                if eigenvalues[i] < lambda_max and q_ratio > 1:
                    cleaned_eigenvalues[i] = max(theoretical_mean, lambda_min)
        else:
            for i in range(k):
                if eigenvalues[i] < theoretical_mean * 0.5:
                    cleaned_eigenvalues[i] = theoretical_mean

        denoised_corr = eigenvectors @ np.diag(cleaned_eigenvalues) @ eigenvectors.T
        denoised_corr = denoised_corr / np.sqrt(np.outer(np.diag(denoised_corr), np.diag(denoised_corr)))
        np.fill_diagonal(denoised_corr, 1.0)
        denoised_corr = np.clip(denoised_corr, -1.0, 1.0)
        metadata["Q_ratio"] = q_ratio
        metadata["lambda_max"] = lambda_max
        metadata["lambda_min"] = lambda_min
        metadata["method"] = "random_matrix"

    else:
        denoised_corr = corr.copy()
        metadata["method"] = "none"

    original_corr_df = pd.DataFrame(corr, index=prices_or_returns.columns, columns=prices_or_returns.columns)
    denoised_corr_df = pd.DataFrame(denoised_corr, index=prices_or_returns.columns, columns=prices_or_returns.columns)

    return original_corr_df, denoised_corr_df, metadata
