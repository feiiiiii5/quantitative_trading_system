import pytest

from core.trade_journal import JournalEntry, TradeJournal


@pytest.fixture
def journal(tmp_path):
    db_path = str(tmp_path / "test_journal.db")
    return TradeJournal(db_path=db_path)


class TestTradeJournalAdd:
    def test_add_basic(self, journal):
        entry = JournalEntry(
            symbol="000001",
            name="平安银行",
            trade_type="buy",
            price=10.5,
            quantity=1000,
            notes="测试买入",
        )
        entry_id = journal.add_entry(entry)
        assert entry_id > 0

    def test_add_with_tags(self, journal):
        entry = JournalEntry(
            symbol="000001",
            name="平安银行",
            trade_type="sell",
            price=11.0,
            quantity=500,
            tags=["突破", "放量"],
            emotion="confident",
            rating=4,
        )
        entry_id = journal.add_entry(entry)
        assert entry_id > 0

    def test_add_empty_symbol(self, journal):
        entry = JournalEntry(symbol="", trade_type="buy")
        entry_id = journal.add_entry(entry)
        assert entry_id > 0

    def test_rating_clamped(self, journal):
        entry = JournalEntry(symbol="000001", trade_type="buy", rating=10)
        journal.add_entry(entry)
        entries = journal.get_entries(symbol="000001")
        assert entries[0].rating == 5


class TestTradeJournalGet:
    def test_get_all(self, journal):
        for i in range(5):
            journal.add_entry(JournalEntry(symbol=f"00000{i}", trade_type="buy"))
        entries = journal.get_entries()
        assert len(entries) == 5

    def test_get_by_symbol(self, journal):
        journal.add_entry(JournalEntry(symbol="000001", trade_type="buy"))
        journal.add_entry(JournalEntry(symbol="000002", trade_type="sell"))
        entries = journal.get_entries(symbol="000001")
        assert len(entries) == 1
        assert entries[0].symbol == "000001"

    def test_get_by_tag(self, journal):
        journal.add_entry(JournalEntry(symbol="000001", trade_type="buy", tags=["突破"]))
        journal.add_entry(JournalEntry(symbol="000002", trade_type="buy", tags=["回调"]))
        entries = journal.get_entries(tag="突破")
        assert len(entries) == 1

    def test_get_with_pagination(self, journal):
        for _i in range(10):
            journal.add_entry(JournalEntry(symbol="000001", trade_type="buy"))
        entries = journal.get_entries(limit=5, offset=0)
        assert len(entries) == 5

    def test_get_empty(self, journal):
        entries = journal.get_entries()
        assert entries == []


class TestTradeJournalUpdate:
    def test_update_notes(self, journal):
        entry_id = journal.add_entry(JournalEntry(symbol="000001", trade_type="buy", notes="old"))
        ok = journal.update_entry(entry_id, {"notes": "new notes"})
        assert ok
        entries = journal.get_entries(symbol="000001")
        assert entries[0].notes == "new notes"

    def test_update_tags(self, journal):
        entry_id = journal.add_entry(JournalEntry(symbol="000001", trade_type="buy"))
        ok = journal.update_entry(entry_id, {"tags": ["趋势", "突破"]})
        assert ok
        entries = journal.get_entries(symbol="000001")
        assert "趋势" in entries[0].tags

    def test_update_rating(self, journal):
        entry_id = journal.add_entry(JournalEntry(symbol="000001", trade_type="buy", rating=3))
        journal.update_entry(entry_id, {"rating": 5})
        entries = journal.get_entries(symbol="000001")
        assert entries[0].rating == 5

    def test_update_nonexistent(self, journal):
        ok = journal.update_entry(9999, {"notes": "test"})
        assert not ok

    def test_update_disallowed_field(self, journal):
        entry_id = journal.add_entry(JournalEntry(symbol="000001", trade_type="buy"))
        ok = journal.update_entry(entry_id, {"symbol": "000002"})
        assert not ok


class TestTradeJournalDelete:
    def test_delete(self, journal):
        entry_id = journal.add_entry(JournalEntry(symbol="000001", trade_type="buy"))
        ok = journal.delete_entry(entry_id)
        assert ok
        entries = journal.get_entries(symbol="000001")
        assert len(entries) == 0

    def test_delete_nonexistent(self, journal):
        ok = journal.delete_entry(9999)
        assert not ok


class TestTradeJournalStats:
    def test_empty_stats(self, journal):
        stats = journal.get_stats()
        assert stats["total_entries"] == 0

    def test_stats_with_data(self, journal):
        journal.add_entry(JournalEntry(symbol="000001", trade_type="buy", emotion="confident", rating=4))
        journal.add_entry(JournalEntry(symbol="000002", trade_type="sell", emotion="nervous", rating=2))
        stats = journal.get_stats()
        assert stats["total_entries"] == 2
        assert "buy" in stats["by_type"]
        assert "sell" in stats["by_type"]
        assert stats["avg_rating"] > 0
