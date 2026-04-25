import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class QualityIssueType(Enum):
    MISSING = "missing"
    DUPLICATE = "duplicate"
    OUTLIER = "outlier"
    STALE = "stale"
    GAP = "gap"
    INCONSISTENT = "inconsistent"
    TIMEZONE = "timezone"


@dataclass
class QualityIssue:
    issue_type: QualityIssueType
    symbol: str
    field: str
    severity: str
    details: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "issue_type": self.issue_type.value,
            "symbol": self.symbol,
            "field": self.field,
            "severity": self.severity,
            "details": self.details,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.timestamp)),
        }


@dataclass
class QualityReport:
    symbol: str
    total_records: int
    issues: List[QualityIssue] = field(default_factory=list)
    score: float = 100.0

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "total_records": self.total_records,
            "score": round(self.score, 2),
            "issue_count": len(self.issues),
            "issues": [i.to_dict() for i in self.issues],
        }


class DataQualityChecker:
    def __init__(
        self,
        max_missing_pct: float = 0.05,
        outlier_std_threshold: float = 5.0,
        stale_seconds: int = 300,
        max_gap_seconds: int = 65,
    ):
        self.max_missing_pct = max_missing_pct
        self.outlier_std_threshold = outlier_std_threshold
        self.stale_seconds = stale_seconds
        self.max_gap_seconds = max_gap_seconds
        self._issue_history: List[QualityIssue] = []
        self._max_history = 10000

    def check_dataframe(self, df: pd.DataFrame, symbol: str) -> QualityReport:
        if df.empty:
            return QualityReport(symbol=symbol, total_records=0, score=0.0)

        issues: List[QualityIssue] = []
        total_records = len(df)

        issues.extend(self._check_missing(df, symbol))
        issues.extend(self._check_duplicates(df, symbol))
        issues.extend(self._check_outliers(df, symbol))
        issues.extend(self._check_gaps(df, symbol))
        issues.extend(self._check_stale(df, symbol))

        score = self._calculate_score(total_records, issues)

        report = QualityReport(
            symbol=symbol, total_records=total_records, issues=issues, score=score
        )

        self._issue_history.extend(issues)
        self._trim_history()

        return report

    def _check_missing(self, df: pd.DataFrame, symbol: str) -> List[QualityIssue]:
        issues = []
        for col in df.columns:
            missing_count = df[col].isna().sum()
            if missing_count > 0:
                missing_pct = missing_count / len(df)
                if missing_pct > self.max_missing_pct:
                    issues.append(QualityIssue(
                        issue_type=QualityIssueType.MISSING,
                        symbol=symbol, field=col, severity="high",
                        details={"missing_count": int(missing_count), "missing_pct": round(missing_pct, 4)},
                    ))
                else:
                    issues.append(QualityIssue(
                        issue_type=QualityIssueType.MISSING,
                        symbol=symbol, field=col, severity="low",
                        details={"missing_count": int(missing_count), "missing_pct": round(missing_pct, 4)},
                    ))
        return issues

    def _check_duplicates(self, df: pd.DataFrame, symbol: str) -> List[QualityIssue]:
        issues = []
        if "timestamp" in df.columns:
            dup_count = df["timestamp"].duplicated().sum()
            if dup_count > 0:
                issues.append(QualityIssue(
                    issue_type=QualityIssueType.DUPLICATE,
                    symbol=symbol, field="timestamp", severity="medium",
                    details={"duplicate_count": int(dup_count)},
                ))
        return issues

    def _check_outliers(self, df: pd.DataFrame, symbol: str) -> List[QualityIssue]:
        issues = []
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if col in ("timestamp", "volume"):
                continue
            col_data = df[col].dropna()
            if len(col_data) < 10:
                continue
            mean = col_data.mean()
            std = col_data.std()
            if std <= 0:
                continue
            outliers = col_data[(col_data - mean).abs() > self.outlier_std_threshold * std]
            if len(outliers) > 0:
                issues.append(QualityIssue(
                    issue_type=QualityIssueType.OUTLIER,
                    symbol=symbol, field=col, severity="medium",
                    details={
                        "outlier_count": int(len(outliers)),
                        "threshold": self.outlier_std_threshold,
                        "mean": round(float(mean), 4),
                        "std": round(float(std), 4),
                        "max_outlier": round(float(outliers.max()), 4),
                        "min_outlier": round(float(outliers.min()), 4),
                    },
                ))
        return issues

    def _check_gaps(self, df: pd.DataFrame, symbol: str) -> List[QualityIssue]:
        issues = []
        if "timestamp" not in df.columns or len(df) < 2:
            return issues

        timestamps = pd.to_datetime(df["timestamp"])
        diffs = timestamps.diff().dt.total_seconds().dropna()
        if len(diffs) == 0:
            return issues

        large_gaps = diffs[diffs > self.max_gap_seconds]
        if len(large_gaps) > 0:
            issues.append(QualityIssue(
                issue_type=QualityIssueType.GAP,
                symbol=symbol, field="timestamp", severity="high",
                details={
                    "gap_count": int(len(large_gaps)),
                    "max_gap_seconds": round(float(large_gaps.max()), 2),
                    "avg_gap_seconds": round(float(diffs.mean()), 2),
                },
            ))
        return issues

    def _check_stale(self, df: pd.DataFrame, symbol: str) -> List[QualityIssue]:
        issues = []
        if "timestamp" not in df.columns or len(df) == 0:
            return issues

        last_ts = df["timestamp"].iloc[-1]
        try:
            last_time = pd.to_datetime(last_ts)
            now = pd.Timestamp.now()
            diff_seconds = (now - last_time).total_seconds()
            if diff_seconds > self.stale_seconds:
                issues.append(QualityIssue(
                    issue_type=QualityIssueType.STALE,
                    symbol=symbol, field="timestamp", severity="high",
                    details={
                        "last_update": str(last_time),
                        "stale_seconds": round(diff_seconds, 2),
                        "threshold_seconds": self.stale_seconds,
                    },
                ))
        except Exception:
            pass
        return issues

    def _calculate_score(self, total_records: int, issues: List[QualityIssue]) -> float:
        if total_records == 0:
            return 0.0

        score = 100.0
        severity_weights = {"high": 10, "medium": 5, "low": 2}
        for issue in issues:
            weight = severity_weights.get(issue.severity, 2)
            score -= weight

        return max(0, score)

    def get_summary(self, symbol: Optional[str] = None) -> dict:
        issues = self._issue_history
        if symbol:
            issues = [i for i in issues if i.symbol == symbol]

        issue_counts = {}
        severity_counts = {}
        for issue in issues:
            it = issue.issue_type.value
            issue_counts[it] = issue_counts.get(it, 0) + 1
            sev = issue.severity
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        return {
            "total_issues": len(issues),
            "issue_breakdown": issue_counts,
            "severity_breakdown": severity_counts,
        }

    def _trim_history(self):
        if len(self._issue_history) > self._max_history:
            self._issue_history = self._issue_history[-self._max_history:]
