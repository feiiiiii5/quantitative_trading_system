import time

import pytest

from core.journal_analytics import analyze_journal


def _make_entry(
    pnl: float = 0,
    emotion: str = "neutral",
    rating: int = 3,
    timestamp: float = 0,
    tags: list[str] | None = None,
    notes: str = "",
) -> dict:
    return {
        "pnl": pnl,
        "emotion": emotion,
        "rating": rating,
        "timestamp": timestamp,
        "tags": tags or [],
        "notes": notes,
    }


class TestJournalAnalytics:
    def test_empty_entries(self):
        report = analyze_journal([])
        assert report.total_entries == 0

    def test_basic_stats(self):
        entries = [
            _make_entry(pnl=100, emotion="confident", rating=4, timestamp=time.time()),
            _make_entry(pnl=-50, emotion="anxious", rating=2, timestamp=time.time()),
            _make_entry(pnl=200, emotion="confident", rating=5, timestamp=time.time()),
        ]
        report = analyze_journal(entries)
        assert report.total_entries == 3
        assert "confident" in report.win_rate_by_emotion
        assert "anxious" in report.win_rate_by_emotion

    def test_emotion_distribution(self):
        entries = [
            _make_entry(emotion="confident"),
            _make_entry(emotion="confident"),
            _make_entry(emotion="anxious"),
        ]
        report = analyze_journal(entries)
        assert report.emotion_distribution["confident"] == 2
        assert report.emotion_distribution["anxious"] == 1

    def test_win_rate_by_emotion(self):
        entries = [
            _make_entry(pnl=100, emotion="confident"),
            _make_entry(pnl=-50, emotion="confident"),
            _make_entry(pnl=200, emotion="confident"),
        ]
        report = analyze_journal(entries)
        assert report.win_rate_by_emotion["confident"] == pytest.approx(2 / 3, abs=0.01)

    def test_avg_return_by_emotion(self):
        entries = [
            _make_entry(pnl=100, emotion="confident"),
            _make_entry(pnl=-50, emotion="confident"),
        ]
        report = analyze_journal(entries)
        assert report.avg_return_by_emotion["confident"] == pytest.approx(25.0, abs=0.01)

    def test_revenge_trading_detection(self):
        now = time.time()
        entries = [
            _make_entry(pnl=-100, timestamp=now),
            _make_entry(pnl=-200, timestamp=now + 1800),
            _make_entry(pnl=-150, timestamp=now + 3600),
            _make_entry(pnl=-80, timestamp=now + 5400),
        ]
        report = analyze_journal(entries)
        patterns = [i.pattern for i in report.behavioral_insights]
        assert "revenge_trading" in patterns

    def test_fomo_detection(self):
        entries = [
            _make_entry(pnl=-100, emotion="greedy"),
            _make_entry(pnl=-200, emotion="fomo"),
            _make_entry(pnl=-50, emotion="excited"),
        ]
        report = analyze_journal(entries)
        patterns = [i.pattern for i in report.behavioral_insights]
        assert "fomo" in patterns

    def test_loss_aversion_detection(self):
        entries = [
            _make_entry(pnl=-100, tags=["held_too_long"]),
            _make_entry(pnl=-200, notes="I held too long and should have sold"),
            _make_entry(pnl=-50, tags=["held_too_long"]),
        ]
        report = analyze_journal(entries)
        patterns = [i.pattern for i in report.behavioral_insights]
        assert "loss_aversion" in patterns

    def test_overtrading_detection(self):
        base = time.time() - 86400 * 3
        entries = []
        for day in range(3):
            for _ in range(6):
                entries.append(_make_entry(pnl=10, timestamp=base + day * 86400 + _ * 600))
        report = analyze_journal(entries)
        patterns = [i.pattern for i in report.behavioral_insights]
        assert "overtrading" in patterns

    def test_no_false_positives(self):
        entries = [
            _make_entry(pnl=100, emotion="confident", rating=4, timestamp=time.time()),
        ]
        report = analyze_journal(entries)
        assert len(report.behavioral_insights) == 0

    def test_to_dict(self):
        entries = [
            _make_entry(pnl=100, emotion="confident", rating=4, timestamp=time.time()),
            _make_entry(pnl=-50, emotion="anxious", rating=2, timestamp=time.time()),
        ]
        report = analyze_journal(entries)
        d = report.to_dict()
        assert "total_entries" in d
        assert "behavioral_insights" in d
        assert "win_rate_by_emotion" in d
        assert "emotion_distribution" in d

    def test_rating_correlation(self):
        entries = [
            _make_entry(pnl=100, rating=5),
            _make_entry(pnl=50, rating=4),
            _make_entry(pnl=-10, rating=3),
            _make_entry(pnl=-50, rating=2),
            _make_entry(pnl=-100, rating=1),
        ]
        report = analyze_journal(entries)
        assert report.rating_correlation > 0.5

    def test_performance_by_time(self):
        now = time.time()
        entries = [
            _make_entry(pnl=100, timestamp=now - 3600),
            _make_entry(pnl=-50, timestamp=now - 7200),
        ]
        report = analyze_journal(entries)
        assert len(report.performance_by_time_of_day) > 0

    def test_insight_severity(self):
        now = time.time()
        entries = []
        for i in range(8):
            entries.append(_make_entry(pnl=-100, timestamp=now + i * 1800))
        report = analyze_journal(entries)
        revenge_insights = [i for i in report.behavioral_insights if i.pattern == "revenge_trading"]
        if revenge_insights:
            assert revenge_insights[0].severity in ("medium", "high")
