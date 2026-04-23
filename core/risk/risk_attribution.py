import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class BrinsonResult:
    total_return: float = 0.0
    allocation_effect: float = 0.0
    selection_effect: float = 0.0
    interaction_effect: float = 0.0
    timing_effect: float = 0.0
    details: Dict[str, dict] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "total_return": round(self.total_return, 4),
            "allocation_effect": round(self.allocation_effect, 4),
            "selection_effect": round(self.selection_effect, 4),
            "interaction_effect": round(self.interaction_effect, 4),
            "timing_effect": round(self.timing_effect, 4),
            "details": self.details,
        }


@dataclass
class BarraExposure:
    factor_name: str
    exposure: float = 0.0
    contribution: float = 0.0

    def to_dict(self) -> dict:
        return {
            "factor_name": self.factor_name,
            "exposure": round(self.exposure, 4),
            "contribution": round(self.contribution, 4),
        }


@dataclass
class RiskReport:
    report_date: str = ""
    total_risk: float = 0.0
    systematic_risk: float = 0.0
    idiosyncratic_risk: float = 0.0
    brinson: Optional[BrinsonResult] = None
    barra_exposures: List[BarraExposure] = field(default_factory=list)
    risk_decomposition: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "report_date": self.report_date,
            "total_risk": round(self.total_risk, 4),
            "systematic_risk": round(self.systematic_risk, 4),
            "idiosyncratic_risk": round(self.idiosyncratic_risk, 4),
            "brinson": self.brinson.to_dict() if self.brinson else None,
            "barra_exposures": [e.to_dict() for e in self.barra_exposures],
            "risk_decomposition": {k: round(v, 4) for k, v in self.risk_decomposition.items()},
        }


class RiskAttribution:
    def __init__(self):
        self._barra_factors = [
            "market", "size", "value", "momentum", "volatility",
            "liquidity", "quality", "growth", "leverage",
        ]

    def brinson_attribution(
        self,
        portfolio_returns: Dict[str, float],
        benchmark_returns: Dict[str, float],
        portfolio_weights: Dict[str, float],
        benchmark_weights: Dict[str, float],
    ) -> BrinsonResult:
        sectors = set(list(portfolio_weights.keys()) + list(benchmark_weights.keys()))

        allocation_effect = 0.0
        selection_effect = 0.0
        interaction_effect = 0.0
        details = {}

        for sector in sectors:
            wp = portfolio_weights.get(sector, 0)
            wb = benchmark_weights.get(sector, 0)
            rp = portfolio_returns.get(sector, 0)
            rb = benchmark_returns.get(sector, 0)

            alloc = (wp - wb) * rb
            select = wb * (rp - rb)
            interact = (wp - wb) * (rp - rb)

            allocation_effect += alloc
            selection_effect += select
            interaction_effect += interact

            details[sector] = {
                "portfolio_weight": round(wp, 4),
                "benchmark_weight": round(wb, 4),
                "portfolio_return": round(rp, 4),
                "benchmark_return": round(rb, 4),
                "allocation": round(alloc, 4),
                "selection": round(select, 4),
                "interaction": round(interact, 4),
            }

        total_return = allocation_effect + selection_effect + interaction_effect

        return BrinsonResult(
            total_return=total_return,
            allocation_effect=allocation_effect,
            selection_effect=selection_effect,
            interaction_effect=interaction_effect,
            details=details,
        )

    def calculate_barra_exposures(
        self,
        returns: np.ndarray,
        factor_returns: Optional[Dict[str, np.ndarray]] = None,
    ) -> List[BarraExposure]:
        if factor_returns is None:
            factor_returns = self._generate_synthetic_factors(returns)

        exposures = []
        n = min(len(returns), min(len(v) for v in factor_returns.values()))

        if n < 20:
            return exposures

        r = returns[:n]
        for factor_name, factor_r in factor_returns.items():
            fr = factor_r[:n]
            if np.std(fr) > 0:
                cov = np.cov(r, fr)
                var = np.var(fr)
                if var > 0:
                    beta = cov[0, 1] / var
                    contribution = beta * np.mean(fr)
                    exposures.append(BarraExposure(
                        factor_name=factor_name,
                        exposure=beta,
                        contribution=contribution,
                    ))

        return exposures

    def _generate_synthetic_factors(self, returns: np.ndarray) -> Dict[str, np.ndarray]:
        n = len(returns)
        factors = {}

        factors["market"] = returns + np.random.normal(0, 0.001, n)
        factors["size"] = np.random.normal(0, 0.01, n)
        factors["value"] = np.random.normal(0, 0.008, n)
        factors["momentum"] = np.concatenate([
            np.random.normal(0, 0.005, n // 2),
            np.random.normal(0, 0.015, n - n // 2),
        ])
        factors["volatility"] = np.abs(returns) * np.random.normal(1, 0.3, n)
        factors["liquidity"] = np.random.normal(0, 0.005, n)
        factors["quality"] = np.random.normal(0, 0.006, n)
        factors["growth"] = np.random.normal(0, 0.007, n)
        factors["leverage"] = np.random.normal(0, 0.004, n)

        return factors

    def generate_risk_report(
        self,
        returns: np.ndarray,
        portfolio_returns: Optional[Dict[str, float]] = None,
        benchmark_returns: Optional[Dict[str, float]] = None,
        portfolio_weights: Optional[Dict[str, float]] = None,
        benchmark_weights: Optional[Dict[str, float]] = None,
    ) -> RiskReport:
        total_risk = np.std(returns) * np.sqrt(252) if len(returns) > 1 else 0

        factor_returns = self._generate_synthetic_factors(returns)
        barra_exposures = self.calculate_barra_exposures(returns, factor_returns)

        systematic_risk = 0.0
        idiosyncratic_risk = 0.0
        if barra_exposures:
            systematic_risk = sum(e.contribution ** 2 for e in barra_exposures) ** 0.5
            idiosyncratic_risk = max(0, total_risk ** 2 - systematic_risk ** 2) ** 0.5

        brinson = None
        if portfolio_returns and benchmark_returns and portfolio_weights and benchmark_weights:
            brinson = self.brinson_attribution(
                portfolio_returns, benchmark_returns,
                portfolio_weights, benchmark_weights,
            )

        risk_decomp = {
            "systematic_pct": systematic_risk / total_risk if total_risk > 0 else 0,
            "idiosyncratic_pct": idiosyncratic_risk / total_risk if total_risk > 0 else 0,
        }

        return RiskReport(
            report_date=time.strftime("%Y-%m-%d"),
            total_risk=total_risk,
            systematic_risk=systematic_risk,
            idiosyncratic_risk=idiosyncratic_risk,
            brinson=brinson,
            barra_exposures=barra_exposures,
            risk_decomposition=risk_decomp,
        )

    def generate_periodic_reports(
        self,
        equity_curve: List[float],
        period: str = "daily",
    ) -> Dict[str, RiskReport]:
        if len(equity_curve) < 30:
            return {}

        returns = np.diff(equity_curve) / np.maximum(equity_curve[:-1], 1)
        returns = returns[np.isfinite(returns)]

        if period == "daily":
            return {"daily": self.generate_risk_report(returns)}
        elif period == "weekly":
            weekly_returns = returns[::5]
            return {"weekly": self.generate_risk_report(weekly_returns)}
        elif period == "monthly":
            monthly_returns = returns[::20]
            return {"monthly": self.generate_risk_report(monthly_returns)}
        else:
            return {
                "daily": self.generate_risk_report(returns),
                "weekly": self.generate_risk_report(returns[::5]),
                "monthly": self.generate_risk_report(returns[::20]),
            }
