"""
QuantCore 相关性分析模块
提供资产间相关性矩阵、滚动相关性、聚类分析等功能
"""
import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class CorrelationResult:
    correlation_matrix: dict[str, dict[str, float]]
    highly_correlated_pairs: list[tuple[str, str, float]]
    low_correlated_pairs: list[tuple[str, str, float]]
    average_correlation: float
    diversification_score: float
    n_assets: int
    is_valid: bool
    message: str


@dataclass
class RollingCorrelationResult:
    rolling_correlations: dict[str, dict[str, list[tuple[str, float]]]]
    window_size: int
    is_valid: bool
    message: str


class CorrelationAnalyzer:

    def __init__(
        self,
        high_correlation_threshold: float = 0.7,
        low_correlation_threshold: float = 0.3,
    ):
        self.high_threshold = high_correlation_threshold
        self.low_threshold = low_correlation_threshold

    def analyze(
        self,
        prices: pd.DataFrame,
        method: str = "pearson",
    ) -> CorrelationResult:
        """
        Compute correlation matrix and identify highly/low correlated pairs.

        Parameters
        ----------
        prices : DataFrame of asset prices
        method : 'pearson' or 'spearman'
        """
        try:
            returns = np.log(prices / prices.shift(1)).dropna()
            if len(returns) < 20:
                return CorrelationResult(
                    correlation_matrix={}, highly_correlated_pairs=[],
                    low_correlated_pairs=[], average_correlation=0.0,
                    diversification_score=0.0, n_assets=0,
                    is_valid=False,
                    message="Insufficient data, need at least 20 days",
                )

            if method not in ("pearson", "spearman"):
                method = "pearson"

            corr_matrix = returns.corr(method=method)

            columns = list(corr_matrix.columns)
            n = len(columns)

            corr_dict: dict[str, dict[str, float]] = {}
            for col in columns:
                corr_dict[col] = {}
                for col2 in columns:
                    corr_dict[col][col2] = float(corr_matrix.loc[col, col2])

            high_pairs: list[tuple[str, str, float]] = []
            low_pairs: list[tuple[str, str, float]] = []

            for i in range(n):
                for j in range(i + 1, n):
                    val = float(corr_matrix.iloc[i, j])
                    if abs(val) >= self.high_threshold:
                        high_pairs.append((columns[i], columns[j], val))
                    elif abs(val) <= self.low_threshold:
                        low_pairs.append((columns[i], columns[j], val))

            upper_tri = []
            for i in range(n):
                for j in range(i + 1, n):
                    upper_tri.append(float(corr_matrix.iloc[i, j]))

            avg_corr = float(np.mean(upper_tri)) if upper_tri else 0.0
            div_score = 1.0 - avg_corr

            return CorrelationResult(
                correlation_matrix=corr_dict,
                highly_correlated_pairs=high_pairs,
                low_correlated_pairs=low_pairs,
                average_correlation=avg_corr,
                diversification_score=div_score,
                n_assets=n,
                is_valid=True,
                message="Correlation analysis successful",
            )
        except (ValueError, KeyError, TypeError) as e:
            logger.warning("Correlation analysis failed: %s", e)
            return CorrelationResult(
                correlation_matrix={}, highly_correlated_pairs=[],
                low_correlated_pairs=[], average_correlation=0.0,
                diversification_score=0.0, n_assets=0,
                is_valid=False, message=f"Analysis failed: {e}",
            )

    def rolling_correlation(
        self,
        prices: pd.DataFrame,
        window: int = 60,
        method: str = "pearson",
    ) -> RollingCorrelationResult:
        """
        Compute rolling pairwise correlations.

        Parameters
        ----------
        prices : DataFrame of asset prices
        window : Rolling window size in days
        method : 'pearson' or 'spearman'
        """
        try:
            returns = np.log(prices / prices.shift(1)).dropna()
            if len(returns) < window:
                return RollingCorrelationResult(
                    rolling_correlations={}, window_size=window,
                    is_valid=False,
                    message=f"Insufficient data, need at least {window} days",
                )

            columns = list(prices.columns)
            result: dict[str, dict[str, list[tuple[str, float]]]] = {}

            for i, col1 in enumerate(columns):
                result[col1] = {}
                for j, col2 in enumerate(columns):
                    if i >= j:
                        continue
                    rolling_corr = returns[col1].rolling(window).corr(returns[col2])
                    valid = rolling_corr.dropna()
                    result[col1][col2] = [
                        (str(date), float(val))
                        for date, val in valid.items()
                    ]

            return RollingCorrelationResult(
                rolling_correlations=result,
                window_size=window,
                is_valid=True,
                message="Rolling correlation analysis successful",
            )
        except (ValueError, KeyError, TypeError) as e:
            logger.warning("Rolling correlation analysis failed: %s", e)
            return RollingCorrelationResult(
                rolling_correlations={}, window_size=window,
                is_valid=False, message=f"Analysis failed: {e}",
            )

    def find_optimal_pairs(self, prices: pd.DataFrame, target_corr: float = 0.0) -> list[tuple[str, str, float]]:
        """Find asset pairs closest to target correlation (for pairs trading)."""
        try:
            result = self.analyze(prices)
            if not result.is_valid:
                return []

            all_pairs = []
            columns = list(prices.columns)
            n = len(columns)
            corr_matrix = result.correlation_matrix

            for i in range(n):
                for j in range(i + 1, n):
                    val = corr_matrix[columns[i]][columns[j]]
                    all_pairs.append((columns[i], columns[j], val))

            all_pairs.sort(key=lambda x: abs(x[2] - target_corr))
            return all_pairs[:10]
        except (ValueError, KeyError, TypeError) as e:
            logger.warning("Optimal pair search failed: %s", e)
            return []
