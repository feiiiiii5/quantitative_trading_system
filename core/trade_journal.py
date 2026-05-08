import json
import logging
import sqlite3
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class JournalEntry:
    id: int = 0
    symbol: str = ""
    name: str = ""
    trade_type: str = ""
    price: float = 0.0
    quantity: int = 0
    notes: str = ""
    tags: list[str] = field(default_factory=list)
    emotion: str = ""
    rating: int = 0
    timestamp: float = 0.0


class TradeJournal:
    """交易日志系统

    允许用户为交易添加注释、标签和评分，
    存储在SQLite中以便后续回顾分析。
    """

    def __init__(self, db_path: str = "data/trade_journal.db"):
        self._db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_db(self):
        conn = self._get_conn()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS journal_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    name TEXT DEFAULT '',
                    trade_type TEXT NOT NULL,
                    price REAL DEFAULT 0,
                    quantity INTEGER DEFAULT 0,
                    notes TEXT DEFAULT '',
                    tags TEXT DEFAULT '[]',
                    emotion TEXT DEFAULT '',
                    rating INTEGER DEFAULT 0 CHECK(rating >= 0 AND rating <= 5),
                    timestamp REAL DEFAULT 0,
                    created_at REAL DEFAULT (strftime('%s','now'))
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_journal_symbol ON journal_entries(symbol)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_journal_timestamp ON journal_entries(timestamp)")
            conn.commit()
        finally:
            conn.close()

    def add_entry(self, entry: JournalEntry) -> int:
        conn = self._get_conn()
        try:
            if entry.timestamp == 0:
                entry.timestamp = time.time()
            cursor = conn.execute(
                """INSERT INTO journal_entries
                   (symbol, name, trade_type, price, quantity, notes, tags, emotion, rating, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    entry.symbol,
                    entry.name,
                    entry.trade_type,
                    entry.price,
                    entry.quantity,
                    entry.notes,
                    json.dumps(entry.tags, ensure_ascii=False),
                    entry.emotion,
                    max(0, min(5, entry.rating)),
                    entry.timestamp,
                ),
            )
            conn.commit()
            return cursor.lastrowid if cursor.lastrowid is not None else -1
        finally:
            conn.close()

    def get_entries(
        self,
        symbol: str | None = None,
        tag: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[JournalEntry]:
        conn = self._get_conn()
        try:
            query = "SELECT * FROM journal_entries WHERE 1=1"
            params: list = []
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            if tag:
                query += " AND tags LIKE ?"
                params.append(f'%"{tag}"%')
            query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            rows = conn.execute(query, params).fetchall()
            entries = []
            for row in rows:
                entries.append(JournalEntry(
                    id=row["id"],
                    symbol=row["symbol"],
                    name=row["name"],
                    trade_type=row["trade_type"],
                    price=row["price"],
                    quantity=row["quantity"],
                    notes=row["notes"],
                    tags=json.loads(row["tags"]) if row["tags"] else [],
                    emotion=row["emotion"],
                    rating=row["rating"],
                    timestamp=row["timestamp"],
                ))
            return entries
        finally:
            conn.close()

    def update_entry(self, entry_id: int, updates: dict) -> bool:
        allowed = {"notes", "tags", "emotion", "rating", "name"}
        fields = []
        params: list = []
        for k, v in updates.items():
            if k not in allowed:
                continue
            if k == "tags":
                v = json.dumps(v, ensure_ascii=False) if isinstance(v, list) else v
            if k == "rating":
                v = max(0, min(5, int(v)))
            fields.append(f"{k} = ?")
            params.append(v)
        if not fields:
            return False
        params.append(entry_id)
        conn = self._get_conn()
        try:
            conn.execute(f"UPDATE journal_entries SET {', '.join(fields)} WHERE id = ?", params)
            conn.commit()
            return conn.total_changes > 0
        finally:
            conn.close()

    def delete_entry(self, entry_id: int) -> bool:
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM journal_entries WHERE id = ?", (entry_id,))
            conn.commit()
            return conn.total_changes > 0
        finally:
            conn.close()

    def get_stats(self) -> dict:
        conn = self._get_conn()
        try:
            total = conn.execute("SELECT COUNT(*) FROM journal_entries").fetchone()[0]
            by_type = dict(conn.execute(
                "SELECT trade_type, COUNT(*) FROM journal_entries GROUP BY trade_type"
            ).fetchall())
            by_emotion = dict(conn.execute(
                "SELECT emotion, COUNT(*) FROM journal_entries WHERE emotion != '' GROUP BY emotion"
            ).fetchall())
            avg_rating = conn.execute(
                "SELECT AVG(rating) FROM journal_entries WHERE rating > 0"
            ).fetchone()[0]
            return {
                "total_entries": total,
                "by_type": by_type,
                "by_emotion": by_emotion,
                "avg_rating": round(avg_rating, 2) if avg_rating else 0,
            }
        finally:
            conn.close()
