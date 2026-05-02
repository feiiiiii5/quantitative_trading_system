import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class OverfittingReport:
    is_overfitted: bool
    overfitting_score: float
    train_test_sharpe_gap: float
    sharpe_degradation_pct: float
    consistency_score: float
    details: Dict = field(default_factory=dict)


@dataclass
class AnomalyReport:
    has_anomaly: bool
    anomaly_score: float
    anomaly_dates: List[str]
    anomaly_types: List[str]
    details: Dict = field(default_factory=dict)


@dataclass
class SignalAnomalyReport:
    has_anomaly: bool
    concentration_score: float
    turnover_anomaly: bool
    stale_signal: bool
    details: Dict = field(default_factory=dict)


@dataclass
class FullAuditReport:
    overfitting: OverfittingReport
    return_anomaly: AnomalyReport
    signal_anomaly: SignalAnomalyReport
    overall_score: float
    passed: bool
    recommendations: List[str]


class OverfittingDetector:
    def __init__(
        self,
        sharpe_gap_threshold: float = 1.0,
        degradation_threshold: float = 0.5,
        consistency_threshold: float = 0.6,
    ):
        self._sharpe_gap_threshold = sharpe_gap_threshold
        self._degradation_threshold = degradation_threshold
        self._consistency_threshold = consistency_threshold

    def detect(
        self,
        train_metrics: Dict,
        test_metrics: Dict,
        walk_forward_results: List[Dict] = None,
    ) -> OverfittingReport:
        train_sharpe = train_metrics.get("sharpe_ratio", 0)
        test_sharpe = test_metrics.get("sharpe_ratio", 0)

        sharpe_gap = train_sharpe - test_sharpe
        degradation_pct = sharpe_gap / abs(train_sharpe) if abs(train_sharpe) > 1e-10 else 0.0

        consistency_score = 0.0
        if walk_forward_results:
            positive_tests = sum(
                1 for r in walk_forward_results
                if r.get("test_metrics", {}).get("sharpe_ratio", 0) > 0
            )
            consistency_score = positive_tests / len(walk_forward_results)

        score = 0.0
        if sharpe_gap > self._sharpe_gap_threshold:
            score += 0.4
        if degradation_pct > self._degradation_threshold:
            score += 0.3
        if consistency_score < self._consistency_threshold:
            score += 0.3

        is_overfitted = score > 0.5

        details = {
            "train_sharpe": train_sharpe,
            "test_sharpe": test_sharpe,
            "sharpe_gap": round(sharpe_gap, 4),
            "degradation_pct": round(degradation_pct, 4),
            "consistency_score": round(consistency_score, 4),
        }

        if walk_forward_results:
            wf_sharpes = [r.get("test_metrics", {}).get("sharpe_ratio", 0) for r in walk_forward_results]
            details["wf_test_sharpe_std"] = round(float(np.std(wf_sharpes)), 4) if wf_sharpes else 0.0
            details["wf_test_sharpe_mean"] = round(float(np.mean(wf_sharpes)), 4) if wf_sharpes else 0.0

        return OverfittingReport(
            is_overfitted=is_overfitted,
            overfitting_score=round(score, 4),
            train_test_sharpe_gap=round(sharpe_gap, 4),
            sharpe_degradation_pct=round(degradation_pct, 4),
            consistency_score=round(consistency_score, 4),
            details=details,
        )


class ReturnAnomalyDetector:
    def __init__(
        self,
        zscore_threshold: float = 3.0,
        max_single_day_return: float = 0.10,
        max_consecutive_losses: int = 10,
    ):
        self._zscore_threshold = zscore_threshold
        self._max_single_day = max_single_day_return
        self._max_consecutive_losses = max_consecutive_losses

    def detect(
        self,
        returns: pd.Series,
        equity_curve: List[float] = None,
    ) -> AnomalyReport:
        if returns is None or len(returns) < 10:
            return AnomalyReport(
                has_anomaly=False, anomaly_score=0.0,
                anomaly_dates=[], anomaly_types=[],
            )

        anomaly_dates = []
        anomaly_types = []
        score = 0.0

        mean_ret = returns.mean()
        std_ret = returns.std()
        if std_ret > 1e-12:
            zscores = (returns - mean_ret) / std_ret
            extreme = zscores.abs() > self._zscore_threshold
            if extreme.any():
                for idx in returns.index[extreme]:
                    date_str = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)
                    anomaly_dates.append(date_str)
                anomaly_types.append("extreme_return")
                score += 0.3

        large_returns = returns.abs() > self._max_single_day
        if large_returns.any():
            for idx in returns.index[large_returns]:
                date_str = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)
                if date_str not in anomaly_dates:
                    anomaly_dates.append(date_str)
            anomaly_types.append("large_single_day")
            score += 0.3

        negative = returns < 0
        max_consec = 0
        current_consec = 0
        for val in negative:
            if val:
                current_consec += 1
                max_consec = max(max_consec, current_consec)
            else:
                current_consec = 0
        if max_consec > self._max_consecutive_losses:
            anomaly_types.append("consecutive_losses")
            score += 0.2

        if equity_curve and len(equity_curve) > 20:
            eq = pd.Series(equity_curve)
            eq_returns = eq.pct_change().dropna()
            if len(eq_returns) > 10:
                skew = float(eq_returns.skew())
                kurt = float(eq_returns.kurtosis())
                if abs(skew) > 2:
                    anomaly_types.append("skewness_anomaly")
                    score += 0.1
                if kurt > 7:
                    anomaly_types.append("kurtosis_anomaly")
                    score += 0.1

        has_anomaly = score > 0.3
        return AnomalyReport(
            has_anomaly=has_anomaly,
            anomaly_score=round(min(score, 1.0), 4),
            anomaly_dates=anomaly_dates[:20],
            anomaly_types=anomaly_types,
            details={
                "max_consecutive_losses": max_consec,
                "n_extreme_returns": int((returns.abs() > self._max_single_day).sum()),
            },
        )


class SignalAnomalyDetector:
    def __init__(
        self,
        max_signal_concentration: float = 0.5,
        max_turnover: float = 0.8,
        min_signal_frequency: float = 0.01,
        stale_threshold: int = 30,
    ):
        self._max_concentration = max_signal_concentration
        self._max_turnover = max_turnover
        self._min_frequency = min_signal_frequency
        self._stale_threshold = stale_threshold

    def detect(
        self,
        signals: pd.Series,
        factor_values: pd.Series = None,
    ) -> SignalAnomalyReport:
        if signals is None or len(signals) < 10:
            return SignalAnomalyReport(
                has_anomaly=False, concentration_score=0.0,
                turnover_anomaly=False, stale_signal=False,
            )

        concentration_score = 0.0
        turnover_anomaly = False
        stale_signal = False

        value_counts = signals.value_counts(normalize=True)
        if len(value_counts) > 0:
            max_freq = value_counts.iloc[0]
            concentration_score = float(max_freq)
        if concentration_score > self._max_concentration:
            concentration_score = min(concentration_score, 1.0)

        if factor_values is not None and len(factor_values) > 5:
            ranked = factor_values.rank(pct=True)
            changed = (ranked - ranked.shift(1)).abs() > 0.01
            turnover = float(changed.sum() / len(changed))
            if turnover > self._max_turnover:
                turnover_anomaly = True

        non_hold = (signals != 0).sum()
        frequency = non_hold / len(signals)
        if frequency < self._min_frequency:
            stale_signal = True

        last_signal_idx = signals[signals != 0].last_valid_index()
        if last_signal_idx is not None:
            if hasattr(signals.index, "get_loc"):
                try:
                    last_pos = signals.index.get_loc(last_signal_idx)
                    bars_since = len(signals) - last_pos - 1
                    if bars_since > self._stale_threshold:
                        stale_signal = True
                except Exception:
                    pass

        has_anomaly = concentration_score > self._max_concentration or turnover_anomaly or stale_signal

        return SignalAnomalyReport(
            has_anomaly=has_anomaly,
            concentration_score=round(concentration_score, 4),
            turnover_anomaly=turnover_anomaly,
            stale_signal=stale_signal,
            details={
                "signal_frequency": round(float(frequency), 4),
                "unique_signals": int(signals.nunique()),
            },
        )


class AutoAuditor:
    def __init__(self):
        self._overfitting_detector = OverfittingDetector()
        self._return_anomaly_detector = ReturnAnomalyDetector()
        self._signal_anomaly_detector = SignalAnomalyDetector()

    def audit(
        self,
        train_metrics: Dict,
        test_metrics: Dict,
        returns: pd.Series,
        signals: pd.Series = None,
        factor_values: pd.Series = None,
        walk_forward_results: List[Dict] = None,
        equity_curve: List[float] = None,
    ) -> FullAuditReport:
        overfitting = self._overfitting_detector.detect(
            train_metrics, test_metrics, walk_forward_results,
        )

        return_anomaly = self._return_anomaly_detector.detect(
            returns, equity_curve,
        )

        signal_anomaly = SignalAnomalyReport(
            has_anomaly=False, concentration_score=0.0,
            turnover_anomaly=False, stale_signal=False,
        )
        if signals is not None:
            signal_anomaly = self._signal_anomaly_detector.detect(
                signals, factor_values,
            )

        overall_score = (
            overfitting.overfitting_score * 0.4
            + return_anomaly.anomaly_score * 0.35
            + (signal_anomaly.concentration_score * 0.25 if signal_anomaly.has_anomaly else 0.0)
        )

        passed = overall_score < 0.4 and not overfitting.is_overfitted

        recommendations = []
        if overfitting.is_overfitted:
            recommendations.append("策略可能过拟合：训练集Sharpe显著高于测试集，建议简化策略或增加正则化")
        if overfitting.consistency_score < 0.6:
            recommendations.append("策略一致性不足：Walk-forward测试中正收益比例过低，建议增加样本外验证")
        if return_anomaly.has_anomaly:
            if "extreme_return" in return_anomaly.anomaly_types:
                recommendations.append("存在极端收益异常：建议检查数据质量和策略逻辑")
            if "consecutive_losses" in return_anomaly.anomaly_types:
                recommendations.append("存在连续亏损异常：建议增加止损机制")
        if signal_anomaly.has_anomaly:
            if signal_anomaly.concentration_score > 0.5:
                recommendations.append("信号过度集中：策略大部分时间输出同一信号，建议增加信号多样性")
            if signal_anomaly.turnover_anomaly:
                recommendations.append("换手率异常：因子值变化过于频繁，建议增加信号平滑")
            if signal_anomaly.stale_signal:
                recommendations.append("信号过期：策略长时间未产生新信号，建议检查策略逻辑")

        if not recommendations:
            recommendations.append("策略通过自动审计，未发现明显异常")

        return FullAuditReport(
            overfitting=overfitting,
            return_anomaly=return_anomaly,
            signal_anomaly=signal_anomaly,
            overall_score=round(overall_score, 4),
            passed=passed,
            recommendations=recommendations,
        )
