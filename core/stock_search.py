"""
QuantCore 股票搜索模块
使用东方财富API构建全量A股索引，支持代码/名称/拼音模糊搜索
"""
import asyncio
import logging
import threading
from difflib import SequenceMatcher
from typing import Optional

from core.market_data import fetch_all_a_stocks_async

logger = logging.getLogger(__name__)

_PINYIN_MAP: dict[str, str] | None = None
_PINYIN_MAP_LOCK = threading.Lock()

_code_index: dict[str, list[tuple[str, dict]]] = {}
_name_index: dict[str, list[tuple[str, dict]]] = {}
_pinyin_index: dict[str, list[tuple[str, dict]]] = {}
_all_stocks: dict[str, dict] = {}
_index_built = False
_index_lock = threading.Lock()

_STOCK_INDEX = {
    "600519": {"name": "贵州茅台", "market": "A", "sector": "白酒"},
    "000858": {"name": "五粮液", "market": "A", "sector": "白酒"},
    "000333": {"name": "美的集团", "market": "A", "sector": "家电"},
    "601318": {"name": "中国平安", "market": "A", "sector": "保险"},
    "300750": {"name": "宁德时代", "market": "A", "sector": "新能源"},
    "002594": {"name": "比亚迪", "market": "A", "sector": "汽车"},
    "600036": {"name": "招商银行", "market": "A", "sector": "银行"},
    "601012": {"name": "隆基绿能", "market": "A", "sector": "光伏"},
    "000001": {"name": "平安银行", "market": "A", "sector": "银行"},
    "600900": {"name": "长江电力", "market": "A", "sector": "电力"},
    "601398": {"name": "工商银行", "market": "A", "sector": "银行"},
    "600276": {"name": "恒瑞医药", "market": "A", "sector": "医药"},
    "000651": {"name": "格力电器", "market": "A", "sector": "家电"},
    "002475": {"name": "立讯精密", "market": "A", "sector": "电子"},
    "600809": {"name": "山西汾酒", "market": "A", "sector": "白酒"},
    "000568": {"name": "泸州老窖", "market": "A", "sector": "白酒"},
    "601888": {"name": "中国中免", "market": "A", "sector": "旅游"},
    "600030": {"name": "中信证券", "market": "A", "sector": "证券"},
    "002714": {"name": "牧原股份", "market": "A", "sector": "畜牧"},
    "603259": {"name": "药明康德", "market": "A", "sector": "医药"},
    "AAPL": {"name": "苹果", "market": "US", "sector": "科技"},
    "MSFT": {"name": "微软", "market": "US", "sector": "科技"},
    "GOOGL": {"name": "谷歌", "market": "US", "sector": "科技"},
    "AMZN": {"name": "亚马逊", "market": "US", "sector": "电商"},
    "TSLA": {"name": "特斯拉", "market": "US", "sector": "汽车"},
    "NVDA": {"name": "英伟达", "market": "US", "sector": "芯片"},
    "META": {"name": "Meta", "market": "US", "sector": "社交"},
    "NFLX": {"name": "奈飞", "market": "US", "sector": "流媒体"},
    "00700": {"name": "腾讯控股", "market": "HK", "sector": "科技"},
    "09988": {"name": "阿里巴巴", "market": "HK", "sector": "电商"},
    "09618": {"name": "京东集团", "market": "HK", "sector": "电商"},
    "03690": {"name": "美团", "market": "HK", "sector": "本地生活"},
    "01810": {"name": "小米集团", "market": "HK", "sector": "科技"},
    "09888": {"name": "百度集团", "market": "HK", "sector": "科技"},
    "02318": {"name": "中国平安H", "market": "HK", "sector": "保险"},
    "01299": {"name": "友邦保险", "market": "HK", "sector": "保险"},
}


def _get_pinyin_map() -> dict[str, str]:
    global _PINYIN_MAP
    if _PINYIN_MAP is not None:
        return _PINYIN_MAP
    with _PINYIN_MAP_LOCK:
        if _PINYIN_MAP is not None:
            return _PINYIN_MAP
        from pathlib import Path
        json_path = Path(__file__).parent / "data" / "pinyin_map.json"
        try:
            import json
            with open(json_path, "r", encoding="utf-8") as f:
                _PINYIN_MAP = json.load(f)
        except Exception as e:
            logger.debug(f"Failed to load pinyin map from {json_path}: {e}")
            _PINYIN_MAP = {}
        return _PINYIN_MAP


def _get_pinyin_initial(name: str) -> str:
    pinyin_map = _get_pinyin_map()
    result = []
    for ch in name:
        if ch in pinyin_map:
            result.append(pinyin_map[ch])
        elif 'a' <= ch <= 'z':
            result.append(ch)
        elif 'A' <= ch <= 'Z':
            result.append(ch.lower())
    return ''.join(result)


def _build_inverted_index() -> None:
    global _index_built, _code_index, _name_index, _pinyin_index, _all_stocks
    if _index_built:
        return
    with _index_lock:
        if _index_built:
            return

        all_stocks: dict[str, dict] = {}

        try:
            from core.market_data import _all_a_stocks_cache
            if _all_a_stocks_cache:
                for s in _all_a_stocks_cache:
                    code = s.get("symbol", s.get("code", ""))
                    if code:
                        mk = f"A:{code}"
                        all_stocks[mk] = {
                            "code": code,
                            "name": s.get("name", ""),
                            "market": "A",
                            "sector": s.get("industry", s.get("sector", "")),
                        }
                logger.info(f"Loaded {len(_all_a_stocks_cache)} stocks from EastMoney cache into search index")
        except Exception as e:
            logger.debug(f"Load from EastMoney cache error: {e}")

        for key, info in _STOCK_INDEX.items():
            mk = f"{info.get('market', 'A')}:{key}"
            if mk not in all_stocks:
                all_stocks[mk] = {"code": key, **info}

        if len(all_stocks) < 100:
            try:
                from core.market_data import get_stock_list
                for market in ("A", "HK", "US"):
                    try:
                        stocks = get_stock_list(market)
                        for s in stocks:
                            code = s.get("code", s.get("symbol", ""))
                            if code:
                                mk = f"{market}:{code}"
                                if mk not in all_stocks:
                                    all_stocks[mk] = {
                                        "code": code,
                                        "name": s.get("name", ""),
                                        "market": market,
                                        "sector": s.get("industry", s.get("sector", "")),
                                    }
                    except Exception:
                        pass
            except Exception:
                pass

        if len(all_stocks) < 100:
            try:
                from core.database import get_db
                db = get_db()
                rows = db.fetchall("SELECT symbol AS code, name, market, industry AS sector FROM stock_info")
                for r in rows:
                    mk = f"{r.get('market', 'A')}:{r.get('code', '')}"
                    if mk not in all_stocks and r.get("code"):
                        all_stocks[mk] = dict(r)
            except Exception:
                pass

        _all_stocks = all_stocks

        local_code: dict[str, list] = {}
        local_name: dict[str, list] = {}
        local_pinyin: dict[str, list] = {}

        for mk, s in all_stocks.items():
            code = s.get("code", "")
            name = s.get("name", "")

            for prefix_len in range(1, min(len(code) + 1, 7)):
                prefix = code[:prefix_len].upper()
                local_code.setdefault(prefix, []).append((mk, s))

            for ch in name:
                local_name.setdefault(ch, []).append((mk, s))

            py = _get_pinyin_initial(name)
            for prefix_len in range(1, min(len(py) + 1, 7)):
                prefix = py[:prefix_len].upper()
                local_pinyin.setdefault(prefix, []).append((mk, s))

        _code_index = local_code
        _name_index = local_name
        _pinyin_index = local_pinyin
        _index_built = True
        logger.info(f"Search index built: {len(all_stocks)} stocks, {len(local_code)} code prefixes, {len(local_name)} name chars, {len(local_pinyin)} pinyin prefixes")


def build_search_index():
    _build_inverted_index()


async def build_search_index_async() -> int:
    try:
        from core.market_data import fetch_all_a_stocks_async
        await fetch_all_a_stocks_async()
    except Exception as e:
        logger.debug(f"Pre-fetch stocks for index error: {e}")
    _build_inverted_index()
    return len(_all_stocks)


def _ensure_index():
    if not _index_built:
        _build_inverted_index()


def search_stocks(query: str, limit: int = 10, market: Optional[str] = None) -> list[dict]:
    _ensure_index()

    if not query or not query.strip():
        return []

    raw_q = query.strip()
    q = raw_q.upper()
    is_pinyin_input = raw_q.isalpha() and raw_q == raw_q.lower() and raw_q.isascii()

    results: dict[str, tuple[int, float, dict]] = {}
    counter = 0

    if q in _code_index:
        for mk, s in _code_index[q]:
            if mk not in results:
                counter += 1
                code = s.get("code", "")
                score = 1.0 if code == q else 0.9
                results[mk] = (1, score, s)

    for mk, s in _all_stocks.items():
        name = s.get("name", "")
        code = s.get("code", "")
        if name == raw_q or name == q:
            if mk not in results:
                counter += 1
                results[mk] = (1, 1.0, s)
        elif raw_q in name or q in name:
            if mk not in results:
                counter += 1
                score = 0.8 if len(raw_q) == 1 else 0.85
                results[mk] = (2, score, s)

    if is_pinyin_input:
        py_key = q.upper()
        if py_key in _pinyin_index:
            for mk, s in _pinyin_index[py_key]:
                if mk not in results:
                    counter += 1
                    results[mk] = (2, 0.85, s)

        for prefix_len in range(max(1, len(q) - 1), len(q) + 1):
            prefix = q[:prefix_len].upper()
            if prefix in _pinyin_index:
                for mk, s in _pinyin_index[prefix]:
                    if mk not in results:
                        counter += 1
                        results[mk] = (3, 0.75, s)

        for prefix_len in range(1, len(q) + 1):
            prefix = q[:prefix_len]
            if prefix in _code_index:
                for mk, s in _code_index[prefix]:
                    if mk not in results:
                        counter += 1
                        results[mk] = (5, 0.6, s)

        for ch in q:
            if ch in _name_index:
                for mk, s in _name_index[ch]:
                    if mk not in results:
                        counter += 1
                        results[mk] = (6, 0.5, s)

        for mk, s in _all_stocks.items():
            if mk in results:
                continue
            name = s.get("name", "")
            py = _get_pinyin_initial(name)
            if py and SequenceMatcher(None, q.lower(), py).ratio() > 0.5:
                counter += 1
                results[mk] = (7, 0.4, s)
    else:
        for prefix_len in range(1, len(q) + 1):
            prefix = q[:prefix_len]
            if prefix in _code_index:
                for mk, s in _code_index[prefix]:
                    if mk not in results:
                        counter += 1
                        results[mk] = (2, 0.8, s)

        for ch in q:
            if ch in _name_index:
                for mk, s in _name_index[ch]:
                    if mk not in results:
                        counter += 1
                        results[mk] = (3, 0.7, s)

        py = _get_pinyin_initial(q)
        if py:
            for prefix_len in range(1, len(py) + 1):
                prefix = py[:prefix_len]
                if prefix in _pinyin_index:
                    for mk, s in _pinyin_index[prefix]:
                        if mk not in results:
                            counter += 1
                            results[mk] = (4, 0.65, s)

    sorted_results = sorted(results.items(), key=lambda x: (x[1][0], -x[1][1]))

    output = []
    for mk, (priority, _score, s) in sorted_results:
        if market and s.get("market", "A") != market:
            continue
        output.append({
            "symbol": s.get("code", ""),
            "code": s.get("code", ""),
            "name": s.get("name", ""),
            "market": s.get("market", "A"),
            "sector": s.get("sector", s.get("industry", "")),
            "priority": priority,
        })
        if len(output) >= limit:
            break

    return output


def get_stock_info(symbol: str) -> Optional[dict]:
    _ensure_index()
    symbol_upper = symbol.upper()
    for mk, s in _all_stocks.items():
        if s.get("code", "").upper() == symbol_upper:
            return {
                "code": s.get("code", ""),
                "name": s.get("name", ""),
                "market": s.get("market", "A"),
                "sector": s.get("sector", s.get("industry", "")),
            }
    return None


def get_stock_name(symbol: str) -> Optional[str]:
    info = get_stock_info(symbol)
    return info.get("name", "") if info else None


def get_all_industries() -> list[str]:
    _ensure_index()
    industries = set()
    for s in _all_stocks.values():
        sector = s.get("sector", s.get("industry", ""))
        if sector:
            industries.add(sector)
    return sorted(industries)
