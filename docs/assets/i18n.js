// UI 문구 (KO 기본, EN/JA/ZH는 해외 관람객용 핵심 문구 중심)
window.I18N = {
 ko: {
  tagline:'공연이 끝나기 전에, 나가는 길을 먼저', tab_car:'차량 관람객', tab_transit:'대중교통·해외팬', tab_live:'실시간 주차', tab_ops:'운영 브리핑', tab_acc:'정확도', tab_data:'데이터·품질',
  exit_wave:'공연 후 출차 혼잡 (15분 단위)', exit_wave_hint:'막대가 높을수록 같은 시간에 나가려는 차량이 많습니다', occ_title:'예상 주차 중 차량 (보정값)', occ_hint:'기관 실시간 수치에서 밤새 빠지지 않는 미출차 기록을 걷어낸 값',
  station_title:'공연 후 역별 혼잡 예보', station_hint:'서울교통공사 역별 시간대 승차 실측(2024)과 공연 규모로 추정', live_title:'기관 실시간 값 vs 보정값 (최근 48시간)', live_hint:'새벽 바닥값은 실제로는 나간 차량의 미출차 기록으로 추정',
  agency_vs_ours:'기관 예상 이용률 vs 퇴장예보', ops_timeline:'공연 시간표와 퇴장 예상 구간', ops_gate:'게이트별 출차 예상 (15분)', acc_backtest:'과거 검증(백테스트)', acc_example:'예시: 예보 vs 실측', acc_live:'현장 검증 기록',
  data_used:'사용한 공공데이터', quality_title:'데이터 품질 점검 결과와 개선 제안', endtime_title:'새로 만든 데이터: 공연 실제 퇴장 시작 추정', download_csv:'CSV 내려받기', api_note:'(챗봇·앱이 그대로 불러 쓸 수 있는 공개 JSON)',
  foot_note:'예보는 공공데이터 기반 추정이며 현장 안내를 우선합니다. 출처: 한국체육산업개발(주) 공공데이터, 서울교통공사, 기상청.',
  noshow:'이날은 대형 공연이 없습니다. 평소 패턴으로 예보합니다.', est_end:'퇴장 시작 추정', arrive_by:'이 시각 전 도착 권장', full_at:'주차 만차 예상', exit_peak:'출차 피크', leave_after:'여유 출차 시각', conflict:'퇴장 충돌',
  st_now:'공연 후 30분', st_alt:'대안', walk:'도보', luggage:'짐 보관 주의', lost:'분실물', level:['여유','보통','혼잡','매우 혼잡'], gate:'게이트'
 },
 en: {
  tagline:'Know your way out before the show ends', tab_car:'By car', tab_transit:'Transit & fans', tab_live:'Live parking', tab_ops:'Operations', tab_acc:'Accuracy', tab_data:'Data & quality',
  exit_wave:'Post-show exit traffic (15-min)', exit_wave_hint:'Taller bars mean more cars leaving at the same time', occ_title:'Cars parked (corrected)', occ_hint:'Official count minus stale records that never exit',
  station_title:'Station crowding after the show', station_hint:'Estimated from Seoul Metro hourly boardings (2024) and show size', live_title:'Official live count vs corrected (48h)', live_hint:'Overnight floor = stale entry records',
  agency_vs_ours:'Official forecast vs Exit Forecast', ops_timeline:'Show schedule and exit windows', ops_gate:'Exits by gate (15-min)', acc_backtest:'Backtest', acc_example:'Example: forecast vs actual', acc_live:'Field validation',
  data_used:'Public data used', quality_title:'Data quality findings', endtime_title:'New dataset: estimated actual exit start', download_csv:'Download CSV', api_note:'(open JSON for chatbots and apps)',
  foot_note:'Forecasts are estimates from public data. Follow on-site guidance first.',
  noshow:'No major show this day. Forecast uses the usual pattern.', est_end:'Exit starts (est.)', arrive_by:'Arrive before', full_at:'Parking full (est.)', exit_peak:'Exit peak', leave_after:'Easier to leave after', conflict:'Exit clash',
  st_now:'30 min after show', st_alt:'Alternative', walk:'walk', luggage:'Luggage', lost:'Lost & found', level:['Low','Normal','Busy','Very busy'], gate:'Gate'
 },
 ja: {
  tagline:'終演前に、帰り道を先に', tab_car:'車で来場', tab_transit:'電車・海外ファン', tab_live:'駐車場ライブ', tab_ops:'運営', tab_acc:'精度', tab_data:'データ',
  station_title:'終演後の駅の混雑予報', station_hint:'ソウル交通公社の時間帯別乗車実績(2024)と公演規模から推定', st_now:'終演後30分', st_alt:'代替駅', walk:'徒歩', luggage:'荷物の預け入れ', lost:'落とし物', level:['空いている','普通','混雑','非常に混雑'],
  est_end:'退場開始(推定)', noshow:'この日は大型公演がありません。', foot_note:'予報は公共データに基づく推定です。現場の案内を優先してください。'
 },
 zh: {
  tagline:'演出结束前，先知道回家的路', tab_car:'驾车', tab_transit:'地铁·海外粉丝', tab_live:'实时停车', tab_ops:'运营', tab_acc:'准确度', tab_data:'数据',
  station_title:'散场后地铁站拥挤预报', station_hint:'根据首尔交通公社分时段乘车数据(2024)和演出规模估算', st_now:'散场后30分钟', st_alt:'备选车站', walk:'步行', luggage:'行李寄存', lost:'失物招领', level:['空闲','一般','拥挤','非常拥挤'],
  est_end:'预计开始退场', noshow:'当天没有大型演出。', foot_note:'预报为基于公共数据的估算，请以现场指引为准。'
 }
};
