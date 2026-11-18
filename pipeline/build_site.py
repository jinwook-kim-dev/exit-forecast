# 퇴장예보: 모델 결과 + 공연 일정 + 날씨 예보 + 실시간 기록 → site/data/*.json
import json, os, csv, math, re, datetime as dt, collections, urllib.request
import numpy as np
from events import load_shows, VENUES
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..'); DATA = os.path.join(HERE, 'state'); RES = os.path.join(HERE, 'params'); SITE = os.path.join(ROOT, 'docs', 'data')
STATE = os.path.join(HERE, 'state')
os.makedirs(SITE, exist_ok=True)
KST = dt.timezone(dt.timedelta(hours=9))
NOW = dt.datetime.now(KST).replace(tzinfo=None)
CAP_TOTAL = 2800   # 기관 FAQ "주차장 2,800여 대"
CAP_MAIN = 2200    # 기관 예상이용률 서비스 표기(동2·남2·북2문)
VERSION = 'v0.9 (2024-07 원자료·2025 연계 기반 예비 파라미터)'

# ---------- 파라미터(최종 학습 결과가 있으면 덮어씀) ----------
P = {
  'rush_center_min': {'D': 205, 'H': 240, 'O': 190, 'W': 170, 'M': 140, 'K': 110, 'G': 0},
  'rush_sd_min': {'D': 28, 'H': 28, 'O': 25, 'W': 25, 'M': 20, 'K': 20, 'G': 60},
  'cars_per_1000': {'D': 26, 'H': 50, 'O': 60, 'W': 40, 'M': 60, 'K': 40, 'G': 15},  # 공연 관객 차량(동2·남2·북2문 기준, 2024-07 중앙값)
  'cars_range_per_1000': {'D': [14, 91]},
  'gate_share_D': {'동2문': 0.35, '북2문': 0.31, '남2문': 0.28, '기타': 0.06},
  'gate_share_S': {'동2문': 0.25, '북2문': 0.15, '남2문': 0.50, '기타': 0.10},
  'delay_p50': 74, 'delay_p90': 116,  # 러시 시작 기준 관객 차량 출차 지연(분), 2024-07 KSPO 중앙값
  'station_excess_per_1000': {'올림픽공원': {'-1': 11.5, '0': 30.8, '1': 12.0}, '몽촌토성': {'0': 0.5}, '방이': {'0': 1.0}},
}
pf = os.path.join(RES, 'final_params.json')
if os.path.exists(pf): P.update(json.load(open(pf, encoding='utf-8'))); VERSION = P.get('version', VERSION)

AN = json.load(open(os.path.join(RES, 'analog_params.json'), encoding='utf-8')) if os.path.exists(os.path.join(RES, 'analog_params.json')) else None
from analog import dclass
def interp_offset(tab, off_h):
    lo = math.floor(off_h); hi = lo + 1; f = off_h - lo
    a = tab.get(str(lo)); b = tab.get(str(hi))
    if a is None and b is None: return None
    if a is None: return b
    if b is None: return a
    return [a[k] + (b[k] - a[k]) * f for k in range(3)]

GEO = {'KSPO DOME': (37.5192242, 127.1274696), '올림픽홀': (37.514747, 127.1275894), '우리금융아트홀': (37.5167377, 127.1250518), '티켓링크 라이브 아레나': (37.5183, 127.1255),
       '올림픽공원역': (37.5165221, 127.1308904), '몽촌토성역': (37.5185895, 127.1131442), '방이역': (37.5088199, 127.1264659), '한성백제역': (37.5165, 127.1162)}
def walk_min(a, b):
    (la1, lo1), (la2, lo2) = GEO[a], GEO[b]
    dy = (la2 - la1) * 111000; dx = (lo2 - lo1) * 111000 * math.cos(math.radians(la1))
    return round(math.hypot(dx, dy) * 1.3 / 75)

# ---------- 기본 재차 프로필(2025 연계, 순재차 = 표시값 - 새벽 바닥값) ----------
def base_profile():
    rows = collections.defaultdict(dict)
    for l in open(os.path.join(DATA, 'raw_API_CPM_009.jsonl'), encoding='utf-8'):
        r = json.loads(l)
        if not r['LOCAL_ID'].isdigit(): continue
        m = re.search(r'주차대수:(\d+)', r['DESCRIPTION']); sh = re.search(r'공연명:([^,]*)', r['DESCRIPTION'])
        if not m: continue
        t = dt.datetime.fromisoformat(r['ISSUED_DATE']); rows[t.date()][t.hour] = (int(m.group(1)), (sh.group(1).strip() if sh else ''))
    prof = collections.defaultdict(list)
    for d, hrs in rows.items():
        night = [hrs[h][0] for h in (2, 3, 4) if h in hrs]
        if not night or any(v[1] for v in hrs.values()): continue  # 공연 없는 날만
        fl = min(night); t = 2 if d.weekday() == 6 else (1 if d.weekday() == 5 else 0)
        for h, (v, _) in hrs.items(): prof[(t, h)].append(v - fl)
    return {k: float(np.median(v)) for k, v in prof.items()}

def base_exits():
    p = os.path.join(RES, 'm2_results.json')
    if os.path.exists(p):
        b = json.load(open(p, encoding='utf-8')).get('base_exit15', {})
        if b: return {int(k): v for k, v in b.items()}
    return None

def weather():
    try:
        u = 'https://api.open-meteo.com/v1/forecast?latitude=37.519&longitude=127.124&hourly=temperature_2m,precipitation&timezone=Asia%2FSeoul&forecast_days=16'
        w = json.loads(urllib.request.urlopen(u, timeout=20).read())
        out = {}
        for t, temp, pr in zip(w['hourly']['time'], w['hourly']['temperature_2m'], w['hourly']['precipitation']):
            out[dt.datetime.fromisoformat(t)] = (temp, pr or 0)
        return out
    except Exception as e:
        print('weather fail', e); return {}

SLOTS = [f'{h:02d}:{m:02d}' for h in range(12, 24) for m in (0, 15, 30, 45)]
def slot_dt(d, i): return dt.datetime.combine(d, dt.time(12 + i // 4, (i % 4) * 15))

def gauss_bins(center_dt, sd_min, total, d):
    out = np.zeros(len(SLOTS))
    for i in range(len(SLOTS)):
        t0 = slot_dt(d, i); mid = t0 + dt.timedelta(minutes=7.5)
        z = (mid - center_dt).total_seconds() / 60 / sd_min
        out[i] = math.exp(-0.5 * z * z)
    s = out.sum(); return out / s * total if s > 0 else out

def level_from_excess(x):
    return 3 if x >= 400 else 2 if x >= 200 else 1 if x >= 80 else 0

def build_days(shows, prof, bex, wx):
    days = []
    start = NOW.date()
    for k in range(0, 18):
        d = start + dt.timedelta(k)
        ds = [s for s in shows if s['date'] == d and s['start'] is not None and s['venue'] != 'G' or (s['date'] == d and s['venue'] == 'G' and s['start'] is not None)]
        dtp = 2 if d.weekday() == 6 else (1 if d.weekday() == 5 else 0)
        # 공연별 파라미터
        sh_out = []; exits_ev = np.zeros(len(SLOTS)); occ_ev = np.zeros(len(SLOTS)); gates = {'동2문': np.zeros(len(SLOTS)), '북2문': np.zeros(len(SLOTS)), '남2문': np.zeros(len(SLOTS)), '기타': np.zeros(len(SLOTS))}
        for s in ds:
            v = s['venue']; rc = s['start'] + dt.timedelta(minutes=P['rush_center_min'][v]) if v != 'G' else s['start'] + dt.timedelta(hours=8)
            end_est = rc - dt.timedelta(minutes=P['rush_sd_min'][v] + 10)
            cars = P['cars_per_1000'][v] * s['cap'] / 1000
            w = gauss_bins(rc, P['rush_sd_min'][v], cars, d)
            exits_ev += w
            share = P['gate_share_D'] if v in ('D', 'H', 'O', 'M') else P['gate_share_S']
            for g, f in share.items(): gates[g] += w * f
            # 재차: 시작 3시간 전부터 도착, 러시 중심까지 유지 후 감소
            for i in range(len(SLOTS)):
                t = slot_dt(d, i)
                arr = min(1.0, max(0.0, ((t - (s['start'] - dt.timedelta(hours=3))).total_seconds() / 3600) / 3.0))
                left = float(np.sum(w[:i + 1])) / cars if cars else 0
                occ_ev[i] += cars * arr * (1 - min(1, left)) if t < rc + dt.timedelta(hours=2) else 0
            ei = None
            if end_est.date() == d and end_est.hour >= 12: ei = (end_est.hour - 12) * 4 + end_est.minute // 15
            sh_out.append({'v': v, 'venue': VENUES[v][0], 'title': s['title'], 'start': s['start'].strftime('%H:%M'), 'end_est': end_est.strftime('%H:%M'), 'rush': rc.strftime('%H:%M'), 'cap': s['cap'], 'cars_est': round(cars), 'end_idx': ei, 'how': s['how']})
        # 유사일 예보(재차)
        cls = dclass(d, [x for x in ds if x['start'] is not None])
        an_occ = None; an_lo = None; an_hi = None; an_ex = None
        big = [x for x in ds if x['venue'] in ('D', 'H', 'O')]
        if AN and big:
            mainb = max(big, key=lambda x: x['cap']); shh = mainb['start'].hour + mainb['start'].minute / 60
            tab = AN['occ']['occ_offset'].get(cls) or AN['occ']['occ_offset'].get(cls.replace('M', '')) or {}
            vals = [interp_offset(tab, (12 + i / 4) - shh) for i in range(len(SLOTS))]
            if all(v is not None for v in vals):
                an_lo = [round(v[0]) for v in vals]; an_occ = [round(v[1]) for v in vals]; an_hi = [round(v[2]) for v in vals]
            etab = AN['exit']['exit_offset'].get(cls) or AN['exit']['exit_offset'].get(cls.replace('M', ''))
            if etab:
                sb = mainb['start'].hour * 4 + mainb['start'].minute // 15
                an_ex = [etab.get(str(48 + i - sb), [None, None, None])[1] for i in range(len(SLOTS))]
        an_n = (AN or {}).get('occ', {}).get('n', {}).get(cls)
        # 기본 재차·날씨
        occ_base = []
        for i in range(len(SLOTS)):
            t = slot_dt(d, i); h = t.hour
            b = prof.get((dtp, h), prof.get((0, h), 0))
            b2 = prof.get((dtp, min(23, h + 1)), b); b = b + (b2 - b) * (t.minute / 60)
            temp, pr = wx.get(t.replace(minute=0), (None, 0))
            if pr and 9 <= h <= 19: b = max(0, b - 85 - 27 * min(pr, 20))
            occ_base.append(b)
        occ = an_occ if an_occ else [round(a + b) for a, b in zip(occ_base, occ_ev)]
        exb = [round(bex[dtp][48 + i], 1) if bex and dtp in bex else None for i in range(len(SLOTS))] if bex else None
        base_ex = np.array([x or 0 for x in exb]) if exb else np.zeros(len(SLOTS))
        tot_gates = {g: [round(float(v + base_ex[i] * (0.33 if g != '기타' else 0.01))) for i, v in enumerate(arr)] for g, arr in gates.items()}
        exits = [round(float(exits_ev[i] + base_ex[i])) for i in range(len(SLOTS))]
        if an_ex and sum(1 for x in an_ex if x is not None) > 20:
            exits = [round(x) if x is not None else exits[i] for i, x in enumerate(an_ex)]
            tot = sum(exits_ev) + sum(base_ex) or 1
            for g in tot_gates:
                sh_g = (sum(tot_gates[g]) / max(1, sum(sum(v) for v in tot_gates.values())))
                tot_gates[g] = [round(e * sh_g) for e in exits]
        # 차량 안내
        car = {}
        pi = int(np.argmax(occ)); car['occ_peak_t'] = SLOTS[pi]; car['occ_peak_pct'] = round(occ[pi] / CAP_TOTAL * 100)
        if an_hi: hi_i = int(np.argmax(an_hi)); car['occ_hi_pct'] = round(an_hi[hi_i] / CAP_TOTAL * 100); car['occ_hi_t'] = SLOTS[hi_i]
        risk_i = next((i for i, v in enumerate(an_hi or occ) if v >= 0.8 * CAP_TOTAL), None)
        if risk_i is not None: car['full_at'] = SLOTS[risk_i]; car['arrive_by'] = SLOTS[max(0, risk_i - 4)]
        if ds:
            main = max(sh_out, key=lambda x: x['cars_est'])
            win = [i for i in range(len(SLOTS)) if exits_ev[i] > 0.05 * max(exits_ev.max(), 1)]
            pk = int(np.argmax(exits)) if exits_ev.max() > 5 else None
            if pk is not None:
                car['exit_peak'] = SLOTS[pk]; car['exit_peak_cars'] = int(exits[pk])
                after = next((i for i in range(pk, len(SLOTS)) if exits[i] <= 0.5 * exits[pk]), None)
                car['leave_after'] = SLOTS[after] if after is not None else '24:00 이후'
                # 덜 붐비는 출구: 피크 구간 게이트 차량/차로 2개 기준 최소
                car['best_gate'] = min(['동2문', '북2문', '남2문'], key=lambda g: tot_gates[g][pk])
            car['basis'] = f'유사 공연일 {an_n}회' if an_n else '기본 파라미터'; car['band'] = [an_lo, an_hi] if an_lo else None
            tips = [f"예보 근거: 같은 요일형·공연장 조합의 2025년 유사 공연일 {an_n or '-'}회 중앙값(범위 25~75%). 같은 KSPO 공연도 관객층에 따라 차량 수가 크게 다릅니다.",
                    f"출차 러시는 {main['rush']} 전후에 몰립니다. {car.get('leave_after', '')} 이후 출차하면 덜 붐빕니다.",
                    "10분 이내 출차는 무료입니다. 만차 시간대에 들어왔다 나가는 '헛걸음' 차량이 늘어나니 도착 시각을 앞당기세요.",
                    "투어 2·3일차는 1일차 실측으로 예보를 보정합니다."]
            if len({x['v'] for x in sh_out if x['v'] in ('D', 'H', 'O')}) >= 2: tips.insert(0, '두 곳 이상의 대형 공연장이 같은 날 공연합니다. 퇴장 시간이 겹칠 수 있습니다.')
            car['tips'] = tips
        else:
            car['tips'] = ['대형 공연이 없는 날입니다. 평일 오전 8~10시는 출근·스포츠센터 이용으로 주차가 빠르게 찹니다.']
        # 충돌 지수
        ends = sorted([(dt.datetime.strptime(x['end_est'], '%H:%M'), x['cap'], x['venue']) for x in sh_out if x['v'] in ('D', 'H', 'O', 'W')])
        people = 0
        for i, (t0, c0, v0) in enumerate(ends):
            ppl = sum(c for t, c, v in ends if abs((t - t0).total_seconds()) <= 30 * 60); people = max(people, ppl)
        lvl = 3 if people > 18000 else 2 if people > 12000 else 1 if people > 4000 else 0
        conflict = {'level': lvl, 'people': people, 'text': f'퇴장 예정 30분 창 최대 {people:,}명' if people else '대형 공연 없음'}
        # 역 혼잡
        stations = []
        if ds:
            caps = sum(x['cap'] for x in sh_out if x['v'] in ('D', 'H', 'O'))
            rc_main = max(sh_out, key=lambda x: x['cap'])['rush']; rch = int(rc_main[:2])
            hours = [f'{h:02d}:00' for h in range(max(17, rch - 1), min(24, rch + 3))]
            for nm, key, line, note in [('올림픽공원역', '올림픽공원', '5·9호선', '공연장 바로 앞(3번 출구). 공연 후 승차가 몰림'), ('한성백제역', None, '9호선', '9호선 승하차 자료 미개방으로 혼잡 추정 제외'), ('몽촌토성역', '몽촌토성', '8호선', '평화의문 쪽. 공연일에도 평소 수준'), ('방이역', '방이', '5호선', '남쪽 방향. 공연일에도 평소 수준')]:
                walk = walk_min('KSPO DOME', nm)
                levels = []
                for hstr in hours:
                    off = str(int(hstr[:2]) - rch)
                    if key is None: levels.append({'t': hstr, 'lv': -1, 'est': None}); continue
                    ex = P['station_excess_per_1000'].get(key, {}).get(off, 0) * caps / 1000
                    levels.append({'t': hstr, 'lv': level_from_excess(ex), 'est': round(ex)})
                pk = max(levels, key=lambda x: x['lv'])
                stations.append({'name': f'{nm} ({line})', 'walk_min': walk, 'levels': levels, 'peak_lv': pk['lv'], 'peak_t': pk['t'], 'note': note})
        transit_tips = {
            'ko': ['평화의광장 안내센터 유료 보관함은 19시에 닫습니다. 저녁 공연이면 역 물품보관함이나 짐보관 서비스를 이용하세요.', '공연 직후 올림픽공원역이 가장 붐빕니다. 한성백제역(9호선)·몽촌토성역(8호선)·방이역(5호선)은 도보 18~22분이지만 평소 수준입니다.', '분실물: 공연장 내부 분실물은 각 공연 기획사, 공원 안내센터(02-410-1114), 경찰청 LOST112를 함께 확인하세요.'],
            'en': ['Park info-center lockers close at 19:00. For evening shows, use station lockers or a luggage service.', 'Olympic Park Station is busiest right after the show. Hanseong Baekje (L9), Mongchontoseong (L8) and Bangi (L5) are an 18-22 min walk but stay at normal levels.', 'Lost items: check the promoter, the park info center (+82-2-410-1114) and LOST112.'],
            'ja': ['平和の広場案内センターのロッカーは19時に閉まります。夜公演は駅のロッカーをご利用ください。', '終演直後はオリンピック公園駅が最も混雑します。漢城百済駅(9号線)・夢村土城駅(8号線)・芳荑駅(5号線)は徒歩18〜22分ですが普段どおりです。', '落とし物: 主催者、公園案内センター(02-410-1114)、LOST112をご確認ください。'],
            'zh': ['和平广场服务中心的寄存柜19点关闭。晚场演出请使用地铁站寄存柜。', '散场后奥林匹克公园站最拥挤。汉城百济站(9号线)、梦村土城站(8号线)、芳荑站(5号线)步行18~22分钟，但客流正常。', '失物: 请联系主办方、公园服务中心(02-410-1114)和LOST112。'],
        }
        # 운영
        ops = {'recs': []}
        if ds:
            pk = int(np.argmax(exits)); s0 = max(0, pk - 2); s1 = min(len(SLOTS) - 1, pk + 3)
            ops['lanes_window'] = f'{SLOTS[s0]}~{SLOTS[s1]}'; ops['lanes_note'] = '출차 러시 ±45분'
            ops['recs'] = [f'{SLOTS[s0]}~{SLOTS[s1]} 동2·북2·남2문 정산 차로 전면 개방, 출구 유도 인력 배치',
                           f'공연 종료 30분 창 최대 {people:,}명 퇴장 예상. 올림픽공원역 3번 출구 동선 분리, 9호선·5호선 승강장 안내',
                           '한성백제역·몽촌토성역·방이역 분산 안내판(도보 시간 표기)을 퇴장 동선에 배치']
            if lvl >= 2: ops['recs'].append('동시 종료가 예상됩니다. 기획사와 종료 시각 15~20분 차등을 협의하면 피크가 낮아집니다(사전 시뮬레이션 제공 가능).')
        wtxt = None
        days.append({'date': d.isoformat(), 'dow': '월화수목금토일'[d.weekday()], 'shows': sh_out, 'conflict': conflict, 'slots': SLOTS,
                     'occ': occ, 'occ_lo': an_lo, 'occ_hi': an_hi, 'occ_base': [round(x) for x in occ_base], 'class': cls, 'analog_n': an_n, 'exits': exits, 'exits_base': [round(x, 1) for x in base_ex], 'gates': tot_gates,
                     'car': car, 'stations': stations, 'transit_tips': transit_tips, 'ops': ops})
    return days

def realtime():
    p = os.path.join(STATE, 'realtime.csv')
    if not os.path.exists(p): return None
    rows = [(dt.datetime.fromisoformat(r['ts']), int(r['parking_count'])) for r in csv.DictReader(open(p)) if r['parking_count']]
    if not rows: return None
    last_t, last_v = rows[-1]
    night = [v for t, v in rows if t.date() == last_t.date() and 2 <= t.hour < 5] or [v for t, v in rows if (last_t - t).total_seconds() < 86400 and 2 <= t.hour < 5]
    floor = min(night) if night else min(v for t, v in rows)
    def fl_for(t):
        n = [v for tt, v in rows if tt.date() == t.date() and 2 <= tt.hour < 5]
        return min(n) if n else floor
    hist = [[t.isoformat(sep=' ')[:16], v, max(0, v - fl_for(t))] for t, v in rows if (last_t - t).total_seconds() <= 48 * 3600]
    hist = hist[::2] if len(hist) > 300 else hist
    agency = []
    pp = os.path.join(STATE, 'predictions.csv')
    if os.path.exists(pp):
        pr = list(csv.DictReader(open(pp)))
        if pr:
            lastf = pr[-1]['fetched_ts']
            agency = [{'date': r['date'], 'slot': r['slot'], 'pct': int(r['pred_pct'])} for r in pr if r['fetched_ts'] == lastf]
    return {'ts': last_t.isoformat(sep=' ')[:16], 'raw': last_v, 'floor': floor, 'corrected': max(0, last_v - floor), 'cap': CAP_MAIN, 'hist': hist, 'agency': agency,
            'agency_pct': agency[0]['pct'] if agency else None, 'agency_note': '주말 입차 기준 단일값' if agency else ''}

QUALITY = [
 ('Q1', '주차장 혼잡도(파일)', '등록시간의 분:초가 등록일의 월:일과 같음', '699/699행 (예: 2026-08-12 → 17:08:12)', '시각 포맷 수정, 실제 시간 해상도 명시'),
 ('Q2', '입출차·공연·날씨 연계(API)', '방문객 = 주차대수×3 또는 ×5 고정배수', '유효 7,303행 전수(×3 4,867행, ×5 2,436행)', '방문객 산식 공개 또는 실측 방문객 연계'),
 ('Q3', '입출차 2024-07(파일) vs 월별주차현황', '같은 달 215,528건 vs 59,808대', '두 파일 직접 비교(3.6배)', '집계 정의(무료 10분 출차·정기권 포함 여부) 메타데이터화'),
 ('Q4', '실시간 주차현황', '새벽에도 약 1,080대가 빠지지 않음', '2026-11-18 00~05시 기록 1,081~1,095대, 2024-07 원자료 23시 실재차 82~190대', '미출차 기록 자동 마감 규칙(예: 24시간 경과)'),
 ('Q5', '공연정보', '공연장명 표기 40종 이상(핸드볼경기장만 15종 이상)', '공연 508건 직접 집계', '공연장 코드 표준화'),
 ('Q6', '스포츠센터 월회원 이용현황(API)', '설명은 2025년 6월 기준이나 실제 범위 2013~2015', '포털 설명문', '적시성 갱신'),
 ('Q7', '입출차 2024-07(파일)', '설명에는 구역이 있으나 구역 컬럼 없음', '헤더 3개(입차일, 입차일시, 출차일시)', '게이트·차로 컬럼 추가(2025 API처럼)'),
 ('Q8', '주차장 예상 이용률 서비스', '공식 일정에 없는 공연이 함께 표시, 모든 30분 슬롯 예측값 동일(89%)', '2026-11-17~ 기록(11/21·22 화면)', '공연 일정 정합성 점검, 슬롯별 예측'),
 ('Q9', '연계 API 응답', '다른 데이터(입출차 원자료) 600건 혼입, 일부는 입차시간 칸에 게이트명', 'API_CPM_009 전량 수집 결과', '응답 필터링, 필드 검증'),
 ('Q10', '대관·운영현황·유실물(문화공공데이터광장)', '데이터 수정일 2020-12~2021-01에서 멈춤, 유실물은 공지 목록만', '포털 메타는 2026-09 수정으로 표시', '갱신 또는 메타 정정'),
 ('Q11', '연계 API 페이지네이션', '같은 요청에서 페이지 간 중복·누락 발생(7,803건 중 7,303건 확보)', '500건×16페이지 수집 결과', '정렬 키 고정 페이지네이션'),
]
DATASETS = [
 ('올림픽공원 입출차정보 2025(전체 게이트·차로, 약 241만 건)', '한국체육산업개발', 'API(API_CPM_008)', '출차 웨이브·차로 처리량·공연 관객 차량 추정', 'https://www.culture.go.kr/data/openapi/openapiView.do?id=659&gubun=A'),
 ('올림픽공원 2025 차량입출차·공연·날씨 연계', '한국체육산업개발', 'API(API_CPM_009)', '시간별 재차·날씨 효과·미출차 바닥값', 'https://www.culture.go.kr/data/openapi/openapiView.do?id=675&gubun=A'),
 ('올림픽공원 입출차 정보(2024-07, 215,528건)', '한국체육산업개발', '파일', '공연일 출차 곡선·헛걸음 지수', 'https://www.data.go.kr/data/15138735/fileData.do'),
 ('실시간 주차현황 / 주차장 예상 이용률 서비스', '한국체육산업개발', 'API·웹', '보정 실시간 주차, 기관 예보 비교', 'https://www.data.go.kr/data/15168686/openapi.do'),
 ('주차장 혼잡도 정보(P1A~P11)', '한국체육산업개발', '파일', '구역별 만차 기록 검증', 'https://www.data.go.kr/data/15164156/fileData.do'),
 ('올림픽공원 공연정보·일정', '한국체육산업개발', 'API·웹', '공연 시작시각·공연장·규모', 'https://www.data.go.kr/data/3037877/openapi.do'),
 ('영문 공연정보', '한국체육산업개발', '파일', '해외 관람객 안내 문구', 'https://www.data.go.kr/data/15149169/fileData.do'),
 ('월별주차현황', '한국체육산업개발', '파일', '월 단위 수요 검증', 'https://www.data.go.kr/data/15131671/fileData.do'),
 ('자주 묻는 질문정보', '한국체육산업개발', '파일', '안내 문구(주차요금, 무료 10분 등)', 'https://www.data.go.kr/data/15089962/fileData.do'),
 ('역별 일별 시간대별 승하차인원(2024)', '서울교통공사', '파일', '공연 후 역별 혼잡 추정', 'https://data.seoul.go.kr/dataList/OA-12921/A/1/datasetView.do'),
 ('단기 기상 예보(Open-Meteo, 기상청 단기예보로 교체 예정)', '기상청 외', 'API', '강수·기온 보정', 'https://open-meteo.com/'),
]

def endtimes():
    p = os.path.join(RES, 'm2_delay_202407.json')
    out = []
    if os.path.exists(p):
        for r in json.load(open(p, encoding='utf-8')):
            st = dt.datetime.strptime(r['date'] + ' ' + r['start'], '%Y-%m-%d %H:%M')
            out.append({'date': r['date'], 'dow': r['dow'], 'venue': VENUES[r['v']][0], 'title': r['title'], 'start': r['start'], 'exit_start': (st + dt.timedelta(minutes=r['rush_center_min'] - 35)).strftime('%H:%M'), 'peak': (st + dt.timedelta(minutes=r['rush_center_min'])).strftime('%H:%M'), 'cars': r['cars']})
    fin = os.path.join(RES, 'final_endtimes.json')
    if os.path.exists(fin): out = json.load(open(fin, encoding='utf-8'))
    return out

def accuracy():
    fa = os.path.join(RES, 'final_accuracy.json')
    if os.path.exists(fa): return json.load(open(fa, encoding='utf-8'))
    bt = json.load(open(os.path.join(RES, 'final_backtest.json'), encoding='utf-8'))
    m1 = json.load(open(os.path.join(RES, 'm1_results.json'), encoding='utf-8'))
    imp = round((1 - bt['blend'] / bt['naive7']) * 100); imp2 = round((1 - bt['blend'] / bt['analog']) * 100)
    ser = json.load(open(os.path.join(RES, 'm1_test_series.json')))
    byd = collections.defaultdict(list)
    for x in ser: byd[x['t'][:10]].append(x)
    shows = load_shows(2025, 2025); sd = {s['date'].isoformat(): s for s in shows if s['venue'] == 'D'}
    ex_day = next((d for d in sorted(byd) if d in sd and len(byd[d]) >= 20), None)
    example = None
    if ex_day:
        xs = sorted(byd[ex_day], key=lambda x: x['t'])
        example = {'date': ex_day, 'title': f"{ex_day} {sd[ex_day]['title'][:20]}", 'slots': [x['t'][11:16] for x in xs], 'actual': [round(x['y']) for x in xs], 'pred': [round(x['pred']) for x in xs], 'naive': [None if x['sn'] is None else round(x['sn']) for x in xs]}
    live = []
    lv = os.path.join(RES, 'live_validation.json')
    if os.path.exists(lv): live = json.load(open(lv, encoding='utf-8'))
    return {'headline': f"투어 보정 오차 {bt['blend']:.0f}대(-{imp}%)", 'cards': [
        {'k': '공연일 12~22시 재차 오차(투어 보정)', 'v': f"{bt['blend']:.0f}대", 's': f"1주 전 같은 시각 대비 {imp}% · 유사일만 대비 {imp2}% 개선", 'cls': 'grn'},
        {'k': '검증 표본', 'v': f"{bt['n_days']}일 · {bt['n_hours']}시간", 's': '2025 투어 2일차 이후 공연일, 하루씩 제외 검증'},
        {'k': 'KSPO DOME 출차 러시 중심', 'v': '시작 후 205분', 's': '2024-07 7회 공연 중앙값(범위 160~215)'},
        {'k': '같은 15,000석 공연의 관객 차량', 'v': '207~1,366대', 's': '관객층에 따라 6.6배 차이 → 투어 1일차 보정', 'cls': 'org'}],
        'metrics': [{'name': '공연일 12~22시 재차(투어 2일차~)', 'model': f"{bt['blend']:.0f}대", 'naive': f"{bt['naive7']:.0f}대", 'profile': f"{bt['analog']:.0f}대(유사일만)", 'n': bt['n_hours']},
                    {'name': '공연일 12~22시 재차(시간대 회귀, 2025-10~12 시험)', 'model': f"{round(m1['test_event_12_22h']['model'][0])}대", 'naive': f"{round(m1['test_event_12_22h']['seasonal_naive'][0])}대", 'profile': f"{round(m1['test_event_12_22h']['profile'][0])}대", 'n': m1['test_event_12_22h']['model'][1]}],
        'note': bt['method'], 'example': example, 'live': live}

def main():
    shows = load_shows(2025, 2026)
    prof = base_profile(); bex = base_exits(); wx = weather()
    F = {'generated_at': NOW.strftime('%Y-%m-%d %H:%M'), 'version': VERSION, 'capacity': CAP_TOTAL, 'capacity_main': CAP_MAIN, 'days': build_days(shows, prof, bex, wx)}
    json.dump(F, open(os.path.join(SITE, 'forecast.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    rt = realtime()
    if rt:
        # 기관 예측 슬롯에 우리 예보(보정 재차) 붙이기
        dd = {d['date']: d for d in F['days']}
        for a in rt['agency']:
            d = dd.get(a['date'])
            if d and a['slot'] in d['slots']: a['ours'] = d['occ'][d['slots'].index(a['slot'])]
        json.dump(rt, open(os.path.join(SITE, 'realtime.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    json.dump(accuracy(), open(os.path.join(SITE, 'accuracy.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    json.dump([dict(zip(['id', 'ds', 'issue', 'evidence', 'fix'], q)) for q in QUALITY], open(os.path.join(SITE, 'quality.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    json.dump([dict(zip(['name', 'org', 'type', 'use', 'url'], q)) for q in DATASETS], open(os.path.join(SITE, 'datasets.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    E = endtimes(); json.dump(E, open(os.path.join(SITE, 'endtimes.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    with open(os.path.join(SITE, 'endtimes.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f); w.writerow(['날짜', '요일', '공연장', '공연', '공지 시작', '퇴장 시작(추정)', '출차 피크(추정)', '관객 차량(추정)'])
        for e in E: w.writerow([e['date'], e['dow'], e['venue'], e['title'], e['start'], e['exit_start'], e['peak'], e.get('cars', '')])
    print('days', len(F['days']), 'shows', sum(len(d['shows']) for d in F['days']), 'rt', bool(rt), 'weather', len(wx))
    for d in F['days'][:12]:
        print(d['date'], d['dow'], [(s['venue'], s['start'], s['rush'], s['cars_est']) for s in d['shows']], d['car'].get('exit_peak'), d['car'].get('full_at'), d['conflict'])

if __name__ == '__main__':
    main()
