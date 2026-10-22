"""Validate the actual publisher schema; never silently substitute demo data."""
from pathlib import Path
import hashlib
import io
import json
import tarfile
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ['GAME_ID', 'GAME_EVENT_ID', 'PLAYER_NAME', 'TEAM_NAME', 'PERIOD',
            'SHOT_TYPE', 'SHOT_ZONE_BASIC', 'SHOT_DISTANCE', 'SHOT_MADE_FLAG',
            'SHOT_ATTEMPTED_FLAG', 'GAME_DATE']


def clean_shots(raw):
    missing = sorted(set(REQUIRED) - set(raw.columns))
    if missing:
        raise ValueError('Missing required fields: ' + ', '.join(missing))
    df = raw.copy()
    if df.duplicated(['GAME_ID', 'GAME_EVENT_ID']).any():
        raise ValueError('Duplicate game/event keys; resolve upstream duplicates first.')
    for col in ['SHOT_DISTANCE', 'PERIOD', 'SHOT_MADE_FLAG', 'SHOT_ATTEMPTED_FLAG']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df['date'] = pd.to_datetime(df.GAME_DATE.astype(str), format='%Y%m%d', errors='coerce')
    valid = (df.SHOT_MADE_FLAG.isin([0, 1]) & df.SHOT_ATTEMPTED_FLAG.eq(1)
             & df.SHOT_DISTANCE.between(0, 95) & df.PERIOD.between(1, 20)
             & df.PERIOD.mod(1).eq(0) & df.date.notna()
             & df.SHOT_TYPE.isin(['2PT Field Goal', '3PT Field Goal']))
    for col in ['PLAYER_NAME', 'TEAM_NAME', 'SHOT_ZONE_BASIC']:
        valid &= df[col].notna() & df[col].astype(str).str.strip().ne('')
    df = df.loc[valid].copy()
    if df.empty:
        raise ValueError('No valid shot attempts remain after validation.')
    df['season'] = df.date.map(lambda d: f'{d.year if d.month >= 7 else d.year - 1}-{str(d.year + 1 if d.month >= 7 else d.year)[-2:]}')
    df['period_label'] = df.PERIOD.map(lambda p: f'Q{int(p)}' if p <= 4 else 'Overtime')
    for col in ['LOC_X', 'LOC_Y']:
        df[col] = pd.to_numeric(df[col], errors='coerce') if col in df else np.nan
    # NBA shot chart locations use tenths of a foot relative to the basket.
    df['x_ft'], df['y_ft'] = df.LOC_X / 10, df.LOC_Y / 10
    return df.reset_index(drop=True), {'input_rows': len(raw), 'valid_rows': len(df), 'dropped_rows': int((~valid).sum())}


def load_shots(root=ROOT):
    root = Path(root)
    source = json.loads((root / 'data/source.json').read_text())
    payload = (root / 'data/raw' / source['filename']).read_bytes()
    if hashlib.sha256(payload).hexdigest() != source['sha256']:
        raise ValueError('Dataset checksum mismatch. Restore the pinned archive with scripts/download_data.py.')
    with tarfile.open(fileobj=io.BytesIO(payload), mode='r:xz') as archive:
        # Read a named file in memory; never extract archive paths to disk.
        member = archive.extractfile('shotdetail_2023.csv')
        if member is None:
            raise ValueError('Shot CSV missing from archive.')
        raw = pd.read_csv(member, dtype={'GAME_ID': str, 'GAME_EVENT_ID': str})
    df, audit = clean_shots(raw)
    return df, audit, source
