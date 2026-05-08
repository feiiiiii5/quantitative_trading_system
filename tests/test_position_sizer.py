
from core.position_sizer import PositionSizer


class TestKellyFraction:
    def test_valid_inputs(self):
        result = PositionSizer.kelly_fraction(0.6, 0.05, 0.03)
        assert result["suggested_fraction"] > 0
        assert result["suggested_fraction"] <= 0.25

    def test_zero_avg_loss(self):
        result = PositionSizer.kelly_fraction(0.6, 0.05, 0)
        assert "error" in result
        assert result["suggested_fraction"] == 0.0

    def test_zero_win_rate(self):
        result = PositionSizer.kelly_fraction(0, 0.05, 0.03)
        assert "error" in result

    def test_win_rate_one(self):
        result = PositionSizer.kelly_fraction(1.0, 0.05, 0.03)
        assert "error" in result

    def test_negative_kelly_no_bet(self):
        result = PositionSizer.kelly_fraction(0.3, 0.01, 0.05)
        assert result["suggested_fraction"] == 0.0
        assert result["fraction_type"] == "no_bet"


class TestATRPositionSize:
    def test_valid_inputs(self):
        result = PositionSizer.atr_position_size(100000, 50.0, 2.0)
        assert result["shares"] > 0
        assert result["stop_price"] < 50.0

    def test_zero_entry_price(self):
        result = PositionSizer.atr_position_size(100000, 0, 2.0)
        assert "error" in result
        assert result["shares"] == 0

    def test_zero_atr(self):
        result = PositionSizer.atr_position_size(100000, 50.0, 0)
        assert "error" in result

    def test_zero_capital(self):
        result = PositionSizer.atr_position_size(0, 50.0, 2.0)
        assert "error" in result

    def test_negative_entry_price(self):
        result = PositionSizer.atr_position_size(100000, -10.0, 2.0)
        assert "error" in result


class TestFixedRatioSize:
    def test_valid_inputs(self):
        result = PositionSizer.fixed_ratio_size(100000, 50.0)
        assert result["shares"] > 0

    def test_zero_entry_price(self):
        result = PositionSizer.fixed_ratio_size(100000, 0)
        assert "error" in result
        assert result["shares"] == 0

    def test_zero_capital(self):
        result = PositionSizer.fixed_ratio_size(0, 50.0)
        assert "error" in result

    def test_negative_price(self):
        result = PositionSizer.fixed_ratio_size(100000, -50.0)
        assert "error" in result


class TestRiskParitySize:
    def test_valid_inputs(self):
        positions = [
            {"symbol": "A", "volatility": 0.20},
            {"symbol": "B", "volatility": 0.30},
        ]
        result = PositionSizer.risk_parity_size(100000, positions)
        assert len(result["allocations"]) == 2
        total_weight = sum(a["weight"] for a in result["allocations"])
        assert abs(total_weight - 1.0) < 0.01

    def test_empty_positions(self):
        result = PositionSizer.risk_parity_size(100000, [])
        assert "error" in result

    def test_zero_capital(self):
        positions = [{"symbol": "A", "volatility": 0.20}]
        result = PositionSizer.risk_parity_size(0, positions)
        assert "error" in result

    def test_zero_volatility(self):
        positions = [
            {"symbol": "A", "volatility": 0.0},
            {"symbol": "B", "volatility": 0.0},
        ]
        result = PositionSizer.risk_parity_size(100000, positions)
        assert "error" in result
