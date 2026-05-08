import re
from pathlib import Path

BASE = Path("/Users/fei/Desktop/大三下 /quantitative-trading-system/frontend")
TMP = BASE / ".qc_style_tmp"

MAPPING = {
    "src/views/market/MarketPage.vue": "market.css",
    "src/views/stock/StockDetailPage.vue": "stock.css",
    "src/views/moneyflow/MoneyFlowPage.vue": "moneyflow.css",
    "src/views/chip/ChipPage.vue": "chip.css",
    "src/views/sector/SectorPage.vue": "sector.css",
    "src/views/watchlist/WatchlistPage.vue": "watchlist.css",
    "src/views/news/NewsPage.vue": "news.css",
    "src/views/screener/ScreenerPage.vue": "screener.css",
}

for vue_rel, css_name in MAPPING.items():
    vue_path = BASE / vue_rel
    css_path = TMP / css_name

    content = vue_path.read_text(encoding="utf-8")
    new_css = css_path.read_text(encoding="utf-8").rstrip()

    pattern = r"<style scoped>.*?</style>"
    replacement = f"<style scoped>\n{new_css}\n</style>"

    new_content = re.sub(pattern, replacement, content, count=1, flags=re.DOTALL)

    if new_content == content:
        print(f"WARNING: No change for {vue_rel}")
    else:
        vue_path.write_text(new_content, encoding="utf-8")
        print(f"OK: {vue_rel}")
