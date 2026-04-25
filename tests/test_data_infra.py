import time
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from core.data_infra.tick_store import TickStore, TickData, BarData, OrderBookData, DataType
from core.data_infra.data_adapter import (
    DataSourceHealth, SourceStatus, UnifiedDataAdapter, SourceHealth,
)
from core.data_infra.realtime_stream import RealtimeStreamManager, ConnectionState, StreamMessage
from core.data_infra.history_manager import HistoryDataManager, AdjustType, CorporateAction
from core.data_infra.alt_data import (
    AltDataPipeline, NewsSentimentAnalyzer, NorthboundFlow, SocialHeat,
)


class TestTickStore:
    def test_tick_data_to_dict(self):
        tick = TickData(symbol="600519", timestamp=1700000000000000000, price=1800.0, volume=100)
        d = tick.to_dict()
        assert d["symbol"] == "600519"
        assert d["price"] == 1800.0

    def test_bar_data_to_dict(self):
        bar = BarData(symbol="600519", timestamp=1700000000000000000,
                      open=1790, high=1810, low=1785, close=1800, volume=5000)
        d = bar.to_dict()
        assert d["open"] == 1790

    def test_orderbook_data_to_dict(self):
        from core.data_infra.tick_store import OrderBookLevel
        ob = OrderBookData(
            symbol="600519", timestamp=1700000000000000000,
            bids=[OrderBookLevel(price=1799, volume=200)],
            asks=[OrderBookLevel(price=1801, volume=150)],
        )
        d = ob.to_dict()
        assert len(d["bids"]) == 1
        assert d["bids"][0]["price"] == 1799

    def test_write_and_read(self, tmp_path):
        store = TickStore(base_dir=str(tmp_path / "tick"))
        tick = TickData(symbol="000001", timestamp=int(time.time() * 1e9), price=10.5, volume=100)
        store.write_tick(tick, DataType.TICK)
        store.flush_all()

        df = store.read_ticks("000001", DataType.TICK)
        assert not df.empty
        assert df.iloc[0]["price"] == 10.5

    def test_import_from_dataframe(self, tmp_path):
        store = TickStore(base_dir=str(tmp_path / "tick"))
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=10),
            "open": np.random.uniform(10, 20, 10),
            "close": np.random.uniform(10, 20, 10),
            "high": np.random.uniform(10, 20, 10),
            "low": np.random.uniform(10, 20, 10),
            "volume": np.random.randint(100, 1000, 10),
        })
        store.import_from_dataframe("TEST", DataType.BAR, df)

        result = store.read_ticks("TEST", DataType.BAR)
        assert not result.empty

    def test_get_symbols(self, tmp_path):
        store = TickStore(base_dir=str(tmp_path / "tick"))
        tick = TickData(symbol="SYM1", timestamp=int(time.time() * 1e9), price=10, volume=100)
        store.write_tick(tick, DataType.TICK)
        store.flush_all()
        symbols = store.get_symbols()
        assert "SYM1" in symbols

    def test_delete_data(self, tmp_path):
        store = TickStore(base_dir=str(tmp_path / "tick"))
        tick = TickData(symbol="DEL", timestamp=int(time.time() * 1e9), price=10, volume=100)
        store.write_tick(tick, DataType.TICK)
        store.flush_all()
        store.delete_data("DEL", DataType.TICK)
        result = store.read_ticks("DEL", DataType.TICK)
        assert result.empty


class TestDataSourceHealth:
    def test_record_success(self):
        health = DataSourceHealth()
        health.record_success("test_source", 50.0)
        h = health.get_health("test_source")
        assert h.status == SourceStatus.HEALTHY
        assert h.total_requests == 1

    def test_record_failure(self):
        health = DataSourceHealth()
        for _ in range(10):
            health.record_failure("test_source", "error")
        h = health.get_health("test_source")
        assert h.success_rate < 0.5
        assert h.status == SourceStatus.DOWN

    def test_is_available(self):
        health = DataSourceHealth()
        health.record_success("good", 10)
        assert health.is_available("good")
        for _ in range(10):
            health.record_failure("bad", "err")
        assert not health.is_available("bad")


class TestRealtimeStreamManager:
    def test_subscribe(self):
        mgr = RealtimeStreamManager()
        assert mgr.subscribe("600519")
        assert "600519" in mgr._subscriptions

    def test_unsubscribe(self):
        mgr = RealtimeStreamManager()
        mgr.subscribe("600519")
        mgr.unsubscribe("600519")
        assert "600519" not in mgr._subscriptions

    def test_max_subscriptions(self):
        mgr = RealtimeStreamManager(max_subscriptions=2)
        assert mgr.subscribe("A")
        assert mgr.subscribe("B")
        assert not mgr.subscribe("C")

    def test_push_data(self):
        mgr = RealtimeStreamManager()
        mgr.subscribe("600519")
        received = []
        mgr._subscriptions["600519"].callback = lambda msg: received.append(msg)
        import asyncio
        asyncio.run(mgr.push_data("600519", {"price": 1800}))
        assert len(received) == 1
        assert received[0].data["price"] == 1800

    def test_get_status(self):
        mgr = RealtimeStreamManager()
        mgr.subscribe("600519")
        status = mgr.get_status()
        assert status["subscriptions"] == 1
        assert status["state"] == ConnectionState.DISCONNECTED.value


class TestHistoryDataManager:
    def test_save_and_load(self, tmp_path):
        mgr = HistoryDataManager(base_dir=str(tmp_path / "hist"))
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=30),
            "open": np.random.uniform(10, 20, 30),
            "close": np.random.uniform(10, 20, 30),
            "high": np.random.uniform(10, 20, 30),
            "low": np.random.uniform(10, 20, 30),
            "volume": np.random.randint(100, 1000, 30),
        })
        mgr.save_history("600519", df, AdjustType.FORWARD)
        loaded = mgr.load_history("600519", AdjustType.FORWARD)
        assert not loaded.empty

    def test_corporate_action(self, tmp_path):
        mgr = HistoryDataManager(base_dir=str(tmp_path / "hist"))
        action = CorporateAction(
            symbol="600519", date="2024-06-01", action_type="dividend",
            dividend_per_share=10.0, description="每10股派10元",
        )
        mgr.add_corporate_action(action)
        actions = mgr.get_corporate_actions("600519")
        assert len(actions) == 1
        assert actions[0]["dividend_per_share"] == 10.0

    def test_adjustment_factors(self, tmp_path):
        mgr = HistoryDataManager(base_dir=str(tmp_path / "hist"))
        action = CorporateAction(
            symbol="600519", date="2024-06-01", action_type="split",
            split_ratio=2.0, description="10送10",
        )
        mgr.add_corporate_action(action)
        factors = mgr.get_adjustment_factors("600519")
        assert len(factors) == 1
        assert factors[0].factor == 2.0

    def test_list_symbols(self, tmp_path):
        mgr = HistoryDataManager(base_dir=str(tmp_path / "hist"))
        df = pd.DataFrame({
            "date": ["2024-01-01"],
            "open": [10], "close": [11], "high": [12], "low": [9], "volume": [100],
        })
        mgr.save_history("TEST1", df)
        symbols = mgr.list_symbols()
        assert any(s.get("symbol") == "TEST1" for s in symbols)


class TestNewsSentimentAnalyzer:
    def test_positive_sentiment(self):
        analyzer = NewsSentimentAnalyzer()
        result = analyzer.analyze("贵州茅台业绩超预期，股价强势上涨")
        assert result.sentiment_score > 0
        assert result.sentiment_label == "positive"

    def test_negative_sentiment(self):
        analyzer = NewsSentimentAnalyzer()
        result = analyzer.analyze("市场暴跌，多只股票破位下跌")
        assert result.sentiment_score < 0
        assert result.sentiment_label == "negative"

    def test_neutral_sentiment(self):
        analyzer = NewsSentimentAnalyzer()
        result = analyzer.analyze("今日市场正常交易")
        assert result.sentiment_label == "neutral"

    def test_batch_analysis(self):
        analyzer = NewsSentimentAnalyzer()
        items = [
            {"title": "利好消息推动上涨", "content": "", "source": "test"},
            {"title": "利空导致暴跌", "content": "", "source": "test"},
        ]
        results = analyzer.analyze_batch(items)
        assert len(results) == 2
        assert results[0].sentiment_label == "positive"
        assert results[1].sentiment_label == "negative"
