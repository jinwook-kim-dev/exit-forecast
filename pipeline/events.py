# 올림픽공원 공연 일정 → 일자별 (공연장, 시작시각, 규모) 테이블
import json, re, os, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'state')

VENUES = {  # code: (이름, 수용인원, 기본 소요시간(분), 가까운 게이트)
    'D': ('KSPO DOME', 15000, 150, '동2문'),
    'H': ('티켓링크 라이브 아레나', 5003, 150, '동2문'),
    'O': ('올림픽홀', 2452, 140, '동2문'),
    'W': ('우리금융아트홀', 1184, 150, '남2문'),
    'M': ('뮤즈라이브', 237, 120, '동2문'),
    'K': ('K-아트홀', 500, 90, '남2문'),
    'G': ('88잔디마당', 10000, 480, '남2문'),
}
def venue_code(p):
    p = p or ''
    if 'KSPO' in p or '체조' in p: return 'D'
    if '핸드볼' in p or '티켓링크' in p: return 'H'
    if '뮤즈' in p: return 'M'
    if '올림픽홀' in p: return 'O'
    if '우리금융' in p or '역도' in p: return 'W'
    if 'K-아트' in p or '태권도' in p: return 'K'
    if '88' in p or '잔디' in p or '수변' in p: return 'G'
    return None

DOW = {'월': 0, '화': 1, '수': 2, '목': 3, '금': 4, '토': 5, '일': 6}
EN = {'MON': 0, 'TUE': 1, 'WED': 2, 'THU': 3, 'FRI': 4, 'SAT': 5, 'SUN': 6}
TIME_PATS = [
    re.compile(r'(오후|오전)?\s*(\d{1,2})\s*:\s*(\d{2})()'),
    re.compile(r'(오후|오전)?\s*(\d{1,2})\s*시(?:\s*(\d{1,2})\s*분)?()'),
    re.compile(r'()(\d{1,2})(?::(\d{2}))?\s*(PM|AM|pm|am)'),
]
def _times(tm):
    out = []; used = set()
    for pat in TIME_PATS:
        for m in pat.finditer(tm):
            if any(i in used for i in range(m.start(), m.end())): continue
            ap, h, mi, pm = m.group(1), int(m.group(2)), m.group(3), m.group(4)
            if h > 24: continue
            mi = int(mi) if mi else 0
            if mi >= 60: continue
            if (ap == '오후' or (pm and pm.lower() == 'pm')) and h < 12: h += 12
            elif not ap and not pm and h < 10: h += 12
            out.append((m.start(), h, mi)); used.update(range(m.start(), m.end()))
    return sorted(out)

def start_for(tm, d):
    """해당 날짜 d의 시작시각과 파싱 방식 반환"""
    tm = (tm or '').replace('\u200b', ' ')
    ts = _times(tm)
    if not ts: return None, 'none'
    # 각 시간 앞의 맥락(이전 시간 이후 ~ 현재 시간 전)에서 날짜/요일 단서 찾기
    prev = 0; cands = []
    for pos, h, mi in ts:
        ctx = tm[prev:pos]; prev = pos + 1
        days = [int(x) for x in re.findall(r'(\d{1,2})\s*일', ctx)] + [int(x) for x in re.findall(r'(?:^|[^\d.])(\d{1,2})\s*\(', ctx)]
        days += [int(m2.group(3)) for m2 in re.finditer(r'(\d{4})[./](\d{1,2})[./](\d{1,2})', ctx)]
        days += [int(m2.group(2)) for m2 in re.finditer(r'(?:^|[^\d.])(\d{1,2})[./](\d{1,2})(?![\d])', ctx) if not re.search(r'\d{4}[./]$', ctx[:m2.start()+1])]
        wds = [DOW[x] for x in re.findall(r'(월|화|수|목|금|토|일)\s*(?:요일)?', ctx) if x in DOW]
        wds += [EN[x.upper()] for x in re.findall(r'(MON|TUE|WED|THU|FRI|SAT|SUN)', ctx, flags=re.I)]
        cands.append((h, mi, days, wds))
    # 1) 일자 일치
    hit = [(h, mi) for h, mi, days, wds in cands if d.day in days]
    if hit: h, mi = max(hit); return dt.datetime.combine(d, dt.time(h % 24, mi)), 'day'
    # 2) 요일 일치(같은 요일 여러 회차면 마지막 회차)
    hit = []
    for k, (h, mi, days, wds) in enumerate(cands):
        if wds and d.weekday() in wds and not days: hit.append((h, mi))
        elif not wds and not days and k > 0 and cands[k-1][3] and d.weekday() in cands[k-1][3]: hit.append((h, mi))
    if hit: h, mi = max(hit); return dt.datetime.combine(d, dt.time(h % 24, mi)), 'weekday'
    for h, mi, days, wds in cands:
        if wds and d.weekday() == wds[-1]: return dt.datetime.combine(d, dt.time(h % 24, mi)), 'weekday2'
    # 3) 시간이 하나뿐이거나 모두 같으면 그 시간
    uniq = {(h, mi) for h, mi, _, _ in cands}
    if len(uniq) == 1:
        h, mi = uniq.pop(); return dt.datetime.combine(d, dt.time(h % 24, mi)), 'single'
    # 4) 첫 시간(낮 공연 여러 회차면 마지막 회차가 퇴장에 중요 → 저녁 회차 우선)
    eve = [c for c in cands if c[0] >= 17]
    h, mi = (eve[-1][:2] if eve else cands[0][:2])
    return dt.datetime.combine(d, dt.time(h % 24, mi)), 'fallback'

def load_shows(year_from=2023, year_to=2026):
    ev = json.load(open(os.path.join(DATA, '올림픽공원_공연일정_2023_2026.json'), encoding='utf-8'))
    rows = []
    for e in ev:
        v = venue_code(e['plc'])
        if not v: continue
        try:
            b = dt.date.fromisoformat(e['b']); en = dt.date.fromisoformat(e['e'])
        except Exception:
            continue
        long_run = (en - b).days > 10
        d = b
        while d <= en:
            if year_from <= d.year <= year_to:
                s, how = start_for(e.get('tm'), d)
                if long_run and v in ('W', 'M', 'K'):
                    pass  # 장기 공연(뮤지컬·가족극)은 포함하되 규모 작음
                if not (long_run and v in ('D', 'H', 'O')):
                    rows.append({'date': d, 'venue': v, 'start': s, 'how': how, 'title': e['title'], 'cap': VENUES[v][1], 'dur': VENUES[v][2], 'long_run': long_run, 'seq': e['seq']})
            d += dt.timedelta(1)
    # 같은 날·같은 공연장 중복 제거(가장 늦은 시작 = 퇴장 기준)
    best = {}
    for r in rows:
        k = (r['date'], r['venue'])
        if k not in best or (r['start'] and (not best[k]['start'] or r['start'] > best[k]['start'])): best[k] = r
    return sorted(best.values(), key=lambda r: (r['date'], r['venue']))

if __name__ == '__main__':
    import collections
    rows = load_shows()
    print(len(rows), collections.Counter(r['how'] for r in rows))
    for r in [x for x in rows if x['how'] in ('fallback', 'none')][:15]:
        print(r['date'], r['venue'], r['how'], r['start'], r['title'][:30])
    for r in [x for x in rows if x['date'] >= dt.date(2026, 11, 18)][:20]:
        print(r['date'], r['venue'], r['start'], r['how'], r['title'][:40])
