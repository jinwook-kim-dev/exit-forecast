// 퇴장예보 프런트엔드 (의존성 없음). data/*.json 을 읽어 그린다.
(function () {
  const S = { lang: 'ko', day: 0, F: null, RT: null, ACC: null, Q: null, DS: null, END: null };
  const $ = (s, el = document) => el.querySelector(s);
  const T = (k) => (I18N[S.lang] && I18N[S.lang][k]) || I18N.ko[k] || k;
  const NS = 'http://www.w3.org/2000/svg';
  const VCOL = { D: '#e2463c', H: '#ef8a17', O: '#7c3aed', W: '#15a05a', M: '#0ea5e9', K: '#64748b', G: '#a16207' };
  const LVC = ['l0', 'l1', 'l2', 'l3'];
  const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  async function j(u) { try { const r = await fetch(u, { cache: 'no-store' }); return await r.json(); } catch (e) { return null; } }

  function svg(host, W, H) { host.innerHTML = ''; const s = document.createElementNS(NS, 'svg'); s.setAttribute('viewBox', `0 0 ${W} ${H}`); host.appendChild(s); return s; }
  function el(p, t, a, txt) { const e = document.createElementNS(NS, t); for (const k in a) e.setAttribute(k, a[k]); if (txt != null) e.textContent = txt; p.appendChild(e); return e; }

  function bars(host, labels, series, opt = {}) {
    const W = 760, H = opt.h || 240, L = 42, R = 8, Tp = 10, B = 28; const s = svg(host, W, H);
    const n = labels.length; const stacked = series.reduce((a, se) => a.map((v, i) => v + (se.data[i] || 0)), new Array(n).fill(0));
    const ymax = Math.max(10, ...stacked, ...(opt.lines || []).flatMap((l) => l.data.filter((v) => v != null))) * 1.12;
    const x = (i) => L + (W - L - R) * i / n, bw = (W - L - R) / n * 0.82, y = (v) => Tp + (H - Tp - B) * (1 - v / ymax);
    for (let k = 0; k <= 4; k++) { const v = ymax * k / 4; el(s, 'line', { x1: L, x2: W - R, y1: y(v), y2: y(v), stroke: '#edf0f5' }); el(s, 'text', { x: L - 5, y: y(v) + 4, 'text-anchor': 'end', 'font-size': 10, fill: '#8492a3' }, Math.round(v)); }
    (opt.shade || []).forEach((sh) => { el(s, 'rect', { x: x(sh.from), y: Tp, width: x(sh.to) - x(sh.from), height: H - Tp - B, fill: sh.color || '#1d5bff', opacity: 0.07 }); if (sh.label) el(s, 'text', { x: x(sh.from) + 3, y: Tp + 11, 'font-size': 10, fill: '#4b5b6d' }, sh.label); });
    const acc = new Array(n).fill(0);
    series.forEach((se) => { se.data.forEach((v, i) => { if (!v) return; el(s, 'rect', { x: x(i), y: y(acc[i] + v), width: bw, height: y(acc[i]) - y(acc[i] + v), fill: se.color, rx: 1.5 }); acc[i] += v; }); });
    (opt.lines || []).forEach((l) => { const pts = l.data.map((v, i) => v == null ? null : `${x(i) + bw / 2},${y(v)}`).filter(Boolean).join(' '); el(s, 'polyline', { points: pts, fill: 'none', stroke: l.color, 'stroke-width': l.w || 2, 'stroke-dasharray': l.dash || '' }); });
    const step = Math.ceil(n / 12); labels.forEach((lb, i) => { if (i % step === 0) el(s, 'text', { x: x(i) + bw / 2, y: H - 9, 'text-anchor': 'middle', 'font-size': 10, fill: '#8492a3' }, lb); });
    if (opt.hline) { el(s, 'line', { x1: L, x2: W - R, y1: y(opt.hline.v), y2: y(opt.hline.v), stroke: opt.hline.color || '#e2463c', 'stroke-dasharray': '5 4' }); el(s, 'text', { x: W - R - 2, y: y(opt.hline.v) - 4, 'text-anchor': 'end', 'font-size': 10, fill: opt.hline.color || '#e2463c' }, opt.hline.label || ''); }
  }
  function lines(host, labels, ls, opt = {}) { bars(host, labels, [], Object.assign({}, opt, { lines: ls })); }

  function legend(host, items) { host.innerHTML = items.map((it) => `<span><i style="background:${it.c}"></i>${esc(it.t)}</span>`).join(''); }
  function card(k, v, s, cls) { return `<div class="card ${cls || ''}"><div class="k">${esc(k)}</div><div class="v">${esc(v ?? '-')}</div>${s ? `<div class="s">${esc(s)}</div>` : ''}</div>`; }
  function lvl(n) { if (n < 0) return '<span class="lvl l0">자료 없음</span>'; const names = T('level'); return `<span class="lvl ${LVC[n] || 'l0'}">${esc((Array.isArray(names) ? names : I18N.ko.level)[n] ?? '-')}</span>`; }

  function renderChips() {
    const h = $('#dayChips'); const days = S.F.days;
    h.innerHTML = days.map((d, i) => { const c = d.conflict || { level: 0 }; const col = ['#cbd5e1', '#15a05a', '#ef8a17', '#e2463c'][c.level || 0];
      return `<button class="chip ${i === S.day ? 'on' : ''}" data-i="${i}"><div class="d">${d.date.slice(5).replace('-', '/')} (${esc(d.dow)})</div><div class="n"><span class="lv" style="background:${col}"></span>${d.shows.length ? d.shows.length + '개 공연' : '공연 없음'}</div></button>`; }).join('');
    h.querySelectorAll('.chip').forEach((b) => b.onclick = () => { S.day = +b.dataset.i; renderAll(); });
  }

  function showList(d) {
    if (!d.shows.length) return `<div class="show"><span class="tt">${T('noshow')}</span></div>`;
    return d.shows.map((s) => `<div class="show"><span class="vn" style="background:${VCOL[s.v]}22;color:${VCOL[s.v]}">${esc(s.venue)}</span><span class="tt">${esc(s.title)}</span><span class="tm">${esc(s.start)} → ${T('est_end')} ${esc(s.end_est)}</span></div>`).join('');
  }

  function renderCar(d) {
    $('#showList').innerHTML = showList(d);
    const c = d.car || {};
    $('#carCards').innerHTML = [
      card('주차 혼잡 피크', c.occ_peak_t ? `${c.occ_peak_t} · ${c.occ_peak_pct}%` : '-', c.occ_hi_pct ? `붐비는 날(상위 25%) ${c.occ_hi_pct}%` + (c.full_at ? ` · ${c.arrive_by} 전 도착 권장` : '') : '', (c.occ_hi_pct || 0) >= 80 ? 'red' : (c.occ_peak_pct || 0) >= 60 ? 'org' : 'grn'),
      card(T('exit_peak'), c.exit_peak || '-', c.exit_peak_cars ? `15분에 약 ${c.exit_peak_cars}대` : ''),
      card('예보 근거', c.basis || '-', '2025년 실측 · 범위는 25~75%', 'org'),
      card(T('leave_after'), c.leave_after || '-', c.best_gate ? `덜 붐비는 출구: ${c.best_gate}` : '', 'grn'),
    ].join('');
    const lab = d.slots; const g = d.gates || {};
    const gcol = { '동2문': '#1d5bff', '북2문': '#7c3aed', '남2문': '#15a05a', '기타': '#94a3b8' };
    const ser = Object.keys(g).map((k) => ({ data: g[k], color: gcol[k] || '#94a3b8', name: k }));
    const big = d.shows.filter((s) => s.end_idx != null).sort((a, b) => b.cap - a.cap); const shade = big.map((s, k) => ({ from: Math.max(0, s.end_idx), to: Math.min(lab.length, s.end_idx + 4), color: VCOL[s.v], label: k === 0 ? '퇴장 시작 추정' : '' }));
    bars($('#exitChart'), lab, ser, { shade, lines: d.exits_base ? [{ data: d.exits_base, color: '#94a3b8', dash: '4 3', w: 1.5 }] : [] });
    legend($('#exitLegend'), ser.map((s) => ({ c: s.color, t: s.name })).concat([{ c: '#94a3b8', t: '평소(공연 없는 같은 요일)' }]));
    const occL = [{ data: d.occ, color: '#1d5bff', w: 2.6 }];
    if (d.occ_lo) occL.push({ data: d.occ_lo, color: '#9db8ff', dash: '3 3', w: 1.2 }, { data: d.occ_hi, color: '#9db8ff', dash: '3 3', w: 1.2 });
    occL.push({ data: d.occ_base || [], color: '#94a3b8', dash: '5 4', w: 1.4 });
    lines($('#occChart'), lab, occL, { hline: { v: S.F.capacity || 2800, label: `주차면 약 ${(S.F.capacity || 2800).toLocaleString()}면(기관 FAQ)` } });
    $('#carTips').innerHTML = `<b>안내</b><ul>${(c.tips || []).map((t) => `<li>${esc(t)}</li>`).join('')}</ul>`;
  }

  function renderTransit(d) {
    const st = d.stations || [];
    $('#transitCards').innerHTML = st.slice(0, 4).map((s) => card(`${s.name}`, s.peak_lv < 0 ? '자료 없음' : (T('level')[s.peak_lv] || ''), `${s.peak_t || ''} · ${T('walk')} ${s.walk_min}분`, ['', 'grn', 'org', 'red'][s.peak_lv] || '')).join('');
    if (!st.length) { $('#stationTable').innerHTML = `<div class="empty">${T('noshow')}</div>`; }
    else {
      const cols = st[0].levels.map((x) => x.t);
      $('#stationTable').innerHTML = `<div class="tw"><table><tr><th>역</th>${cols.map((c) => `<th>${c}</th>`).join('')}<th>${T('walk')}</th></tr>${st.map((s) => `<tr><td><b>${esc(s.name)}</b><div class="hint">${esc(s.note || '')}</div></td>${s.levels.map((x) => `<td>${lvl(x.lv)}</td>`).join('')}<td>${s.walk_min}분</td></tr>`).join('')}</table></div>`;
    }
    const tips = (d.transit_tips && (d.transit_tips[S.lang] || d.transit_tips.ko)) || [];
    $('#transitTips').innerHTML = `<b>${T('luggage')} · ${T('lost')}</b><ul>${tips.map((t) => `<li>${esc(t)}</li>`).join('')}</ul>`;
  }

  function renderLive() {
    const R = S.RT; if (!R) { $('#liveCards').innerHTML = `<div class="empty">실시간 데이터 준비 중</div>`; return; }
    $('#liveCards').innerHTML = [card('기관 표시값', `${R.raw}대`, R.ts), card('미출차 바닥값(추정)', `${R.floor}대`, '오늘 02~05시 최저'), card('보정 주차 중', `${R.corrected}대`, `정원 ${R.cap}면 대비 ${Math.round(R.corrected / R.cap * 100)}%`, 'grn'), card('기관 예상 이용률', R.agency_pct != null ? `${R.agency_pct}%` : '-', R.agency_note || '')].join('');
    const lab = R.hist.map((h) => h[0].slice(5, 16)); lines($('#liveChart'), lab, [{ data: R.hist.map((h) => h[1]), color: '#94a3b8', w: 1.8 }, { data: R.hist.map((h) => h[2]), color: '#1d5bff', w: 2.4 }], { hline: { v: R.cap, label: `${R.cap}면` } });
    const A = R.agency || [];
    $('#agencyTable').innerHTML = A.length ? `<div class="tw"><table><tr><th>날짜</th><th>시각</th><th>기관 예상 이용률</th><th>퇴장예보(보정 재차)</th></tr>${A.map((a) => `<tr><td>${a.date}</td><td>${a.slot}</td><td>${a.pct}%</td><td>${a.ours != null ? a.ours + '대 (' + Math.round(a.ours / R.cap * 100) + '%)' : '-'}</td></tr>`).join('')}</table></div><p class="hint">기관 예보는 주말·입차 기준 단일값입니다. 퇴장예보는 같은 시각의 보정 재차 예보를 함께 보여줍니다.</p>` : '<div class="empty">주말 예보 없음</div>';
  }

  function renderOps(d) {
    const o = d.ops || {};
    $('#opsCards').innerHTML = [card(T('conflict'), ['낮음', '보통', '높음', '매우 높음'][d.conflict?.level || 0], d.conflict?.text || '', ['grn', 'grn', 'org', 'red'][d.conflict?.level || 0]), card('30분 안 퇴장 인원(추정)', d.conflict?.people ? d.conflict.people.toLocaleString() + '명' : '-', '공연장 수용인원 기준'), card('정산 차로 추가 개방', o.lanes_window || '-', o.lanes_note || ''), card('지난 예보 오차', S.ACC?.headline || '-', '정확도 탭 참고')].join('');
    // 간트
    const host = $('#opsGantt'); const W = 760, rowH = 30, L = 150, R = 10, H = Math.max(80, d.shows.length * rowH + 40); const s = svg(host, W, H);
    const h0 = 12, h1 = 24; const x = (h) => L + (W - L - R) * (h - h0) / (h1 - h0);
    for (let h = h0; h <= h1; h += 2) { el(s, 'line', { x1: x(h), x2: x(h), y1: 6, y2: H - 22, stroke: '#edf0f5' }); el(s, 'text', { x: x(h), y: H - 6, 'text-anchor': 'middle', 'font-size': 10, fill: '#8492a3' }, h + ':00'); }
    d.shows.forEach((sh, i) => { const y = 10 + i * rowH; const st = hm(sh.start), en = hm(sh.end_est);
      el(s, 'text', { x: 4, y: y + 15, 'font-size': 11, fill: '#14202e' }, (sh.venue + ' ' + sh.title).slice(0, 18));
      el(s, 'rect', { x: x(st), y: y + 3, width: Math.max(2, x(en) - x(st)), height: 16, rx: 4, fill: VCOL[sh.v], opacity: 0.35 });
      el(s, 'rect', { x: x(en), y: y + 1, width: x(en + 0.75) - x(en), height: 20, rx: 4, fill: VCOL[sh.v] });
      el(s, 'text', { x: x(en + 0.8) + 3, y: y + 15, 'font-size': 10, fill: '#4b5b6d' }, '퇴장 ' + sh.end_est); });
    if (!d.shows.length) host.innerHTML = `<div class="empty">${T('noshow')}</div>`;
    const g = d.gates || {}; const gcol = { '동2문': '#1d5bff', '북2문': '#7c3aed', '남2문': '#15a05a', '기타': '#94a3b8' };
    bars($('#opsGate'), d.slots, Object.keys(g).map((k) => ({ data: g[k], color: gcol[k] })), { lines: o.lane_cap ? [{ data: d.slots.map(() => o.lane_cap), color: '#e2463c', dash: '5 4', w: 1.2 }] : [] });
    $('#opsTips').innerHTML = `<b>권고</b><ul>${(o.recs || []).map((t) => `<li>${esc(t)}</li>`).join('')}</ul>`;
  }
  function hm(s) { const [h, m] = (s || '0:0').split(':').map(Number); return h + m / 60; }

  function renderAcc() {
    const A = S.ACC; if (!A) return;
    $('#accCards').innerHTML = (A.cards || []).map((c) => card(c.k, c.v, c.s, c.cls)).join('');
    $('#accTable').innerHTML = `<div class="tw"><table><tr><th>지표</th><th>퇴장예보</th><th>비교: 1주 전 같은 시각</th><th>비교: 요일·시각 평균</th><th>표본</th></tr>${(A.metrics || []).map((m) => `<tr><td>${esc(m.name)}</td><td><b>${esc(m.model)}</b></td><td>${esc(m.naive)}</td><td>${esc(m.profile)}</td><td>${esc(m.n)}</td></tr>`).join('')}</table></div><p class="hint">${esc(A.note || '')}</p>`;
    if (A.example) { lines($('#accChart'), A.example.slots, [{ data: A.example.actual, color: '#14202e', w: 2.4 }, { data: A.example.pred, color: '#1d5bff', w: 2.2 }, { data: A.example.naive || [], color: '#94a3b8', dash: '4 3', w: 1.5 }]); legend($('#accLegend'), [{ c: '#14202e', t: '실측 ' + A.example.title }, { c: '#1d5bff', t: '퇴장예보' }, { c: '#94a3b8', t: '1주 전 같은 시각' }]); }
    $('#accLive').innerHTML = (A.live && A.live.length) ? `<div class="tw"><table><tr><th>날짜</th><th>공연</th><th>예보</th><th>실측</th><th>기관 예보</th><th>메모</th></tr>${A.live.map((r) => `<tr><td>${esc(r.date)}</td><td>${esc(r.show)}</td><td>${esc(r.ours)}</td><td>${esc(r.actual)}</td><td>${esc(r.agency)}</td><td>${esc(r.note)}</td></tr>`).join('')}</table></div>` : '<div class="empty">11/21~22, 11/28~29 공연일 현장 기록 후 갱신</div>';
  }

  function renderData() {
    const D = S.DS || []; $('#dataTable').innerHTML = `<div class="tw"><table><tr><th>데이터</th><th>제공</th><th>형태</th><th>쓰임</th></tr>${D.map((d) => `<tr><td>${d.url ? `<a href="${d.url}" target="_blank">${esc(d.name)}</a>` : esc(d.name)}</td><td>${esc(d.org)}</td><td>${esc(d.type)}</td><td>${esc(d.use)}</td></tr>`).join('')}</table></div>`;
    const Q = S.Q || []; $('#qualityTable').innerHTML = `<div class="tw"><table><tr><th>#</th><th>데이터</th><th>발견</th><th>근거</th><th>제안</th></tr>${Q.map((q) => `<tr><td>${esc(q.id)}</td><td>${esc(q.ds)}</td><td>${esc(q.issue)}</td><td>${esc(q.evidence)}</td><td>${esc(q.fix)}</td></tr>`).join('')}</table></div>`;
    const E = S.END || []; $('#endTable').innerHTML = E.length ? `<div class="tw"><table><tr><th>날짜</th><th>공연장</th><th>공연</th><th>공지 시작</th><th>퇴장 시작(추정)</th><th>출차 피크</th></tr>${E.slice(0, 40).map((e) => `<tr><td>${e.date} (${e.dow})</td><td>${esc(e.venue)}</td><td>${esc(e.title)}</td><td>${e.start}</td><td><b>${e.exit_start}</b></td><td>${e.peak}</td></tr>`).join('')}</table></div>` : '<div class="empty">준비 중</div>';
  }

  function applyI18n() { document.querySelectorAll('[data-i18n]').forEach((e) => { const v = T(e.dataset.i18n); if (typeof v === 'string') e.textContent = v; }); document.documentElement.lang = S.lang; }
  function renderAll() { renderChips(); const d = S.F.days[S.day]; renderCar(d); renderTransit(d); renderOps(d); renderLive(); renderAcc(); renderData(); applyI18n();
    $('#genInfo').textContent = `예보 생성 ${S.F.generated_at} · 모델 ${S.F.version}`; }

  document.querySelectorAll('.tabs button').forEach((b) => b.onclick = () => { document.querySelectorAll('.tabs button').forEach((x) => x.classList.toggle('on', x === b)); document.querySelectorAll('.panel').forEach((p) => p.classList.toggle('on', p.id === 'p-' + b.dataset.tab)); });
  document.querySelectorAll('.lang button').forEach((b) => b.onclick = () => { S.lang = b.dataset.lang; document.querySelectorAll('.lang button').forEach((x) => x.classList.toggle('on', x === b)); if (S.lang !== 'ko') { const tb = document.querySelector('.tabs button[data-tab="transit"]'); tb.click(); } renderAll(); });

  (async function init() {
    [S.F, S.RT, S.ACC, S.Q, S.DS, S.END] = await Promise.all(['data/forecast.json', 'data/realtime.json', 'data/accuracy.json', 'data/quality.json', 'data/datasets.json', 'data/endtimes.json'].map(j));
    if (!S.F) { document.querySelector('main').innerHTML = '<div class="empty">예보 데이터를 불러오지 못했습니다.</div>'; return; }
    const today = new Date(Date.now() + 9 * 3600e3).toISOString().slice(0, 10);
    const idx = S.F.days.findIndex((d) => d.date >= today); S.day = idx >= 0 ? idx : 0;
    const q = new URLSearchParams(location.search); if (q.get('date')) { const k = S.F.days.findIndex((d) => d.date === q.get('date')); if (k >= 0) S.day = k; }
    if (q.get('tab')) { const tb = document.querySelector(`.tabs button[data-tab="${q.get('tab')}"]`); if (tb) tb.click(); }
    renderAll();
  })();
})();
