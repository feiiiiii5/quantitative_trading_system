"""
QuantCore 策略生命周期管理模块
提供策略从研究到上线的全流程状态机与沙盒环境
"""
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from core.database import SQLiteStore, get_db

logger = logging.getLogger(__name__)

__all__ = [
    'StrategyState',
    'StrategyConfig',
    'StrategyVersion',
    'PromotionResult',
    'PaperTradingSession',
    'DeviationAlert',
    'StrategyLifecycleManager',
    'PaperTradingSandbox',
    'LiveMonitor',
]


class StrategyState(Enum):
    RESEARCH = "research"
    BACKTEST_PASSED = "backtest_passed"
    PAPER_TRADING = "paper_trading"
    PILOT = "pilot"
    LIVE = "live"
    ARCHIVED = "archived"


_VALID_TRANSITIONS: dict[StrategyState, set[StrategyState]] = {
    StrategyState.RESEARCH: {StrategyState.BACKTEST_PASSED, StrategyState.ARCHIVED},
    StrategyState.BACKTEST_PASSED: {StrategyState.PAPER_TRADING, StrategyState.ARCHIVED},
    StrategyState.PAPER_TRADING: {StrategyState.PILOT, StrategyState.ARCHIVED},
    StrategyState.PILOT: {StrategyState.LIVE, StrategyState.ARCHIVED},
    StrategyState.LIVE: {StrategyState.ARCHIVED},
    StrategyState.ARCHIVED: set(),
}

_PROMOTION_CRITERIA: dict[tuple[StrategyState, StrategyState], dict[str, Any]] = {
    (StrategyState.RESEARCH, StrategyState.BACKTEST_PASSED): {
        "sharpe_min": 0.0,
    },
    (StrategyState.BACKTEST_PASSED, StrategyState.PAPER_TRADING): {
        "sharpe_min": 1.0,
    },
    (StrategyState.PAPER_TRADING, StrategyState.PILOT): {
        "sharpe_min": 1.5,
        "min_positive_months": 3,
    },
    (StrategyState.PILOT, StrategyState.LIVE): {
        "sharpe_min": 1.5,
        "max_drawdown": 0.15,
        "min_positive_months": 3,
    },
}


@dataclass
class PromotionCriteria:
    sharpe_threshold: float = 1.5
    min_positive_months: int = 3
    max_drawdown: float = 0.15


@dataclass
class StrategyConfig:
    name: str
    version: str
    parameters: dict[str, Any] = field(default_factory=dict)
    risk_limits: dict[str, Any] = field(default_factory=dict)
    universe: dict[str, Any] = field(default_factory=dict)
    schedule: dict[str, Any] = field(default_factory=dict)
    promotion_criteria: PromotionCriteria = field(default_factory=PromotionCriteria)


@dataclass
class StrategyVersion:
    version_id: str
    strategy_name: str
    version: str
    config: StrategyConfig
    git_commit: str
    created_at: datetime
    state: StrategyState
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass
class PromotionResult:
    from_state: StrategyState
    to_state: StrategyState
    approved: bool
    reason: str
    metrics_snapshot: dict[str, Any] = field(default_factory=dict)


@dataclass
class PaperTradingSession:
    session_id: str
    strategy_version_id: str
    start_date: datetime
    initial_capital: float
    current_equity: float
    trades: list[dict[str, Any]] = field(default_factory=list)
    pnl: float = 0.0


@dataclass
class DeviationAlert:
    metric_name: str
    live_value: float
    backtest_value: float
    deviation: float
    threshold: float
    severity: str


class StrategyLifecycleManager:
    def __init__(self, db: SQLiteStore | None = None) -> None:
        self._db = db or get_db()
        self._strategies: dict[str, StrategyVersion] = {}
        self._metrics_history: dict[str, list[dict[str, Any]]] = {}
        self._init_tables()

    def _init_tables(self) -> None:
        with self._db.transaction() as tx:
            tx.execute("""
                CREATE TABLE IF NOT EXISTS strategy_versions (
                    version_id TEXT PRIMARY KEY,
                    strategy_name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    config_json TEXT NOT NULL,
                    git_commit TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    state TEXT NOT NULL,
                    metrics_json TEXT NOT NULL DEFAULT '{}'
                )
            """)
            tx.execute("""
                CREATE TABLE IF NOT EXISTS strategy_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version_id TEXT NOT NULL,
                    metrics_json TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    FOREIGN KEY (version_id) REFERENCES strategy_versions(version_id)
                )
            """)
            tx.execute("""
                CREATE INDEX IF NOT EXISTS idx_sv_state ON strategy_versions(state)
            """)
            tx.execute("""
                CREATE INDEX IF NOT EXISTS idx_sm_version ON strategy_metrics(version_id)
            """)
        logger.info("Strategy lifecycle tables initialized")

    def register_strategy(self, config: StrategyConfig) -> str:
        version_id = f"{config.name}_{config.version}_{uuid.uuid4().hex[:8]}"
        now = datetime.now()
        sv = StrategyVersion(
            version_id=version_id,
            strategy_name=config.name,
            version=config.version,
            config=config,
            git_commit="",
            created_at=now,
            state=StrategyState.RESEARCH,
            metrics={},
        )
        self._strategies[version_id] = sv
        self._metrics_history[version_id] = []

        with self._db.transaction() as tx:
            tx.execute(
                """
                INSERT INTO strategy_versions
                    (version_id, strategy_name, version, config_json, git_commit, created_at, state, metrics_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    version_id,
                    config.name,
                    config.version,
                    json.dumps({
                        "parameters": config.parameters,
                        "risk_limits": config.risk_limits,
                        "universe": config.universe,
                        "schedule": config.schedule,
                        "promotion_criteria": {
                            "sharpe_threshold": config.promotion_criteria.sharpe_threshold,
                            "min_positive_months": config.promotion_criteria.min_positive_months,
                            "max_drawdown": config.promotion_criteria.max_drawdown,
                        },
                    }),
                    "",
                    now.isoformat(),
                    StrategyState.RESEARCH.value,
                    json.dumps({}),
                ),
            )
        logger.info("Registered strategy version_id=%s name=%s", version_id, config.name)
        return version_id

    def update_state(self, version_id: str, new_state: StrategyState) -> bool:
        sv = self._strategies.get(version_id)
        if sv is None:
            logger.warning("update_state: version_id=%s not found", version_id)
            return False
        if new_state not in _VALID_TRANSITIONS.get(sv.state, set()):
            logger.warning(
                "Invalid transition version_id=%s from %s to %s",
                version_id,
                sv.state.value,
                new_state.value,
            )
            return False
        old_state = sv.state
        sv.state = new_state

        with self._db.transaction() as tx:
            tx.execute(
                "UPDATE strategy_versions SET state = ? WHERE version_id = ?",
                (new_state.value, version_id),
            )
        logger.info(
            "State transition version_id=%s %s -> %s",
            version_id,
            old_state.value,
            new_state.value,
        )
        return True

    def check_promotion_eligibility(self, version_id: str) -> PromotionResult:
        sv = self._strategies.get(version_id)
        if sv is None:
            return PromotionResult(
                from_state=StrategyState.RESEARCH,
                to_state=StrategyState.RESEARCH,
                approved=False,
                reason=f"Version {version_id} not found",
            )

        current = sv.state
        if current == StrategyState.ARCHIVED:
            return PromotionResult(
                from_state=current,
                to_state=current,
                approved=False,
                reason="Archived strategies cannot be promoted",
                metrics_snapshot=sv.metrics.copy(),
            )

        if current == StrategyState.LIVE:
            return PromotionResult(
                from_state=current,
                to_state=current,
                approved=False,
                reason="Strategy is already LIVE, no further promotion",
                metrics_snapshot=sv.metrics.copy(),
            )

        next_state_map = {
            StrategyState.RESEARCH: StrategyState.BACKTEST_PASSED,
            StrategyState.BACKTEST_PASSED: StrategyState.PAPER_TRADING,
            StrategyState.PAPER_TRADING: StrategyState.PILOT,
            StrategyState.PILOT: StrategyState.LIVE,
        }
        next_state = next_state_map.get(current)
        if next_state is None:
            return PromotionResult(
                from_state=current,
                to_state=current,
                approved=False,
                reason="No valid next state",
                metrics_snapshot=sv.metrics.copy(),
            )

        criteria = _PROMOTION_CRITERIA.get((current, next_state), {})
        metrics = sv.metrics
        failures: list[str] = []

        sharpe_min = criteria.get("sharpe_min", 0.0)
        actual_sharpe = metrics.get("sharpe", 0.0)
        if actual_sharpe < sharpe_min:
            failures.append(
                f"Sharpe {actual_sharpe:.2f} below threshold {sharpe_min:.2f}"
            )

        if "min_positive_months" in criteria:
            required = criteria["min_positive_months"]
            actual = metrics.get("consecutive_positive_months", 0)
            if actual < required:
                failures.append(
                    f"Consecutive positive months {actual} below required {required}"
                )

        if "max_drawdown" in criteria:
            max_dd = criteria["max_drawdown"]
            actual_dd = metrics.get("max_drawdown", 1.0)
            if actual_dd > max_dd:
                failures.append(
                    f"Max drawdown {actual_dd:.2%} exceeds limit {max_dd:.2%}"
                )

        approved = len(failures) == 0
        reason = "All criteria met" if approved else "; ".join(failures)
        return PromotionResult(
            from_state=current,
            to_state=next_state,
            approved=approved,
            reason=reason,
            metrics_snapshot=metrics.copy(),
        )

    def promote(self, version_id: str) -> PromotionResult:
        result = self.check_promotion_eligibility(version_id)
        if not result.approved:
            logger.info(
                "Promotion denied version_id=%s: %s", version_id, result.reason
            )
            return result

        success = self.update_state(version_id, result.to_state)
        if not success:
            result.approved = False
            result.reason = "State transition failed"
            return result

        logger.info(
            "Promoted version_id=%s %s -> %s",
            version_id,
            result.from_state.value,
            result.to_state.value,
        )
        return result

    def get_strategy(self, version_id: str) -> StrategyVersion | None:
        return self._strategies.get(version_id)

    def list_strategies(
        self, state: StrategyState | None = None
    ) -> list[StrategyVersion]:
        if state is None:
            return list(self._strategies.values())
        return [sv for sv in self._strategies.values() if sv.state == state]

    def record_metrics(self, version_id: str, metrics: dict[str, Any]) -> None:
        sv = self._strategies.get(version_id)
        if sv is None:
            logger.warning("record_metrics: version_id=%s not found", version_id)
            return
        sv.metrics.update(metrics)
        history = self._metrics_history.setdefault(version_id, [])
        history.append({**metrics, "_recorded_at": datetime.now().isoformat()})

        import json

        with self._db.transaction() as tx:
            tx.execute(
                "UPDATE strategy_versions SET metrics_json = ? WHERE version_id = ?",
                (json.dumps(sv.metrics), version_id),
            )
            tx.execute(
                """
                INSERT INTO strategy_metrics (version_id, metrics_json, recorded_at)
                VALUES (?, ?, ?)
                """,
                (version_id, json.dumps(metrics), datetime.now().isoformat()),
            )
        logger.debug("Recorded metrics for version_id=%s", version_id)

    def compare_versions(
        self, version_id_a: str, version_id_b: str
    ) -> dict[str, Any]:
        sv_a = self._strategies.get(version_id_a)
        sv_b = self._strategies.get(version_id_b)
        if sv_a is None or sv_b is None:
            return {"error": "One or both versions not found"}

        metrics_a = sv_a.metrics
        metrics_b = sv_b.metrics
        comparison: dict[str, Any] = {
            "version_a": version_id_a,
            "version_b": version_id_b,
            "state_a": sv_a.state.value,
            "state_b": sv_b.state.value,
            "metric_deltas": {},
        }

        all_keys = set(metrics_a.keys()) | set(metrics_b.keys())
        for key in all_keys:
            val_a = metrics_a.get(key)
            val_b = metrics_b.get(key)
            if isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
                comparison["metric_deltas"][key] = {
                    "a": val_a,
                    "b": val_b,
                    "delta": val_b - val_a,
                    "pct_change": (
                        (val_b - val_a) / abs(val_a) if val_a != 0 else None
                    ),
                }

        return comparison


class PaperTradingSandbox:
    def __init__(self, lifecycle_manager: StrategyLifecycleManager) -> None:
        self._manager = lifecycle_manager
        self._sessions: dict[str, PaperTradingSession] = {}

    def start(self, strategy_version_id: str, initial_capital: float) -> str:
        sv = self._manager.get_strategy(strategy_version_id)
        if sv is None:
            raise ValueError(f"Strategy version {strategy_version_id} not found")
        if sv.state not in {
            StrategyState.BACKTEST_PASSED,
            StrategyState.PAPER_TRADING,
        }:
            raise ValueError(
                f"Strategy must be BACKTEST_PASSED or PAPER_TRADING, got {sv.state.value}"
            )

        session_id = f"pt_{uuid.uuid4().hex[:8]}"
        session = PaperTradingSession(
            session_id=session_id,
            strategy_version_id=strategy_version_id,
            start_date=datetime.now(),
            initial_capital=initial_capital,
            current_equity=initial_capital,
        )
        self._sessions[session_id] = session
        logger.info(
            "Started paper trading session=%s version_id=%s capital=%.2f",
            session_id,
            strategy_version_id,
            initial_capital,
        )
        return session_id

    def stop(self, session_id: str) -> dict[str, Any]:
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")

        session.pnl = session.current_equity - session.initial_capital
        result = {
            "session_id": session.session_id,
            "strategy_version_id": session.strategy_version_id,
            "start_date": session.start_date.isoformat(),
            "initial_capital": session.initial_capital,
            "final_equity": session.current_equity,
            "pnl": session.pnl,
            "return_pct": (
                session.pnl / session.initial_capital
                if session.initial_capital > 0
                else 0.0
            ),
            "total_trades": len(session.trades),
        }
        logger.info(
            "Stopped paper trading session=%s pnl=%.2f trades=%d",
            session_id,
            session.pnl,
            len(session.trades),
        )
        return result

    def get_session(self, session_id: str) -> PaperTradingSession | None:
        return self._sessions.get(session_id)


class LiveMonitor:
    SHARPE_DEVIATION_THRESHOLD = 0.5
    DRAWDOWN_DEVIATION_THRESHOLD = 0.05
    WIN_RATE_DEVIATION_THRESHOLD = 0.10

    def check_deviation(
        self,
        version_id: str,
        live_metrics: dict[str, Any],
        backtest_metrics: dict[str, Any],
    ) -> list[DeviationAlert]:
        alerts: list[DeviationAlert] = []

        live_sharpe = live_metrics.get("sharpe", 0.0)
        bt_sharpe = backtest_metrics.get("sharpe", 0.0)
        sharpe_dev = abs(live_sharpe - bt_sharpe)
        if sharpe_dev > self.SHARPE_DEVIATION_THRESHOLD:
            alerts.append(
                DeviationAlert(
                    metric_name="sharpe",
                    live_value=live_sharpe,
                    backtest_value=bt_sharpe,
                    deviation=sharpe_dev,
                    threshold=self.SHARPE_DEVIATION_THRESHOLD,
                    severity="critical" if sharpe_dev > 1.0 else "warning",
                )
            )

        live_dd = live_metrics.get("max_drawdown", 0.0)
        bt_dd = backtest_metrics.get("max_drawdown", 0.0)
        dd_dev = abs(live_dd - bt_dd)
        if dd_dev > self.DRAWDOWN_DEVIATION_THRESHOLD:
            alerts.append(
                DeviationAlert(
                    metric_name="max_drawdown",
                    live_value=live_dd,
                    backtest_value=bt_dd,
                    deviation=dd_dev,
                    threshold=self.DRAWDOWN_DEVIATION_THRESHOLD,
                    severity="critical" if dd_dev > 0.10 else "warning",
                )
            )

        live_wr = live_metrics.get("win_rate", 0.0)
        bt_wr = backtest_metrics.get("win_rate", 0.0)
        wr_dev = abs(live_wr - bt_wr)
        if wr_dev > self.WIN_RATE_DEVIATION_THRESHOLD:
            alerts.append(
                DeviationAlert(
                    metric_name="win_rate",
                    live_value=live_wr,
                    backtest_value=bt_wr,
                    deviation=wr_dev,
                    threshold=self.WIN_RATE_DEVIATION_THRESHOLD,
                    severity="critical" if wr_dev > 0.20 else "warning",
                )
            )

        if alerts:
            logger.warning(
                "Deviation alerts for version_id=%s: %d alerts",
                version_id,
                len(alerts),
            )
        return alerts
