import json
import logging
import re
import threading
import time
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from core.database import get_db

logger = logging.getLogger(__name__)

_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://finance.sina.com.cn",
})
_ADAPTER = HTTPAdapter(pool_connections=20, pool_maxsize=50, max_retries=Retry(total=2, backoff_factor=0.5, status_forcelist=[429, 502, 503]))
_SESSION.mount("http://", _ADAPTER)
_SESSION.mount("https://", _ADAPTER)

_LIST_CACHE_TTL = 14400  # 股票列表缓存4小时
_QUOTE_CACHE_TTL = 15    # 实时行情缓存15秒
_SINA_PAGE_SIZE = 80     # 新浪每页最大条数

_lock = threading.Lock()
_stock_list_cache: dict[str, dict] = {}   # market -> {"data": [...], "ts": float}
_quote_cache: dict[str, dict] = {}        # market -> {"data": {code: {...}}, "ts": float}


def _code_to_tencent_prefix(code: str, market: str) -> str:
    if market == "A":
        if code.startswith(("6", "9")):
            return f"sh{code}"
        return f"sz{code}"
    elif market == "HK":
        return f"hk{code}"
    elif market == "US":
        return f"us{code}"
    return code


def _parse_tencent_quote(raw: str) -> Optional[dict]:
    try:
        parts = raw.split("~")
        if len(parts) < 50:
            return None
        market = int(parts[0]) if parts[0].isdigit() else 0
        name = parts[1]
        code = parts[2]
        price = float(parts[3]) if parts[3] else 0
        prev_close = float(parts[4]) if parts[4] else 0
        open_price = float(parts[5]) if parts[5] else 0
        volume = float(parts[6]) if parts[6] else 0
        high = float(parts[33]) if len(parts) > 33 and parts[33] else 0
        low = float(parts[34]) if len(parts) > 34 and parts[34] else 0
        change = price - prev_close if prev_close > 0 else 0
        pct = (change / prev_close * 100) if prev_close > 0 else 0
        turnover = float(parts[38]) if len(parts) > 38 and parts[38] else 0
        mkt_cap = float(parts[45]) if len(parts) > 45 and parts[45] else 0

        market_tag = "A"
        if market == 100:
            market_tag = "HK"
        elif market == 200:
            market_tag = "US"

        return {
            "code": code,
            "name": name,
            "price": round(price, 3),
            "change": round(change, 3),
            "pct": round(pct, 2),
            "open": round(open_price, 3),
            "high": round(high, 3),
            "low": round(low, 3),
            "prev_close": round(prev_close, 3),
            "volume": int(volume),
            "turnover": round(turnover, 2),
            "market_cap": round(mkt_cap, 2),
            "market": market_tag,
        }
    except Exception:
        return None


def _fetch_tencent_batch(codes: list[str], market: str) -> dict[str, dict]:
    result = {}
    if not codes:
        return result
    batch_size = 50
    for i in range(0, len(codes), batch_size):
        batch = codes[i:i + batch_size]
        prefixed = [_code_to_tencent_prefix(c, market) for c in batch]
        url = f"https://qt.gtimg.cn/q={','.join(prefixed)}"
        try:
            r = _SESSION.get(url, timeout=8)
            if r.status_code != 200:
                continue
            for line in r.text.split(";"):
                line = line.strip()
                if not line or 'v_' not in line:
                    continue
                match = re.search(r'"(.+)"', line)
                if not match:
                    continue
                q = _parse_tencent_quote(match.group(1))
                if q and q["price"] > 0:
                    result[q["code"]] = q
        except Exception as e:
            logger.debug(f"Tencent batch fetch error: {e}")
    return result


def _fetch_sina_page(page: int, num: int, sort: str = "changepercent", asc: int = 0) -> list[dict]:
    url = (
        f"https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/"
        f"Market_Center.getHQNodeData?page={page}&num={num}&sort={sort}&asc={asc}"
        f"&node=hs_a&symbol=&_s_r_a=auto"
    )
    try:
        r = _SESSION.get(url, timeout=10)
        if r.status_code != 200 or not r.text or r.text.strip() == "null":
            return []
        data = json.loads(r.text)
        results = []
        for item in data:
            price = float(item.get("trade", 0))
            prev_close = float(item.get("settlement", 0))
            change = float(item.get("pricechange", 0))
            pct = float(item.get("changepercent", 0))
            results.append({
                "code": item.get("code", ""),
                "name": item.get("name", ""),
                "price": round(price, 2),
                "change": round(change, 2),
                "pct": round(pct, 2),
                "open": round(float(item.get("open", 0)), 2),
                "high": round(float(item.get("high", 0)), 2),
                "low": round(float(item.get("low", 0)), 2),
                "prev_close": round(prev_close, 2),
                "volume": int(float(item.get("volume", 0))),
                "amount": round(float(item.get("amount", 0)), 2),
                "turnoverratio": round(float(item.get("turnoverratio", 0)), 2),
                "pe": round(float(item.get("per", 0)), 2) if item.get("per") else 0,
                "pb": round(float(item.get("pb", 0)), 2) if item.get("pb") else 0,
                "mktcap": round(float(item.get("mktcap", 0)), 2) if item.get("mktcap") else 0,
                "nmc": round(float(item.get("nmc", 0)), 2) if item.get("nmc") else 0,
                "market": "A",
            })
        return results
    except Exception as e:
        logger.debug(f"Sina page fetch error: {e}")
        return []


def _fetch_a_stock_list() -> list[dict]:
    try:
        import akshare as ak
        df = ak.stock_info_a_code_name()
        if df is not None and not df.empty:
            stocks = []
            for _, row in df.iterrows():
                code = str(row.get("code", row.iloc[0])).strip()
                name = str(row.get("name", row.iloc[1])).strip()
                if not code or not name:
                    continue
                market = "A"
                sector = ""
                if code.startswith("6"):
                    sector = "沪市主板"
                elif code.startswith("0"):
                    sector = "深市主板"
                elif code.startswith("3"):
                    sector = "创业板"
                elif code.startswith("68"):
                    sector = "科创板"
                stocks.append({
                    "code": code,
                    "name": name,
                    "market": market,
                    "sector": sector,
                })
            return stocks
    except Exception as e:
        logger.debug(f"AKShare A-stock list fetch error: {e}")
    return []


_HK_STOCK_CODES = [
    "00700", "09988", "01810", "00941", "03690", "01288", "01398", "02388",
    "00388", "02318", "09618", "09999", "01024", "09888", "02018", "02269",
    "01109", "02015", "01896", "06098", "02628", "00005", "00001", "00002",
    "00003", "00006", "00011", "00012", "00016", "00017", "00027", "00066",
    "00101", "00135", "00144", "00151", "00165", "00175", "00241", "00267",
    "00270", "00293", "00316", "00345", "00354", "00386", "00388", "00425",
    "00489", "00493", "00522", "00551", "00552", "00570", "00576", "00590",
    "00636", "00669", "00683", "00688", "00694", "00698", "00710", "00728",
    "00753", "00762", "00772", "00788", "00823", "00836", "00853", "00857",
    "00868", "00881", "00883", "00888", "00914", "00916", "00939", "00941",
    "00960", "00968", "00981", "00998", "01024", "01044", "01066", "01088",
    "01113", "01128", "01171", "01177", "01200", "01211", "01288", "01336",
    "01339", "01357", "01378", "01398", "01448", "01513", "01579", "01658",
    "01766", "01787", "01800", "01810", "01816", "01833", "01876", "01918",
    "01919", "01928", "01958", "01988", "02007", "02015", "02018", "02039",
    "02128", "02196", "02202", "02208", "02233", "02269", "02313", "02318",
    "02331", "02333", "02338", "02382", "02388", "02518", "02601", "02607",
    "02628", "02688", "02727", "02799", "02822", "02899", "03032", "03323",
    "03328", "03454", "03528", "03606", "03669", "03690", "03769", "03800",
    "03888", "03960", "03968", "03988", "03993", "03999", "06060", "06098",
    "06618", "06690", "06862", "06969", "06988", "07332", "07552", "07576",
    "07618", "07772", "07800", "07827", "07936", "07999", "08069", "08222",
    "08322", "08367", "08447", "08535", "08613", "08668", "08716", "08813",
    "09618", "09626", "09633", "09668", "09688", "09698", "09758", "09868",
    "09888", "09896", "09899", "09922", "09955", "09961", "09988", "09999",
]

_HK_STOCK_NAMES = {
    "00700": "腾讯控股", "09988": "阿里巴巴-SW", "01810": "小米集团-W",
    "00941": "中国移动", "03690": "美团-W", "01288": "农业银行",
    "01398": "工商银行", "02388": "中银香港", "00388": "香港交易所",
    "02318": "中国平安", "09618": "京东集团-SW", "09999": "网易-S",
    "01024": "快手-W", "09888": "百度集团-SW", "02018": "瑞声科技",
    "02269": "药明生物", "01109": "华润置地", "02015": "比亚迪电子",
    "00005": "汇丰控股", "00001": "长和", "00002": "中电控股",
    "00003": "香港中华煤气", "00006": "电能实业", "00011": "恒生银行",
    "00012": "恒基兆业地产", "00016": "新鸿基地产", "00017": "新世界发展",
    "00027": "银河娱乐", "00066": "港铁公司", "00135": "昆仑能源",
    "00144": "招商局港口", "00165": "中国光大控股", "00175": "吉利汽车",
    "00241": "阿里健康", "00267": "中信股份", "00270": "粤海投资",
    "00293": "国泰航空", "00316": "东方海外国际", "00345": "维他奶国际",
    "00354": "中国软件国际", "00386": "中国石油化工", "00425": "敏实集团",
    "00489": "东风集团", "00493": "国美零售", "00522": "ASM太平洋",
    "00551": "裕元集团", "00570": "中国中药", "00576": "浙江沪杭甬",
    "00590": "六福集团", "00636": "富智康集团", "00669": "创科实业",
    "00683": "嘉里建设", "00688": "中国海外发展", "00694": "北京首都机场",
    "00698": "通达集团", "00710": "众安在线", "00728": "中国电信",
    "00753": "中国国航", "00762": "中国联通", "00772": "阅文集团",
    "00788": "中国铁塔", "00823": "领展房产基金", "00836": "华润电力",
    "00853": "微创医疗", "00857": "中国石油", "00868": "信义玻璃",
    "00881": "中升集团", "00883": "中海油", "00888": "碧桂园",
    "00914": "海螺水泥", "00916": "龙源电力", "00939": "建设银行",
    "00960": "龙湖集团", "00968": "信义光能", "00981": "中芯国际",
    "00998": "中信银行", "01044": "恒安国际", "01066": "威高股份",
    "01088": "中国神华", "01113": "长实集团", "01128": "永利澳门",
    "01171": "兖矿能源", "01177": "中国生物制药", "01200": "海底捞",
    "01211": "比亚迪", "01336": "新华保险", "01339": "中国人民保险",
    "01357": "美图", "01378": "中金公司", "01448": "福寿园",
    "01513": "丽珠医药", "01579": "颐海国际", "01658": "邮储银行",
    "01766": "中国中车", "01787": "山东黄金", "01800": "中国交通建设",
    "01816": "中广核电力", "01833": "平安好医生", "01876": "百威亚太",
    "01918": "融创服务", "01919": "中远海控", "01928": "金沙中国",
    "01958": "北京汽车", "01988": "民生银行", "02007": "碧桂服",
    "02039": "IMAX CHINA", "02128": "中国利郎", "02196": "复星医药",
    "02202": "万科企业", "02208": "金风科技", "02233": "西部水泥",
    "02313": "申洲国际", "02331": "李宁", "02333": "长城汽车",
    "02338": "潍柴动力", "02382": "舜宇光学科技", "02518": "汽车之家",
    "02601": "中国太保", "02607": "上海医药", "02628": "中国人寿",
    "02688": "新奥能源", "02727": "瑞声科技", "02799": "同程旅行",
    "02822": "汇付天下", "02899": "紫金矿业", "03032": "SOPHGO",
    "03323": "中国建材", "03328": "交通银行", "03454": "JS环球生活",
    "03528": "叮当健康", "03606": "福耀玻璃", "03669": "永达汽车",
    "03769": "理想汽车-W", "03800": "协鑫科技", "03888": "金山软件",
    "03960": "东方电气", "03968": "招商银行", "03988": "中国银行",
    "03993": "洛阳钼业", "03999": "江西铜业", "06060": "众安智慧生活",
    "06618": "京东健康", "06690": "海尔智家", "06862": "海底捞",
    "06969": "思摩尔国际", "06988": "矿机集团", "07332": "嘉泓物流",
    "07552": "汇通达网络", "07576": "微泰医疗-B", "07618": "京东物流",
    "07772": "阅文集团", "07800": "易点云", "07827": "涂鸦智能",
    "07936": "中国中免", "07999": "网龙", "08069": "同源康医药-B",
    "09626": "哔哩哔哩-W", "09633": "农夫山泉", "09668": "路特斯科技",
    "09688": "再鼎医药-B", "09698": "万国数据-SW", "09758": "荣昌生物",
    "09868": "小鹏汽车-W", "09896": "名创优品", "09899": "海吉亚医疗",
    "09922": "九毛九", "09955": "淮北矿业", "09961": "携程集团-S",
}

_US_STOCK_CODES = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK.B", "JPM", "V",
    "JNJ", "WMT", "PG", "MA", "HD", "UNH", "DIS", "BAC", "XOM", "KO",
    "PFE", "CSCO", "ADBE", "CRM", "NFLX", "AMD", "INTC", "PYPL", "UBER", "ABNB",
    "NIO", "PDD", "BIDU", "BABA", "JD", "TME", "LI", "XPEV", "SHOP", "SQ",
    "SNAP", "SE", "TCEHY", "SPOT", "ZM", "ROKU", "CRWD", "SNOW", "PLTR", "COIN",
    "RIVN", "LCID", "FSR", "NKLA", "NNDM", "SOFI", "HOOD", "RBLX", "ABNB", "DASH",
    "COIN", "MARA", "RIOT", "HUT", "CLSK", "BTBT", "BITF", "SI", "SBNY", "VIRT",
    "ORCL", "IBM", "ACN", "NOW", "INTU", "ADP", "MDLZ", "PEP", "COST", "AVGO",
    "TXN", "QCOM", "AMAT", "LRCX", "KLAC", "MU", "WDC", "STX", "MRVL", "SWKS",
    "MPWR", "ON", "ENPH", "SEDG", "FSLR", "RUN", "SPWR", "NOVA", "BE", "BLDK",
    "TMO", "ABT", "LLY", "MRK", "BMY", "AMGN", "GILD", "REGN", "VRTX", "BIIB",
    "MRNA", "AZN", "ROCHE", "NVS", "SNY", "GSK", "AZN", "BNTX", "VTRS", "TEVA",
    "BA", "CAT", "GE", "HON", "LMT", "NOC", "RTX", "UPS", "FDX", "DE",
    "CVX", "COP", "SLB", "EOG", "OXY", "MPC", "VLO", "PSX", "KMI", "WMB",
    "GS", "MS", "BLK", "SCHW", "C", "AXP", "CB", "AIG", "MET", "PRU",
    "AAPL", "T", "VZ", "TMUS", "CMCSA", "CHTR", "DIS", "WBD", "PARA", "NFLX",
    "F", "GM", "TM", "HMC", "STLA", "RACE", "CARZ", "FCAU", "VWAGY", "BMWYY",
    "WELL", "AMT", "PLD", "CCI", "EQIX", "PSA", "O", "SPG", "DLR", "AVB",
    "BTC-USD", "ETH-USD", "GC=F", "CL=F", "HG=F", "SI=F", "ZW=F", "ZC=F", "ZS=F", "KE=F",
    "^GSPC", "^DJI", "^IXIC", "^VIX", "^RUT", "DX-Y.NYB", "TLT", "GLD", "SLV", "USO",
]

_US_STOCK_NAMES = {
    "AAPL": "苹果", "MSFT": "微软", "GOOGL": "谷歌", "AMZN": "亚马逊",
    "NVDA": "英伟达", "META": "Meta", "TSLA": "特斯拉", "BRK.B": "伯克希尔",
    "JPM": "摩根大通", "V": "Visa", "JNJ": "强生", "WMT": "沃尔玛",
    "PG": "宝洁", "MA": "万事达", "HD": "家得宝", "UNH": "联合健康",
    "DIS": "迪士尼", "BAC": "美国银行", "XOM": "埃克森美孚", "KO": "可口可乐",
    "PFE": "辉瑞", "CSCO": "思科", "ADBE": "Adobe", "CRM": "Salesforce",
    "NFLX": "奈飞", "AMD": "AMD", "INTC": "英特尔", "PYPL": "PayPal",
    "UBER": "Uber", "ABNB": "Airbnb", "NIO": "蔚来", "PDD": "拼多多",
    "BIDU": "百度", "BABA": "阿里巴巴", "JD": "京东", "TME": "腾讯音乐",
    "LI": "理想汽车", "XPEV": "小鹏汽车", "SHOP": "Shopify", "SQ": "Block",
    "ORCL": "甲骨文", "IBM": "IBM", "ACN": "埃森哲", "NOW": "ServiceNow",
    "AVGO": "博通", "TXN": "德州仪器", "QCOM": "高通", "AMAT": "应用材料",
    "COST": "好市多", "PEP": "百事", "MDLZ": "亿滋", "ADP": "ADP",
    "TMO": "赛默飞", "ABT": "雅培", "LLY": "礼来", "MRK": "默克",
    "BMY": "百时美施贵宝", "AMGN": "安进", "GILD": "吉利德", "REGN": "再生元",
    "BA": "波音", "CAT": "卡特彼勒", "GE": "通用电气", "HON": "霍尼韦尔",
    "LMT": "洛克希德马丁", "NOC": "诺斯洛普·格鲁曼", "RTX": "雷神技术",
    "CVX": "雪佛龙", "COP": "康菲石油", "GS": "高盛", "MS": "摩根士丹利",
    "BLK": "贝莱德", "SCHW": "嘉信理财", "C": "花旗", "AXP": "美国运通",
    "F": "福特", "GM": "通用汽车", "T": "AT&T", "VZ": "威瑞森",
    "CMCSA": "康卡斯特", "WBD": "华纳兄弟探索", "SNAP": "Snap",
    "SE": "Sea", "SPOT": "Spotify", "ZM": "Zoom", "ROKU": "Roku",
    "CRWD": "CrowdStrike", "SNOW": "Snowflake", "PLTR": "Palantir",
    "COIN": "Coinbase", "RIVN": "Rivian", "SOFI": "SoFi", "HOOD": "Robinhood",
    "RBLX": "Roblox", "DASH": "DoorDash", "MRNA": "Moderna",
    "^GSPC": "S&P 500", "^DJI": "道琼斯", "^IXIC": "纳斯达克", "^VIX": "VIX恐慌指数",
}


def _get_hk_stock_list() -> list[dict]:
    stocks = []
    for code in _HK_STOCK_CODES:
        name = _HK_STOCK_NAMES.get(code, "")
        stocks.append({"code": code, "name": name, "market": "HK", "sector": "港股"})
    return stocks


def _get_us_stock_list() -> list[dict]:
    stocks = []
    seen = set()
    for code in _US_STOCK_CODES:
        if code in seen:
            continue
        seen.add(code)
        name = _US_STOCK_NAMES.get(code, code)
        stocks.append({"code": code, "name": name, "market": "US", "sector": "美股"})
    return stocks


def get_stock_list(market: str, force_refresh: bool = False) -> list[dict]:
    market = market.upper()
    if market not in ("A", "HK", "US"):
        return []

    with _lock:
        cached = _stock_list_cache.get(market)
        if not force_refresh and cached and (time.time() - cached["ts"]) < _LIST_CACHE_TTL:
            return cached["data"]

    if market == "A":
        stocks = _fetch_a_stock_list()
        if not stocks:
            db = get_db()
            try:
                rows = db.fetchall("SELECT code, name, market, sector FROM stock_info WHERE market = 'A' ORDER BY code")
                stocks = [{"code": r["code"], "name": r.get("name", ""), "market": "A", "sector": r.get("sector", "")} for r in rows]
            except Exception:
                pass
        if not stocks:
            from core.stock_search import _STOCK_INDEX
            stocks = [{"code": k, "name": v.get("name", ""), "market": "A", "sector": v.get("sector", "")} for k, v in _STOCK_INDEX.items() if v.get("market") == "A"]
    elif market == "HK":
        stocks = _get_hk_stock_list()
    elif market == "US":
        stocks = _get_us_stock_list()

    with _lock:
        _stock_list_cache[market] = {"data": stocks, "ts": time.time()}

    if market == "A" and stocks:
        _persist_stock_list(stocks)

    return stocks


def _persist_stock_list(stocks: list[dict]):
    db = get_db()
    try:
        rows = []
        for s in stocks:
            rows.append({
                "symbol": s["code"],
                "market": s.get("market", "A"),
                "name": s.get("name", ""),
                "instrument_type": "stock",
                "industry": s.get("sector", ""),
            })
        if rows:
            db.upsert_stock_info_rows(rows)
    except Exception as e:
        logger.debug(f"Persist stock list error: {e}")


def get_realtime_quotes(market: str, codes: list[str] = None, force_refresh: bool = False) -> dict[str, dict]:
    market = market.upper()
    if market not in ("A", "HK", "US"):
        return {}

    with _lock:
        cached = _quote_cache.get(market)
        if not force_refresh and cached and (time.time() - cached["ts"]) < _QUOTE_CACHE_TTL:
            if codes:
                return {k: v for k, v in cached["data"].items() if k in codes}
            return dict(cached["data"])

    if market == "A" and not codes:
        all_quotes = _fetch_sina_all_a_quotes()
        if all_quotes:
            with _lock:
                _quote_cache[market] = {"data": all_quotes, "ts": time.time()}
            return dict(all_quotes)

    stock_list = get_stock_list(market)
    all_codes = codes or [s["code"] for s in stock_list]
    quotes = _fetch_tencent_batch(all_codes, market)

    if quotes:
        with _lock:
            existing = _quote_cache.get(market, {}).get("data", {})
            existing.update(quotes)
            _quote_cache[market] = {"data": existing, "ts": time.time()}

    if codes:
        return {k: v for k, v in quotes.items() if k in codes}
    return quotes


def _fetch_sina_all_a_quotes() -> dict[str, dict]:
    result = {}
    try:
        for page in range(1, 80):
            batch = _fetch_sina_page(page, _SINA_PAGE_SIZE, sort="symbol", asc=1)
            if not batch:
                break
            for item in batch:
                result[item["code"]] = item
            if len(batch) < _SINA_PAGE_SIZE:
                break
            time.sleep(0.05)
    except Exception as e:
        logger.debug(f"Sina all A-quotes fetch error: {e}")
    return result


def get_market_page(
    market: str,
    page: int = 1,
    page_size: int = 50,
    sort: str = "pct",
    asc: bool = False,
    sector: str = None,
    search: str = None,
) -> dict:
    market = market.upper()
    if market not in ("A", "HK", "US"):
        return {"total": 0, "stocks": [], "page": page, "page_size": page_size}

    if market == "A" and not sector and not search:
        return _get_a_market_page_sina(page, page_size, sort, asc)

    stock_list = get_stock_list(market)
    quotes = get_realtime_quotes(market)

    merged = []
    for s in stock_list:
        code = s["code"]
        q = quotes.get(code, {})
        item = {
            "code": code,
            "name": q.get("name") or s.get("name", ""),
            "market": market,
            "sector": s.get("sector", ""),
        }
        if q:
            item.update({
                "price": q.get("price", 0),
                "change": q.get("change", 0),
                "pct": q.get("pct", 0),
                "volume": q.get("volume", 0),
                "amount": q.get("amount", q.get("turnover", 0)),
                "high": q.get("high", 0),
                "low": q.get("low", 0),
                "open": q.get("open", 0),
                "prev_close": q.get("prev_close", 0),
                "turnoverratio": q.get("turnoverratio", 0),
                "pe": q.get("pe", 0),
                "pb": q.get("pb", 0),
                "mktcap": q.get("mktcap", q.get("market_cap", 0)),
            })
        else:
            item.update({"price": 0, "change": 0, "pct": 0, "volume": 0})
        merged.append(item)

    if sector:
        merged = [s for s in merged if s.get("sector") == sector]
    if search:
        search_lower = search.lower()
        merged = [s for s in merged if search_lower in s.get("code", "").lower() or search_lower in s.get("name", "").lower()]

    sort_key_map = {
        "pct": "pct", "change": "change", "price": "price",
        "volume": "volume", "amount": "amount", "turnover": "amount",
        "mktcap": "mktcap", "pe": "pe", "pb": "pb",
        "turnoverratio": "turnoverratio", "code": "code", "name": "name",
    }
    sort_key = sort_key_map.get(sort, "pct")
    merged.sort(key=lambda x: x.get(sort_key, 0) if isinstance(x.get(sort_key, 0), (int, float)) else str(x.get(sort_key, "")), reverse=not asc)

    total = len(merged)
    start = (page - 1) * page_size
    end = start + page_size
    page_data = merged[start:end]

    return {
        "total": total,
        "stocks": page_data,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
        "market": market,
        "sort": sort,
        "asc": asc,
    }


def _get_a_market_page_sina(page: int, page_size: int, sort: str, asc: bool) -> dict:
    sort_map = {
        "pct": "changepercent", "change": "pricechange", "price": "trade",
        "volume": "volume", "amount": "amount", "mktcap": "mktcap",
        "turnoverratio": "turnoverratio", "pe": "per", "pb": "pb",
        "code": "symbol", "name": "name",
    }
    sina_sort = sort_map.get(sort, "changepercent")
    asc_val = 1 if asc else 0

    if page_size > _SINA_PAGE_SIZE:
        page_size = _SINA_PAGE_SIZE

    stocks = _fetch_sina_page(page, page_size, sort=sina_sort, asc=asc_val)
    total_estimate = 5500

    return {
        "total": total_estimate,
        "stocks": stocks,
        "page": page,
        "page_size": page_size,
        "pages": (total_estimate + page_size - 1) // page_size,
        "market": "A",
        "sort": sort,
        "asc": asc,
    }


def search_all_markets(query: str, limit: int = 20) -> list[dict]:
    if not query or not query.strip():
        return []
    q = query.strip()
    results = []
    seen = set()

    for market in ("A", "HK", "US"):
        stock_list = get_stock_list(market)
        for s in stock_list:
            code = s.get("code", "")
            name = s.get("name", "")
            matched = False
            score = 0

            if q.isdigit():
                if code.startswith(q):
                    matched = True
                    score = 100 - len(code) + len(q)
            elif re.match(r'^[A-Za-z.]+$', q):
                q_upper = q.upper()
                code_upper = code.upper()
                if code_upper == q_upper:
                    matched = True
                    score = 200
                elif code_upper.startswith(q_upper):
                    matched = True
                    score = 100
                elif q_upper in name.upper():
                    matched = True
                    score = 30
            else:
                if q in name:
                    matched = True
                    score = 100 if name.startswith(q) else 50
                elif q.upper() in code.upper():
                    matched = True
                    score = 80

            if matched and (market, code) not in seen:
                seen.add((market, code))
                results.append({
                    "code": code,
                    "name": name,
                    "market": market,
                    "sector": s.get("sector", ""),
                    "score": score,
                    "market_order": {"A": 0, "HK": 1, "US": 2}.get(market, 9),
                })

    results.sort(key=lambda x: (x["market_order"], -x["score"]))
    results = results[:limit]
    for r in results:
        r.pop("score", None)
        r.pop("market_order", None)
    return results


def get_market_summary() -> dict:
    summaries = {}
    for market in ("A", "HK", "US"):
        stock_list = get_stock_list(market)
        summaries[market] = {
            "name": {"A": "沪深A股", "HK": "港股", "US": "美股"}[market],
            "count": len(stock_list),
            "currency": {"A": "CNY", "HK": "HKD", "US": "USD"}[market],
        }
    return {
        "markets": summaries,
        "data_sources": [
            {"name": "AKShare", "markets": ["A", "HK", "US"], "type": "股票列表", "update_freq": "4小时"},
            {"name": "Sina Finance", "markets": ["A"], "type": "实时行情(分页)", "update_freq": "实时"},
            {"name": "Tencent Finance", "markets": ["A", "HK", "US"], "type": "实时行情(批量)", "update_freq": "实时"},
        ],
    }


def refresh_stock_list(market: str = "A") -> dict:
    stocks = get_stock_list(market, force_refresh=True)
    return {"success": True, "market": market, "count": len(stocks)}
