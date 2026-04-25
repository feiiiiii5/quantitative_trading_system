import logging
from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class VaRResult:
    historical_var: float = 0.0
    parametric_var: float = 0.0
    monte_carlo_var: float = 0.0
    cvar: float = 0.0
    expected_shortfall: float = 0.0
    confidence_level: float = 0.95
    time_horizon: int = 1
    portfolio_value: float = 0.0

    def to_dict(self) -> dict:
        return {
            "historical_var": round(self.historical_var, 2),
            "parametric_var": round(self.parametric_var, 2),
            "monte_carlo_var": round(self.monte_carlo_var, 2),
            "cvar": round(self.cvar, 2),
            "expected_shortfall": round(self.expected_shortfall, 2),
            "confidence_level": self.confidence_level,
            "time_horizon": self.time_horizon,
            "portfolio_value": round(self.portfolio_value, 2),
        }


@dataclass
class GreeksResult:
    symbol: str
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0
    rho: float = 0.0

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "delta": round(self.delta, 4),
            "gamma": round(self.gamma, 6),
            "theta": round(self.theta, 4),
            "vega": round(self.vega, 4),
            "rho": round(self.rho, 4),
        }


class VaRMonitor:
    def __init__(
        self,
        confidence_level: float = 0.95,
        time_horizon: int = 1,
        n_simulations: int = 10000,
    ):
        self.confidence_level = confidence_level
        self.time_horizon = time_horizon
        self.n_simulations = n_simulations

    def calculate_var(
        self,
        returns: np.ndarray,
        portfolio_value: float = 100000.0,
    ) -> VaRResult:
        if returns is None or len(returns) < 30:
            return VaRResult(portfolio_value=portfolio_value)

        hist_var = self._historical_var(returns, portfolio_value)
        param_var = self._parametric_var(returns, portfolio_value)
        mc_var = self._monte_carlo_var(returns, portfolio_value)
        cvar = self._calculate_cvar(returns, portfolio_value)
        es = cvar

        return VaRResult(
            historical_var=hist_var,
            parametric_var=param_var,
            monte_carlo_var=mc_var,
            cvar=cvar,
            expected_shortfall=es,
            confidence_level=self.confidence_level,
            time_horizon=self.time_horizon,
            portfolio_value=portfolio_value,
        )

    def calculate_portfolio_var(
        self,
        positions: Dict[str, float],
        returns_data: Dict[str, np.ndarray],
        weights: Optional[Dict[str, float]] = None,
    ) -> VaRResult:
        if not positions or not returns_data:
            return VaRResult()

        total_value = sum(positions.values())
        if total_value <= 0:
            return VaRResult(portfolio_value=total_value)

        if weights is None:
            weights = {s: v / total_value for s, v in positions.items()}

        common_len = min(len(r) for r in returns_data.values())
        if common_len < 30:
            return VaRResult(portfolio_value=total_value)

        portfolio_returns = np.zeros(common_len)
        for symbol, weight in weights.items():
            if symbol in returns_data:
                r = returns_data[symbol][:common_len]
                portfolio_returns += weight * r

        return self.calculate_var(portfolio_returns, total_value)

    def _historical_var(self, returns: np.ndarray, portfolio_value: float) -> float:
        sorted_returns = np.sort(returns)
        idx = int(len(sorted_returns) * (1 - self.confidence_level))
        if idx < 0:
            idx = 0
        var_return = sorted_returns[idx]
        return abs(var_return * portfolio_value * np.sqrt(self.time_horizon))

    def _parametric_var(self, returns: np.ndarray, portfolio_value: float) -> float:
        from scipy import stats
        mean = np.mean(returns)
        std = np.std(returns)
        z_score = stats.norm.ppf(1 - self.confidence_level)
        var_return = mean + z_score * std
        return abs(var_return * portfolio_value * np.sqrt(self.time_horizon))

    def _monte_carlo_var(self, returns: np.ndarray, portfolio_value: float, seed: int = 42) -> float:
        np.random.seed(seed)
        mean = np.mean(returns)
        std = np.std(returns)
        simulated = np.random.normal(mean, std, self.n_simulations)
        sorted_sim = np.sort(simulated)
        idx = int(len(sorted_sim) * (1 - self.confidence_level))
        if idx < 0:
            idx = 0
        var_return = sorted_sim[idx]
        return abs(var_return * portfolio_value * np.sqrt(self.time_horizon))

    def _calculate_cvar(self, returns: np.ndarray, portfolio_value: float) -> float:
        sorted_returns = np.sort(returns)
        idx = int(len(sorted_returns) * (1 - self.confidence_level))
        if idx < 0:
            idx = 0
        tail_returns = sorted_returns[:idx + 1]
        if len(tail_returns) == 0:
            return 0.0
        cvar_return = np.mean(tail_returns)
        return abs(cvar_return * portfolio_value * np.sqrt(self.time_horizon))

    def calculate_option_greeks(
        self, symbol: str, S: float, K: float, T: float,
        r: float = 0.03, sigma: float = 0.3, option_type: str = "call",
    ) -> GreeksResult:
        try:
            from scipy.stats import norm
        except ImportError:
            return GreeksResult(symbol=symbol)

        if T <= 0 or sigma <= 0:
            return GreeksResult(symbol=symbol)

        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)

        if option_type == "call":
            delta = norm.cdf(d1)
            theta = (-(S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T))
                     - r * K * np.exp(-r * T) * norm.cdf(d2)) / 365
        else:
            delta = norm.cdf(d1) - 1
            theta = (-(S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T))
                     + r * K * np.exp(-r * T) * norm.cdf(-d2)) / 365

        gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
        vega = S * norm.pdf(d1) * np.sqrt(T) / 100
        rho = K * T * np.exp(-r * T) * norm.cdf(d2 if option_type == "call" else -d2) / 100

        return GreeksResult(
            symbol=symbol, delta=delta, gamma=gamma,
            theta=theta, vega=vega, rho=rho,
        )

    def get_risk_summary(
        self,
        returns: np.ndarray,
        portfolio_value: float = 100000.0,
    ) -> dict:
        var_result = self.calculate_var(returns, portfolio_value)
        return {
            "var": var_result.to_dict(),
            "max_loss_1d": round(var_result.historical_var, 2),
            "max_loss_10d": round(var_result.historical_var * np.sqrt(10), 2),
            "portfolio_volatility": round(np.std(returns) * np.sqrt(252) * 100, 2),
            "downside_deviation": round(self._downside_deviation(returns) * 100, 2),
        }

    def _downside_deviation(self, returns: np.ndarray, target: float = 0.0) -> float:
        downside = returns[returns < target]
        if len(downside) == 0:
            return 0.0
        return np.sqrt(np.mean(downside ** 2))
