# 올림픽공원 공연 일정(기관 홈페이지) 이번 달·다음 달 갱신 → state/올림픽공원_공연일정_2023_2026.json 병합
import json, os, urllib.request, datetime
HERE = os.path.dirname(os.path.abspath(__file__)); P = os.path.join(HERE, 'state', '올림픽공원_공연일정_2023_2026.json')
KST = datetime.timezone(datetime.timedelta(hours=9)); now = datetime.datetime.now(KST)
ev = {e['seq']: e for e in json.load(open(P, encoding='utf-8'))}
for k in range(0, 2):
    y = now.year + (now.month - 1 + k) // 12; m = (now.month - 1 + k) % 12 + 1
    req = urllib.request.Request('https://www.ksponco.or.kr/olympicpark/eventInfo/eventInfoListAjax.es', data=json.dumps({'nowYM': f'{y}{m:02d}', 'plcCd': ''}).encode(), headers={'Content-Type': 'application/json;charset=UTF-8', 'User-Agent': 'Mozilla/5.0'})
    r = json.loads(urllib.request.urlopen(req, timeout=30).read())
    for e in (r[0] or []) + (r[1] or []):
        ev[e['evtSeq']] = {'seq': e['evtSeq'], 'plc': e['plc'], 'title': e['title'], 'b': e['beginDt'], 'e': e['endDt'], 'tm': e['tm']}
json.dump(sorted(ev.values(), key=lambda x: x['b']), open(P, 'w', encoding='utf-8'), ensure_ascii=False)
print('events', len(ev))
