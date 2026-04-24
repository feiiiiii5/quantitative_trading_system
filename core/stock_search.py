import re
from typing import Optional

from core.database import get_db
from core.market_data import (
    get_stock_list,
    search_all_markets,
    get_market_summary as _get_market_summary,
    get_market_page,
)

_STOCK_INDEX = {
    "000001": {"name": "平安银行", "market": "A", "sector": "银行"},
    "000002": {"name": "万科A", "market": "A", "sector": "房地产"},
    "000333": {"name": "美的集团", "market": "A", "sector": "家电"},
    "000858": {"name": "五粮液", "market": "A", "sector": "白酒"},
    "600519": {"name": "贵州茅台", "market": "A", "sector": "白酒"},
    "601318": {"name": "中国平安", "market": "A", "sector": "保险"},
    "600036": {"name": "招商银行", "market": "A", "sector": "银行"},
    "002594": {"name": "比亚迪", "market": "A", "sector": "新能源"},
    "300750": {"name": "宁德时代", "market": "A", "sector": "新能源"},
    "00700": {"name": "腾讯控股", "market": "HK", "sector": "科技", "exchange": "HKEX"},
    "09988": {"name": "阿里巴巴-SW", "market": "HK", "sector": "科技", "exchange": "HKEX"},
    "01810": {"name": "小米集团-W", "market": "HK", "sector": "科技", "exchange": "HKEX"},
    "AAPL": {"name": "苹果", "market": "US", "sector": "科技", "exchange": "NASDAQ"},
    "MSFT": {"name": "微软", "market": "US", "sector": "科技", "exchange": "NASDAQ"},
    "NVDA": {"name": "英伟达", "market": "US", "sector": "芯片", "exchange": "NASDAQ"},
    "TSLA": {"name": "特斯拉", "market": "US", "sector": "新能源", "exchange": "NASDAQ"},
}

_INDUSTRY_LIST = sorted(set(
    info["sector"] for info in _STOCK_INDEX.values() if info.get("sector")
))

_HOT_SEARCH_TERMS = ["白酒", "科技", "银行", "医药", "新能源", "芯片", "军工", "券商", "新能源车", "人工智能"]


def search_stocks(query: str, limit: int = 10, market: Optional[str] = None, category: Optional[str] = None) -> list:
    q = query.strip()
    if not q:
        return []

    results = search_all_markets(q, limit=limit * 2)
    if market:
        results = [r for r in results if r.get("market") == market]

    if category == "ETF" or category == "bond" or category == "future" or category == "index":
        db = get_db()
        instrument_types = [category]
        try:
            db_results = db.search_stock_info(q, limit=limit, market=market, instrument_types=instrument_types)
            for row in db_results:
                results.append({
                    "code": row.get("code", ""),
                    "name": row.get("name", ""),
                    "market": row.get("market", ""),
                    "sector": row.get("sector", ""),
                    "instrument_type": row.get("instrument_type", "stock"),
                })
        except Exception:
            pass

    seen = set()
    unique_results = []
    for r in results:
        key = (r.get("market", ""), r.get("code", ""))
        if key not in seen:
            seen.add(key)
            unique_results.append(r)

    return unique_results[:limit]


def get_stock_name(symbol: str) -> Optional[str]:
    db = get_db()
    info = db.get_stock_info(symbol)
    if info:
        return info.get("name")
    info = _STOCK_INDEX.get(symbol)
    if info:
        return info.get("name")
    for market in ("A", "HK", "US"):
        stocks = get_stock_list(market)
        for s in stocks:
            if s.get("code") == symbol:
                return s.get("name")
    return None


def get_stock_info(symbol: str) -> Optional[dict]:
    db = get_db()
    info = db.get_stock_info(symbol)
    if info:
        return dict(info)
    info = _STOCK_INDEX.get(symbol)
    if info:
        return dict(info)
    for market in ("A", "HK", "US"):
        stocks = get_stock_list(market)
        for s in stocks:
            if s.get("code") == symbol:
                return {
                    "code": s.get("code"),
                    "name": s.get("name"),
                    "market": s.get("market"),
                    "sector": s.get("sector", ""),
                }
    return None


def get_all_industries() -> list:
    db = get_db()
    rows = db.fetchall(
        """
        SELECT DISTINCT industry
        FROM stock_info
        WHERE industry <> ''
        ORDER BY industry ASC
        """
    )
    db_industries = [row["industry"] for row in rows if row.get("industry")]
    return sorted(set(_INDUSTRY_LIST).union(db_industries))


def get_hot_search_terms() -> list:
    return _HOT_SEARCH_TERMS


def get_stocks_by_market(market: str, limit: int = 100, offset: int = 0) -> dict:
    market = market.upper()
    if market not in ("A", "HK", "US"):
        return {"total": 0, "stocks": []}

    page_data = get_market_page(market, page=offset // limit + 1, page_size=limit, sort="mktcap", asc=False)
    stocks = page_data.get("stocks", [])

    return {
        "total": page_data.get("total", 0),
        "market": market,
        "stocks": stocks,
    }


def get_market_summary() -> dict:
    return _get_market_summary()
