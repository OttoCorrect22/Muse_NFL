/* NFL Model v1 — home base. All numbers come from scoreboard.json (same folder)
   plus the two real constants below. Nothing is invented. */
'use strict';

/* First live prediction — from hidden_files/live/prediction_2026_w4_pit_cle.json.
   Graded 2026-10-02 after the final whistle: Browns 27, Steelers 24. */
const LIVE = {
  away: 'PIT', home: 'CLE',
  awayFull: 'Pittsburgh Steelers', homeFull: 'Cleveland Browns',
  kickoffLabel: 'Thu Oct 1, 8:15 PM ET',
  kickoffMs: new Date('2026-10-01T20:15:00-04:00').getTime(),
  predAwayBy: 1.22,          // Steelers by 1.22
  winProbAway: 53.8,         // Steelers win probability %
  bucket: "pick'em",
  lineNote: 'Steelers −2.5', // benchmark only, never a model input
  qbs: 'Aaron Rodgers (PIT) vs Deshaun Watson (CLE) — Tuesday-morning starters',
  graded: true,              // final whistle has blown; liveRowHtml() renders the grade
  finalAway: 24, finalHome: 27,
  modelMiss: 4.2,            // |(+1.22) - (-3)| pts — model's margin error
  vegasMiss: 5.5,            // |(+2.5) - (-3)| pts — closing line's margin error
  winnerRight: false,        // both the model and Vegas picked Pittsburgh; Browns won
  gradeNote: 'Cooler on the favorite was the better read on the margin — wrong on the winner. ' +
    'A pick’em-bucket call loses about half the time by design.'
};

/* Locked v1 feature weights, in plain points (from the official backtest) */
const FEATURES = [
  { code: 'elo_diff',     name: 'Team strength gap', weight: '+0.0268', per: 'per rating point',
    desc: 'Overall team strength from win/loss history. Each point of rating gap is worth about three-hundredths of a point on the scoreboard.' },
  { code: 'off_pass_epa', name: 'Passing offense',   weight: '+3.88', per: 'per EPA/play',
    desc: 'How efficient the offense is throwing the ball — expected points added per pass play.' },
  { code: 'off_rush_epa', name: 'Rushing offense',   weight: '+6.28', per: 'per EPA/play',
    desc: 'How efficient the offense is running the ball, per run play.' },
  { code: 'def_pass_epa', name: 'Pass defense',      weight: '+2.72', per: 'per EPA/play',
    desc: 'How well the defense shuts down the other team\u2019s pass, per play.' },
  { code: 'def_rush_epa', name: 'Run defense',       weight: '+3.28', per: 'per EPA/play',
    desc: 'How well the defense stops the other team\u2019s run, per play.' },
  { code: 'qb_edge',      name: 'Quarterback edge',  weight: '+6.43', per: 'per EPA/play',
    desc: 'The gap between the two starting quarterbacks\u2019 recent efficiency.' },
  { code: 'st_epa_diff',  name: 'Special teams gap', weight: '+6.90', per: 'per EPA/play',
    desc: 'Kicking, punting and returns edge, per play.' },
];
const INTERCEPT = { name: 'Home field', weight: '+1.69', per: 'points',
  desc: 'The built-in edge of playing at home, baked into every prediction.' };

const TEAMS = { ARI:'Arizona Cardinals', ATL:'Atlanta Falcons', BAL:'Baltimore Ravens',
  BUF:'Buffalo Bills', CAR:'Carolina Panthers', CHI:'Chicago Bears', CIN:'Cincinnati Bengals',
  CLE:'Cleveland Browns', DAL:'Dallas Cowboys', DEN:'Denver Broncos', DET:'Detroit Lions',
  GB:'Green Bay Packers', HOU:'Houston Texans', IND:'Indianapolis Colts', JAX:'Jacksonville Jaguars',
  KC:'Kansas City Chiefs', LA:'Los Angeles Rams', LAC:'Los Angeles Chargers', LV:'Las Vegas Raiders',
  MIA:'Miami Dolphins', MIN:'Minnesota Vikings', NE:'New England Patriots', NO:'New Orleans Saints',
  NYG:'New York Giants', NYJ:'New York Jets', PHI:'Philadelphia Eagles', PIT:'Pittsburgh Steelers',
  SEA:'Seattle Seahawks', SF:'San Francisco 49ers', TB:'Tampa Bay Buccaneers', TEN:'Tennessee Titans',
  WAS:'Washington Commanders' };

const SPLIT_LABELS = {
  train_in_sample: 'Training · 2015–2021',
  val: 'Validation · 2022–2023',
  test: 'Final test · 2024'
};

const $ = (id) => document.getElementById(id);
const pct1 = (x) => (x * 100).toFixed(1) + '%';
const f2 = (x) => x.toFixed(2);
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;');

function teamName(abbr) { return TEAMS[abbr] || abbr; }

/* "BUF by 7.7" style pick from a home-margin number */
function pickLabel(margin, home, away) {
  if (margin > 0) return teamName(home) + ' by ' + Math.abs(margin).toFixed(1);
  if (margin < 0) return teamName(away) + ' by ' + Math.abs(margin).toFixed(1);
  return 'Pick\u2019em';
}
function resultLabel(margin, home, away) {
  if (margin > 0) return teamName(home) + ' won by ' + Math.abs(margin).toFixed(0);
  if (margin < 0) return teamName(away) + ' won by ' + Math.abs(margin).toFixed(0);
  return 'Tie';
}
function fmtDate(iso) {
  const d = new Date(iso + 'T12:00:00');
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}
function winnerCorrect(pred, actual) {
  if (actual === 0) return 'push';
  if (pred === 0) return 'push';
  return Math.sign(pred) === Math.sign(actual) ? 'yes' : 'no';
}

/* ---------------- tabs ---------------- */
document.querySelectorAll('.tab').forEach((btn) => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach((b) => {
      b.classList.remove('active'); b.setAttribute('aria-selected', 'false');
    });
    btn.classList.add('active'); btn.setAttribute('aria-selected', 'true');
    document.querySelectorAll('.panel').forEach((p) => p.classList.remove('active'));
    $('tab-' + btn.dataset.tab).classList.add('active');
  });
});

/* ---------------- main ---------------- */
let DB = null;

fetch('scoreboard.json')
  .then((r) => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
  .then((data) => { DB = data; renderAll(); })
  .catch((e) => {
    document.querySelector('main').innerHTML =
      '<div class="error">Couldn\u2019t load the backtest data (scoreboard.json). ' + esc(e.message) + '</div>';
  });

function renderAll() {
  renderBuild();
  renderGames();
  renderScoreboard();
  // live chip: show until ~4h after kickoff
  if (Date.now() < LIVE.kickoffMs + 4 * 3600 * 1000) $('live-chip').hidden = false;
}

/* ---------------- BUILD MODEL ---------------- */
function renderBuild() {
  const w = DB.meta.weights_native;
  const rows = FEATURES.map((f) => {
    const exact = w[f.code];
    const shown = (exact !== undefined && Math.abs(exact - parseFloat(f.weight)) < 0.011)
      ? f.weight : f2(exact);
    return '<div class="feature">' +
      '<div class="feature-name">' + esc(f.name) + '<span class="code">' + esc(f.code) + '</span></div>' +
      '<p class="feature-desc">' + esc(f.desc) + '</p>' +
      '<div class="feature-weight">' + shown + '<span class="per">' + esc(f.per) + '</span></div>' +
      '</div>';
  }).join('');
  $('feature-list').innerHTML = rows +
    '<div class="feature intercept">' +
    '<div class="feature-name">' + esc(INTERCEPT.name) + '<span class="code">intercept</span></div>' +
    '<p class="feature-desc">' + esc(INTERCEPT.desc) + '</p>' +
    '<div class="feature-weight">' + INTERCEPT.weight + '<span class="per">' + esc(INTERCEPT.per) + '</span></div>' +
    '</div>';
}

/* ---------------- GAMES ---------------- */
function liveRowHtml() {
  if (!LIVE.graded) {
    return '<div class="live-row">' +
      '<span class="badge">Live · result pending</span>' +
      '<h3>' + esc(LIVE.awayFull) + ' @ ' + esc(LIVE.homeFull) + '</h3>' +
      '<p class="pred-line">Model says <strong>' + esc(LIVE.awayFull.split(' ')[1]) + ' by ' + LIVE.predAwayBy.toFixed(2) +
      '</strong> · win chance ' + LIVE.winProbAway.toFixed(1) + '% (' + esc(LIVE.bucket) + ')</p>' +
      '<p>Kickoff: ' + esc(LIVE.kickoffLabel) + ' · Closing line for reference: ' + esc(LIVE.lineNote) + ' (benchmark only)</p>' +
      '<p>QBs: ' + esc(LIVE.qbs) + '</p>' +
      '<p><em>Graded here after the final whistle — model miss vs. Vegas miss, and whether the pick was right.</em></p>' +
      '</div>';
  }
  return '<div class="live-row">' +
    '<span class="badge">Graded · first live result</span>' +
    '<h3>' + esc(LIVE.awayFull) + ' @ ' + esc(LIVE.homeFull) + '</h3>' +
    '<p class="pred-line">Final: <strong>' + esc(LIVE.homeFull) + ' ' + LIVE.finalHome + ', ' + esc(LIVE.awayFull) + ' ' + LIVE.finalAway + '</strong>' +
    ' · played ' + esc(LIVE.kickoffLabel) + '</p>' +
    '<p>Model said ' + esc(LIVE.awayFull.split(' ')[1]) + ' by ' + LIVE.predAwayBy.toFixed(2) +
    ' · ' + LIVE.winProbAway.toFixed(1) + '% to win (' + esc(LIVE.bucket) + ') · Closing line ' + esc(LIVE.lineNote) + ' (benchmark only)</p>' +
    '<div class="stat-row"><span class="lbl">Winner picked right?</span><span class="win-no">No — both picked Pittsburgh</span></div>' +
    '<div class="stat-row"><span class="lbl">Model margin miss</span><span class="model-c">' + LIVE.modelMiss.toFixed(1) + ' pts</span></div>' +
    '<div class="stat-row"><span class="lbl">Vegas margin miss</span><span class="vegas-c">' + LIVE.vegasMiss.toFixed(1) + ' pts</span></div>' +
    '<p><em>' + esc(LIVE.gradeNote) + '</em></p>' +
    '</div>';
}

function renderGames() {
  const seasons = DB.per_season.map((s) => s.season);
  const sel = $('season-select');
  sel.innerHTML = seasons.map((y) => '<option value="' + y + '"' + (y === 2024 ? ' selected' : '') + '>' + y + '</option>').join('');
  sel.addEventListener('change', renderGamesTable);
  $('live-row-wrap').innerHTML = liveRowHtml();
  renderGamesTable();
}

function renderGamesTable() {
  const year = parseInt($('season-select').value, 10);
  const wrap = $('games-table-wrap');

  if (year !== 2024) {
    const s = DB.per_season.find((x) => x.season === year);
    wrap.innerHTML =
      '<div class="card"><h3>' + year + ' season totals <span class="pill">Season totals only</span></h3>' +
      '<p class="explain">Individual game rows are stored only for the 2024 final-test season. ' +
      'Earlier seasons are shown as totals below.</p>' +
      '<div class="stat-row"><span class="lbl">Games</span><span><strong>' + s.n + '</strong></span></div>' +
      '<div class="stat-row"><span class="lbl">Model avg miss</span><span class="model-c">' + f2(s.model_mae) + ' pts</span></div>' +
      '<div class="stat-row"><span class="lbl">Model winner picks</span><span class="model-c">' + pct1(s.model_win_acc) + '</span></div>' +
      '<div class="stat-row"><span class="lbl">Vegas avg miss</span><span class="vegas-c">' + f2(s.vegas_mae) + ' pts</span></div>' +
      '<div class="stat-row"><span class="lbl">Vegas winner picks</span><span class="vegas-c">' + pct1(s.vegas_win_acc) + '</span></div>' +
      '</div>';
    return;
  }

  const games = DB.panel3_us_vs_vegas_vs_reality.games.slice()
    .sort((a, b) => a.date.localeCompare(b.date));
  const rows = games.map((g) => {
    const wc = winnerCorrect(g.pred_margin, g.actual_margin);
    const wcHtml = wc === 'yes' ? '<span class="win-yes">Yes</span>'
      : wc === 'no' ? '<span class="win-no">No</span>' : '<span class="win-push">Push</span>';
    const mBetter = g.model_abs_err < g.vegas_abs_err;
    const vBetter = g.vegas_abs_err < g.model_abs_err;
    return '<tr>' +
      '<td>' + esc(fmtDate(g.date)) + '</td>' +
      '<td><strong>' + esc(g.away) + '</strong> @ <strong>' + esc(g.home) + '</strong><br><span style="color:var(--muted);font-size:.75rem">Wk ' + g.week + '</span></td>' +
      '<td>' + esc(pickLabel(g.pred_margin, g.home, g.away)) + '</td>' +
      '<td>' + esc(pickLabel(g.closing_line, g.home, g.away)) + '</td>' +
      '<td>' + esc(resultLabel(g.actual_margin, g.home, g.away)) + '</td>' +
      '<td class="num ' + (mBetter ? 'err-better' : 'err-worse') + '">' + f2(g.model_abs_err) + '</td>' +
      '<td class="num ' + (vBetter ? 'err-better' : 'err-worse') + '">' + f2(g.vegas_abs_err) + '</td>' +
      '<td>' + wcHtml + '</td>' +
      '</tr>';
  }).join('');

  wrap.innerHTML =
    '<div class="legend"><span><span class="dot" style="background:var(--green)"></span>smaller miss = closer to the final score</span>' +
    '<span>Closing line is the benchmark only — the model never sees it.</span></div>' +
    '<div class="table-scroll"><table>' +
    '<thead><tr><th>Date</th><th>Matchup</th><th>Model pick</th><th>Closing line</th><th>Final</th>' +
    '<th class="num">Model miss</th><th class="num">Vegas miss</th><th>Winner right?</th></tr></thead>' +
    '<tbody>' + rows + '</tbody></table></div>';
}

/* ---------------- SCOREBOARD ---------------- */
function renderScoreboard() {
  renderPanel1();
  renderPanel2('test');
  document.querySelectorAll('.mini-tab').forEach((b) => {
    b.addEventListener('click', () => {
      document.querySelectorAll('.mini-tab').forEach((x) => x.classList.remove('active'));
      b.classList.add('active');
      renderPanel2(b.dataset.bucket);
    });
  });
  renderPanel3();
}

function renderPanel1() {
  const p1 = DB.panel1_vs_raw_results;
  const cards = ['train_in_sample', 'val', 'test'].map((k) => {
    const s = p1[k];
    return '<div class="stat-card"><h3>' + SPLIT_LABELS[k] + '</h3>' +
      '<div class="games-n">' + s.n.toLocaleString() + ' games</div>' +
      '<div class="stat-row"><span class="lbl">Avg miss</span><span class="big model-c">' + f2(s.model_mae) + ' <small>pts</small></span></div>' +
      '<div class="stat-row"><span class="lbl">Winners picked</span><span class="big model-c">' + pct1(s.model_win_acc) + '</span></div>' +
      '<div class="stat-row"><span class="lbl">Vegas avg miss</span><span class="vegas-c">' + f2(s.vegas_mae) + ' pts</span></div>' +
      '<div class="stat-row"><span class="lbl">Vegas winners</span><span class="vegas-c">' + pct1(s.vegas_win_acc) + '</span></div>' +
      '</div>';
  }).join('');
  $('panel1').innerHTML = cards +
    '<div class="takeaway" style="grid-column:1/-1">The model held up on the season it had never seen: ' +
    'winner picks actually <strong>rose from 63.6% to 68.0%</strong> on the 2024 final test, and the gap to Vegas narrowed.</div>';
}

function bucketHtml(b) {
  const pred = b.avg_pred_fav_winprob * 100, act = b.actual_fav_winrate * 100;
  return '<div class="bucket">' +
    '<div class="bucket-head"><h4>' + esc(b.bucket) + ' games</h4><span class="n">' + b.n + ' games</span></div>' +
    '<div class="calib">' +
    '<div><div class="calib-lbl"><span>We said the favorite wins</span><strong>' + pred.toFixed(0) + '%</strong></div>' +
    '<div class="calib-bar bar-pred"><i style="width:' + pred.toFixed(1) + '%"></i></div></div>' +
    '<div><div class="calib-lbl"><span>The favorite actually won</span><strong>' + act.toFixed(0) + '%</strong></div>' +
    '<div class="calib-bar bar-actual"><i style="width:' + act.toFixed(1) + '%"></i></div></div>' +
    '</div>' +
    '<div class="bucket-meta"><span>Avg miss <strong>' + f2(b.avg_abs_margin_err) + ' pts</strong></span>' +
    '<span>Decided by a field goal or less <strong>' + b.close_pct.toFixed(1) + '%</strong></span>' +
    '<span>Blowouts (14+ pts) <strong>' + b.blowout_pct.toFixed(1) + '%</strong></span></div>' +
    '</div>';
}

function renderPanel2(which) {
  const buckets = DB.panel2_confidence_buckets[which];
  const title = which === 'test' ? '2024 final test' : '2022–23 validation';
  let takeaway;
  if (which === 'test') {
    takeaway = 'When we said <strong>86%</strong>, favorites won <strong>87%</strong> — the model\u2019s confidence ' +
      'matches reality. Only the mildest calls were a touch underconfident (we said 60%, favorites won 73%).';
  } else {
    takeaway = 'Same honest picture a year earlier: confidence tracks reality closely across every bucket.';
  }
  $('panel2').innerHTML = '<p class="explain" style="margin-top:10px">' + title +
    ' — favorites grouped by how strongly the model liked them.</p>' +
    buckets.map(bucketHtml).join('') +
    '<div class="takeaway">' + takeaway + '</div>';

  // favorites vs underdogs + close vs blowouts (2024 games)
  const games = DB.panel3_us_vs_vegas_vs_reality.games;
  let favW = 0, favN = 0, vFavW = 0, vFavN = 0;
  let closeN = 0, closeW = 0, blowN = 0, blowW = 0;
  games.forEach((g) => {
    const am = Math.abs(g.actual_margin);
    if (g.pred_margin !== 0 && g.actual_margin !== 0) {
      favN++; if (Math.sign(g.pred_margin) === Math.sign(g.actual_margin)) favW++;
    }
    if (g.closing_line !== 0 && g.actual_margin !== 0) {
      vFavN++; if (Math.sign(g.closing_line) === Math.sign(g.actual_margin)) vFavW++;
    }
    if (am <= 3) { closeN++; if (winnerCorrect(g.pred_margin, g.actual_margin) === 'yes') closeW++; }
    if (am >= 14) { blowN++; if (winnerCorrect(g.pred_margin, g.actual_margin) === 'yes') blowW++; }
  });
  $('panel2-extra').innerHTML =
    '<div class="card"><h3>Favorites vs. underdogs <span style="color:var(--muted);font-weight:400;font-size:.8rem">2024</span></h3>' +
    '<div class="stat-row"><span class="lbl">Our favorites won</span><span class="model-c"><strong>' + pct1(favW / favN) + '</strong></span></div>' +
    '<div class="stat-row"><span class="lbl">Vegas favorites won</span><span class="vegas-c"><strong>' + pct1(vFavW / vFavN) + '</strong></span></div>' +
    '<p class="explain" style="font-size:.82rem">Underdogs, of course, won the rest — that\u2019s where the points come from.</p></div>' +
    '<div class="card"><h3>Close games vs. blowouts <span style="color:var(--muted);font-weight:400;font-size:.8rem">2024</span></h3>' +
    '<div class="stat-row"><span class="lbl">Nail-biters (3 pts or less)</span><span><strong>' + pct1(closeN / games.length) + '</strong> of games</span></div>' +
    '<div class="stat-row"><span class="lbl">We picked the winner in those</span><span class="model-c"><strong>' + pct1(closeW / closeN) + '</strong></span></div>' +
    '<div class="stat-row"><span class="lbl">Blowouts (14+ pts)</span><span><strong>' + pct1(blowN / games.length) + '</strong> of games</span></div>' +
    '<div class="stat-row"><span class="lbl">We picked the winner in those</span><span class="model-c"><strong>' + pct1(blowW / blowN) + '</strong></span></div></div>';
}

function renderPanel3() {
  const a = DB.panel3_us_vs_vegas_vs_reality.aggregate;
  const gap = a.vegas_mae - a.model_mae;
  $('panel3-agg').innerHTML =
    '<div class="stat-card"><h3>Average miss</h3>' +
    '<div class="stat-row"><span class="lbl">Us</span><span class="big model-c">' + f2(a.model_mae) + ' <small>pts</small></span></div>' +
    '<div class="stat-row"><span class="lbl">Vegas</span><span class="big vegas-c">' + f2(a.vegas_mae) + ' <small>pts</small></span></div>' +
    '<p class="explain" style="font-size:.82rem">Gap: ' + gap.toFixed(2) + ' pts — the price of predicting from team stats alone.</p></div>' +
    '<div class="stat-card"><h3>Winner picks</h3>' +
    '<div class="stat-row"><span class="lbl">Us</span><span class="big model-c">' + pct1(a.model_win_acc) + '</span></div>' +
    '<div class="stat-row"><span class="lbl">Vegas</span><span class="big vegas-c">' + pct1(a.vegas_win_acc) + '</span></div></div>' +
    '<div class="stat-card"><h3>Head to head</h3>' +
    '<div class="big model-c">' + a.games_model_closer_than_vegas + '<small> / ' + a.n + ' games</small></div>' +
    '<p class="explain" style="font-size:.85rem">We were closer to the final score than the closing line in <strong>' +
    a.pct_games_model_closer.toFixed(1) + '%</strong> of games.</p></div>';

  const games = DB.panel3_us_vs_vegas_vs_reality.games;
  const bins = [
    { label: 'We were much closer (7+ pts)', test: (d) => d >= 7, color: 'var(--green)' },
    { label: 'We were closer (3–7 pts)', test: (d) => d >= 3 && d < 7, color: '#6fe3a0' },
    { label: 'We were a bit closer (0.5–3)', test: (d) => d >= 0.5 && d < 3, color: '#a9ecc6' },
    { label: 'About even (within half a point)', test: (d) => Math.abs(d) < 0.5, color: '#5a6b88' },
    { label: 'Vegas a bit closer (0.5–3)', test: (d) => d <= -0.5 && d > -3, color: '#f8d68a' },
    { label: 'Vegas closer (3–7 pts)', test: (d) => d <= -3 && d > -7, color: 'var(--gold)' },
    { label: 'Vegas much closer (7+ pts)', test: (d) => d <= -7, color: '#d99a26' },
  ];
  const counts = bins.map((b) => ({ label: b.label, color: b.color, n: 0 }));
  games.forEach((g) => {
    const d = g.vegas_abs_err - g.model_abs_err; // positive = we were closer
    const i = bins.findIndex((b) => b.test(d));
    if (i >= 0) counts[i].n++;
  });
  const max = Math.max.apply(null, counts.map((c) => c.n));
  $('panel3-dist').innerHTML = counts.map((c) =>
    '<div class="dist-row"><span class="dlbl">' + esc(c.label) + '</span>' +
    '<div class="dist-bar"><i style="width:' + (100 * c.n / max).toFixed(1) + '%;background:' + c.color + '"></i></div>' +
    '<span class="dn">' + c.n + '</span></div>'
  ).join('');
}
