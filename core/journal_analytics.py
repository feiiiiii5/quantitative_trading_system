import logging
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class BehavioralInsight:
    pattern: str
    severity: str
    description: str
    evidence: list[str] = field(default_factory=list)
    recommendation: str = ""


@dataclass
class JournalAnalyticsReport:
    total_entries: int = 0
    win_rate_by_emotion: dict = field(default_factory=dict)
    avg_return_by_emotion: dict = field(default_factory=dict)
    emotion_distribution: dict = field(default_factory=dict)
    behavioral_insights: list[BehavioralInsight] = field(default_factory=list)
    performance_by_time_of_day: dict = field(default_factory=dict)
    consecutive_loss_streaks: list[dict] = field(default_factory=dict)
    avg_rating: float = 0.0
    rating_correlation: float = 0.0

    def to_dict(self) -> dict:
        return {
            "total_entries": self.total_entries,
            "win_rate_by_emotion": self.win_rate_by_emotion,
            "avg_return_by_emotion": self.avg_return_by_emotion,
            "emotion_distribution": self.emotion_distribution,
            "behavioral_insights": [
                {
                    "pattern": i.pattern,
                    "severity": i.severity,
                    "description": i.description,
                    "evidence": i.evidence,
                    "recommendation": i.recommendation,
                }
                for i in self.behavioral_insights
            ],
            "performance_by_time_of_day": self.performance_by_time_of_day,
            "consecutive_loss_streaks": self.consecutive_loss_streaks,
            "avg_rating": round(self.avg_rating, 2),
            "rating_correlation": round(self.rating_correlation, 4),
        }


def analyze_journal(entries: list[dict]) -> JournalAnalyticsReport:
    if not entries:
        return JournalAnalyticsReport()

    report = JournalAnalyticsReport(total_entries=len(entries))

    emotion_returns: dict[str, list[float]] = {}
    emotion_counts: dict[str, int] = {}
    ratings: list[float] = []
    returns: list[float] = []
    time_returns: dict[str, list[float]] = {}

    for entry in entries:
        emotion = entry.get("emotion", "neutral")
        rating = entry.get("rating", 0)
        pnl = entry.get("pnl", 0)

        if isinstance(rating, (int, float)):
            ratings.append(float(rating))
        if isinstance(pnl, (int, float)):
            returns.append(float(pnl))
            emotion_returns.setdefault(emotion, []).append(float(pnl))

        emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1

        timestamp = entry.get("timestamp", 0)
        if isinstance(timestamp, (int, float)) and timestamp > 0:
            from datetime import datetime
            try:
                dt = datetime.fromtimestamp(timestamp)
                hour_key = f"{dt.hour:02d}:00"
                if isinstance(pnl, (int, float)):
                    time_returns.setdefault(hour_key, []).append(float(pnl))
            except (OSError, ValueError, OverflowError):
                pass

    if emotion_returns:
        for emotion, rets in emotion_returns.items():
            wins = sum(1 for r in rets if r > 0)
            total = len(rets)
            report.win_rate_by_emotion[emotion] = round(wins / total, 4) if total > 0 else 0
            report.avg_return_by_emotion[emotion] = round(float(np.mean(rets)), 4) if rets else 0

    report.emotion_distribution = emotion_counts

    if ratings:
        report.avg_rating = float(np.mean(ratings))

    if len(ratings) > 2 and len(returns) >= len(ratings):
        min_len = min(len(ratings), len(returns))
        r_arr = np.array(ratings[:min_len])
        p_arr = np.array(returns[:min_len])
        if np.std(r_arr) > 0 and np.std(p_arr) > 0:
            report.rating_correlation = float(np.corrcoef(r_arr, p_arr)[0, 1])

    if time_returns:
        for hour, rets in sorted(time_returns.items()):
            wins = sum(1 for r in rets if r > 0)
            total = len(rets)
            report.performance_by_time_of_day[hour] = {
                "win_rate": round(wins / total, 4) if total > 0 else 0,
                "avg_return": round(float(np.mean(rets)), 4) if rets else 0,
                "n_trades": total,
            }

    _detect_behavioral_patterns(entries, report)

    return report


def _detect_behavioral_patterns(entries: list[dict], report: JournalAnalyticsReport) -> None:
    sorted_entries = sorted(entries, key=lambda e: e.get("timestamp", 0))

    _check_revenge_trading(sorted_entries, report)
    _check_fomo(sorted_entries, report)
    _check_loss_aversion(sorted_entries, report)
    _check_overtrading(sorted_entries, report)


def _check_revenge_trading(entries: list[dict], report: JournalAnalyticsReport) -> None:
    evidence = []
    for i in range(1, len(entries)):
        prev = entries[i - 1]
        curr = entries[i]
        prev_pnl = prev.get("pnl", 0)
        curr_pnl = curr.get("pnl", 0)
        prev_time = prev.get("timestamp", 0)
        curr_time = curr.get("timestamp", 0)

        if (isinstance(prev_pnl, (int, float)) and isinstance(curr_pnl, (int, float))
                and isinstance(prev_time, (int, float)) and isinstance(curr_time, (int, float))
                and prev_pnl < 0 and curr_pnl < 0 and (curr_time - prev_time) < 3600):
                evidence.append(
                    f"Consecutive losses within 1h at timestamps {int(prev_time)}/{int(curr_time)}"
                )

    if len(evidence) >= 2:
        report.behavioral_insights.append(BehavioralInsight(
            pattern="revenge_trading",
            severity="high" if len(evidence) >= 4 else "medium",
            description="Pattern of entering trades quickly after losses, suggesting emotional revenge trading",
            evidence=evidence[:5],
            recommendation="Implement a mandatory cooling-off period after a loss (e.g., 30 minutes) before entering a new trade",
        ))


def _check_fomo(entries: list[dict], report: JournalAnalyticsReport) -> None:
    fomo_emotions = {"greedy", "fomo", "excited", "anxious", "eager"}
    evidence = []
    for entry in entries:
        emotion = entry.get("emotion", "").lower()
        if emotion in fomo_emotions:
            pnl = entry.get("pnl", 0)
            if isinstance(pnl, (int, float)) and pnl < 0:
                evidence.append(f"Trade with {emotion} emotion resulted in loss: {pnl}")

    if len(evidence) >= 2:
        report.behavioral_insights.append(BehavioralInsight(
            pattern="fomo",
            severity="medium",
            description="Trades entered with FOMO-related emotions tend to result in losses",
            evidence=evidence[:5],
            recommendation="Wait for confirmation signals before entering trades driven by excitement or urgency",
        ))


def _check_loss_aversion(entries: list[dict], report: JournalAnalyticsReport) -> None:
    evidence = []
    for entry in entries:
        tags = entry.get("tags", [])
        if isinstance(tags, list) and "held_too_long" in [t.lower() for t in tags]:
            evidence.append("Trade tagged as held_too_long")
        notes = entry.get("notes", "").lower()
        if "should have sold" in notes or "held too long" in notes:
            evidence.append(f"Self-reported holding too long: {notes[:80]}")

    if len(evidence) >= 2:
        report.behavioral_insights.append(BehavioralInsight(
            pattern="loss_aversion",
            severity="medium",
            description="Tendency to hold losing positions too long, suggesting loss aversion bias",
            evidence=evidence[:5],
            recommendation="Set predefined stop-loss levels before entering each trade and commit to executing them",
        ))


def _check_overtrading(entries: list[dict], report: JournalAnalyticsReport) -> None:
    if len(entries) < 5:
        return

    day_counts: dict[str, int] = {}
    for entry in entries:
        timestamp = entry.get("timestamp", 0)
        if isinstance(timestamp, (int, float)) and timestamp > 0:
            from datetime import datetime
            try:
                dt = datetime.fromtimestamp(timestamp)
                day_key = dt.strftime("%Y-%m-%d")
                day_counts[day_key] = day_counts.get(day_key, 0) + 1
            except (OSError, ValueError, OverflowError):
                pass

    high_volume_days = {d: c for d, c in day_counts.items() if c >= 5}
    if len(high_volume_days) >= 2:
        evidence = [f"{d}: {c} trades" for d, c in sorted(high_volume_days.items())]
        avg_trades = float(np.mean(list(day_counts.values())))
        report.behavioral_insights.append(BehavioralInsight(
            pattern="overtrading",
            severity="high" if len(high_volume_days) >= 4 else "medium",
            description=f"Multiple days with 5+ trades (avg: {avg_trades:.1f}/day), suggesting overtrading",
            evidence=evidence[:5],
            recommendation="Set a daily trade limit (e.g., 3 trades/day) and track compliance",
        ))
