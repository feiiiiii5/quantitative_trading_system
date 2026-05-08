

class TestSimulatedTradingBuySell:
    def test_buy_and_sell_same_day_fails_t1(self):
        from core.simulated_trading import SimulatedTrading

        st = SimulatedTrading(initial_capital=100000)
        result = st.execute_buy("000001", "平安银行", "A", 10.0, 1000)
        assert result["success"] is True

        sell_result = st.execute_sell("000001", 10.5)
        assert sell_result["success"] is False
        assert "T+1" in sell_result["error"]

    def test_buy_sets_available_shares_to_zero(self):
        from core.simulated_trading import SimulatedTrading

        st = SimulatedTrading(initial_capital=100000)
        st.execute_buy("000001", "平安银行", "A", 10.0, 1000)
        pos = st._positions["000001"]
        assert pos.available_shares == 0

    def test_settle_makes_shares_available(self):
        from core.simulated_trading import SimulatedTrading

        st = SimulatedTrading(initial_capital=100000)
        st.execute_buy("000001", "平安银行", "A", 10.0, 1000)
        st.daily_settlement()
        pos = st._positions["000001"]
        assert pos.available_shares == 1000

    def test_sell_after_settlement_succeeds(self):
        from datetime import datetime, timedelta

        from core.simulated_trading import SimulatedTrading

        st = SimulatedTrading(initial_capital=100000)
        st.execute_buy("000001", "平安银行", "A", 10.0, 1000)
        st._positions["000001"].buy_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        st.daily_settlement()
        result = st.execute_sell("000001", 10.5)
        assert result["success"] is True

    def test_sell_partial_after_settlement(self):
        from datetime import datetime, timedelta

        from core.simulated_trading import SimulatedTrading

        st = SimulatedTrading(initial_capital=100000)
        st.execute_buy("000001", "平安银行", "A", 10.0, 1000)
        st._positions["000001"].buy_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        st.daily_settlement()
        result = st.execute_sell("000001", 10.5, shares=500)
        assert result["success"] is True
        assert st._positions["000001"].shares == 500
        assert st._positions["000001"].available_shares == 500

    def test_sell_more_than_available_fails(self):
        from datetime import datetime, timedelta

        from core.simulated_trading import SimulatedTrading

        st = SimulatedTrading(initial_capital=100000)
        st.execute_buy("000001", "平安银行", "A", 10.0, 1000)
        st._positions["000001"].buy_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        st.daily_settlement()
        st.execute_sell("000001", 10.5, shares=500)
        result = st.execute_sell("000001", 10.5, shares=600)
        assert result["success"] is False
        assert "可卖数量不足" in result["error"]

    def test_insufficient_funds_buy(self):
        from core.simulated_trading import SimulatedTrading

        st = SimulatedTrading(initial_capital=1000)
        result = st.execute_buy("000001", "平安银行", "A", 10.0, 1000)
        assert result["success"] is False
        assert "资金不足" in result["error"]

    def test_invalid_lot_size_buy(self):
        from core.simulated_trading import SimulatedTrading

        st = SimulatedTrading(initial_capital=100000)
        result = st.execute_buy("000001", "平安银行", "A", 10.0, 50)
        assert result["success"] is False
        assert "最小买入" in result["error"]

    def test_duplicate_order_id_rejected(self):
        from core.simulated_trading import SimulatedTrading

        st = SimulatedTrading(initial_capital=100000)
        result1 = st.execute_buy("000001", "平安银行", "A", 10.0, 1000, order_id="order-1")
        assert result1["success"] is True
        result2 = st.execute_buy("000001", "平安银行", "A", 10.0, 1000, order_id="order-1")
        assert result2["success"] is False
        assert "重复订单" in result2["error"]

    def test_cash_consistency_check_rolls_back_on_buy(self):
        from core.simulated_trading import SimulatedTrading

        st = SimulatedTrading(initial_capital=100000)
        st._cash = 5.0
        result = st.execute_buy("000001", "平安银行", "A", 10.0, 1000)
        assert result["success"] is False
        assert "资金不足" in result["error"]

    def test_sell_negative_price_rejected(self):
        from datetime import datetime, timedelta

        from core.simulated_trading import SimulatedTrading

        st = SimulatedTrading(initial_capital=100000)
        st.execute_buy("000001", "平安银行", "A", 10.0, 1000)
        st._positions["000001"].buy_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        st.daily_settlement()
        result = st.execute_sell("000001", -5.0)
        assert result["success"] is False
        assert "无效" in result["error"]

    def test_sell_zero_price_rejected(self):
        from datetime import datetime, timedelta

        from core.simulated_trading import SimulatedTrading

        st = SimulatedTrading(initial_capital=100000)
        st.execute_buy("000001", "平安银行", "A", 10.0, 1000)
        st._positions["000001"].buy_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        st.daily_settlement()
        result = st.execute_sell("000001", 0)
        assert result["success"] is False
        assert "无效" in result["error"]


class TestGetPositions:
    def test_get_positions_returns_dict(self):
        from core.simulated_trading import SimulatedTrading

        st = SimulatedTrading(initial_capital=100000)
        positions = st.get_positions()
        assert isinstance(positions, dict)
        assert len(positions) == 0

    def test_get_positions_after_buy(self):
        from core.simulated_trading import SimulatedTrading

        st = SimulatedTrading(initial_capital=100000)
        st.execute_buy("000001", "平安银行", "A", 10.0, 1000)
        positions = st.get_positions()
        assert "000001" in positions
        assert positions["000001"].symbol == "000001"
        assert positions["000001"].shares == 1000

    def test_get_positions_returns_copy(self):
        from core.simulated_trading import SimulatedTrading

        st = SimulatedTrading(initial_capital=100000)
        st.execute_buy("000001", "平安银行", "A", 10.0, 1000)
        pos1 = st.get_positions()
        pos2 = st.get_positions()
        assert pos1 is not pos2


class TestExportImportPortfolio:
    def test_export_empty_portfolio(self):
        from core.simulated_trading import SimulatedTrading

        st = SimulatedTrading(initial_capital=100000)
        data = st.export_portfolio()
        assert data["version"] == "1.0"
        assert data["initial_capital"] == 100000
        assert data["cash"] == 100000
        assert data["positions"] == []
        assert data["pending_orders"] == []
        assert data["trade_history"] == []

    def test_export_with_positions(self):
        from core.simulated_trading import SimulatedTrading

        st = SimulatedTrading(initial_capital=100000)
        st.execute_buy("000001", "平安银行", "A", 10.0, 1000)
        data = st.export_portfolio()
        assert len(data["positions"]) == 1
        assert data["positions"][0]["symbol"] == "000001"
        assert data["positions"][0]["shares"] == 1000
        assert len(data["trade_history"]) == 1

    def test_import_restores_positions(self):
        from datetime import datetime, timedelta

        from core.simulated_trading import SimulatedTrading

        st = SimulatedTrading(initial_capital=100000)
        st.execute_buy("000001", "平安银行", "A", 10.0, 1000)
        st._positions["000001"].buy_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        st.daily_settlement()
        st.execute_sell("000001", 10.5, shares=500)
        data = st.export_portfolio()

        st2 = SimulatedTrading(initial_capital=100000)
        result = st2.import_portfolio(data)
        assert result["success"] is True
        assert "000001" in st2._positions
        assert st2._positions["000001"].shares == 500
        assert len(st2._trade_history) == 2

    def test_import_rejects_invalid_version(self):
        from core.simulated_trading import SimulatedTrading

        st = SimulatedTrading(initial_capital=100000)
        result = st.import_portfolio({"version": "2.0"})
        assert result["success"] is False
        assert "version" in result["error"].lower()

    def test_export_import_roundtrip(self):
        from core.simulated_trading import SimulatedTrading

        st = SimulatedTrading(initial_capital=500000)
        st.execute_buy("600036", "招商银行", "A", 35.0, 1000)
        st.execute_buy("000858", "五粮液", "A", 180.0, 100)
        data = st.export_portfolio()

        st2 = SimulatedTrading(initial_capital=500000)
        st2.import_portfolio(data)
        data2 = st2.export_portfolio()

        assert data["cash"] == data2["cash"]
        assert len(data["positions"]) == len(data2["positions"])
        assert len(data["trade_history"]) == len(data2["trade_history"])
