// Rows: season, team, player, zone, type, period, distance, made, expected, x, y, game.
export function filterRows(rows, filters) {
  return rows.filter(row => filters.every((value, index) => value === '' || row[index] === Number(value)));
}
// For each filter, count matches with the OTHER filters applied. Never clear
// a selection silently; selected zero-count options remain visible for recovery.
export function filterCounts(rows, filters, sizes) {
  return sizes.map((size, column) => {
    const relaxed = filters.map((value, index) => index === column ? '' : value);
    const counts = Array(size).fill(0);
    for (const row of filterRows(rows, relaxed)) counts[row[column]]++;
    return counts;
  });
}
export function summarize(rows) {
  const n = rows.length;
  const makes = rows.reduce((s, row) => s + row[7], 0);
  const expected = rows.reduce((s, row) => s + row[8], 0);
  return {n, makes, expected, residual: makes - expected,
    actualPct: n ? 100 * makes / n : null, expectedPct: n ? 100 * expected / n : null,
    delta: n ? 100 * (makes - expected) / n : null,
    games: new Set(rows.map(row => row[11])).size};
}
export function groupRows(rows, column, labels, minimum = 30) {
  const groups = new Map();
  for (const row of rows) {
    if (!groups.has(row[column])) groups.set(row[column], []);
    groups.get(row[column]).push(row);
  }
  return [...groups.entries()].map(([code, shots]) => {
    const result = {...summarize(shots), label: labels[code]};
    const games = new Map();
    for (const row of shots) games.set(row[11], (games.get(row[11]) || 0) + row[7] - row[8]);
    const totals = [...games.values()], count = totals.length;
    const mean = result.residual / count;
    const variance = count > 1 ? totals.reduce((s, v) => s + (v - mean) ** 2, 0) / (count - 1) : 0;
    const margin = count >= 5 ? 1.96 * Math.sqrt(variance * count) : null;
    return {...result, low: margin === null ? null : result.residual - margin,
      high: margin === null ? null : result.residual + margin};
  }).filter(group => group.n >= minimum).sort((a, b) => a.residual - b.residual);
}
