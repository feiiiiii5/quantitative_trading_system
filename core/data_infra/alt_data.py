import asyncio
import json
import logging
import os
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


logger = logging.getLogger(__name__)

ALT_DATA_DIR = Path(os.environ.get("ALT_DATA_DIR", str(Path(__file__).parent.parent.parent / "data" / "alt_data")))


@dataclass
class NewsSentiment:
    title: str
    source: str
    published_at: str
    sentiment_score: float = 0.0
    sentiment_label: str = "neutral"
    relevance: float = 0.0
    symbols: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class NorthboundFlow:
    date: str
    sh_connect: float = 0.0
    sz_connect: float = 0.0
    total_flow: float = 0.0
    net_buy: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SocialHeat:
    symbol: str
    platform: str
    heat_index: float = 0.0
    mention_count: int = 0
    positive_ratio: float = 0.5
    timestamp: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


class NewsSentimentAnalyzer:
    def __init__(self):
        self._model = None
        self._model_name = os.environ.get("SENTIMENT_MODEL", "")
        try:
            from cachetools import TTLCache
            self._cache = TTLCache(maxsize=1000, ttl=3600)
        except ImportError:
            self._cache = {}
            self._cache_maxsize = 1000
        self._keyword_weights = {
            "利好": 0.8, "上涨": 0.6, "突破": 0.7, "新高": 0.7,
            "增长": 0.6, "盈利": 0.7, "超预期": 0.8, "强势": 0.6,
            "利空": -0.8, "下跌": -0.6, "暴跌": -0.9, "破位": -0.7,
            "亏损": -0.7, "不及预期": -0.8, "弱势": -0.6, "减持": -0.5,
            "回购": 0.5, "分红": 0.4, "重组": 0.3, "并购": 0.4,
        }

    def analyze(self, title: str, content: str = "", source: str = "") -> NewsSentiment:
        cache_key = f"{title}:{source}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        text = f"{title} {content}"
        score = 0.0
        matched_keywords = 0

        for keyword, weight in self._keyword_weights.items():
            count = text.count(keyword)
            if count > 0:
                score += weight * count
                matched_keywords += count

        if matched_keywords > 0:
            score = max(-1.0, min(1.0, score / matched_keywords))
        else:
            score = 0.0

        if score > 0.2:
            label = "positive"
        elif score < -0.2:
            label = "negative"
        else:
            label = "neutral"

        sentiment = NewsSentiment(
            title=title, source=source,
            published_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            sentiment_score=round(score, 4),
            sentiment_label=label,
        )
        self._cache[cache_key] = sentiment
        if isinstance(self._cache, dict) and len(self._cache) > self._cache_maxsize:
            oldest = list(self._cache.keys())[:len(self._cache) - self._cache_maxsize]
            for k in oldest:
                del self._cache[k]
        return sentiment

    def analyze_batch(self, items: List[dict]) -> List[NewsSentiment]:
        results = []
        for item in items:
            title = item.get("title", "")
            content = item.get("content", "")
            source = item.get("source", "")
            results.append(self.analyze(title, content, source))
        return results


class NorthboundFlowTracker:
    def __init__(self):
        self._cache: List[NorthboundFlow] = []
        self._last_fetch = 0.0
        self._fetch_interval = int(os.environ.get("NORTHBOUND_FETCH_INTERVAL", "300"))

    async def fetch_flow(self) -> List[NorthboundFlow]:
        now = time.time()
        if self._cache and (now - self._last_fetch) < self._fetch_interval:
            return self._cache

        try:
            data = await self._fetch_from_eastmoney()
            if data:
                self._cache = data
                self._last_fetch = now
                return data
        except Exception as e:
            logger.debug(f"Northbound flow fetch failed: {e}")

        return self._cache

    async def _fetch_from_eastmoney(self) -> Optional[List[NorthboundFlow]]:
        try:
            import requests
            url = "https://push2his.eastmoney.com/api/qt/kamt.kline/get"
            params = {
                "fields1": "f1,f2,f3,f4",
                "fields2": "f51,f52,f53,f54,f55,f56",
                "klt": "101",
                "lmt": "30",
                "ut": "b955e6154c27a7de8ee4dc42d7ba41cc",
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
                "Referer": "https://data.eastmoney.com/",
            }
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(
                None, lambda: requests.get(url, params=params, headers=headers, timeout=10)
            )
            if resp.status_code == 200:
                d = resp.json().get("data", {})
                klines = d.get("s2n", [])
                if not klines:
                    klines = d.get("klines", [])
                result = []
                for line in klines:
                    if isinstance(line, str):
                        parts = line.split(",")
                    elif isinstance(line, list):
                        parts = line
                    else:
                        continue
                    if len(parts) >= 4:
                        result.append(NorthboundFlow(
                            date=parts[0],
                            sh_connect=float(parts[1]) if parts[1] != "-" else 0,
                            sz_connect=float(parts[2]) if parts[2] != "-" else 0,
                            total_flow=float(parts[3]) if parts[3] != "-" else 0,
                            net_buy=float(parts[3]) if parts[3] != "-" else 0,
                        ))
                return result
        except Exception as e:
            logger.debug(f"EastMoney northbound fetch error: {e}")
        return None

    def get_latest(self) -> Optional[NorthboundFlow]:
        return self._cache[-1] if self._cache else None


class SocialHeatTracker:
    def __init__(self):
        self._cache: Dict[str, SocialHeat] = {}
        self._last_fetch = 0.0

    async def fetch_heat(self, symbol: str) -> Optional[SocialHeat]:
        cache_key = symbol
        now = time.time()
        if cache_key in self._cache and (now - self._cache[cache_key].timestamp) < 300:
            return self._cache[cache_key]

        try:
            heat = await self._fetch_from_eastmoney_guba(symbol)
            if heat:
                self._cache[cache_key] = heat
                return heat
        except Exception as e:
            logger.debug(f"Social heat fetch failed for {symbol}: {e}")

        return self._cache.get(cache_key)

    async def _fetch_from_eastmoney_guba(self, symbol: str) -> Optional[SocialHeat]:
        try:
            import requests
            url = "https://guba.eastmoney.com/interface/GetData.aspx"
            params = {
                "path": "newtopic/api/GetTopicList",
                "param": f"ps=10&p=1&code={symbol}",
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
                "Referer": "https://guba.eastmoney.com/",
            }
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(
                None, lambda: requests.get(url, params=params, headers=headers, timeout=8)
            )
            if resp.status_code == 200:
                data = resp.json()
                mention_count = data.get("Data", {}).get("TotalCount", 0)
                heat_index = min(100, mention_count / 10) if mention_count > 0 else 0
                return SocialHeat(
                    symbol=symbol,
                    platform="eastmoney_guba",
                    heat_index=round(heat_index, 2),
                    mention_count=mention_count,
                    timestamp=time.time(),
                )
        except Exception as e:
            logger.debug(f"Guba heat fetch error for {symbol}: {e}")
        return None

    async def fetch_batch(self, symbols: List[str]) -> Dict[str, SocialHeat]:
        results = {}
        tasks = [self.fetch_heat(s) for s in symbols]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        for symbol, resp in zip(symbols, responses):
            if isinstance(resp, SocialHeat):
                results[symbol] = resp
        return results


class AltDataPipeline:
    def __init__(self):
        self.news_analyzer = NewsSentimentAnalyzer()
        self.northbound_tracker = NorthboundFlowTracker()
        self.social_tracker = SocialHeatTracker()
        self._data_dir = ALT_DATA_DIR
        self._data_dir.mkdir(parents=True, exist_ok=True)

    async def get_news_sentiment(self, symbol: str, limit: int = 20) -> List[dict]:
        try:
            news_items = await self._fetch_news(symbol, limit)
            if news_items:
                sentiments = self.news_analyzer.analyze_batch(news_items)
                return [s.to_dict() for s in sentiments]
        except Exception as e:
            logger.debug(f"News sentiment fetch failed for {symbol}: {e}")
        return []

    async def _fetch_news(self, symbol: str, limit: int = 20) -> List[dict]:
        try:
            import requests
            url = "https://search-api-web.eastmoney.com/search/jsonp"
            params = {
                "cb": "jQuery",
                "param": json.dumps({
                    "uid": "",
                    "keyword": symbol,
                    "type": ["cmsArticleWebOld"],
                    "client": "web",
                    "clientType": "web",
                    "clientVersion": "curr",
                    "param": {"cmsArticleWebOld": {"searchScope": "default", "sort": "default", "pageIndex": 1, "pageSize": limit, "preTag": "", "postTag": ""}},
                }),
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
                "Referer": "https://so.eastmoney.com/",
            }
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(
                None, lambda: requests.get(url, params=params, headers=headers, timeout=8)
            )
            if resp.status_code == 200:
                text = resp.text
                json_str = re.search(r"jQuery\((.*)\)", text)
                if json_str:
                    data = json.loads(json_str.group(1))
                    articles = data.get("result", {}).get("cmsArticleWebOld", {}).get("list", [])
                    return [
                        {
                            "title": a.get("title", ""),
                            "content": a.get("content", ""),
                            "source": a.get("mediaName", ""),
                            "published_at": a.get("date", ""),
                        }
                        for a in articles
                    ]
        except Exception as e:
            logger.debug(f"News fetch error for {symbol}: {e}")
        return []

    async def get_northbound_flow(self) -> List[dict]:
        data = await self.northbound_tracker.fetch_flow()
        return [d.to_dict() for d in data]

    async def get_social_heat(self, symbol: str) -> Optional[dict]:
        heat = await self.social_tracker.fetch_heat(symbol)
        return heat.to_dict() if heat else None

    async def get_social_heat_batch(self, symbols: List[str]) -> Dict[str, dict]:
        results = await self.social_tracker.fetch_batch(symbols)
        return {s: h.to_dict() for s, h in results.items()}

    async def get_comprehensive_alt_data(self, symbol: str) -> dict:
        news, northbound, social = await asyncio.gather(
            self.get_news_sentiment(symbol, limit=10),
            self.get_northbound_flow(),
            self.get_social_heat(symbol),
            return_exceptions=True,
        )
        return {
            "symbol": symbol,
            "news_sentiment": news if isinstance(news, list) else [],
            "northbound_flow": northbound if isinstance(northbound, list) else [],
            "social_heat": social if isinstance(social, dict) else None,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
