"""One fixed, interpretable model; all preprocessing fitted on training data only."""
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

NUMERIC = ['SHOT_DISTANCE']
CATEGORICAL = ['SHOT_ZONE_BASIC', 'SHOT_TYPE', 'PERIOD']
FEATURES = NUMERIC + CATEGORICAL


def chronological_split(df, fraction=0.8):
    if not 0 < fraction < 1:
        raise ValueError('Training fraction must be between zero and one.')
    dates = sorted(df.date.unique())
    if len(dates) < 5:
        raise ValueError('At least five distinct game dates are required.')
    cutoff = dates[min(len(dates) - 1, max(1, int(len(dates) * fraction)))]
    train, test = df.loc[df.date < cutoff].copy(), df.loc[df.date >= cutoff].copy()
    if set(train.GAME_ID) & set(test.GAME_ID):
        raise ValueError('A game crosses the train/test split.')
    if train.SHOT_MADE_FLAG.nunique() != 2 or test.SHOT_MADE_FLAG.nunique() != 2:
        raise ValueError('Both splits must contain makes and misses.')
    return train, test


def build_model():
    numeric = Pipeline([('impute', SimpleImputer(strategy='median')),
                        ('scale', StandardScaler())])
    preprocess = ColumnTransformer([
        ('distance', numeric, NUMERIC),
        ('context', OneHotEncoder(handle_unknown='ignore'), CATEGORICAL)])
    return Pipeline([('features', preprocess),
                     ('logistic', LogisticRegression(C=1.0, max_iter=500, random_state=42))])


def evaluate(y, probability):
    p = np.asarray(probability, dtype=float)
    if len(p) != len(y) or not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError('Expected a finite probability in [0, 1] for every outcome.')
    return {'brier': float(brier_score_loss(y, p)),
            'log_loss': float(log_loss(y, p, labels=[0, 1])),
            'roc_auc': float(roc_auc_score(y, p)) if len(set(y)) == 2 else None}


def calibration(df):
    bins = pd.cut(df.expected, np.linspace(0, 1, 11), include_lowest=True)
    return df.groupby(bins, observed=True).agg(attempts=('expected', 'size'),
        predicted=('expected', 'mean'), actual=('SHOT_MADE_FLAG', 'mean')).reset_index(drop=True)


def fit_analysis(df):
    train, test = chronological_split(df)
    model = build_model().fit(train[FEATURES], train.SHOT_MADE_FLAG)
    test['expected'] = model.predict_proba(test[FEATURES])[:, 1]
    rate = float(train.SHOT_MADE_FLAG.mean())
    test['baseline'] = rate
    names = model.named_steps['features'].get_feature_names_out()
    coefficients = pd.DataFrame({'feature': names, 'log_odds_coefficient': model.named_steps['logistic'].coef_[0]})
    report = {
        'train_rows': len(train), 'test_rows': len(test),
        'train_games': train.GAME_ID.nunique(), 'test_games': test.GAME_ID.nunique(),
        'train_start': str(train.date.min().date()), 'train_end': str(train.date.max().date()),
        'test_start': str(test.date.min().date()), 'test_end': str(test.date.max().date()),
        'baseline_train_make_rate': rate, 'model': evaluate(test.SHOT_MADE_FLAG, test.expected),
        'baseline': evaluate(test.SHOT_MADE_FLAG, test.baseline),
        'intercept': float(model.named_steps['logistic'].intercept_[0]),
        'iterations': int(model.named_steps['logistic'].n_iter_[0]),
        'features': FEATURES, 'shot_clock_available': False,
    }
    return test, report, coefficients
