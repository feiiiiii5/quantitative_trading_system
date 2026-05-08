"""市场识别模块测试"""

from core.market_detector import MarketDetector


class TestDetect:
    def test_a_share_shanghai(self):
        assert MarketDetector.detect("600000") == "A"

    def test_a_share_shenzhen(self):
        assert MarketDetector.detect("000001") == "A"

    def test_a_share_chinext(self):
        assert MarketDetector.detect("300001") == "A"

    def test_a_share_bse(self):
        assert MarketDetector.detect("830001") == "A"

    def test_hk_stock_with_suffix(self):
        assert MarketDetector.detect("00700.HK") == "HK"

    def test_hk_stock_5digit(self):
        assert MarketDetector.detect("00700") == "HK"

    def test_hk_index(self):
        assert MarketDetector.detect("HSI") == "HK"

    def test_hk_tech_index(self):
        assert MarketDetector.detect("HSTECH") == "HK"

    def test_us_stock(self):
        assert MarketDetector.detect("AAPL") == "US"

    def test_us_stock_with_suffix(self):
        assert MarketDetector.detect("BRK.B") == "US"

    def test_mixed_alpha_digit_goes_hk(self):
        assert MarketDetector.detect("AAPL1") == "HK"

    def test_short_digits_goes_hk(self):
        assert MarketDetector.detect("123") == "HK"

    def test_whitespace_trimmed(self):
        assert MarketDetector.detect("  600000  ") == "A"

    def test_case_insensitive(self):
        assert MarketDetector.detect("aapl") == "US"


class TestGetConfig:
    def test_a_share_config(self):
        config = MarketDetector.get_config("600000")
        assert config["market"] == "A"
        assert config["currency"] == "CNY"

    def test_hk_config(self):
        config = MarketDetector.get_config("00700.HK")
        assert config["market"] == "HK"
        assert config["currency"] == "HKD"

    def test_us_config(self):
        config = MarketDetector.get_config("AAPL")
        assert config["market"] == "US"
        assert config["currency"] == "USD"


class TestNormalizeSymbol:
    def test_a_share_normalized(self):
        assert MarketDetector.normalize_symbol("sh600000") == "600000"

    def test_hk_normalized(self):
        assert MarketDetector.normalize_symbol("00700.HK") == "00700"

    def test_hk_short_padded(self):
        assert MarketDetector.normalize_symbol("700") == "00700"

    def test_us_normalized_upper(self):
        assert MarketDetector.normalize_symbol("aapl") == "AAPL"

    def test_us_suffix_stripped(self):
        assert MarketDetector.normalize_symbol("BRK.B") == "BRK"
