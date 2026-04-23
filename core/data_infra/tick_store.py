import gzip
import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

DATA_DIR = Path(os.environ.get("TICK_DATA_DIR", str(Path(__file__).parent.parent.parent / "data" / "tick_store")))


class DataType(Enum):
    TICK = "tick"
    BAR = "bar"
    ORDERBOOK = "orderbook"


@dataclass
class TickData:
    symbol: str
    timestamp: int
    price: float
    volume: float
    side: str = ""
    bid_price: float = 0.0
    bid_volume: float = 0.0
    ask_price: float = 0.0
    ask_volume: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BarData:
    symbol: str
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    turnover: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class OrderBookLevel:
    price: float
    volume: float
    order_count: int = 0


@dataclass
class OrderBookData:
    symbol: str
    timestamp: int
    bids: List[OrderBookLevel] = field(default_factory=list)
    asks: List[OrderBookLevel] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = {"symbol": self.symbol, "timestamp": self.timestamp}
        d["bids"] = [{"price": lv.price, "volume": lv.volume, "order_count": lv.order_count} for lv in self.bids]
        d["asks"] = [{"price": lv.price, "volume": lv.volume, "order_count": lv.order_count} for lv in self.asks]
        return d


class TickStore:
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir) if base_dir else DATA_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._write_buffer: Dict[str, list] = {}
        self._buffer_size = int(os.environ.get("TICK_BUFFER_SIZE", "1000"))
        self._flush_count = 0

    def _get_store_path(self, symbol: str, data_type: DataType, date_str: str) -> Path:
        p = self.base_dir / symbol / data_type.value / date_str
        p.mkdir(parents=True, exist_ok=True)
        return p

    def write_tick(self, data: Union[TickData, BarData, OrderBookData], data_type: DataType):
        key = f"{data.symbol}:{data_type.value}"
        if key not in self._write_buffer:
            self._write_buffer[key] = []
        self._write_buffer[key].append(data.to_dict())
        if len(self._write_buffer[key]) >= self._buffer_size:
            self._flush_buffer(key)

    def write_ticks_batch(self, symbol: str, data_type: DataType, records: List[dict]):
        key = f"{symbol}:{data_type.value}"
        if key not in self._write_buffer:
            self._write_buffer[key] = []
        self._write_buffer[key].extend(records)
        if len(self._write_buffer[key]) >= self._buffer_size:
            self._flush_buffer(key)

    def _flush_buffer(self, key: str):
        buf = self._write_buffer.get(key)
        if not buf:
            return
        symbol, dtype_str = key.split(":")
        data_type = DataType(dtype_str)
        ts = buf[0].get("timestamp", int(time.time() * 1e9))
        date_str = pd.Timestamp(ts).strftime("%Y%m%d")
        store_path = self._get_store_path(symbol, data_type, date_str)
        chunk_id = int(time.time() * 1000)
        file_path = store_path / f"chunk_{chunk_id}.parquet.gz"
        try:
            df = pd.DataFrame(buf)
            df.to_parquet(file_path, engine="pyarrow", compression="gzip")
            self._flush_count += 1
            logger.debug(f"Flushed {len(buf)} records to {file_path}")
        except Exception as e:
            logger.error(f"Flush failed: {e}")
            json_path = store_path / f"chunk_{chunk_id}.json.gz"
            try:
                with gzip.open(json_path, "wt", encoding="utf-8") as f:
                    json.dump(buf, f)
            except Exception as e2:
                logger.error(f"JSON fallback also failed: {e2}")
        self._write_buffer[key] = []

    def flush_all(self):
        for key in list(self._write_buffer.keys()):
            self._flush_buffer(key)

    def read_ticks(
        self, symbol: str, data_type: DataType,
        start: Optional[str] = None, end: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        store_base = self.base_dir / symbol / data_type.value
        if not store_base.exists():
            return pd.DataFrame()

        all_dfs = []
        date_dirs = sorted([d for d in store_base.iterdir() if d.is_dir()])

        for date_dir in date_dirs:
            if start and date_dir.name < start.replace("-", ""):
                continue
            if end and date_dir.name > end.replace("-", ""):
                continue
            for f in sorted(date_dir.glob("*.parquet.gz")):
                try:
                    df = pd.read_parquet(f, engine="pyarrow")
                    all_dfs.append(df)
                except Exception:
                    pass
            for f in sorted(date_dir.glob("*.json.gz")):
                try:
                    with gzip.open(f, "rt", encoding="utf-8") as fh:
                        records = json.load(fh)
                    all_dfs.append(pd.DataFrame(records))
                except Exception:
                    pass

        if not all_dfs:
            return pd.DataFrame()

        result = pd.concat(all_dfs, ignore_index=True)
        if "timestamp" in result.columns:
            result = result.sort_values("timestamp").reset_index(drop=True)
        if limit and limit > 0:
            result = result.tail(limit).reset_index(drop=True)
        return result

    def replay_ticks(
        self, symbol: str, data_type: DataType,
        start: Optional[str] = None, end: Optional[str] = None,
        speed: float = 1.0,
    ):
        df = self.read_ticks(symbol, data_type, start, end)
        if df.empty:
            return
        if "timestamp" not in df.columns or len(df) < 2:
            yield from df.to_dict("records")
            return

        ts_col = df["timestamp"].values
        base_ts = ts_col[0]
        for i, row in df.iterrows():
            if i > 0 and speed > 0:
                delay_ns = (ts_col[i] - ts_col[i - 1]) / speed
                delay_s = delay_ns / 1e9
                if 0 < delay_s < 60:
                    time.sleep(delay_s)
            yield row.to_dict()

    def get_symbols(self) -> List[str]:
        if not self.base_dir.exists():
            return []
        return [d.name for d in self.base_dir.iterdir() if d.is_dir()]

    def get_data_info(self, symbol: str, data_type: DataType) -> dict:
        store_base = self.base_dir / symbol / data_type.value
        if not store_base.exists():
            return {"symbol": symbol, "type": data_type.value, "exists": False}

        total_records = 0
        total_size = 0
        date_range = []

        for date_dir in sorted(store_base.iterdir()):
            if not date_dir.is_dir():
                continue
            date_range.append(date_dir.name)
            for f in date_dir.iterdir():
                if f.is_file():
                    total_size += f.stat().st_size
                    try:
                        df = pd.read_parquet(f, engine="pyarrow")
                        total_records += len(df)
                    except Exception:
                        pass

        return {
            "symbol": symbol,
            "type": data_type.value,
            "exists": True,
            "total_records": total_records,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "date_range": date_range,
            "date_count": len(date_range),
        }

    def delete_data(self, symbol: str, data_type: DataType, date_str: Optional[str] = None):
        if date_str:
            target = self.base_dir / symbol / data_type.value / date_str
            if target.exists():
                import shutil
                shutil.rmtree(target)
        else:
            target = self.base_dir / symbol / data_type.value
            if target.exists():
                import shutil
                shutil.rmtree(target)

    def import_from_dataframe(
        self, symbol: str, data_type: DataType, df: pd.DataFrame,
        timestamp_col: str = "timestamp",
    ):
        if df.empty:
            return
        if timestamp_col not in df.columns:
            if "date" in df.columns:
                df = df.copy()
                df["timestamp"] = pd.to_datetime(df["date"]).astype(np.int64)
                timestamp_col = "timestamp"

        records = df.to_dict("records")
        self.write_ticks_batch(symbol, data_type, records)
        self.flush_all()
