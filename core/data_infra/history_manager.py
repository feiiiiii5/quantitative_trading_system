import logging
import os
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

HISTORY_DIR = Path(os.environ.get("HISTORY_DATA_DIR", str(Path(__file__).parent.parent.parent / "data" / "history")))


class AdjustType(Enum):
    NONE = "none"
    FORWARD = "forward"
    BACKWARD = "backward"


@dataclass
class CorporateAction:
    symbol: str
    date: str
    action_type: str
    dividend_per_share: float = 0.0
    split_ratio: float = 1.0
    bonus_ratio: float = 0.0
    rights_ratio: float = 0.0
    rights_price: float = 0.0
    description: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AdjustmentFactor:
    date: str
    factor: float = 1.0
    cumulative_factor: float = 1.0
    actions: List[CorporateAction] = field(default_factory=list)


class HistoryDataManager:
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir) if base_dir else HISTORY_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._corporate_actions: Dict[str, List[CorporateAction]] = {}
        self._adjustment_factors: Dict[str, List[AdjustmentFactor]] = {}
        self._ingest_timestamps: Dict[str, float] = {}
        self._load_actions()

    def _get_symbol_dir(self, symbol: str) -> Path:
        p = self.base_dir / symbol
        p.mkdir(parents=True, exist_ok=True)
        return p

    def _load_actions(self):
        actions_file = self.base_dir / "corporate_actions.json"
        if actions_file.exists():
            try:
                import json
                with open(actions_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for symbol, actions in data.items():
                    self._corporate_actions[symbol] = [
                        CorporateAction(**a) for a in actions
                    ]
            except Exception as e:
                logger.debug(f"Failed to load corporate actions: {e}")

    def _save_actions(self):
        actions_file = self.base_dir / "corporate_actions.json"
        try:
            import json
            data = {}
            for symbol, actions in self._corporate_actions.items():
                data[symbol] = [asdict(a) for a in actions]
            with open(actions_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save corporate actions: {e}")

    def add_corporate_action(self, action: CorporateAction):
        if action.symbol not in self._corporate_actions:
            self._corporate_actions[action.symbol] = []
        self._corporate_actions[action.symbol].append(action)
        self._corporate_actions[action.symbol].sort(key=lambda a: a.date)
        self._rebuild_factors(action.symbol)
        self._save_actions()

    def add_corporate_actions_batch(self, actions: List[CorporateAction]):
        for action in actions:
            if action.symbol not in self._corporate_actions:
                self._corporate_actions[action.symbol] = []
            self._corporate_actions[action.symbol].append(action)
        for symbol in set(a.symbol for a in actions):
            self._corporate_actions[symbol].sort(key=lambda a: a.date)
            self._rebuild_factors(symbol)
        self._save_actions()

    def _rebuild_factors(self, symbol: str):
        actions = self._corporate_actions.get(symbol, [])
        if not actions:
            self._adjustment_factors[symbol] = []
            return

        factors = []
        cum_factor = 1.0

        for action in actions:
            factor = 1.0
            if action.split_ratio != 1.0 and action.split_ratio > 0:
                factor *= action.split_ratio
            if action.dividend_per_share > 0:
                pass
            if action.bonus_ratio > 0:
                factor *= (1 + action.bonus_ratio)
            cum_factor *= factor

            factors.append(AdjustmentFactor(
                date=action.date,
                factor=factor,
                cumulative_factor=cum_factor,
                actions=[action],
            ))

        self._adjustment_factors[symbol] = factors

    def get_adjustment_factors(self, symbol: str) -> List[AdjustmentFactor]:
        return self._adjustment_factors.get(symbol, [])

    def apply_adjustment(self, df: pd.DataFrame, symbol: str, adjust_type: AdjustType) -> pd.DataFrame:
        if adjust_type == AdjustType.NONE or df.empty:
            return df

        factors = self._adjustment_factors.get(symbol, [])
        if not factors:
            return df

        df = df.copy()
        if "date" not in df.columns:
            return df

        dates = df["date"].values
        close = df["close"].values.astype(float)

        if adjust_type == AdjustType.FORWARD:
            latest_factor = factors[-1].cumulative_factor if factors else 1.0
            for i in range(len(dates)):
                date_str = str(pd.Timestamp(dates[i]).date()) if not isinstance(dates[i], str) else dates[i]
                applicable_factor = latest_factor
                for f in factors:
                    if date_str >= f.date:
                        applicable_factor = f.cumulative_factor
                    else:
                        break
                if applicable_factor != 0:
                    ratio = latest_factor / applicable_factor
                    for col in ["open", "high", "low", "close"]:
                        if col in df.columns:
                            df.iloc[i, df.columns.get_loc(col)] = close[i] * ratio if col == "close" else float(df.iloc[i][col]) * ratio

        elif adjust_type == AdjustType.BACKWARD:
            for i in range(len(dates)):
                date_str = str(pd.Timestamp(dates[i]).date()) if not isinstance(dates[i], str) else dates[i]
                applicable_factor = 1.0
                for f in factors:
                    if date_str >= f.date:
                        applicable_factor = f.cumulative_factor
                    else:
                        break
                if applicable_factor != 0:
                    for col in ["open", "high", "low", "close"]:
                        if col in df.columns:
                            df.iloc[i, df.columns.get_loc(col)] = float(df.iloc[i][col]) / applicable_factor

        return df

    def save_history(self, symbol: str, df: pd.DataFrame, adjust_type: AdjustType = AdjustType.FORWARD):
        if df.empty:
            return
        symbol_dir = self._get_symbol_dir(symbol)
        adjusted_df = self.apply_adjustment(df, symbol, adjust_type)

        filename = f"{adjust_type.value}.parquet"
        filepath = symbol_dir / filename

        if filepath.exists() and "date" in adjusted_df.columns:
            try:
                existing_df = pd.read_parquet(filepath, engine="pyarrow")
                if "date" in existing_df.columns:
                    combined = pd.concat([existing_df, adjusted_df], ignore_index=True)
                    combined = combined.drop_duplicates(subset=["date"], keep="last")
                    combined = combined.sort_values("date").reset_index(drop=True)
                    adjusted_df = combined
            except Exception as e:
                logger.debug(f"Failed to merge existing data for {symbol}: {e}")

        adjusted_df.to_parquet(filepath, engine="pyarrow")

        meta_file = symbol_dir / "meta.json"
        import json
        meta = {
            "symbol": symbol,
            "adjust_type": adjust_type.value,
            "rows": len(adjusted_df),
            "ingest_timestamp": time.time(),
            "ingest_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "date_range": {
                "start": str(adjusted_df["date"].min()),
                "end": str(adjusted_df["date"].max()),
            } if "date" in adjusted_df.columns else {},
        }
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        self._ingest_timestamps[symbol] = time.time()
        logger.info(f"Saved {len(adjusted_df)} rows for {symbol} ({adjust_type.value})")

    def load_history(self, symbol: str, adjust_type: AdjustType = AdjustType.FORWARD) -> pd.DataFrame:
        symbol_dir = self._get_symbol_dir(symbol)
        filename = f"{adjust_type.value}.parquet"
        filepath = symbol_dir / filename
        if filepath.exists():
            try:
                return pd.read_parquet(filepath, engine="pyarrow")
            except Exception as e:
                logger.error(f"Failed to load history for {symbol}: {e}")
        return pd.DataFrame()

    def get_meta(self, symbol: str) -> Optional[dict]:
        meta_file = self._get_symbol_dir(symbol) / "meta.json"
        if meta_file.exists():
            try:
                import json
                with open(meta_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    def check_future_leak(self, symbol: str, df: pd.DataFrame) -> List[dict]:
        if symbol not in self._ingest_timestamps:
            return []
        ingest_ts = self._ingest_timestamps[symbol]
        leaks = []
        if "date" in df.columns:
            ingest_date = time.strftime("%Y-%m-%d", time.localtime(ingest_ts))
            for i, row in df.iterrows():
                date_str = str(row["date"])
                if date_str > ingest_date:
                    leaks.append({
                        "index": i,
                        "date": date_str,
                        "ingest_date": ingest_date,
                        "warning": "数据时间晚于入库时间，可能存在未来函数污染",
                    })
        return leaks

    def list_symbols(self) -> List[dict]:
        result = []
        if not self.base_dir.exists():
            return result
        for d in self.base_dir.iterdir():
            if d.is_dir() and (d / "meta.json").exists():
                try:
                    import json
                    with open(d / "meta.json", "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    result.append(meta)
                except Exception:
                    result.append({"symbol": d.name})
        return result

    def delete_history(self, symbol: str):
        symbol_dir = self._get_symbol_dir(symbol)
        if symbol_dir.exists():
            import shutil
            shutil.rmtree(symbol_dir)

    def get_corporate_actions(self, symbol: str) -> List[dict]:
        actions = self._corporate_actions.get(symbol, [])
        return [asdict(a) for a in actions]
