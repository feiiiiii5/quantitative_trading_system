import requests
import json

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0',
    'Referer': 'https://finance.sina.com.cn'
})

# Test different Sina node names for HK stocks
hk_nodes = ['hk_stock', 'hk_main', 'hkex', 'ggb_hk', 'hk_stock_main']
for node in hk_nodes:
    url = f'https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData?page=1&num=5&sort=changepercent&asc=0&node={node}&symbol=&_s_r_a=auto'
    try:
        r = session.get(url, timeout=5)
        data = json.loads(r.text) if r.text and r.text.strip() != 'null' else []
        print(f'Node "{node}": {len(data)} items')
        if data:
            print(f'  Sample: {data[0].get("code")} {data[0].get("name")}')
    except Exception as e:
        print(f'Node "{node}": error - {e}')

# Test Tencent for HK stock list
print('\n--- Tencent HK ---')
url = 'https://qt.gtimg.cn/q=hk00700,hk09988,hk01810,hk00941,hk03690,hk01288,hk01398,hk02388,hk00388,hk02318'
r = session.get(url, timeout=10)
lines = [l for l in r.text.split(';') if l.strip() and 'v_' in l]
print(f'Tencent HK: {len(lines)} items')

# Test Tencent for US stock list
print('\n--- Tencent US ---')
url = 'https://qt.gtimg.cn/q=usAAPL,usMSFT,usGOOGL,usAMZN,usNVDA,usMETA,usTSLA,usBRK.B,usJPM,usV'
r = session.get(url, timeout=10)
lines = [l for l in r.text.split(';') if l.strip() and 'v_' in l]
print(f'Tencent US: {len(lines)} items')

# Test getting A-stock total count from Sina
print('\n--- Sina A-stock total ---')
url = 'https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData?page=1&num=1&sort=symbol&asc=1&node=hs_a&symbol=&_s_r_a=auto'
r = session.get(url, timeout=10)
data = json.loads(r.text) if r.text else []
print(f'Got {len(data)} items (num=1 test)')

# Try getting a large batch
url = 'https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData?page=1&num=500&sort=symbol&asc=1&node=hs_a&symbol=&_s_r_a=auto'
r = session.get(url, timeout=15)
data = json.loads(r.text) if r.text else []
print(f'Got {len(data)} items (num=500 test)')
