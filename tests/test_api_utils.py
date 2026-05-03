import numpy as np
import pytest

from api.utils import sanitize, json_response, safe_error


class TestSanitize:
    def test_numpy_int(self):
        assert sanitize(np.int64(42)) == 42
        assert isinstance(sanitize(np.int64(42)), int)

    def test_numpy_float(self):
        assert sanitize(np.float64(3.14)) == pytest.approx(3.14)
        assert isinstance(sanitize(np.float64(3.14)), float)

    def test_numpy_bool(self):
        assert sanitize(np.bool_(True)) is True
        assert isinstance(sanitize(np.bool_(True)), bool)

    def test_numpy_array(self):
        arr = np.array([1, 2, 3])
        result = sanitize(arr)
        assert result == [1, 2, 3]
        assert isinstance(result, list)

    def test_dict_with_numpy(self):
        data = {"count": np.int64(10), "ratio": np.float64(0.5)}
        result = sanitize(data)
        assert result == {"count": 10, "ratio": 0.5}
        assert isinstance(result["count"], int)
        assert isinstance(result["ratio"], float)

    def test_nested_structure(self):
        data = {"items": [{"val": np.int64(1)}, {"val": np.int64(2)}]}
        result = sanitize(data)
        assert result == {"items": [{"val": 1}, {"val": 2}]}

    def test_plain_types_passthrough(self):
        assert sanitize("hello") == "hello"
        assert sanitize(42) == 42
        assert sanitize(3.14) == 3.14
        assert sanitize(True) is True
        assert sanitize(None) is None

    def test_tuple_converted_to_list(self):
        result = sanitize((np.int64(1), np.int64(2)))
        assert result == [1, 2]
        assert isinstance(result, list)


class TestJsonResponse:
    def test_success_response(self):
        result = json_response(True, data={"key": "value"})
        assert result["success"] is True
        assert result["data"] == {"key": "value"}
        assert result["error"] == ""

    def test_error_response(self):
        result = json_response(False, error="Something went wrong")
        assert result["success"] is False
        assert result["data"] is None
        assert result["error"] == "Something went wrong"

    def test_numpy_data_sanitized(self):
        result = json_response(True, data={"count": np.int64(42)})
        assert result["data"]["count"] == 42
        assert isinstance(result["data"]["count"], int)

    def test_default_values(self):
        result = json_response(True)
        assert result["success"] is True
        assert result["data"] is None
        assert result["error"] == ""


class TestRoutesImport:
    def test_routes_module_imports_successfully(self):
        import api.routes
        assert hasattr(api.routes, "router")

    def test_routes_threading_import_available(self):
        import api.routes
        assert hasattr(api.routes, "threading")

    def test_connection_manager_has_lock(self):
        from api.routes import ConnectionManager
        mgr = ConnectionManager()
        assert hasattr(mgr, "_lock")


class TestCCIIndicator:
    def test_cci_returns_correct_length(self):
        from core.indicators import TechnicalIndicators
        h = np.random.rand(100) * 10 + 50
        low = h - np.random.rand(100) * 2
        c = (h + low) / 2
        result = TechnicalIndicators._cci(h, low, c, period=14)
        assert len(result) == 100

    def test_cci_short_data_returns_zeros(self):
        from core.indicators import TechnicalIndicators
        h = np.array([10.0, 11.0, 12.0])
        low = np.array([9.0, 10.0, 11.0])
        c = np.array([9.5, 10.5, 11.5])
        result = TechnicalIndicators._cci(h, low, c, period=14)
        assert len(result) == 3
        assert np.all(result == 0)

    def test_cci_values_are_finite(self):
        from core.indicators import TechnicalIndicators
        np.random.seed(42)
        h = np.random.rand(200) * 10 + 50
        low = h - np.random.rand(200) * 2
        c = (h + low) / 2
        result = TechnicalIndicators._cci(h, low, c, period=14)
        valid = result[13:]
        assert np.all(np.isfinite(valid))

    def test_indicators_uses_shared_sanitize(self):
        from core.indicators import _sanitize_for_json
        assert callable(_sanitize_for_json)


class TestAuthMiddleware:
    def test_rate_limits_has_max_cap(self):
        from api.auth import APIAuthMiddleware
        from fastapi import FastAPI
        app = FastAPI()
        mw = APIAuthMiddleware(app, enabled=True)
        assert hasattr(mw, "_max_clients")
        assert mw._max_clients > 0

    def test_cleanup_stale_clients(self):
        from api.auth import APIAuthMiddleware
        from fastapi import FastAPI
        import time
        app = FastAPI()
        mw = APIAuthMiddleware(app, enabled=True)
        mw._rate_limits["old_client"] = [time.time() - 600]
        mw._rate_limits["new_client"] = [time.time()]
        mw._cleanup_stale_clients(time.time())
        assert "old_client" not in mw._rate_limits
        assert "new_client" in mw._rate_limits

    def test_backtest_routes_no_dunder_import(self):
        import inspect
        import api.backtest_routes
        source = inspect.getsource(api.backtest_routes)
        assert "__import__" not in source


class TestSafeError:
    def test_normal_message_passes_through(self):
        exc = ValueError("数据不足")
        assert safe_error(exc) == "数据不足"

    def test_long_message_truncated(self):
        exc = ValueError("x" * 500)
        result = safe_error(exc)
        assert len(result) <= 203
        assert result.endswith("...")

    def test_file_path_scrubbed(self):
        exc = ValueError("Error in /Users/fei/project/main.py")
        result = safe_error(exc)
        assert "/Users/fei" not in result
        assert "[internal]" in result

    def test_sql_scrubbed(self):
        exc = ValueError("SELECT * FROM users WHERE id=1")
        result = safe_error(exc)
        assert "SELECT" not in result


class TestBacktestValidation:
    def test_invalid_capital_rejected(self):
        from api.backtest_routes import BacktestRunRequest
        with pytest.raises(Exception):
            BacktestRunRequest(symbol="000001", initial_capital=100)

    def test_invalid_commission_rejected(self):
        from api.backtest_routes import BacktestRunRequest
        with pytest.raises(Exception):
            BacktestRunRequest(symbol="000001", commission=0.1)

    def test_invalid_leverage_rejected(self):
        from api.backtest_routes import BacktestAdvancedRequest
        with pytest.raises(Exception):
            BacktestAdvancedRequest(symbol="000001", leverage=100.0)

    def test_invalid_simulations_rejected(self):
        from api.backtest_routes import BacktestAdvancedRequest
        with pytest.raises(Exception):
            BacktestAdvancedRequest(symbol="000001", n_simulations=999999)

    def test_valid_request_accepted(self):
        from api.backtest_routes import BacktestRunRequest
        req = BacktestRunRequest(symbol="000001", initial_capital=100000, commission=0.0003)
        assert req.symbol == "000001"
