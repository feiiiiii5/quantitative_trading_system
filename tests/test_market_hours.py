from datetime import date, datetime
from unittest.mock import patch

import pytz
import pytest

from core.market_hours import A_HOLIDAYS, HK_HOLIDAYS, US_HOLIDAYS, MarketHours


class TestGetMarketStatus:
    def test_get_market_status_unknown_market(self) -> None:
        result = MarketHours.get_market_status("XX")
        assert result["session"] == "unknown"
        assert result["is_open"] is False

    def test_get_market_status_a_share(self) -> None:
        result = MarketHours.get_market_status("A")
        assert "is_open" in result
        assert "session" in result
        assert "timezone" in result

    def test_get_market_status_hk(self) -> None:
        result = MarketHours.get_market_status("HK")
        assert "is_open" in result
        assert "session" in result
        assert "timezone" in result

    def test_get_market_status_us(self) -> None:
        result = MarketHours.get_market_status("US")
        assert "is_open" in result
        assert "session" in result
        assert "timezone" in result


class TestHolidays:
    def test_a_holidays_contains_known_holiday(self) -> None:
        assert date(2024, 1, 1) in A_HOLIDAYS

    def test_hk_holidays_contains_known_holiday(self) -> None:
        assert date(2024, 1, 1) in HK_HOLIDAYS

    def test_us_holidays_contains_known_holiday(self) -> None:
        assert date(2024, 1, 1) in US_HOLIDAYS

    def test_a_holidays_2025_exists(self) -> None:
        assert date(2025, 1, 1) in A_HOLIDAYS


class TestGetRefreshInterval:
    @patch.object(MarketHours, "get_market_status")
    def test_get_refresh_interval_open_market(self, mock_status: pytest.MonkeyPatch) -> None:
        mock_status.return_value = {"is_open": True, "session": "morning", "timezone": "Asia/Shanghai"}
        assert MarketHours.get_refresh_interval("A") == 1

    @patch.object(MarketHours, "get_market_status")
    def test_get_refresh_interval_closed_market(self, mock_status: pytest.MonkeyPatch) -> None:
        mock_status.return_value = {"is_open": False, "session": "closed", "timezone": "Asia/Shanghai"}
        assert MarketHours.get_refresh_interval("A") == 30


class TestShouldFetchRealtime:
    @patch.object(MarketHours, "get_market_status")
    def test_should_fetch_realtime_open(self, mock_status: pytest.MonkeyPatch) -> None:
        mock_status.return_value = {"is_open": True, "session": "morning", "timezone": "Asia/Shanghai"}
        assert MarketHours.should_fetch_realtime("A") is True

    @patch.object(MarketHours, "get_market_status")
    def test_should_fetch_realtime_closed(self, mock_status: pytest.MonkeyPatch) -> None:
        mock_status.return_value = {"is_open": False, "session": "closed", "timezone": "Asia/Shanghai"}
        assert MarketHours.should_fetch_realtime("A") is False


class TestTimezoneFields:
    def test_a_status_has_timezone_shanghai(self) -> None:
        result = MarketHours._a_status()
        assert result["timezone"] == "Asia/Shanghai"

    def test_hk_status_has_timezone_hong_kong(self) -> None:
        result = MarketHours._hk_status()
        assert result["timezone"] == "Asia/Hong_Kong"

    def test_us_status_has_timezone_eastern(self) -> None:
        result = MarketHours._us_status()
        assert result["timezone"] == "US/Eastern"


class TestNextOpen:
    def test_a_next_open_returns_string(self) -> None:
        saturday = datetime(2024, 3, 2, 10, 0, 0, tzinfo=pytz.timezone("Asia/Shanghai"))
        result = MarketHours._a_next_open(saturday)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_hk_next_open_returns_string(self) -> None:
        saturday = datetime(2024, 3, 2, 10, 0, 0, tzinfo=pytz.timezone("Asia/Hong_Kong"))
        result = MarketHours._hk_next_open(saturday)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_us_next_open_returns_string(self) -> None:
        saturday = datetime(2024, 3, 2, 10, 0, 0, tzinfo=pytz.timezone("US/Eastern"))
        result = MarketHours._us_next_open(saturday)
        assert isinstance(result, str)
        assert len(result) > 0
