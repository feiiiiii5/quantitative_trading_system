import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

AUDIT_DIR = Path(os.environ.get("AUDIT_LOG_DIR", str(Path(__file__).parent.parent.parent / "data" / "audit")))


@dataclass
class AuditEntry:
    event_id: str
    event_type: str
    timestamp: str
    actor: str
    action: str
    details: dict = field(default_factory=dict)
    chain: str = ""

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id, "event_type": self.event_type,
            "timestamp": self.timestamp, "actor": self.actor,
            "action": self.action, "details": self.details, "chain": self.chain,
        }


class ComplianceAuditLog:
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir) if base_dir else AUDIT_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._entries: List[AuditEntry] = []
        self._max_entries = 10000
        self._counter = 0
        self._current_file = self._get_current_file()

    def _get_current_file(self) -> Path:
        date_str = time.strftime("%Y%m%d")
        return self.base_dir / f"audit_{date_str}.jsonl"

    def log_event(
        self,
        event_type: str,
        actor: str,
        action: str,
        details: Optional[dict] = None,
        chain: str = "",
    ):
        self._counter += 1
        entry = AuditEntry(
            event_id=f"evt_{self._counter:08d}",
            event_type=event_type,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S.%f"),
            actor=actor,
            action=action,
            details=details or {},
            chain=chain,
        )
        self._entries.append(entry)
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]
        self._append_to_file(entry)

    def log_signal(self, strategy: str, symbol: str, signal_type: str, strength: float):
        self.log_event("signal", strategy, "generate_signal", {
            "symbol": symbol, "signal_type": signal_type, "strength": strength,
        }, chain="signal")

    def log_risk_check(self, risk_model: str, approved: bool, details: dict):
        self.log_event("risk_check", risk_model, "check_risk", {
            "approved": approved, **details,
        }, chain="risk")

    def log_order(self, executor: str, symbol: str, side: str, quantity: int, price: float):
        self.log_event("order", executor, "place_order", {
            "symbol": symbol, "side": side, "quantity": quantity, "price": price,
        }, chain="execution")

    def log_fill(self, broker: str, symbol: str, fill_price: float, fill_qty: int):
        self.log_event("fill", broker, "order_filled", {
            "symbol": symbol, "fill_price": fill_price, "fill_qty": fill_qty,
        }, chain="execution")

    def log_settlement(self, symbol: str, pnl: float, pnl_pct: float):
        self.log_event("settlement", "system", "trade_settled", {
            "symbol": symbol, "pnl": pnl, "pnl_pct": pnl_pct,
        }, chain="settlement")

    def _append_to_file(self, entry: AuditEntry):
        self._current_file = self._get_current_file()
        try:
            with open(self._current_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Audit log write failed: {e}")

    def query(
        self,
        event_type: Optional[str] = None,
        actor: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100,
    ) -> List[dict]:
        results = []
        for entry in reversed(self._entries):
            if event_type and entry.event_type != event_type:
                continue
            if actor and entry.actor != actor:
                continue
            if start_time and entry.timestamp < start_time:
                continue
            if end_time and entry.timestamp > end_time:
                continue
            results.append(entry.to_dict())
            if len(results) >= limit:
                break
        return results

    def get_full_chain(self, event_id: str) -> List[dict]:
        entry = None
        for e in self._entries:
            if e.event_id == event_id:
                entry = e
                break
        if not entry:
            return []

        chain_entries = [e for e in self._entries if e.chain == entry.chain]
        start_idx = 0
        for i, e in enumerate(chain_entries):
            if e.event_id == event_id:
                start_idx = i
                break
        return [e.to_dict() for e in chain_entries[start_idx:]]

    def generate_regulatory_report(self, date: Optional[str] = None) -> dict:
        if date:
            filepath = self.base_dir / f"audit_{date.replace('-', '')}.jsonl"
        else:
            filepath = self._current_file

        if not filepath.exists():
            return {"error": "No audit data for specified date"}

        entries = []
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entries.append(json.loads(line.strip()))
                    except Exception:
                        pass
        except Exception:
            return {"error": "Failed to read audit file"}

        event_counts = {}
        for e in entries:
            et = e.get("event_type", "unknown")
            event_counts[et] = event_counts.get(et, 0) + 1

        return {
            "report_date": date or time.strftime("%Y-%m-%d"),
            "total_events": len(entries),
            "event_breakdown": event_counts,
            "chains": len(set(e.get("chain", "") for e in entries if e.get("chain"))),
        }
