"""Build the no-login browser dashboard from exactly the Streamlit analysis."""
import json
import math
from pathlib import Path
import shutil
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shotsense.data import ROOT, load_shots
from shotsense.model import fit_analysis


def main():
    shots, audit, source = load_shots()
    test, report, coefficients = fit_analysis(shots)
    output = ROOT / 'public'
    output.mkdir(exist_ok=True)
    categories = ['season', 'TEAM_NAME', 'PLAYER_NAME', 'SHOT_ZONE_BASIC', 'SHOT_TYPE', 'period_label']
    labels = {name: sorted(test[name].unique().tolist()) for name in categories}
    codes = {name: {value: i for i, value in enumerate(labels[name])} for name in categories}
    games = {value: i for i, value in enumerate(sorted(test.GAME_ID.unique()))}
    rows = []
    for record in test.to_dict('records'):
        x, y = record['x_ft'], record['y_ft']
        rows.append([codes[name][record[name]] for name in categories] + [
            int(record['SHOT_DISTANCE']), int(record['SHOT_MADE_FLAG']), round(record['expected'], 10),
            round(x, 1) if math.isfinite(x) else None, round(y, 1) if math.isfinite(y) else None,
            games[record['GAME_ID']]])
    payload = {'source': source, 'audit': audit, 'report': report,
               'coefficients': coefficients.to_dict('records'), 'labels': labels,
               'fields': categories + ['distance_ft', 'made', 'expected', 'x_ft', 'y_ft', 'game'],
               'rows': rows}
    (output / 'shots.json').write_text(json.dumps(payload, separators=(',', ':'), allow_nan=False), encoding='utf-8')
    shutil.copy(ROOT / 'data/licenses/UPSTREAM_LICENSE', output / 'DATA-LICENSE.txt')
    shutil.copy(ROOT / 'NOTICE', output / 'NOTICE.txt')
    (output / '.nojekyll').touch()
    print(f'Exported {len(rows):,} real held-out shots; {(output / "shots.json").stat().st_size:,} bytes')


if __name__ == '__main__':
    main()
