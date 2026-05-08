"""ML-Enhanced Factor Scoring Module.

Uses scikit-learn to train lightweight models that evaluate factor predictive power.
Designed for MPS acceleration when PyTorch is available.
"""
import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

SKLEARN_AVAILABLE = False
try:
    from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier
    from sklearn.model_selection import cross_val_score
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    logger.debug("scikit-learn not available, ML scoring disabled")


@dataclass
class MLScoringResult:
    factor_name: str
    ic_score: float = 0.0
    rf_importance: float = 0.0
    gb_importance: float = 0.0
    cv_score: float = 0.0
    ml_bonus: float = 0.0
    final_score: float = 0.0
    is_ml_enhanced: bool = False


class MLFactorScorer:
    def __init__(
        self,
        use_ml: bool = True,
        n_estimators: int = 50,
        cv_folds: int = 3,
    ):
        self._use_ml = use_ml and SKLEARN_AVAILABLE
        self._n_estimators = n_estimators
        self._cv_folds = cv_folds
        self._scaler = StandardScaler() if self._use_ml else None

    def score_factors(
        self,
        factor_data: dict[str, pd.Series],
        forward_returns: pd.Series,
        labels: pd.Series | None = None,
    ) -> dict[str, MLScoringResult]:
        results = {}
        ic_scores = {}

        for name, factor in factor_data.items():
            valid = factor.notna() & forward_returns.notna()
            if valid.sum() < 30:
                results[name] = MLScoringResult(
                    factor_name=name,
                    final_score=0.0,
                )
                continue

            f_vals = factor[valid].values.reshape(-1, 1)
            r_vals = forward_returns[valid].values

            ic = self._calc_ic(f_vals.flatten(), r_vals)
            ic_scores[name] = ic

            result = MLScoringResult(
                factor_name=name,
                ic_score=ic,
            )

            if self._use_ml and len(f_vals) >= 50:
                ml_score = self._calc_ml_score(f_vals, r_vals, labels)
                result.rf_importance = ml_score.get('rf', 0)
                result.gb_importance = ml_score.get('gb', 0)
                result.cv_score = ml_score.get('cv', 0)
                result.ml_bonus = ml_score.get('bonus', 0)
                result.final_score = ic + result.ml_bonus
                result.is_ml_enhanced = True
            else:
                result.final_score = ic

            results[name] = result

        return results

    def _calc_ic(self, x: np.ndarray, y: np.ndarray) -> float:
        std_x = np.std(x)
        std_y = np.std(y)
        if std_x < 1e-12 or std_y < 1e-12:
            return 0.0
        corr = np.corrcoef(x, y)[0, 1]
        return float(corr) if np.isfinite(corr) else 0.0

    def _calc_ml_score(
        self,
        x: np.ndarray,
        y: np.ndarray,
        labels: pd.Series | None,
    ) -> dict[str, float]:
        try:
            x_scaled = self._scaler.fit_transform(x)

            y_class = (y > np.median(y)).astype(int)
            if labels is not None:
                valid = labels.notna()
                y_class = labels[valid].values.astype(int)
                x_scaled = x_scaled[valid]
                if len(x_scaled) < 30:
                    return {}

            rf = RandomForestClassifier(n_estimators=self._n_estimators, random_state=42)
            rf.fit(x_scaled, y_class)
            rf_score = cross_val_score(rf, x_scaled, y_class, cv=self._cv_folds).mean()

            gb = GradientBoostingRegressor(n_estimators=self._n_estimators, random_state=42)
            gb.fit(x_scaled, y)
            gb_score = cross_val_score(gb, x_scaled, y, cv=self._cv_folds).mean()

            rf_importance = float(rf.feature_importances_[0]) if hasattr(rf, 'feature_importances_') else 0
            gb_importance = float(gb.feature_importances_[0]) if hasattr(gb, 'feature_importances_') else 0

            bonus = (rf_score - 0.5) * 2 * 0.05 + (gb_score - 0.5) * 2 * 0.05

            return {
                'rf': rf_importance,
                'gb': gb_importance,
                'cv': rf_score,
                'bonus': bonus,
            }
        except Exception as e:
            logger.debug("ML scoring failed for factor: %s", e)
            return {}

    def rank_factors(
        self,
        results: dict[str, MLScoringResult],
        top_n: int = 10,
    ) -> list[tuple[str, MLScoringResult]]:
        sorted_results = sorted(
            results.items(),
            key=lambda x: abs(x[1].final_score),
            reverse=True,
        )
        return sorted_results[:top_n]

    def get_summary_report(self, results: dict[str, MLScoringResult]) -> dict:
        ml_enhanced = [r for r in results.values() if r.is_ml_enhanced]
        return {
            "total_factors": len(results),
            "ml_enhanced_count": len(ml_enhanced),
            "avg_ic": np.mean([r.ic_score for r in results.values()]) if results else 0,
            "avg_final_score": np.mean([r.final_score for r in results.values()]) if results else 0,
            "top_factors": [
                {"name": name, "score": r.final_score, "ml_enhanced": r.is_ml_enhanced}
                for name, r in self.rank_factors(results, 5)
            ],
        }


def create_ensemble_signal(
    factor_weights: dict[str, float],
    factor_values: dict[str, pd.Series],
) -> pd.Series:
    if not factor_weights or not factor_values:
        return pd.Series(dtype=float)

    common_index: pd.Index | None = None
    for f in factor_values.values():
        common_index = f.dropna().index if common_index is None else common_index.intersection(f.dropna().index)

    if common_index is None or len(common_index) == 0:
        return pd.Series(dtype=float)

    ensemble = pd.Series(0.0, index=common_index)
    total_weight = 0.0

    for name, weight in factor_weights.items():
        if name in factor_values:
            f = factor_values[name].reindex(common_index).fillna(0)
            ensemble += f * weight
            total_weight += abs(weight)

    if total_weight > 0:
        ensemble /= total_weight

    return ensemble
