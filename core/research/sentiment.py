import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


logger = logging.getLogger(__name__)


@dataclass
class SentimentData:
    symbol: str
    margin_balance: float = 0.0
    margin_balance_change: float = 0.0
    short_selling_volume: float = 0.0
    long_buy_amount: float = 0.0
    long_sell_amount: float = 0.0
    net_long_flow: float = 0.0
    dragon_tiger_data: List[dict] = field(default_factory=list)
    block_trade_discount: float = 0.0
    overall_sentiment: str = "neutral"
    sentiment_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "margin_balance": round(self.margin_balance, 2),
            "margin_balance_change": round(self.margin_balance_change, 4),
            "short_selling_volume": round(self.short_selling_volume, 2),
            "long_buy_amount": round(self.long_buy_amount, 2),
            "long_sell_amount": round(self.long_sell_amount, 2),
            "net_long_flow": round(self.net_long_flow, 2),
            "dragon_tiger_count": len(self.dragon_tiger_data),
            "block_trade_discount": round(self.block_trade_discount, 4),
            "overall_sentiment": self.overall_sentiment,
            "sentiment_score": round(self.sentiment_score, 4),
        }


class MarketSentimentAnalyzer:
    def __init__(self):
        self._cache: Dict[str, SentimentData] = {}
        self._last_fetch: float = 0.0

    async def analyze(self, symbol: str) -> SentimentData:
        now = time.time()
        if symbol in self._cache and (now - self._last_fetch) < 300:
            return self._cache[symbol]

        data = SentimentData(symbol=symbol)

        try:
            margin = await self._fetch_margin_data(symbol)
            if margin:
                data.margin_balance = margin.get("balance", 0)
                data.margin_balance_change = margin.get("change", 0)
        except Exception as e:
            logger.debug(f"Margin data fetch failed for {symbol}: {e}")

        try:
            long_short = await self._fetch_long_short_data(symbol)
            if long_short:
                data.long_buy_amount = long_short.get("buy", 0)
                data.long_sell_amount = long_short.get("sell", 0)
                data.net_long_flow = data.long_buy_amount - data.long_sell_amount
        except Exception as e:
            logger.debug(f"Long/short data fetch failed for {symbol}: {e}")

        try:
            dragon_tiger = await self._fetch_dragon_tiger(symbol)
            if dragon_tiger:
                data.dragon_tiger_data = dragon_tiger
        except Exception as e:
            logger.debug(f"Dragon tiger fetch failed for {symbol}: {e}")

        score = 0.0
        if data.margin_balance_change > 0:
            score += 0.3
        if data.net_long_flow > 0:
            score += 0.3
        if data.dragon_tiger_data:
            score += 0.2
        if data.block_trade_discount < -0.05:
            score -= 0.2

        data.sentiment_score = max(-1, min(1, score))
        if score > 0.3:
            data.overall_sentiment = "bullish"
        elif score < -0.3:
            data.overall_sentiment = "bearish"
        else:
            data.overall_sentiment = "neutral"

        self._cache[symbol] = data
        self._last_fetch = now
        return data

    async def _fetch_margin_data(self, symbol: str) -> Optional[dict]:
        try:
            import requests
            url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
            params = {
                "reportName": "RPT_MARGIN_TRADING",
                "columns": "RQYE,RQYEMRJZB",
                "filter": f'(SECURITY_CODE="{symbol}")',
                "pageNumber": 1, "pageSize": 1,
            }
            headers = {"User-Agent": "Mozilla/5.0"}
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(
                None, lambda: requests.get(url, params=params, headers=headers, timeout=8)
            )
            if resp.status_code == 200:
                d = resp.json().get("result", {}).get("data", [])
                if d:
                    return {"balance": d[0].get("RQYE", 0), "change": d[0].get("RQYEMRJZB", 0)}
        except Exception:
            pass
        return None

    async def _fetch_long_short_data(self, symbol: str) -> Optional[dict]:
        try:
            import requests
            url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
            params = {
                "reportName": "RPT_MARGIN_TRADING",
                "columns": "RZMRE,RZYE,RQMRE,RQYE",
                "filter": f'(SECURITY_CODE="{symbol}")',
                "pageNumber": 1, "pageSize": 1,
            }
            headers = {"User-Agent": "Mozilla/5.0"}
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(
                None, lambda: requests.get(url, params=params, headers=headers, timeout=8)
            )
            if resp.status_code == 200:
                d = resp.json().get("result", {}).get("data", [])
                if d:
                    row = d[0]
                    return {
                        "buy": row.get("RZMRE", 0),
                        "sell": row.get("RQMRE", 0),
                    }
        except Exception as e:
            logger.debug(f"Long/short data fetch failed: {e}")
        return None

    async def _fetch_dragon_tiger(self, symbol: str) -> Optional[List[dict]]:
        try:
            import requests
            url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
            params = {
                "reportName": "RPT_DAILYBILLBOARD_DETAILSNEW",
                "columns": "TRADE_DATE,EXPLAIN,CLOSE_PRICE,CHANGE_RATE,BUY_AMOUNT,SELL_AMOUNT,NET_AMOUNT",
                "filter": f'(SECURITY_CODE="{symbol}")',
                "pageNumber": 1, "pageSize": 5,
                "sortColumns": "TRADE_DATE",
                "sortTypes": -1,
            }
            headers = {"User-Agent": "Mozilla/5.0"}
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(
                None, lambda: requests.get(url, params=params, headers=headers, timeout=8)
            )
            if resp.status_code == 200:
                d = resp.json().get("result", {}).get("data", [])
                result = []
                for row in d:
                    result.append({
                        "date": row.get("TRADE_DATE", ""),
                        "reason": row.get("EXPLAIN", ""),
                        "close_price": row.get("CLOSE_PRICE", 0),
                        "change_rate": row.get("CHANGE_RATE", 0),
                        "buy_amount": row.get("BUY_AMOUNT", 0),
                        "sell_amount": row.get("SELL_AMOUNT", 0),
                        "net_amount": row.get("NET_AMOUNT", 0),
                    })
                return result if result else None
        except Exception as e:
            logger.debug(f"Dragon tiger fetch failed: {e}")
        return None

    def get_cached(self, symbol: str) -> Optional[dict]:
        data = self._cache.get(symbol)
        return data.to_dict() if data else None
