"""
QuantCore 因子分析模块
提供 Fama-French 三因子模型、因子暴露分析和因子收益归因
"""
import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)


@dataclass
class FactorExposureResult:
    alpha: float
    alpha_tstat: float
    alpha_pvalue: float
    betas: dict[str, float]
    beta_tstats: dict[str, float]
    beta_pvalues: dict[str, float]
    r_squared: float
    adjusted_r_squared: float
    residual_volatility: float
    factor_count: int
    is_valid: bool
    message: str


@dataclass
class FactorAttributionResult:
    total_return: float
    factor_returns: dict[str, float]
    specific_return: float
    factor_contributions: dict[str, float]
    is_valid: bool
    message: str


class FactorModel:

    def __init__(self, risk_free_rate: float = 0.03):
        self.risk_free_rate = risk_free_rate

    def _excess_returns(self, returns: pd.Series) -> np.ndarray:
        daily_rf = (1 + self.risk_free_rate) ** (1/252) - 1
        return (returns - daily_rf).values

    def estimate_factor_exposures(
        self,
        asset_returns: pd.Series,
        factor_returns: pd.DataFrame,
    ) -> FactorExposureResult:
        """
        Estimate factor exposures via OLS regression.

        Parameters
        ----------
        asset_returns : Series of daily asset returns
        factor_returns : DataFrame with factor return columns
                         (e.g., 'MKT', 'SMB', 'HML')
        """
        try:
            if len(asset_returns) < 30:
                return FactorExposureResult(
                    alpha=0.0, alpha_tstat=0.0, alpha_pvalue=1.0,
                    betas={}, beta_tstats={}, beta_pvalues={},
                    r_squared=0.0, adjusted_r_squared=0.0,
                    residual_volatility=0.0, factor_count=0,
                    is_valid=False,
                    message="Insufficient data, need at least 30 days",
                )

            y = self._excess_returns(asset_returns)
            factor_names = list(factor_returns.columns)
            x = factor_returns.values

            min_len = min(len(y), len(x))
            y = y[:min_len]
            x = x[:min_len]

            n = len(y)
            k = x.shape[1]

            x_with_const = np.column_stack([np.ones(n), x])

            try:
                beta_vec = np.linalg.lstsq(x_with_const, y, rcond=None)[0]
            except np.linalg.LinAlgError:
                return FactorExposureResult(
                    alpha=0.0, alpha_tstat=0.0, alpha_pvalue=1.0,
                    betas={}, beta_tstats={}, beta_pvalues={},
                    r_squared=0.0, adjusted_r_squared=0.0,
                    residual_volatility=0.0, factor_count=0,
                    is_valid=False,
                    message="Regression failed: singular matrix",
                )

            residuals = y - x_with_const @ beta_vec
            alpha = float(beta_vec[0])
            betas = {name: float(beta_vec[i + 1]) for i, name in enumerate(factor_names)}

            ss_res = np.sum(residuals ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
            adjusted_r_squared = 1 - (1 - r_squared) * (n - 1) / (n - k - 1) if n > k + 1 else 0.0

            residual_vol = float(np.std(residuals) * np.sqrt(252))

            dof = n - k - 1
            if dof > 0:
                mse = ss_res / dof
                try:
                    cov_matrix = mse * np.linalg.inv(x_with_const.T @ x_with_const)
                except np.linalg.LinAlgError:
                    cov_matrix = np.eye(k + 1) * mse

                se = np.sqrt(np.diag(cov_matrix))
                t_stats = beta_vec / (se + 1e-15)
                p_values = 2 * (1 - stats.t.cdf(np.abs(t_stats), dof))

                alpha_tstat = float(t_stats[0])
                alpha_pvalue = float(p_values[0])
                beta_tstats = {name: float(t_stats[i + 1]) for i, name in enumerate(factor_names)}
                beta_pvalues = {name: float(p_values[i + 1]) for i, name in enumerate(factor_names)}
            else:
                alpha_tstat = 0.0
                alpha_pvalue = 1.0
                beta_tstats = dict.fromkeys(factor_names, 0.0)
                beta_pvalues = dict.fromkeys(factor_names, 1.0)

            return FactorExposureResult(
                alpha=alpha, alpha_tstat=alpha_tstat, alpha_pvalue=alpha_pvalue,
                betas=betas, beta_tstats=beta_tstats, beta_pvalues=beta_pvalues,
                r_squared=r_squared, adjusted_r_squared=adjusted_r_squared,
                residual_volatility=residual_vol, factor_count=k,
                is_valid=True, message="Factor exposure estimation successful",
            )
        except Exception as e:
            logger.warning("Factor exposure estimation failed: %s", e)
            return FactorExposureResult(
                alpha=0.0, alpha_tstat=0.0, alpha_pvalue=1.0,
                betas={}, beta_tstats={}, beta_pvalues={},
                r_squared=0.0, adjusted_r_squared=0.0,
                residual_volatility=0.0, factor_count=0,
                is_valid=False, message=f"Estimation failed: {e}",
            )

    def attribute_returns(
        self,
        asset_returns: pd.Series,
        factor_returns: pd.DataFrame,
        betas: dict[str, float],
    ) -> FactorAttributionResult:
        """
        Attribute asset returns to factor exposures.

        Parameters
        ----------
        asset_returns : Series of daily asset returns
        factor_returns : DataFrame with factor return columns
        betas : Dict mapping factor name to beta exposure
        """
        try:
            if len(asset_returns) < 1:
                return FactorAttributionResult(
                    total_return=0.0, factor_returns={},
                    specific_return=0.0, factor_contributions={},
                    is_valid=False, message="No returns data",
                )

            total_return = float(asset_returns.sum())
            factor_names = list(factor_returns.columns)
            min_len = min(len(asset_returns), len(factor_returns))

            factor_contributions = {}
            factor_total_returns = {}
            for name in factor_names:
                if name in betas:
                    factor_data = factor_returns[name].values[:min_len]
                    factor_total = float(factor_data.sum())
                    factor_total_returns[name] = factor_total
                    factor_contributions[name] = betas[name] * factor_total
                else:
                    factor_total_returns[name] = 0.0
                    factor_contributions[name] = 0.0

            total_factor_contribution = sum(factor_contributions.values())
            specific_return = total_return - total_factor_contribution

            return FactorAttributionResult(
                total_return=total_return,
                factor_returns=factor_total_returns,
                specific_return=specific_return,
                factor_contributions=factor_contributions,
                is_valid=True,
                message="Return attribution successful",
            )
        except Exception as e:
            logger.warning("Return attribution failed: %s", e)
            return FactorAttributionResult(
                total_return=0.0, factor_returns={},
                specific_return=0.0, factor_contributions={},
                is_valid=False, message=f"Attribution failed: {e}",
            )

    def construct_factor_mimicking_portfolios(
        self,
        returns: pd.DataFrame,
        sort_variable: pd.Series,
        n_portfolios: int = 5,
    ) -> dict[str, pd.Series]:
        """
        Construct factor-mimicking portfolios by sorting on a characteristic.

        Parameters
        ----------
        returns : DataFrame of asset returns (columns=assets)
        sort_variable : Series of values to sort on (index=assets)
        n_portfolios : Number of portfolios to form
        """
        try:
            assets = list(returns.columns)
            common = [a for a in assets if a in sort_variable.index]
            if len(common) < n_portfolios:
                return {}

            sorted_assets = sort_variable[common].sort_values()
            portfolio_size = len(sorted_assets) // n_portfolios

            portfolios: dict[str, pd.Series] = {}
            for i in range(n_portfolios):
                start = i * portfolio_size
                if i == n_portfolios - 1:
                    bucket = sorted_assets.iloc[start:]
                else:
                    bucket = sorted_assets.iloc[start:start + portfolio_size]

                port_assets = list(bucket.index)
                port_returns = returns[port_assets].mean(axis=1)
                portfolios[f"P{i+1}"] = port_returns

            if "P1" in portfolios and f"P{n_portfolios}" in portfolios:
                portfolios["SMB_like"] = portfolios["P1"] - portfolios[f"P{n_portfolios}"]

            return portfolios
        except Exception as e:
            logger.warning("Factor portfolio construction failed: %s", e)
            return {}
