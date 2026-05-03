import threading
import time
from core.simulated_trading import SimulatedTrading


class TestSimulatedTradingBasic:
    def test_execute_buy_basic(self):
        t = SimulatedTrading(initial_capital=1000000)
        result = t.execute_buy(
            symbol="000001", name="平安银行", market="A",
            price=10.0, shares=100, market_price=10.0,
        )
        assert result["success"] is True
        assert result["trade"]["action"] == "buy"
        assert result["trade"]["shares"] == 100

    def test_execute_sell_basic(self):
        t = SimulatedTrading(initial_capital=1000000)
        t.execute_buy(
            symbol="000001", name="平安银行", market="A",
            price=10.0, shares=100, market_price=10.0,
        )
        t._positions["000001"].available_shares = 100
        t._positions["000001"].buy_date = "2020-01-01"
        result = t.execute_sell(
            symbol="000001", price=11.0, market_price=11.0,
        )
        assert result["success"] is True
        assert result["trade"]["action"] == "sell"

    def test_duplicate_order_id_rejected(self):
        t = SimulatedTrading(initial_capital=1000000)
        r1 = t.execute_buy(
            symbol="000001", name="平安银行", market="A",
            price=10.0, shares=100, market_price=10.0,
            order_id="dup-001",
        )
        assert r1["success"] is True
        r2 = t.execute_buy(
            symbol="000001", name="平安银行", market="A",
            price=10.0, shares=100, market_price=10.0,
            order_id="dup-001",
        )
        assert r2["success"] is False
        assert "重复" in r2["error"]

    def test_reset_account_clears_order_ids(self):
        t = SimulatedTrading(initial_capital=1000000)
        t.execute_buy(
            symbol="000001", name="平安银行", market="A",
            price=10.0, shares=100, market_price=10.0,
            order_id="oid-1",
        )
        assert len(t._order_ids) > 0
        t.reset_account()
        assert len(t._order_ids) == 0

    def test_order_ids_max_cap(self):
        t = SimulatedTrading(initial_capital=1000000000)
        t._max_order_ids = 5
        for i in range(10):
            t.execute_buy(
                symbol=f"00000{i}", name=f"Stock{i}", market="A",
                price=1.0, shares=100, market_price=1.0,
                order_id=f"oid-{i}",
            )
        assert len(t._order_ids) <= 5

    def test_place_order_basic(self):
        t = SimulatedTrading(initial_capital=1000000)
        result = t.place_order(
            symbol="000001", name="平安银行", market="A",
            action="buy", order_type="limit", price=10.0, shares=100,
        )
        assert result["success"] is True
        assert result["order"]["status"] == "pending"

    def test_cancel_order(self):
        t = SimulatedTrading(initial_capital=1000000)
        result = t.place_order(
            symbol="000001", name="平安银行", market="A",
            action="buy", order_type="limit", price=10.0, shares=100,
        )
        order_id = result["order"]["id"]
        cancel_result = t.cancel_order(order_id)
        assert cancel_result["success"] is True

    def test_get_pending_orders(self):
        t = SimulatedTrading(initial_capital=1000000)
        t.place_order(
            symbol="000001", name="平安银行", market="A",
            action="buy", order_type="limit", price=10.0, shares=100,
        )
        pending = t.get_pending_orders()
        assert len(pending) == 1
        assert pending[0]["symbol"] == "000001"

    def test_get_account_info(self):
        t = SimulatedTrading(initial_capital=1000000)
        info = t.get_account_info()
        assert info["total_assets"] == 1000000
        assert info["cash"] == 1000000
        assert info["position_count"] == 0


class TestSimulatedTradingConcurrency:
    def test_concurrent_buys_no_overdraft(self):
        t = SimulatedTrading(initial_capital=100000)
        errors = []
        results = []

        def buy_stock(idx):
            try:
                r = t.execute_buy(
                    symbol=f"00000{idx % 5}", name=f"Stock{idx}", market="A",
                    price=50.0, shares=100, market_price=50.0,
                )
                results.append(r)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=buy_stock, args=(i,)) for i in range(20)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()

        total_spent = sum(
            r["trade"]["amount"] + r["trade"]["fee"]
            for r in results
            if r.get("success") and "trade" in r
        )
        assert total_spent <= 100000 + 1

    def test_concurrent_place_and_cancel(self):
        t = SimulatedTrading(initial_capital=1000000)
        errors = []

        def place_orders():
            for i in range(10):
                try:
                    t.place_order(
                        symbol="000001", name="平安银行", market="A",
                        action="buy", order_type="limit", price=10.0, shares=100,
                    )
                except Exception as e:
                    errors.append(e)

        def cancel_orders():
            time.sleep(0.01)
            for _ in range(5):
                try:
                    pending = t.get_pending_orders()
                    for o in pending[:1]:
                        t.cancel_order(o["id"])
                except Exception as e:
                    errors.append(e)

        t1 = threading.Thread(target=place_orders)
        t2 = threading.Thread(target=cancel_orders)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert len(errors) == 0

    def test_concurrent_read_account(self):
        t = SimulatedTrading(initial_capital=1000000)
        t.execute_buy(
            symbol="000001", name="平安银行", market="A",
            price=10.0, shares=100, market_price=10.0,
        )
        errors = []
        results = []

        def read_account():
            try:
                info = t.get_account_info()
                results.append(info)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=read_account) for _ in range(10)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()

        assert len(errors) == 0
        assert len(results) == 10
        for info in results:
            assert info["total_assets"] > 0


class TestFeeCalculation:
    def test_a_stock_buy_fee(self):
        t = SimulatedTrading(initial_capital=1000000)
        commission, stamp_tax = t._calc_fee(10000.0, is_sell=False, market="A")
        assert commission == max(10000.0 * 0.0003, 5.0)
        assert stamp_tax == 0

    def test_a_stock_sell_fee(self):
        t = SimulatedTrading(initial_capital=1000000)
        commission, stamp_tax = t._calc_fee(10000.0, is_sell=True, market="A")
        assert commission == max(10000.0 * 0.0003, 5.0)
        assert stamp_tax == 10000.0 * 0.001

    def test_us_stock_fee_scales_with_shares(self):
        t = SimulatedTrading(initial_capital=1000000)
        commission_100, _ = t._calc_fee(10000.0, is_sell=False, market="US", shares=100)
        commission_1000, _ = t._calc_fee(100000.0, is_sell=False, market="US", shares=1000)
        assert commission_1000 > commission_100, "US commission must scale with trade size"

    def test_us_stock_no_stamp_tax(self):
        t = SimulatedTrading(initial_capital=1000000)
        _, stamp_tax = t._calc_fee(10000.0, is_sell=True, market="US", shares=100)
        assert stamp_tax == 0

    def test_hk_stock_buy_fee(self):
        t = SimulatedTrading(initial_capital=1000000)
        commission, stamp_tax = t._calc_fee(100000.0, is_sell=False, market="HK")
        assert commission == max(100000.0 * 0.0005, 50.0)
        assert stamp_tax > 0, "HK buy should include SFC levy"

    def test_hk_stock_sell_fee_includes_levy(self):
        t = SimulatedTrading(initial_capital=1000000)
        commission, stamp_tax = t._calc_fee(100000.0, is_sell=True, market="HK")
        assert commission == max(100000.0 * 0.0005, 50.0)
        assert stamp_tax > 0
