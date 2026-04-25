import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import List, Optional


logger = logging.getLogger(__name__)


@dataclass
class SectorFlowData:
    sector_name: str
    sector_code: str
    net_inflow: float = 0.0
    change_pct: float = 0.0
    leading_stock: str = ""
    heat_index: float = 0.0

    def to_dict(self) -> dict:
        return {
            "sector_name": self.sector_name, "sector_code": self.sector_code,
            "net_inflow": round(self.net_inflow, 2),
            "change_pct": round(self.change_pct, 4),
            "leading_stock": self.leading_stock,
            "heat_index": round(self.heat_index, 2),
        }


@dataclass
class ConceptData:
    concept_name: str
    concept_code: str
    change_pct: float = 0.0
    stock_count: int = 0
    heat_index: float = 0.0
    top_stocks: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "concept_name": self.concept_name, "concept_code": self.concept_code,
            "change_pct": round(self.change_pct, 4),
            "stock_count": self.stock_count,
            "heat_index": round(self.heat_index, 2),
            "top_stocks": self.top_stocks,
        }


@dataclass
class ChainLink:
    upstream: str
    midstream: str
    downstream: str
    upstream_change: float = 0.0
    midstream_change: float = 0.0
    downstream_change: float = 0.0

    def to_dict(self) -> dict:
        return {
            "upstream": self.upstream, "midstream": self.midstream, "downstream": self.downstream,
            "upstream_change": round(self.upstream_change, 4),
            "midstream_change": round(self.midstream_change, 4),
            "downstream_change": round(self.downstream_change, 4),
        }


class SectorResearch:
    def __init__(self):
        self._sector_cache: List[SectorFlowData] = []
        self._concept_cache: List[ConceptData] = []
        self._last_fetch = 0.0

    async def get_sector_flows(self) -> List[dict]:
        now = time.time()
        if self._sector_cache and (now - self._last_fetch) < 300:
            return [s.to_dict() for s in self._sector_cache]

        try:
            data = await self._fetch_sector_flows()
            if data:
                self._sector_cache = data
                self._last_fetch = now
        except Exception as e:
            logger.debug(f"Sector flow fetch failed: {e}")

        return [s.to_dict() for s in self._sector_cache]

    async def _fetch_sector_flows(self) -> Optional[List[SectorFlowData]]:
        try:
            import requests
            url = "https://push2.eastmoney.com/api/qt/clist/get"
            params = {
                "pn": 1, "pz": 50, "po": 1, "np": 1,
                "fltt": 2, "invt": 2, "fid": "f62",
                "fs": "m:90+t:2", "fields": "f12,f14,f2,f3,f62,f184,f66",
            }
            headers = {"User-Agent": "Mozilla/5.0"}
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(
                None, lambda: requests.get(url, params=params, headers=headers, timeout=8)
            )
            if resp.status_code == 200:
                d = resp.json().get("data", {}).get("diff", [])
                result = []
                for item in d:
                    result.append(SectorFlowData(
                        sector_name=item.get("f14", ""),
                        sector_code=str(item.get("f12", "")),
                        net_inflow=item.get("f62", 0),
                        change_pct=item.get("f3", 0) / 100 if item.get("f3") else 0,
                        leading_stock=item.get("f14", ""),
                        heat_index=abs(item.get("f62", 0)) / 1e8,
                    ))
                return result
        except Exception as e:
            logger.debug(f"Sector fetch error: {e}")
        return None

    async def get_concept_heat(self) -> List[dict]:
        try:
            import requests
            url = "https://push2.eastmoney.com/api/qt/clist/get"
            params = {
                "pn": 1, "pz": 30, "po": 1, "np": 1,
                "fltt": 2, "invt": 2, "fid": "f3",
                "fs": "m:90+t:3", "fields": "f12,f14,f2,f3,f104,f105",
            }
            headers = {"User-Agent": "Mozilla/5.0"}
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(
                None, lambda: requests.get(url, params=params, headers=headers, timeout=8)
            )
            if resp.status_code == 200:
                d = resp.json().get("data", {}).get("diff", [])
                result = []
                for item in d:
                    result.append(ConceptData(
                        concept_name=item.get("f14", ""),
                        concept_code=str(item.get("f12", "")),
                        change_pct=item.get("f3", 0) / 100 if item.get("f3") else 0,
                        stock_count=item.get("f104", 0) + item.get("f105", 0),
                        heat_index=abs(item.get("f3", 0)),
                    ))
                return result
        except Exception:
            pass
        return []

    def analyze_industry_chain(self, chain_name: str = "锂电池") -> dict:
        chains = {
            "锂电池": ChainLink("锂矿", "电池制造", "新能源车", 0.02, 0.03, 0.01),
            "半导体": ChainLink("硅片", "芯片制造", "消费电子", 0.01, 0.02, -0.01),
            "白酒": ChainLink("粮食", "酿造", "消费", 0.005, 0.02, 0.01),
            "光伏": ChainLink("硅料", "组件", "电站", 0.03, 0.01, 0.02),
        }
        chain = chains.get(chain_name)
        return chain.to_dict() if chain else {}

    def get_sector_rotation(self) -> dict:
        if not self._sector_cache:
            return {}
        sorted_sectors = sorted(self._sector_cache, key=lambda s: s.net_inflow, reverse=True)
        top_inflow = [s.to_dict() for s in sorted_sectors[:5]]
        top_outflow = [s.to_dict() for s in sorted_sectors[-5:]]
        return {"top_inflow": top_inflow, "top_outflow": top_outflow}

    async def analyze_rotation(self, period: int = 20) -> dict:
        await self.get_sector_flows()
        return self.get_sector_rotation()
