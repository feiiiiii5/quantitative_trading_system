"""Tests for core database module."""
import tempfile
from pathlib import Path

import pytest

from core.database import SQLiteStore, ThreadSafeLRU


class TestThreadSafeLRU:
    def test_basic_get_set(self):
        cache = ThreadSafeLRU(maxsize=10, ttl=60)
        cache.set("key1", "value1")
        result = cache.get("key1")
        assert result == "value1"

    def test_ttl_expiry(self):
        cache = ThreadSafeLRU(maxsize=10, ttl=0)
        cache.set("key1", "value1")
        import time
        time.sleep(0.01)
        result = cache.get("key1")
        assert result is None

    def test_lru_eviction(self):
        cache = ThreadSafeLRU(maxsize=3, ttl=60)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        cache.set("key4", "value4")
        assert cache.get("key1") is None
        assert cache.get("key4") == "value4"

    def test_delete(self):
        cache = ThreadSafeLRU(maxsize=10, ttl=60)
        cache.set("key1", "value1")
        cache.delete("key1")
        assert cache.get("key1") is None

    def test_delete_prefix(self):
        cache = ThreadSafeLRU(maxsize=10, ttl=60)
        cache.set("prefix_key1", "value1")
        cache.set("prefix_key2", "value2")
        cache.set("other_key", "value3")
        count = cache.delete_prefix("prefix_")
        assert count == 2
        assert cache.get("prefix_key1") is None
        assert cache.get("other_key") == "value3"

    def test_clear(self):
        cache = ThreadSafeLRU(maxsize=10, ttl=60)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        assert len(cache) == 0


class TestSQLiteStore:
    @pytest.fixture
    def db_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_file = Path(tmpdir) / "test.db"
            yield str(db_file)

    @pytest.fixture
    def db(self, db_path):
        store = SQLiteStore(db_path)
        yield store
        try:
            store._flush_buffer()
            store.close()
        except Exception:
            pass

    def test_kline_crud(self, db):
        rows = [
            {"date": "2024-01-01", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0, "volume": 1000000, "amount": 102000000.0},
            {"date": "2024-01-02", "open": 103.0, "high": 108.0, "low": 102.0, "close": 106.0, "volume": 1200000, "amount": 125000000.0},
        ]
        count = db.upsert_kline_rows("000001", "sz", "daily", "", rows)
        assert count == 2
        db._flush_buffer()

        result = db.load_kline_rows("000001", "sz", "daily")
        assert len(result) == 2

    def test_fetchone(self, db):
        db.execute("CREATE TABLE IF NOT EXISTS test_table (id INTEGER, name TEXT)")
        db.execute("INSERT INTO test_table VALUES (?, ?)", (1, "test"))
        result = db.fetchone("SELECT * FROM test_table WHERE id=?", (1,))
        assert result is not None
        assert result["id"] == 1
        assert result["name"] == "test"

    def test_fetchall(self, db):
        db.execute("CREATE TABLE IF NOT EXISTS test_table2 (id INTEGER, name TEXT)")
        db.execute("INSERT INTO test_table2 VALUES (?, ?)", (1, "name1"))
        db.execute("INSERT INTO test_table2 VALUES (?, ?)", (2, "name2"))
        results = db.fetchall("SELECT * FROM test_table2")
        assert len(results) == 2

    def test_config_operations(self, db):
        db.set_config("test_key", "test_value")
        result = db.get_config("test_key")
        assert result == "test_value"

    def test_transaction(self, db):
        db.execute("CREATE TABLE IF NOT EXISTS trans_test (id INTEGER PRIMARY KEY, value TEXT)")
        with db.transaction() as tx:
            tx.execute("INSERT INTO trans_test VALUES (?, ?)", (1, "value1"))
            tx.execute("INSERT INTO trans_test VALUES (?, ?)", (2, "value2"))
        result = db.fetchall("SELECT * FROM trans_test")
        assert len(result) == 2

    def test_transaction_rollback(self, db):
        db.execute("CREATE TABLE IF NOT EXISTS rollback_test (id INTEGER PRIMARY KEY)")
        try:
            with db.transaction() as tx:
                tx.execute("INSERT INTO rollback_test VALUES (?)", (1,))
                tx.execute("INSERT INTO invalid_table VALUES (?)", (2,))
        except Exception:
            pass
        result = db.fetchall("SELECT * FROM rollback_test")
        assert len(result) == 0
