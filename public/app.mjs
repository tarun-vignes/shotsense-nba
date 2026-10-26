import {filterRows, filterCounts, summarize, groupRows} from './analytics.mjs';

const $ = id => document.getElementById(id);
const names = ['Season', 'Team', 'Player', 'Shot zone', 'Shot type', 'Period'];
const number = (value, digits = 1) => value.toLocaleString('en-US', {minimumFractionDigits: digits, maximumFractionDigits: digits});
const signed = value => `${value >= 0 ? '+' : '−'}${number(Math.abs(value))}`;
let data, selected = [], queue = [];

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function cells(parent, values) {
  const row = element('tr');
  for (const value of values) row.append(element('td', value));
  parent.append(row);
}
function displayMetrics(summary) {
  $('metrics').replaceChildren();
  const cards = [
    ['Shot attempts', number(summary.n, 0), `${number(summary.games, 0)} selected games`],
    ['Actual FG%', `${number(summary.actualPct)}%`, `${number(summary.makes, 0)} actual makes`],
    ['Expected FG%', `${number(summary.expectedPct)}%`, `${number(summary.expected)} expected makes`],
    ['Makes above expectation', signed(summary.residual), `${signed(summary.delta)} percentage points`]
  ];
  for (const [label, value, hint] of cards) {
    const card = element('div', undefined, 'metric');
    card.append(element('span', label), element('strong', value), element('small', hint));
    $('metrics').append(card);
  }
}
function drawZones(zones) {
  const container = $('zones'); container.replaceChildren();
  if (!zones.length) { container.append(element('p', 'No zone reaches the minimum sample size. Lower the threshold or broaden your filters.', 'muted')); return; }
  for (const zone of zones) {
    const item = element('div', undefined, 'zone');
    const heading = element('div', undefined, 'zone-heading');
    heading.append(element('span', zone.label), element('small', `${number(zone.n, 0)} shots · ${signed(zone.delta)} pp`));
    item.append(heading);
    for (const [name, value, color] of [['Actual', zone.actualPct, 'actual'], ['Expected', zone.expectedPct, 'expected']]) {
      const bar = element('div', undefined, 'bar');
      const fill = element('span', undefined, color); fill.style.width = `${value}%`;
      bar.append(fill, element('b', `${name} ${number(value)}%`)); item.append(bar);
    }
    container.append(item);
  }
}
function drawCourt(rows) {
  const canvas = $('court'), ctx = canvas.getContext('2d');
  const valid = rows.filter(row => row[9] !== null && row[10] !== null && Math.abs(row[9]) <= 25 && row[10] >= -5.25 && row[10] <= 42);
  // Deterministic evenly spaced sample; all metrics use the complete selection.
  const count = Math.min(valid.length, 4000), samples = Array.from({length: count}, (_, i) => valid[Math.floor(i * valid.length / count)]);
  const X = x => 45 + (x + 25) / 50 * 560;
  const Y = y => 515 - (y + 5.25) / 47.25 * 490;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = '#f8fafb'; ctx.fillRect(X(-25), Y(42), 560, 490);
  ctx.strokeStyle = '#b8c7d1'; ctx.lineWidth = 2;
  ctx.strokeRect(X(-25), Y(42), 560, 490);
  ctx.strokeRect(X(-8), Y(13.75), X(8) - X(-8), Y(-5.25) - Y(13.75));
  ctx.beginPath(); ctx.ellipse(X(0), Y(13.75), 6 / 50 * 560, 6 / 47.25 * 490, 0, 0, Math.PI * 2); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(X(-3), Y(-.75)); ctx.lineTo(X(3), Y(-.75)); ctx.stroke();
  ctx.globalAlpha = .38;
  for (const row of samples) {
    ctx.fillStyle = row[7] ? '#147c80' : '#d98550';
    ctx.beginPath(); ctx.arc(X(row[9]), Y(row[10]), 2.5, 0, Math.PI * 2); ctx.fill();
  }
  ctx.globalAlpha = 1; ctx.strokeStyle = '#172c40';
  ctx.beginPath(); ctx.ellipse(X(0), Y(0), 8, 8, 0, 0, Math.PI * 2); ctx.stroke();
  ctx.fillStyle = '#607285'; ctx.font = '13px system-ui';
  ctx.fillText('−25 ft', X(-25), 545); ctx.fillText('Basket (0, 0)', X(0) - 42, 545); ctx.fillText('+25 ft', X(25) - 43, 545);
  $('sample').textContent = `Showing ${number(count, 0)} of ${number(valid.length, 0)} half-court shots; ${number(rows.length - valid.length, 0)} outside view or missing coordinates. All summaries use every selected attempt.`;
}
function update() {
  const filters = names.map((_, i) => $(`filter-${i}`).value);
  selected = filterRows(data.rows, filters);
  const counts = filterCounts(data.rows, filters, data.fields.slice(0, 6).map(field => data.labels[field].length));
  $('recovery').replaceChildren();
  counts.forEach((values, column) => {
    const select = $(`filter-${column}`);
    values.forEach((count, code) => {
      const option = select.options[code + 1];
      option.textContent = `${data.labels[data.fields[column]][code]} (${number(count, 0)} shots)`;
      option.disabled = count === 0 && filters[column] !== String(code);
    });
    const available = values.reduce((sum, count) => sum + count, 0);
    if (!selected.length && filters[column] !== '' && available > 0) {
      const button = element('button', `Clear ${names[column].toLowerCase()} — show ${number(available, 0)} shots`);
      button.type = 'button';
      button.addEventListener('click', () => { select.value = ''; update(); });
      $('recovery').append(button);
    }
  });
  $('active').textContent = 'ACTIVE FILTERS · ' + (filters.map((value, i) => value === '' ? '' : `${names[i]}: ${data.labels[data.fields[i]][Number(value)]}`).filter(Boolean).join(' · ') || 'All available held-out shots');
  $('empty').hidden = selected.length > 0;
  $('results').hidden = selected.length === 0;
  $('recovery').hidden = selected.length > 0;
  if (!selected.length) return;
  displayMetrics(summarize(selected));
  const minimum = Number($('minimum').value);
  const zones = groupRows(selected, 3, data.labels.SHOT_ZONE_BASIC, minimum);
  if (zones.length) {
    const lead = [...zones].sort((a, b) => Math.abs(b.residual) - Math.abs(a.residual))[0];
    $('finding').textContent = `${lead.label}: ${number(Math.abs(lead.residual))} makes ${lead.residual >= 0 ? 'above' : 'below'} expectation across ${number(lead.n, 0)} attempts (${signed(lead.delta)} percentage points). Review shooter mix, defensive pressure, and game film; this is a descriptive lead, not a causal finding.`;
  } else $('finding').textContent = `No zone has at least ${minimum} selected attempts. Broaden the filters before drawing conclusions.`;
  drawZones(zones); drawCourt(selected);
  const column = Number($('group').value);
  queue = groupRows(selected, column, data.labels[data.fields[column]], minimum);
  $('queue').replaceChildren();
  for (const group of queue) {
    cells($('queue'), [group.label, number(group.n, 0), number(group.games, 0), `${number(group.actualPct)}%`, `${number(group.expectedPct)}%`, signed(group.residual), signed(group.delta), group.low === null ? 'Unavailable (<5 games)' : `${signed(group.low)} to ${signed(group.high)}`]);
  }
  if (!queue.length) cells($('queue'), ['No situation meets the sample threshold.', '', '', '', '', '', '', '']);
}
function populate() {
  const report = data.report;
  $('coverage').textContent = `REAL NBA DATA · 2023–24 ARCHIVE · HELD OUT ${report.test_start} TO ${report.test_end} · ${number(data.rows.length, 0)} SHOTS`;
  if (data.coverage) {
    $('player-coverage').textContent = `${data.coverage.evaluation_players} of ${data.coverage.source_players} source players have held-out attempts. ${data.coverage.training_only_players.length} have shots only in the training dates, so no held-out player result is available. Players absent from the source cannot be shown. Training shots are not mixed into evaluation.`;
    $('training-only').textContent = data.coverage.training_only_players.map(row => `${row.player} (${number(row.source_attempts, 0)} source attempts; last shot ${row.last_date})`).join('; ');
  }
  for (let i = 0; i < names.length; i++) {
    const label = element('label', names[i]), select = element('select'); select.id = `filter-${i}`;
    const all = element('option', `All ${names[i].toLowerCase()}s`); all.value = ''; select.append(all);
    data.labels[data.fields[i]].forEach((name, code) => { const option = element('option', name); option.value = String(code); select.append(option); });
    label.append(select); $('filters').append(label); select.addEventListener('change', update);
  }
  $('reset').addEventListener('click', () => { names.forEach((_, i) => { $(`filter-${i}`).value = ''; }); update(); });
  $('group').addEventListener('change', update); $('minimum').addEventListener('change', update);
  $('split').textContent = `Training: ${report.train_start}–${report.train_end} (${number(report.train_rows, 0)} attempts, ${number(report.train_games, 0)} games). Evaluation: ${report.test_start}–${report.test_end} (${number(report.test_rows, 0)} attempts, ${number(report.test_games, 0)} games). First 80% of distinct game dates train the model; later dates test it. No game appears in both samples. No test-driven tuning or refitting.`;
  for (const [name, title] of [['baseline', 'Constant training FG% baseline'], ['model', 'Shot-context logistic regression']]) cells($('evaluation'), [title, number(report[name].brier, 5), number(report[name].log_loss, 5), number(report[name].roc_auc, 5)]);
  $('intercept').textContent = `Intercept: ${number(report.intercept, 5)}. logit(p) = intercept + sum(coefficient × encoded feature). Distance is standardized using training data. L2 regularization, C=1. Correlated coefficients are not independent causal effects.`;
  for (const row of data.coefficients) cells($('coefficients'), [row.feature, number(row.log_odds_coefficient, 5)]);
  $('audit').textContent = `Validated ${number(data.audit.valid_rows, 0)} of ${number(data.audit.input_rows, 0)} rows; ${data.audit.dropped_rows} dropped. Source commit ${data.source.commit}. SHA-256 ${data.source.sha256}.`;
  $('download').addEventListener('click', () => {
    const csv = [['situation', 'attempts', 'games', 'actual_pct', 'expected_pct', 'residual_makes', 'delta_pp', 'interval_low', 'interval_high'], ...queue.map(g => [g.label, g.n, g.games, g.actualPct, g.expectedPct, g.residual, g.delta, g.low, g.high])].map(row => row.map(value => `"${String(value ?? '').replaceAll('"', '""')}"`).join(',')).join('\n');
    const url = URL.createObjectURL(new Blob([csv], {type: 'text/csv'}));
    const a = element('a'); a.href = url; a.download = 'shotsense-situations.csv'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  $('status').hidden = true; $('dashboard').hidden = false; update();
}
try {
  const response = await fetch('./shots.json');
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  data = await response.json();
  if (!data.rows?.length || data.rows.length !== data.report.test_rows || data.source.synthetic !== false) throw new Error('Invalid real-data export');
  populate();
} catch (error) {
  $('status').hidden = false;
  $('status').textContent = `Could not load the analysis (${error.message}). Reload the page or run the full application from the linked repository. No synthetic data has been substituted.`;
  $('dashboard').hidden = true;
}
