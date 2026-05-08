import numpy as np
import pandas as pd


class TestComputeAdvanceDecline:
    def test_basic_computation_mixed(self):
        from core.market_breadth import MarketBreadthAnalyzer

        analyzer = MarketBreadthAnalyzer()
        price_changes = {
            "AAPL": 2.5,
            "MSFT": -1.3,
            "GOOG": 0.8,
            "AMZN": -0.4,
            "TSLA": 3.1,
            "META": -2.0,
            "NVDA": 1.5,
            "INTC": -0.7,
            "AMD": 0.0,
            "NFLX": 0.3,
        }
        result = analyzer.compute_advance_decline(price_changes)

        assert result["total_stocks"] == 10
        assert result["advancing"] == 5
        assert result["declining"] == 4
        assert result["unchanged"] == 1
        assert result["advance_decline_ratio"] == round(5 / 4, 2)
        assert result["advance_decline_spread"] == 1
        assert result["breadth_score"] == round(5 / 10 * 100, 2)
        assert result["regime"] == "neutral"
        assert result["limit_up"] == 0
        assert result["limit_down"] == 0

    def test_all_advancing_broad_advance_regime(self):
        from core.market_breadth import MarketBreadthAnalyzer

        analyzer = MarketBreadthAnalyzer()
        price_changes = {f"STOCK{i}": float(i % 5 + 1) for i in range(20)}
        result = analyzer.compute_advance_decline(price_changes)

        assert result["advancing"] == 20
        assert result["declining"] == 0
        assert result["breadth_score"] == 100.0
        assert result["regime"] == "broad_advance"
        assert result["advance_decline_ratio"] == 999.0

    def test_all_declining_broad_decline_regime(self):
        from core.market_breadth import MarketBreadthAnalyzer

        analyzer = MarketBreadthAnalyzer()
        price_changes = {f"STOCK{i}": -float(i % 5 + 1) for i in range(20)}
        result = analyzer.compute_advance_decline(price_changes)

        assert result["advancing"] == 0
        assert result["declining"] == 20
        assert result["breadth_score"] == 0.0
        assert result["regime"] == "broad_decline"
        assert result["advance_decline_ratio"] == 0.0

    def test_empty_input_returns_error(self):
        from core.market_breadth import MarketBreadthAnalyzer

        analyzer = MarketBreadthAnalyzer()
        result = analyzer.compute_advance_decline({})

        assert "error" in result

    def test_unchanged_stocks_counted(self):
        from core.market_breadth import MarketBreadthAnalyzer

        analyzer = MarketBreadthAnalyzer()
        price_changes = {"A": 0.0, "B": 0.0, "C": 1.0}
        result = analyzer.compute_advance_decline(price_changes)

        assert result["unchanged"] == 2
        assert result["advancing"] == 1
        assert result["declining"] == 0

    def test_limit_up_and_limit_down_detection(self):
        from core.market_breadth import MarketBreadthAnalyzer

        analyzer = MarketBreadthAnalyzer()
        price_changes = {
            "A": 9.5,
            "B": 10.0,
            "C": 9.4,
            "D": -9.5,
            "E": -10.0,
            "F": -9.4,
            "G": 2.0,
        }
        result = analyzer.compute_advance_decline(price_changes)

        assert result["limit_up"] == 2
        assert result["limit_down"] == 2

    def test_thrust_ratio_no_declining_stocks(self):
        from core.market_breadth import MarketBreadthAnalyzer

        analyzer = MarketBreadthAnalyzer()
        price_changes = {"A": 3.0, "B": 5.0, "C": 2.0}
        result = analyzer.compute_advance_decline(price_changes)

        assert result["thrust_ratio"] == 999.0

    def test_single_stock(self):
        from core.market_breadth import MarketBreadthAnalyzer

        analyzer = MarketBreadthAnalyzer()
        result = analyzer.compute_advance_decline({"SOLO": 2.5})

        assert result["total_stocks"] == 1
        assert result["advancing"] == 1
        assert result["declining"] == 0
        assert result["breadth_score"] == 100.0
        assert result["regime"] == "broad_advance"


class TestComputeMcClellanOscillator:
    def _make_history(self, n, spread_fn=None):
        if spread_fn is None:
            def spread_fn(i):
                return 100 * np.sin(i * 0.3)
        return [
            {"date": f"2024-01-{i+1:02d}", "spread": spread_fn(i)}
            for i in range(n)
        ]

    def test_basic_computation_sufficient_data(self):
        from core.market_breadth import MarketBreadthAnalyzer

        analyzer = MarketBreadthAnalyzer()
        history = self._make_history(40)
        result = analyzer.compute_mcclellan_oscillator(history)

        assert "current" in result
        assert "signal" in result
        assert "ema_19" in result
        assert "ema_39" in result
        assert "history" in result
        assert isinstance(result["current"], float)
        assert isinstance(result["history"], list)

    def test_insufficient_data_returns_error(self):
        from core.market_breadth import MarketBreadthAnalyzer

        analyzer = MarketBreadthAnalyzer()
        history = self._make_history(15)
        result = analyzer.compute_mcclellan_oscillator(history)

        assert "error" in result
        assert "15" in result["error"]

    def test_bullish_crossover_signal(self):
        from core.market_breadth import MarketBreadthAnalyzer

        analyzer = MarketBreadthAnalyzer()
        spreads = [-200.0] * 19 + [0.0] * 5 + [300.0] * 16
        history = [
            {"date": f"2024-01-{i+1:02d}", "spread": s}
            for i, s in enumerate(spreads)
        ]
        result = analyzer.compute_mcclellan_oscillator(history)

        assert result["signal"] in ("bullish_crossover", "overbought", "neutral")

    def test_bearish_crossover_signal(self):
        from core.market_breadth import MarketBreadthAnalyzer

        analyzer = MarketBreadthAnalyzer()
        spreads = [200.0] * 19 + [0.0] * 5 + [-300.0] * 16
        history = [
            {"date": f"2024-01-{i+1:02d}", "spread": s}
            for i, s in enumerate(spreads)
        ]
        result = analyzer.compute_mcclellan_oscillator(history)

        assert result["signal"] in ("bearish_crossover", "oversold", "neutral")

    def test_history_output_format(self):
        from core.market_breadth import MarketBreadthAnalyzer

        analyzer = MarketBreadthAnalyzer()
        history = self._make_history(30)
        result = analyzer.compute_mcclellan_oscillator(history)

        for entry in result["history"]:
            assert "date" in entry
            assert "value" in entry
            assert isinstance(entry["value"], float)


class TestComputePercentAboveMA:
    def _make_price_data(self, n_stocks, n_days, above=True):
        data = {}
        for i in range(n_stocks):
            if above:
                prices = pd.Series(np.linspace(90, 110, n_days) + i)
            else:
                prices = pd.Series(np.linspace(110, 90, n_days) + i)
            data[f"S{i}"] = prices
        return data

    def test_basic_computation(self):
        from core.market_breadth import MarketBreadthAnalyzer

        analyzer = MarketBreadthAnalyzer()
        price_data = {
            "A": pd.Series(np.linspace(90, 110, 60)),
            "B": pd.Series(np.linspace(110, 90, 60)),
            "C": pd.Series(np.linspace(95, 105, 60)),
        }
        result = analyzer.compute_percent_above_ma(price_data, ma_period=50)

        assert result["total_stocks"] == 3
        assert result["ma_period"] == 50
        assert "pct_above_ma" in result
        assert "signal" in result
        assert "details" in result

    def test_empty_input_returns_error(self):
        from core.market_breadth import MarketBreadthAnalyzer

        analyzer = MarketBreadthAnalyzer()
        result = analyzer.compute_percent_above_ma({})

        assert "error" in result

    def test_insufficient_data_shorter_than_ma_period(self):
        from core.market_breadth import MarketBreadthAnalyzer

        analyzer = MarketBreadthAnalyzer()
        price_data = {"A": pd.Series([100, 101, 102])}
        result = analyzer.compute_percent_above_ma(price_data, ma_period=50)

        assert "error" in result

    def test_all_above_ma_overbought_signal(self):
        from core.market_breadth import MarketBreadthAnalyzer

        analyzer = MarketBreadthAnalyzer()
        price_data = self._make_price_data(5, 60, above=True)
        result = analyzer.compute_percent_above_ma(price_data, ma_period=50)

        assert result["pct_above_ma"] == 100.0
        assert result["signal"] == "overbought"

    def test_all_below_ma_oversold_signal(self):
        from core.market_breadth import MarketBreadthAnalyzer

        analyzer = MarketBreadthAnalyzer()
        price_data = self._make_price_data(5, 60, above=False)
        result = analyzer.compute_percent_above_ma(price_data, ma_period=50)

        assert result["pct_above_ma"] == 0.0
        assert result["signal"] == "oversold"


class TestEMA:
    def test_basic_ema_computation(self):
        from core.market_breadth import MarketBreadthAnalyzer

        data = np.array([10.0, 11.0, 12.0, 13.0, 14.0])
        result = MarketBreadthAnalyzer._ema(data, 3)

        assert len(result) == len(data)
        assert result[0] == data[0]
        multiplier = 2.0 / (3 + 1)
        expected_1 = data[1] * multiplier + data[0] * (1 - multiplier)
        assert abs(result[1] - expected_1) < 1e-10

    def test_single_element(self):
        from core.market_breadth import MarketBreadthAnalyzer

        data = np.array([42.0])
        result = MarketBreadthAnalyzer._ema(data, 5)

        assert len(result) == 1
        assert result[0] == 42.0


class TestGetMarketBreadthAnalyzer:
    def test_singleton_returns_same_instance(self):
        import core.market_breadth as mb_module
        from core.market_breadth import get_market_breadth_analyzer

        mb_module._analyzer = None

        a = get_market_breadth_analyzer()
        b = get_market_breadth_analyzer()
        assert a is b

    def test_returns_correct_type(self):
        import core.market_breadth as mb_module
        from core.market_breadth import MarketBreadthAnalyzer, get_market_breadth_analyzer

        mb_module._analyzer = None

        analyzer = get_market_breadth_analyzer()
        assert isinstance(analyzer, MarketBreadthAnalyzer)
