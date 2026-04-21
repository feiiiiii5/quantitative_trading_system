#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
投资组合优化器

使用 scipy.optimize 实现经典组合优化：
- 风险平价：每资产等风险贡献
- 最大夏普：最大化风险调整后收益
- 最小方差：最小化组合波动率

约束：权重之和=1，各权重∈[0,1]
"""

import numpy as np
from scipy.optimize import minimize


class PortfolioOptimizer:
    """投资组合优化器"""

    @staticmethod
    def risk_parity(cov_matrix: np.ndarray) -> np.ndarray:
        """
        风险平价权重

        数学原理：
        - 目标：各资产对组合总风险的贡献相等
        - RC_i = w_i * (Σw)_i / σ_p = 常数
        - 优化：min Σ(RC_i - RC_j)^2

        Args:
            cov_matrix: 协方差矩阵 (n x n)

        Returns:
            权重数组 (n,)，总和=1，各∈[0,1]
        """
        n = cov_matrix.shape[0]

        def risk_budget_objective(w):
            """风险预算目标函数"""
            port_vol = np.sqrt(w @ cov_matrix @ w)
            marginal = (cov_matrix @ w) / port_vol
            rc = w * marginal  # 风险贡献
            target_rc = port_vol / n  # 目标等风险贡献
            return np.sum((rc - target_rc) ** 2)

        # 初始权重：等权
        w0 = np.ones(n) / n

        # 约束
        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}]
        bounds = [(0.0, 1.0) for _ in range(n)]

        result = minimize(
            risk_budget_objective,
            w0,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )

        return result.x if result.success else w0

    @staticmethod
    def max_sharpe(mean_returns: np.ndarray, cov_matrix: np.ndarray, risk_free: float = 0.03) -> np.ndarray:
        """
        最大夏普比率权重

        数学原理：
        - Sharpe = (E[R_p] - r_f) / σ_p
        - 最大化风险调整后的超额收益

        Args:
            mean_returns: 预期收益率数组 (n,)
            cov_matrix: 协方差矩阵 (n x n)
            risk_free: 无风险利率，默认3%

        Returns:
            权重数组 (n,)，总和=1，各∈[0,1]
        """
        n = len(mean_returns)

        def neg_sharpe(w):
            """负夏普（最小化）"""
            port_ret = w @ mean_returns
            port_vol = np.sqrt(w @ cov_matrix @ w)
            if port_vol < 1e-8:
                return 0
            return -(port_ret - risk_free) / port_vol

        w0 = np.ones(n) / n
        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}]
        bounds = [(0.0, 1.0) for _ in range(n)]

        result = minimize(
            neg_sharpe,
            w0,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )

        return result.x if result.success else w0

    @staticmethod
    def min_volatility(cov_matrix: np.ndarray) -> np.ndarray:
        """
        最小方差权重

        数学原理：
        - 目标：min w^T Σ w
        - 约束：Σw = 1, w_i ≥ 0

        Args:
            cov_matrix: 协方差矩阵 (n x n)

        Returns:
            权重数组 (n,)，总和=1，各∈[0,1]
        """
        n = cov_matrix.shape[0]

        def port_vol(w):
            return w @ cov_matrix @ w

        w0 = np.ones(n) / n
        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}]
        bounds = [(0.0, 1.0) for _ in range(n)]

        result = minimize(
            port_vol,
            w0,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )

        return result.x if result.success else w0
