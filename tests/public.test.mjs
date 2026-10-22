import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {filterRows, summarize, groupRows} from '../public/analytics.mjs';

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
