"""Offline reproduction from the included checksum-verified real dataset."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shotsense.data import ROOT, load_shots
from shotsense.model import fit_analysis, calibration
from shotsense.analytics import situations, investigation


def main():
    df, audit, source = load_shots()
    test, report, coef = fit_analysis(df)
    report.update({'data_audit': audit, 'source_sha256': source['sha256'],
                   'key_finding': investigation(test)})
    out = ROOT / 'reports'
    out.mkdir(exist_ok=True)
    (out / 'evaluation.json').write_text(json.dumps(report, indent=2) + '\n')
    coef.to_csv(out / 'coefficients.csv', index=False)
    calibration(test).to_csv(out / 'calibration.csv', index=False)
    situations(test).to_csv(out / 'zones.csv', index=False)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
