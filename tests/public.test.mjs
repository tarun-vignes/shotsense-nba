import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {filterRows, filterCounts, summarize, groupRows} from '../public/analytics.mjs';

test('browser arithmetic and intersecting filters', () => {
  const rows = [[0,0,0,0,0,0,5,1,.6,0,0,1], [0,1,1,0,0,0,10,0,.4,0,0,2]];
  const summary = summarize(rows);
  assert.equal(summary.expected, 1); assert.equal(summary.actualPct, 50); assert.equal(summary.residual, 0);
  assert.equal(filterRows(rows, ['', '0', '', '', '', '']).length, 1);
  assert.equal(filterRows(rows, ['', '0', '1', '', '', '']).length, 0);
  assert.equal(summarize([]).actualPct, null);
  assert.equal(groupRows(rows, 3, ['Paint'], 3).length, 0);
  assert.equal(groupRows(rows, 3, ['Paint'], 1)[0].low, null);
});

test('public export conserves real held-out analysis and zone results', () => {
  const data = JSON.parse(readFileSync(new URL('../public/shots.json', import.meta.url)));
  const report = JSON.parse(readFileSync(new URL('../reports/evaluation.json', import.meta.url)));
  assert.equal(data.source.synthetic, false);
  assert.equal(data.rows.length, report.test_rows);
  const summary = summarize(data.rows);
  assert.equal(summary.games, report.test_games);
  assert.ok(Math.abs(data.rows.reduce((s, row) => s + (row[7] - row[8]) ** 2, 0) / data.rows.length - report.model.brier) < 1e-8);
  const zones = groupRows(data.rows, 3, data.labels.SHOT_ZONE_BASIC);
  const leader = zones.sort((a, b) => Math.abs(b.residual) - Math.abs(a.residual))[0];
  assert.equal(leader.label, 'Restricted Area');
  assert.equal(leader.n, 13193);
  assert.ok(Math.abs(leader.residual - 126.70083988160332) < 1e-5);
  assert.ok(Math.abs(leader.low - .9785981854564341) < 1e-5);
  const celtics = data.labels.TEAM_NAME.indexOf('Boston Celtics');
  const curry = data.labels.PLAYER_NAME.indexOf('Stephen Curry');
  assert.equal(filterRows(data.rows, ['', String(celtics), String(curry), '', '', '']).length, 0);
  assert.equal(filterRows(data.rows, ['', '', '', '', '', '']).length, data.rows.length);
});

test('every exported player is selectable and contextual counts identify conflicts', () => {
  const data = JSON.parse(readFileSync(new URL('../public/shots.json', import.meta.url)));
  const blank = ['', '', '', '', '', ''];
  const sizes = data.fields.slice(0, 6).map(field => data.labels[field].length);
  for (let player = 0; player < data.labels.PLAYER_NAME.length; player++) {
    const rows = filterRows(data.rows, ['', '', String(player), '', '', '']);
    assert.ok(rows.length > 0, data.labels.PLAYER_NAME[player]);
    assert.ok(Number.isFinite(summarize(rows).expectedPct));
    for (const team of new Set(rows.map(row => row[1]))) {
      assert.equal(filterRows(data.rows, ['', String(team), String(player), '', '', '']).length,
        rows.filter(row => row[1] === team).length);
    }
  }
  const curry = data.labels.PLAYER_NAME.indexOf('Stephen Curry');
  const boston = data.labels.TEAM_NAME.indexOf('Boston Celtics');
  const counts = filterCounts(data.rows, ['', String(boston), String(curry), '', '', ''], sizes);
  assert.equal(counts[2][curry], 0);
  assert.ok(counts[1].reduce((sum, n) => sum + n, 0) > 0); // clearing team recovers Curry
  assert.ok(counts[2].reduce((sum, n) => sum + n, 0) > 0); // clearing player recovers Boston
  const all = filterCounts(data.rows, blank, sizes);
  for (const values of all) assert.equal(values.reduce((sum, n) => sum + n, 0), data.rows.length);
  assert.equal(data.coverage.evaluation_players, data.labels.PLAYER_NAME.length);
  assert.equal(data.coverage.training_only_players.length + data.coverage.evaluation_players, data.coverage.source_players);
});
