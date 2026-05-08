import numpy as np

from core.volatility import detect_regime_hmm, fit_garch


class TestFitGarch:
    def test_basic(self):
        np.random.seed(42)
        returns = np.random.randn(100) * 0.02
        result = fit_garch(returns)
        assert "current_volatility" in result
        assert "long_run_volatility" in result
        assert "persistence" in result
        assert result["current_volatility"] > 0
        assert result["long_run_volatility"] > 0
        assert 0 < result["persistence"] < 1.0

    def test_insufficient_data(self):
        result = fit_garch(np.random.randn(10))
        assert "error" in result

    def test_forecast_series(self):
        np.random.seed(42)
        returns = np.random.randn(100) * 0.02
        result = fit_garch(returns)
        assert "forecast_series" in result
        assert len(result["forecast_series"]) == 22
        for f in result["forecast_series"]:
            assert f["volatility_annualized"] > 0

    def test_regime_classification(self):
        np.random.seed(42)
        returns = np.random.randn(200) * 0.01
        result = fit_garch(returns)
        assert result["regime"] in ("HIGH_VOL", "LOW_VOL", "NORMAL")

    def test_with_nan_values(self):
        np.random.seed(42)
        returns = np.random.randn(100) * 0.02
        returns[10] = np.nan
        returns[50] = np.nan
        result = fit_garch(returns)
        assert "current_volatility" in result

    def test_high_volatility_regime(self):
        np.random.seed(42)
        returns = np.concatenate([
            np.random.randn(80) * 0.01,
            np.random.randn(20) * 0.10,
        ])
        result = fit_garch(returns)
        assert result["current_volatility"] > 0

    def test_constant_returns(self):
        returns = np.full(100, 0.001)
        result = fit_garch(returns)
        assert "current_volatility" in result

    def test_volatility_history(self):
        np.random.seed(42)
        returns = np.random.randn(100) * 0.02
        result = fit_garch(returns)
        assert len(result["volatility_history"]) > 0


class TestDetectRegimeHMM:
    def test_basic(self):
        np.random.seed(42)
        returns = np.random.randn(120) * 0.02
        result = detect_regime_hmm(returns)
        assert "current_state" in result
        assert "current_label" in result
        assert "states" in result
        assert len(result["states"]) == 3

    def test_insufficient_data(self):
        result = detect_regime_hmm(np.random.randn(30))
        assert "error" in result

    def test_state_probabilities(self):
        np.random.seed(42)
        returns = np.random.randn(120) * 0.02
        result = detect_regime_hmm(returns)
        probs = result["state_probabilities"]
        assert isinstance(probs, dict)
        assert len(probs) == 3

    def test_transition_matrix(self):
        np.random.seed(42)
        returns = np.random.randn(120) * 0.02
        result = detect_regime_hmm(returns)
        tm = result["transition_matrix"]
        assert len(tm) == 3
        for row in tm:
            assert len(row) == 3

    def test_regime_history(self):
        np.random.seed(42)
        returns = np.random.randn(120) * 0.02
        result = detect_regime_hmm(returns)
        assert len(result["regime_history"]) > 0

    def test_two_states(self):
        np.random.seed(42)
        returns = np.random.randn(120) * 0.02
        result = detect_regime_hmm(returns, n_states=2)
        assert len(result["states"]) == 2

    def test_with_nan(self):
        np.random.seed(42)
        returns = np.random.randn(120) * 0.02
        returns[10] = np.nan
        result = detect_regime_hmm(returns)
        assert "current_state" in result
