"""Filter-aware shooting calculations, shared by the UI and reproduction pipeline."""
import numpy as np
import pandas as pd


def filter_shots(df, selections):
    result = df
    for field, selected in selections.items():
        if selected:
            result = result.loc[result[field].isin(selected)]
    return result.copy()


def summarize(df):
    n = len(df)
    if not n:
        return {'attempts': 0, 'makes': 0, 'expected_makes': 0.0,
                'actual_pct': None, 'expected_pct': None, 'residual_makes': 0.0, 'delta_pp': None}
    makes, expected = int(df.SHOT_MADE_FLAG.sum()), float(df.expected.sum())
    return {'attempts': n, 'makes': makes, 'expected_makes': expected,
            'actual_pct': 100 * makes / n, 'expected_pct': 100 * expected / n,
            'residual_makes': makes - expected, 'delta_pp': 100 * (makes - expected) / n}


def situations(df, group='SHOT_ZONE_BASIC', minimum=30):
    rows = []
    for label, shots in df.groupby(group, observed=True):
        row = {'situation': str(label), **summarize(shots), 'games': shots.GAME_ID.nunique()}
        # Normal CI on game-level residual totals, allowing within-game correlation.
        residual = (shots.SHOT_MADE_FLAG - shots.expected).groupby(shots.GAME_ID).sum()
        se = float(residual.std(ddof=1) * np.sqrt(len(residual))) if len(residual) >= 5 else np.nan
        row['interval_low'] = row['residual_makes'] - 1.96 * se
        row['interval_high'] = row['residual_makes'] + 1.96 * se
        rows.append(row)
    cols = ['situation', 'attempts', 'makes', 'expected_makes', 'actual_pct', 'expected_pct',
            'residual_makes', 'delta_pp', 'games', 'interval_low', 'interval_high']
    return pd.DataFrame(rows, columns=cols).query('attempts >= @minimum').sort_values('residual_makes')


def investigation(df, minimum=30):
    table = situations(df, minimum=minimum)
    if table.empty:
        return f'No zone has at least {minimum} selected attempts. Broaden the filters before drawing conclusions.'
    row = table.loc[table.residual_makes.abs().idxmax()]
    direction = 'above' if row.residual_makes >= 0 else 'below'
    return (f"{row.situation}: {abs(row.residual_makes):.1f} makes {direction} expectation "
            f"across {row.attempts:,} attempts ({row.delta_pp:+.1f} percentage points). "
            'Review shooter mix, defensive pressure, and game film; this is a descriptive lead, not a causal finding.')
