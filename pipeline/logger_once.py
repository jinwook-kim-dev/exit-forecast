# 기관 '주차장 예상 이용률 서비스' 1회 기록 (GitHub Actions에서 30분마다 실행)
import urllib.request, urllib.parse, re, csv, os, datetime, ssl
HERE = os.path.dirname(os.path.abspath(__file__)); ST = os.path.join(HERE, 'state')
URL = 'https://www.ksponco.or.kr/online/main/parking.do'
UA = {'User-Agent': 'Mozilla/5.0 (exit-forecast public-data logger)'}
KST = datetime.timezone(datetime.timedelta(hours=9))
def fetch(date=None):
    data = urllib.parse.urlencode({'selectdate': date}).encode() if date else None
    with urllib.request.urlopen(urllib.request.Request(URL, data=data, headers=UA), timeout=30, context=ssl.create_default_context()) as r:
        return r.read().decode('utf-8', 'replace')
def text(h):
    t = re.sub(r'<style.*?</style>|<script.*?</script>', '', h, flags=re.S); t = re.sub(r'<[^>]+>', ' ', t).replace('&nbsp;', ' ')
    return re.sub(r'\s+', ' ', t)
def append(name, row, header):
    p = os.path.join(ST, name); new = not os.path.exists(p)
    with open(p, 'a', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        if new: w.writerow(header)
        w.writerow(row)
now = datetime.datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')
h = fetch(); t = text(h)
m = re.search(r'실시간 주차대수[^:]*:\s*([\d,]+)\s*대 주차 중\s*/\s*([\d,]+)대', t)
if m: append('realtime.csv', [now, m.group(1).replace(',', ''), m.group(2).replace(',', '')], ['ts', 'parking_count', 'capacity'])
for d in re.findall(r'<option value="(\d{4}-\d{2}-\d{2})"', h):
    tt = text(fetch(d))
    for slot, pct in re.findall(re.escape(d) + r'\s+(\d{2}:\d{2}):\d{2}\s+(\d+)%', tt):
        append('predictions.csv', [now, d, slot, pct], ['fetched_ts', 'date', 'slot', 'pred_pct'])
print('logged', now, m.group(1) if m else None)
