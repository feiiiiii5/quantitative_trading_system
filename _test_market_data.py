import sys
sys.path.insert(0, '/Users/fei/Desktop/大三下/quantitative-trading-system')

from core.market_data import get_stock_list, get_market_page, search_all_markets, get_market_summary

print("=== Test 1: A-stock list ===")
a_stocks = get_stock_list("A")
print(f"A-stock count: {len(a_stocks)}")
if a_stocks:
    print(f"First 3: {a_stocks[:3]}")

print("\n=== Test 2: HK stock list ===")
hk_stocks = get_stock_list("HK")
print(f"HK stock count: {len(hk_stocks)}")
if hk_stocks:
    print(f"First 3: {hk_stocks[:3]}")

print("\n=== Test 3: US stock list ===")
us_stocks = get_stock_list("US")
print(f"US stock count: {len(us_stocks)}")
if us_stocks:
    print(f"First 3: {us_stocks[:3]}")

print("\n=== Test 4: A-stock market page (top gainers) ===")
page = get_market_page("A", page=1, page_size=5, sort="pct", asc=False)
print(f"Total: {page['total']}, Page: {page['page']}")
for s in page['stocks']:
    print(f"  {s['code']} {s['name']}: price={s.get('price')}, pct={s.get('pct')}%")

print("\n=== Test 5: Search ===")
results = search_all_markets("茅台", limit=5)
print(f"Search '茅台': {len(results)} results")
for r in results:
    print(f"  {r['code']} {r['name']} ({r['market']})")

results2 = search_all_markets("AAPL", limit=5)
print(f"Search 'AAPL': {len(results2)} results")
for r in results2:
    print(f"  {r['code']} {r['name']} ({r['market']})")

print("\n=== Test 6: Market summary ===")
summary = get_market_summary()
print(f"Summary: {summary}")
