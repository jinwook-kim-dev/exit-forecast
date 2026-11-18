# 유사일(analog) 예보: 같은 요일형·같은 공연장 조합의 과거 공연일을 시작시각 기준으로 정렬해 중앙값·범위를 쓴다
# 재차: 2025 연계 데이터(시간 단위, 순재차) / 출차: 원자료(15분) - 2024-07 + 2025 전량(있으면)
import json, os, re, csv, datetime as dt, collections
import numpy as np
from events import load_shows
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'state'); RES = os.path.join(HERE, 'params')

def dclass(d, ss):
    big = sorted({s['venue'] for s in ss if s['venue'] in ('D', 'H', 'O')})
    wk = 'WE' if (d.weekday() >= 5) else ('FRI' if d.weekday() == 4 else 'WD')
    if 'D' in big: return f'{wk}_D' + ('M' if len(big) >= 2 else '')
    if big: return f'{wk}_HO'
    return f'{wk}_none'

def linked_net():
    rows = collections.defaultdict(dict)
    for l in open(os.path.join(DATA, 'raw_API_CPM_009.jsonl'), encoding='utf-8'):
        r = json.loads(l)
        if not r['LOCAL_ID'].isdigit(): continue
        m = re.search(r'주차대수:(\d+)', r['DESCRIPTION'])
        if m: t = dt.datetime.fromisoformat(r['ISSUED_DATE']); rows[t.date()][t.hour] = int(m.group(1))
    net = {}
    for d, h in rows.items():
        n = [h[x] for x in (2, 3, 4) if x in h]
        if n and len(h) >= 20: net[d] = {k: v - min(n) for k, v in h.items()}
    return net

def build(loo_date=None):
    shows = [s for s in load_shows(2024, 2025) if s['start']]
    byd = collections.defaultdict(list)
    for s in shows: byd[s['date']].append(s)
    net = linked_net()
    occ = collections.defaultdict(list)   # class -> list of {offset_hour: value}
    occ_clock = collections.defaultdict(list)
    for d, h in net.items():
        if d == loo_date or (d.month == 12 and d.day >= 22): continue
        ss = byd.get(d, []); c = dclass(d, ss)
        if c.endswith('none'):
            occ_clock[c].append(h)
        else:
            main = max([s for s in ss if s['venue'] in ('D', 'H', 'O')], key=lambda s: s['cap'])
            sh = main['start'].hour + main['start'].minute / 60
            occ[c].append({round(hr - sh): v for hr, v in h.items()})
    out = {'occ_offset': {}, 'occ_clock': {}, 'n': {}}
    for c, lst in occ.items():
        out['n'][c] = len(lst)
        out['occ_offset'][c] = {str(o): [float(np.percentile([x[o] for x in lst if o in x], q)) for q in (25, 50, 75)] for o in range(-12, 8) if sum(1 for x in lst if o in x) >= 3}
    for c, lst in occ_clock.items():
        out['n'][c] = len(lst)
        out['occ_clock'][c] = {str(h): [float(np.percentile([x[h] for x in lst if h in x], q)) for q in (25, 50, 75)] for h in range(24)}
    return out, net, byd

def exits_analog():
    """원자료 15분 출차를 시작시각 기준(-2h~+6h)으로 정렬, 클래스별 중앙값"""
    F1 = '%Y-%m-%d %H:%M'; F2 = '%Y-%m-%d %H:%M:%S'
    ex = collections.Counter(); ent = collections.Counter(); cov = collections.Counter()
    for r in csv.DictReader(open(os.path.join(DATA, '입출차_202407.csv'), encoding='utf-8')):
        try: a = dt.datetime.strptime(r['입차일시'], F1); b = dt.datetime.strptime(r['출차일시'], F1)
        except Exception: continue
        ex[(b.date(), b.hour * 4 + b.minute // 15)] += 1; cov[(a.date(), a.hour)] += 1
    src = '2024-07'
    p = os.path.join(DATA, '입출차_2025_전체_API.csv')
    full2025 = os.path.exists(os.path.join(HERE, 'cpm008_pages.txt')) and len(open(os.path.join(HERE, 'cpm008_pages.txt')).read().split()) >= 240
    if full2025:
        seen = set(); src = '2024-07 + 2025 전량'
        for r in csv.DictReader(open(p, encoding='utf-8')):
            if r['id'] in seen: continue
            seen.add(r['id'])
            try: a = dt.datetime.strptime(r['in_time'].strip(), F2); b = dt.datetime.strptime(r['out_time'].strip(), F2)
            except Exception: continue
            ex[(b.date(), b.hour * 4 + b.minute // 15)] += 1; cov[(a.date(), a.hour)] += 1
    days = {d for d, h in cov}
    full = {d for d in days if all(cov[(d, h)] >= 20 for h in range(7, 22))}
    shows = [s for s in load_shows(2024, 2025) if s['start'] and s['date'] in full]
    byd = collections.defaultdict(list)
    for s in shows: byd[s['date']].append(s)
    cl = collections.defaultdict(list); clock = collections.defaultdict(list)
    for d in full:
        ss = byd.get(d, []); c = dclass(d, ss)
        if c.endswith('none'): clock[c].append([ex[(d, i)] for i in range(96)]); continue
        main = max([s for s in ss if s['venue'] in ('D', 'H', 'O')], key=lambda s: s['cap'])
        sb = main['start'].hour * 4 + main['start'].minute // 15
        cl[c].append({k: ex[(d, sb + k)] for k in range(-8, 25) if 0 <= sb + k < 96})
    out = {'source': src, 'exit_offset': {}, 'exit_clock': {}, 'n': {}}
    for c, lst in cl.items():
        out['n'][c] = len(lst)
        out['exit_offset'][c] = {str(k): [float(np.percentile([x[k] for x in lst if k in x], q)) for q in (25, 50, 75)] for k in range(-8, 25) if sum(1 for x in lst if k in x) >= 2}
    for c, lst in clock.items():
        out['n'][c] = len(lst)
        out['exit_clock'][c] = [float(np.median([x[i] for x in lst])) for i in range(96)]
    return out

def backtest():
    """재차 유사일 예보 leave-one-out: 2025 공연일 12~22시"""
    base, net, byd = build()
    errs = collections.defaultdict(list)
    for d, h in net.items():
        ss = byd.get(d, []); c = dclass(d, ss)
        if c.endswith('none') or (d.month == 12 and d.day >= 22): continue
        m, _, _ = build(loo_date=d)
        main = max([s for s in ss if s['venue'] in ('D', 'H', 'O')], key=lambda s: s['cap']); sh = main['start'].hour + main['start'].minute / 60
        prev = net.get(d - dt.timedelta(7))
        for hr in range(12, 23):
            if hr not in h: continue
            o = str(round(hr - sh)); p = m['occ_offset'].get(c, {}).get(o)
            if p is None: continue
            errs['analog'].append(abs(p[1] - h[hr]))
            if prev and hr in prev: errs['naive7'].append(abs(prev[hr] - h[hr]))
            inband = p[0] <= h[hr] <= p[2]; errs['band'].append(1 if inband else 0)
    return {k: (round(float(np.mean(v)), 1), len(v)) for k, v in errs.items()}

if __name__ == '__main__':
    occ, _, _ = build(); exa = exits_analog()
    json.dump({'occ': occ, 'exit': exa}, open(os.path.join(RES, 'analog_params.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    print('occ classes', occ['n']); print('exit classes', exa['n'], exa['source'])
    bt = backtest(); print('backtest', bt)
    json.dump(bt, open(os.path.join(RES, 'analog_backtest.json'), 'w'), ensure_ascii=False)

def backtest2():
    base, net, byd = build()
    errs = collections.defaultdict(list); cnt = collections.Counter()
    def key(t): return re.sub(r'[^0-9A-Za-z가-힣]', '', t)[:14]
    for d, h in net.items():
        ss = byd.get(d, []); c = dclass(d, ss)
        if c.endswith('none') or (d.month == 12 and d.day >= 22): continue
        main = max([s for s in ss if s['venue'] in ('D', 'H', 'O')], key=lambda s: s['cap']); sh = main['start'].hour + main['start'].minute / 60
        # 같은 투어 직전 공연일(8일 이내)
        prev = None
        for k in range(1, 9):
            pd = d - dt.timedelta(k)
            for s in byd.get(pd, []):
                if s['venue'] == main['venue'] and key(s['title']) == key(main['title']) and pd in net:
                    prev = (pd, s); break
            if prev: break
        if not prev: continue
        cnt['tour_days'] += 1
        m, _, _ = build(loo_date=d)
        pd, ps = prev; psh = ps['start'].hour + ps['start'].minute / 60
        pnet = {round(hr - psh): v for hr, v in net[pd].items()}
        n7 = net.get(d - dt.timedelta(7))
        for hr in range(12, 23):
            if hr not in h: continue
            o = round(hr - sh); a = m['occ_offset'].get(c, {}).get(str(o)); tp = pnet.get(o)
            if a is None or tp is None: continue
            errs['analog'].append(abs(a[1] - h[hr])); errs['tour_prev'].append(abs(tp - h[hr])); errs['blend'].append(abs(0.3 * a[1] + 0.7 * tp - h[hr]))
            if n7 and hr in n7: errs['naive7'].append(abs(n7[hr] - h[hr]))
    return {k: (round(float(np.mean(v)), 1), len(v)) for k, v in errs.items()}, dict(cnt)

if __name__ == '__main__':
    print('backtest2 (투어 2일차 이후 공연일)', backtest2())
