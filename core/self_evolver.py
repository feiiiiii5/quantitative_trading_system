import logging
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from core.alpha_engine import AlphaGenerator, AlphaResult
from core.alpha_screener import AlphaScreener, AlphaScreeningConfig
from core.portfolio_optimizer import PortfolioOptimizer
from core.auto_auditor import AutoAuditor
from core.walk_forward import WalkForwardValidator, WalkForwardConfig

logger = logging.getLogger(__name__)


@dataclass
class EvolutionConfig:
    max_iterations: int = 10
    target_sharpe: float = 1.0
    min_ic: float = 0.02
    min_ic_ir: float = 0.3
    max_alphas_per_round: int = 50
    survival_rate: float = 0.3
    mutation_rate: float = 0.2
    elite_count: int = 5


@dataclass
class EvolutionRound:
    iteration: int
    n_alphas_generated: int
    n_alphas_passed: int
    best_ic: float
    best_ic_ir: float
    portfolio_sharpe: float
    audit_passed: bool
    improvements: List[str]


@dataclass
class EvolutionResult:
    total_iterations: int
    rounds: List[EvolutionRound]
    final_alpha_weights: Dict[str, float]
    final_sharpe: float
    final_ic: float
    best_alphas: List[str]
    is_converged: bool


class SelfEvolver:
    def __init__(
        self,
        alpha_generator: AlphaGenerator = None,
        alpha_screener: AlphaScreener = None,
        portfolio_optimizer: PortfolioOptimizer = None,
        auto_auditor: AutoAuditor = None,
        walk_forward_validator: WalkForwardValidator = None,
        config: EvolutionConfig = None,
    ):
        self._generator = alpha_generator or AlphaGenerator()
        self._screener = alpha_screener or AlphaScreener()
        self._optimizer = portfolio_optimizer or PortfolioOptimizer()
        self._auditor = auto_auditor or AutoAuditor()
        self._wf_validator = walk_forward_validator
        self._config = config or EvolutionConfig()
        self._best_alphas: Dict[str, AlphaResult] = {}
        self._best_weights: Dict[str, float] = {}
        self._history: List[EvolutionRound] = []

    def _generate_round_alphas(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        default_alphas = self._generator.compute_all_alphas(df)
        parametric_alphas = self._generator.generate_parametric_alphas(df)
        all_alphas = {**default_alphas, **parametric_alphas}
        return all_alphas

    def _screen_alphas(
        self,
        alpha_values: Dict[str, pd.Series],
        close: pd.Series,
    ) -> Dict[str, AlphaResult]:
        results = self._screener.screen_all(alpha_values, close)
        passed = self._screener.filter_passed(results)
        return passed

    def _optimize_portfolio(
        self,
        passed_alphas: Dict[str, AlphaResult],
    ) -> Dict[str, float]:
        if not passed_alphas:
            return {}
        return self._optimizer.optimize_from_alphas(
            passed_alphas, pd.DataFrame({k: v.values for k, v in [(n, r.values) for n, r in passed_alphas.items()]}),
            method="ic_weighted",
        )

    def _audit_strategy(
        self,
        train_metrics: Dict,
        test_metrics: Dict,
        returns: pd.Series,
        signals: pd.Series = None,
    ) -> Tuple[bool, List[str]]:
        report = self._auditor.audit(
            train_metrics=train_metrics,
            test_metrics=test_metrics,
            returns=returns,
            signals=signals,
        )
        return report.passed, report.recommendations

    def evolve(
        self,
        df: pd.DataFrame,
        backtest_fn: Callable = None,
    ) -> EvolutionResult:
        close = df["close"]
        rounds = []
        prev_best_sharpe = -np.inf
        converged = False

        for iteration in range(self._config.max_iterations):
            logger.info(f"Evolution iteration {iteration + 1}/{self._config.max_iterations}")

            alpha_values = self._generate_round_alphas(df)
            n_generated = len(alpha_values)

            passed_alphas = self._screen_alphas(alpha_values, close)
            n_passed = len(passed_alphas)

            if not passed_alphas:
                rounds.append(EvolutionRound(
                    iteration=iteration,
                    n_alphas_generated=n_generated,
                    n_alphas_passed=0,
                    best_ic=0.0,
                    best_ic_ir=0.0,
                    portfolio_sharpe=0.0,
                    audit_passed=False,
                    improvements=["No alphas passed screening"],
                ))
                continue

            weights = self._optimize_portfolio(passed_alphas)

            best_ic = max(abs(r.ic) for r in passed_alphas.values())
            best_ic_ir = max(abs(r.ic_ir) for r in passed_alphas.values())

            portfolio_sharpe = 0.0
            audit_passed = False
            improvements = []

            if backtest_fn is not None:
                try:
                    bt_result = backtest_fn(df, weights, passed_alphas)
                    if bt_result is not None:
                        portfolio_sharpe = bt_result.get("sharpe_ratio", 0.0)
                        audit_passed = bt_result.get("audit_passed", False)
                        if portfolio_sharpe > prev_best_sharpe:
                            improvements.append(f"Sharpe improved: {prev_best_sharpe:.4f} → {portfolio_sharpe:.4f}")
                            prev_best_sharpe = portfolio_sharpe
                except Exception as e:
                    logger.warning(f"Backtest failed in evolution round {iteration}: {e}")

            if best_ic > self._config.min_ic:
                improvements.append(f"Best IC: {best_ic:.4f}")
            if best_ic_ir > self._config.min_ic_ir:
                improvements.append(f"Best IC_IR: {best_ic_ir:.4f}")

            sorted_alphas = sorted(passed_alphas.items(), key=lambda x: abs(x[1].ic_ir), reverse=True)
            elite_count = min(self._config.elite_count, len(sorted_alphas))
            for name, result in sorted_alphas[:elite_count]:
                self._best_alphas[name] = result

            if weights:
                self._best_weights = weights

            round_result = EvolutionRound(
                iteration=iteration,
                n_alphas_generated=n_generated,
                n_alphas_passed=n_passed,
                best_ic=round(best_ic, 4),
                best_ic_ir=round(best_ic_ir, 4),
                portfolio_sharpe=round(portfolio_sharpe, 4),
                audit_passed=audit_passed,
                improvements=improvements,
            )
            rounds.append(round_result)

            if portfolio_sharpe >= self._config.target_sharpe and audit_passed:
                converged = True
                logger.info(f"Evolution converged at iteration {iteration + 1}")
                break

            if iteration > 0:
                prev_round = rounds[-2] if len(rounds) >= 2 else rounds[-1]
                if abs(portfolio_sharpe - prev_round.portfolio_sharpe) < 0.01:
                    logger.info(f"Evolution plateaued at iteration {iteration + 1}")
                    if iteration >= 3:
                        break

        final_ic = max(abs(r.ic) for r in self._best_alphas.values()) if self._best_alphas else 0.0
        final_sharpe = prev_best_sharpe

        return EvolutionResult(
            total_iterations=len(rounds),
            rounds=rounds,
            final_alpha_weights=self._best_weights,
            final_sharpe=round(final_sharpe, 4),
            final_ic=round(final_ic, 4),
            best_alphas=list(self._best_alphas.keys()),
            is_converged=converged,
        )

    def get_evolution_report(self, result: EvolutionResult) -> Dict:
        return {
            "total_iterations": result.total_iterations,
            "is_converged": result.is_converged,
            "final_sharpe": result.final_sharpe,
            "final_ic": result.final_ic,
            "n_best_alphas": len(result.best_alphas),
            "best_alphas": result.best_alphas[:20],
            "alpha_weights": {k: v for k, v in result.final_alpha_weights.items() if v > 0.001},
            "rounds_summary": [
                {
                    "iteration": r.iteration,
                    "generated": r.n_alphas_generated,
                    "passed": r.n_alphas_passed,
                    "best_ic": r.best_ic,
                    "best_ic_ir": r.best_ic_ir,
                    "sharpe": r.portfolio_sharpe,
                    "audit": r.audit_passed,
                }
                for r in result.rounds
            ],
        }
