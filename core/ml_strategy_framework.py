from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

logger = logging.getLogger(__name__)

SKLEARN_AVAILABLE = False
try:
    from sklearn.base import BaseEstimator, clone
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score, log_loss
    from sklearn.model_selection import BaseCrossValidator, cross_val_score
    SKLEARN_AVAILABLE = True
except ImportError:
    logger.debug("scikit-learn not available, ML strategy framework disabled")

__all__ = [
    "PurgedKFold",
    "triple_barrier_labels",
    "meta_labeling",
    "mdi_importance",
    "mda_importance",
    "DistributionDriftMonitor",
    "MLStrategyPipeline",
    "MetaLabelingResult",
    "DriftResult",
    "TrainResult",
    "EvaluationResult",
]


@dataclass
class MetaLabelingResult:
    meta_labels: pd.Series
    feature_importance: dict[str, float]
    model: Any
    cv_scores: np.ndarray


@dataclass
class DriftResult:
    drift_detected: bool
    drifted_features: list[str]
    ks_statistics: dict[str, float]
    alert_level: str


@dataclass
class TrainResult:
    model: Any
    cv_scores: np.ndarray
    feature_importance: dict[str, float]
    oof_predictions: np.ndarray


@dataclass
class EvaluationResult:
    accuracy: float
    precision: float
    recall: float
    f1: float
    log_loss: float
    confusion_matrix: np.ndarray


if SKLEARN_AVAILABLE:

    class PurgedKFold(BaseCrossValidator):
        def __init__(self, n_splits: int = 5, pct_embargo: float = 0.01) -> None:
            self.n_splits = n_splits
            self.pct_embargo = pct_embargo

        def get_n_splits(
            self, x: Any = None, y: Any = None, groups: Any = None
        ) -> int:
            return self.n_splits

        def split(
            self,
            x: pd.DataFrame | np.ndarray,
            y: pd.Series | np.ndarray | None = None,
            groups: pd.Series | np.ndarray | None = None,
        ) -> list[tuple[np.ndarray, np.ndarray]]:
            n_samples = len(x)
            indices = np.arange(n_samples)
            embargo_size = int(n_samples * self.pct_embargo)

            fold_size = n_samples // self.n_splits
            splits: list[tuple[np.ndarray, np.ndarray]] = []

            for i in range(self.n_splits):
                test_start = i * fold_size
                test_end = (i + 1) * fold_size if i < self.n_splits - 1 else n_samples

                train_end = max(test_start - embargo_size, 0)
                train_indices = indices[:train_end]
                test_indices = indices[test_start:test_end]

                if len(train_indices) == 0 or len(test_indices) == 0:
                    continue

                splits.append((train_indices, test_indices))

            logger.debug(
                "PurgedKFold produced %d splits with embargo=%d samples",
                len(splits),
                embargo_size,
            )
            return splits

else:

    class PurgedKFold:
        def __init__(self, n_splits: int = 5, pct_embargo: float = 0.01) -> None:
            self.n_splits = n_splits
            self.pct_embargo = pct_embargo

        def split(self, x: Any, y: Any = None, groups: Any = None) -> list[tuple[np.ndarray, np.ndarray]]:
            raise RuntimeError("scikit-learn is required for PurgedKFold")


def triple_barrier_labels(
    prices: pd.Series,
    events: pd.DataFrame,
    pt_sl: list[float] | None = None,
    min_ret: float = 0.01,
) -> pd.DataFrame:
    if pt_sl is None:
        pt_sl = [1.0, 1.0]

    profit_mult, stop_mult = pt_sl
    results: list[dict[str, Any]] = []

    price_values = prices.values
    price_index = prices.index

    for event_idx in range(len(events)):
        row = events.iloc[event_idx]
        t0 = row.get("t0", events.index[event_idx]) if "t0" not in events.columns else row["t0"]
        trgt = row.get("trgt", min_ret)

        if pd.isna(trgt) or trgt <= 0:
            trgt = min_ret

        try:
            start_pos = price_index.get_loc(t0)
        except KeyError:
            start_pos = price_index.searchsorted(t0)
            if start_pos >= len(price_index):
                continue

        entry_price = price_values[start_pos]
        profit_barrier = entry_price * (1.0 + profit_mult * trgt)
        stop_barrier = entry_price * (1.0 - stop_mult * trgt)

        max_holding = len(price_values) - start_pos - 1
        if max_holding <= 0:
            continue

        t1_pos = start_pos + max_holding
        label = 0

        for offset in range(1, max_holding + 1):
            pos = start_pos + offset
            current_price = price_values[pos]

            if current_price >= profit_barrier:
                t1_pos = pos
                label = 1
                break
            if current_price <= stop_barrier:
                t1_pos = pos
                label = -1
                break

        t1 = price_index[t1_pos]
        results.append({"t0": t0, "t1": t1, "label": label})

    result_df = pd.DataFrame(results)
    if not result_df.empty:
        result_df = result_df.set_index("t0")
    logger.debug(
        "Triple barrier labels: %d events, %d profit, %d loss, %d timeout",
        len(result_df),
        (result_df["label"] == 1).sum() if len(result_df) > 0 else 0,
        (result_df["label"] == -1).sum() if len(result_df) > 0 else 0,
        (result_df["label"] == 0).sum() if len(result_df) > 0 else 0,
    )
    return result_df


def meta_labeling(
    primary_signals: pd.Series,
    actual_returns: pd.Series,
    features: pd.DataFrame,
) -> MetaLabelingResult:
    if not SKLEARN_AVAILABLE:
        raise RuntimeError("scikit-learn is required for meta_labeling")

    aligned = primary_signals.align(actual_returns, join="inner")
    signals = aligned[0]
    returns = aligned[1]

    common_idx = signals.index.intersection(features.index)
    signals = signals.loc[common_idx]
    returns = returns.loc[common_idx]
    x = features.loc[common_idx]

    primary_direction = np.sign(signals)
    correct_mask = np.sign(returns) == primary_direction
    meta_labels = correct_mask.astype(int)

    cv = PurgedKFold(n_splits=5, pct_embargo=0.01)

    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=5,
        min_samples_leaf=50,
        random_state=42,
        n_jobs=-1,
    )

    try:
        cv_scores = cross_val_score(
            model, x, meta_labels, cv=cv, scoring="accuracy"
        )
    except (ValueError, AttributeError, TypeError) as e:
        logger.warning("PurgedKFold CV failed (%s), falling back to simple split", e)
        split_point = int(len(x) * 0.7)
        x_train, x_val = x.iloc[:split_point], x.iloc[split_point:]
        y_train, y_val = meta_labels.iloc[:split_point], meta_labels.iloc[split_point:]
        model.fit(x_train, y_train)
        val_pred = model.predict(x_val)
        cv_scores = np.array([accuracy_score(y_val, val_pred)])

    model.fit(x, meta_labels)

    importance = mdi_importance(model, list(x.columns))

    logger.debug(
        "Meta-labeling: %d samples, %.1f%% positive, CV mean=%.3f",
        len(meta_labels),
        meta_labels.mean() * 100,
        cv_scores.mean(),
    )

    return MetaLabelingResult(
        meta_labels=pd.Series(meta_labels.values, index=meta_labels.index),
        feature_importance=importance,
        model=model,
        cv_scores=cv_scores,
    )


def mdi_importance(
    model: Any, feature_names: list[str]
) -> dict[str, float]:
    if not hasattr(model, "feature_importances_"):
        logger.warning("Model does not expose feature_importances_, returning uniform")
        n = len(feature_names)
        return dict.fromkeys(feature_names, 1.0 / n)

    raw = model.feature_importances_
    total = raw.sum()
    if total <= 0:
        total = 1.0
    normalized = raw / total

    return dict(zip(feature_names, normalized.tolist(), strict=False))


def mda_importance(
    model: Any,
    x: pd.DataFrame,
    y: pd.Series,
    cv: Any = None,
    scoring: Callable[..., float] | str = "accuracy",
) -> dict[str, float]:
    if not SKLEARN_AVAILABLE:
        raise RuntimeError("scikit-learn is required for mda_importance")

    if cv is None:
        cv = PurgedKFold(n_splits=5, pct_embargo=0.01)

    base_model = clone(model) if hasattr(model, "fit") else RandomForestClassifier(
        n_estimators=50, random_state=42, n_jobs=-1
    )
    if not hasattr(base_model, "fit"):
        return dict.fromkeys(x.columns, 0.0)

    try:
        base_scores = cross_val_score(base_model, x, y, cv=cv, scoring=scoring)
    except (ValueError, AttributeError, TypeError) as e:
        logger.warning("MDA: base CV failed (%s), returning uniform importance", e)
        return dict.fromkeys(x.columns, 0.0)

    base_mean = base_scores.mean()
    importance: dict[str, float] = {}

    for col in x.columns:
        x_permuted = x.copy()
        x_permuted[col] = np.random.permutation(x_permuted[col].values)

        try:
            perm_scores = cross_val_score(
                clone(base_model), x_permuted, y, cv=cv, scoring=scoring
            )
            importance[col] = base_mean - perm_scores.mean()
        except (ValueError, AttributeError, TypeError):
            importance[col] = 0.0

    total_imp = sum(abs(v) for v in importance.values())
    if total_imp > 0:
        importance = {k: v / total_imp for k, v in importance.items()}

    return importance


class DistributionDriftMonitor:
    def __init__(
        self,
        significance_level: float = 0.05,
        alert_threshold: float = 0.3,
    ) -> None:
        self._significance_level = significance_level
        self._alert_threshold = alert_threshold

    def monitor(
        self,
        features: pd.DataFrame,
        reference_distribution: pd.DataFrame,
    ) -> DriftResult:
        common_cols = [
            c for c in features.columns if c in reference_distribution.columns
        ]
        if not common_cols:
            logger.warning("No common columns between current and reference features")
            return DriftResult(
                drift_detected=True,
                drifted_features=[],
                ks_statistics={},
                alert_level="critical",
            )

        ks_statistics: dict[str, float] = {}
        drifted_features: list[str] = []

        for col in common_cols:
            current = features[col].dropna().values
            reference = reference_distribution[col].dropna().values

            if len(current) < 2 or len(reference) < 2:
                continue

            stat, p_value = scipy_stats.ks_2samp(reference, current)
            ks_statistics[col] = stat

            if p_value < self._significance_level:
                drifted_features.append(col)

        drift_detected = len(drifted_features) > 0
        drift_ratio = len(drifted_features) / len(common_cols) if common_cols else 0.0

        if drift_ratio >= self._alert_threshold:
            alert_level = "critical"
        elif drift_detected:
            alert_level = "warning"
        else:
            alert_level = "normal"

        logger.debug(
            "Drift monitor: %d/%d features drifted, alert=%s",
            len(drifted_features),
            len(common_cols),
            alert_level,
        )

        return DriftResult(
            drift_detected=drift_detected,
            drifted_features=drifted_features,
            ks_statistics=ks_statistics,
            alert_level=alert_level,
        )


class MLStrategyPipeline:
    def __init__(
        self,
        n_splits: int = 5,
        pct_embargo: float = 0.01,
        drift_significance: float = 0.05,
    ) -> None:
        self._n_splits = n_splits
        self._pct_embargo = pct_embargo
        self._cv = PurgedKFold(n_splits=n_splits, pct_embargo=pct_embargo)
        self._drift_monitor = DistributionDriftMonitor(
            significance_level=drift_significance
        )
        self._reference_features: pd.DataFrame | None = None
        self._trained_model: Any = None

    def generate_labels(
        self,
        prices: pd.Series,
        method: str = "triple_barrier",
        **kwargs: Any,
    ) -> pd.DataFrame:
        if method == "triple_barrier":
            events = kwargs.get("events")
            if events is None:
                returns = prices.pct_change().dropna()
                rolling_std = returns.rolling(20).std().dropna()
                trgt = rolling_std.reindex(prices.index).ffill().fillna(0.01)
                events = pd.DataFrame(
                    {"t0": prices.index, "trgt": trgt.values}
                )
                events = events.set_index("t0")

            pt_sl = kwargs.get("pt_sl", [1.0, 1.0])
            min_ret = kwargs.get("min_ret", 0.01)
            return triple_barrier_labels(prices, events, pt_sl=pt_sl, min_ret=min_ret)

        raise ValueError(f"Unknown label generation method: {method}")

    def train_model(
        self,
        x: pd.DataFrame,
        y: pd.Series,
        method: str = "purged_kfold",
        model_type: str = "random_forest",
    ) -> TrainResult:
        if not SKLEARN_AVAILABLE:
            raise RuntimeError("scikit-learn is required for train_model")

        model = self._create_model(model_type)
        cv = self._resolve_cv(method)

        try:
            cv_scores = cross_val_score(model, x, y, cv=cv, scoring="accuracy")
        except (ValueError, AttributeError, TypeError) as e:
            logger.warning("CV failed (%s), falling back to simple chronological split", e)
            split_point = int(len(x) * 0.7)
            x_train, x_val = x.iloc[:split_point], x.iloc[split_point:]
            y_train, y_val = y.iloc[:split_point], y.iloc[split_point:]
            model.fit(x_train, y_train)
            val_pred = model.predict(x_val)
            cv_scores = np.array([accuracy_score(y_val, val_pred)])

        model.fit(x, y)

        importance = mdi_importance(model, list(x.columns))

        oof_predictions = self._compute_oof_predictions(x, y, cv, model_type)

        if self._reference_features is None:
            self._reference_features = x.copy()

        self._trained_model = model

        logger.info(
            "Model trained: type=%s, cv_mean=%.3f (+/-%.3f), n_features=%d",
            model_type,
            cv_scores.mean(),
            cv_scores.std(),
            len(x.columns),
        )

        return TrainResult(
            model=model,
            cv_scores=cv_scores,
            feature_importance=importance,
            oof_predictions=oof_predictions,
        )

    def predict(self, model: Any, x: pd.DataFrame) -> pd.Series:
        if not SKLEARN_AVAILABLE:
            raise RuntimeError("scikit-learn is required for predict")

        predictions = model.predict(x)
        return pd.Series(predictions, index=x.index, name="prediction")

    def evaluate(
        self, predictions: pd.Series, actual: pd.Series
    ) -> EvaluationResult:
        common_idx = predictions.index.intersection(actual.index)
        y_pred = predictions.loc[common_idx].values
        y_true = actual.loc[common_idx].values

        accuracy = accuracy_score(y_true, y_pred)

        tp = np.sum((y_pred == 1) & (y_true == 1))
        fp = np.sum((y_pred == 1) & (y_true != 1))
        fn = np.sum((y_pred != 1) & (y_true == 1))

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        _ = np.unique(y_true)
        try:
            ll = log_loss(y_true, y_pred.astype(float))
        except (ValueError, TypeError):
            ll = float("nan")

        classes = sorted(np.unique(np.concatenate([y_true, y_pred])))
        n_classes = max(len(classes), 2)
        cm = np.zeros((n_classes, n_classes), dtype=int)
        class_to_idx = {c: i for i, c in enumerate(classes)}
        for true_val, pred_val in zip(y_true, y_pred, strict=False):
            cm[class_to_idx[true_val], class_to_idx[pred_val]] += 1

        return EvaluationResult(
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1=f1,
            log_loss=ll,
            confusion_matrix=cm,
        )

    def check_retraining_needed(self, current_features: pd.DataFrame) -> bool:
        if self._reference_features is None:
            logger.info("No reference distribution stored, cannot check drift")
            return False

        result = self._drift_monitor.monitor(current_features, self._reference_features)
        if result.drift_detected:
            logger.warning(
                "Distribution drift detected: %d features drifted, alert=%s",
                len(result.drifted_features),
                result.alert_level,
            )
        return result.drift_detected

    def _create_model(self, model_type: str) -> BaseEstimator:
        if model_type == "random_forest":
            return RandomForestClassifier(
                n_estimators=100,
                max_depth=6,
                min_samples_leaf=50,
                random_state=42,
                n_jobs=-1,
            )
        if model_type == "gradient_boosting":
            from sklearn.ensemble import GradientBoostingClassifier
            return GradientBoostingClassifier(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.1,
                min_samples_leaf=50,
                random_state=42,
            )
        raise ValueError(f"Unknown model_type: {model_type}")

    def _resolve_cv(self, method: str) -> Any:
        if method == "purged_kfold":
            return self._cv
        if method == "walk_forward":
            from sklearn.model_selection import TimeSeriesSplit
            return TimeSeriesSplit(n_splits=self._n_splits)
        raise ValueError(f"Unknown CV method: {method}")

    def _compute_oof_predictions(
        self,
        x: pd.DataFrame,
        y: pd.Series,
        cv: Any,
        model_type: str,
    ) -> np.ndarray:
        oof = np.full(len(x), np.nan)

        try:
            splits = cv.split(x, y)
        except (ValueError, AttributeError, TypeError):
            logger.warning("Cannot compute OOF predictions, CV split failed")
            return oof

        for train_idx, test_idx in splits:
            if len(train_idx) == 0 or len(test_idx) == 0:
                continue

            fold_model = self._create_model(model_type)
            x_train = x.iloc[train_idx]
            y_train = y.iloc[train_idx]
            try:
                fold_model.fit(x_train, y_train)
                oof[test_idx] = fold_model.predict(x.iloc[test_idx])
            except (ValueError, AttributeError, TypeError):
                logger.warning("OOF fold failed, skipping")

        return oof
