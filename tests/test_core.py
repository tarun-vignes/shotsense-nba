import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
import pandas as pd
from shotsense.data import load_shots, clean_shots, ROOT
from shotsense.model import build_model, chronological_split, evaluate, FEATURES, calibration
from shotsense.analytics import summarize, situations, filter_shots, investigation


def fixture():
    n = 100
    return pd.DataFrame({
        'GAME_ID': [str(i // 10) for i in range(n)], 'GAME_EVENT_ID': range(n),
        'PLAYER_NAME': ['Player A'] * n, 'TEAM_NAME': ['Team A'] * n,
        'PERIOD': [1, 2, 3, 4] * 25, 'SHOT_TYPE': ['2PT Field Goal'] * n,
        'SHOT_ZONE_BASIC': ['Mid-Range'] * n, 'SHOT_DISTANCE': [5, 10, 15, 20] * 25,
        'SHOT_MADE_FLAG': [0, 1] * 50, 'SHOT_ATTEMPTED_FLAG': [1] * n,
        'GAME_DATE': [20240101 + i // 10 for i in range(n)]})


class DataTests(unittest.TestCase):
    def test_real_archive_schema_checksum_and_coverage(self):
        df, audit, source = load_shots()
        self.assertFalse(source['synthetic'])
        self.assertEqual(source['license'], 'Apache-2.0')
        self.assertGreater(len(df), 100000)
        self.assertEqual(audit['input_rows'], audit['valid_rows'] + audit['dropped_rows'])
        self.assertEqual(set(df.season), {'2023-24'})
        self.assertFalse(df.duplicated(['GAME_ID', 'GAME_EVENT_ID']).any())

    def test_missing_schema_is_actionable(self):
        with self.assertRaisesRegex(ValueError, 'SHOT_DISTANCE'):
            clean_shots(fixture().drop(columns='SHOT_DISTANCE'))

    def test_bad_rows_excluded_and_missing_coordinates_allowed(self):
        raw = fixture()
        raw.loc[0, 'SHOT_DISTANCE'] = -1
        raw.loc[1, 'SHOT_MADE_FLAG'] = 2
        raw.loc[2, 'GAME_DATE'] = 20240231
        df, audit = clean_shots(raw)
        self.assertEqual(audit['dropped_rows'], 3)
        self.assertTrue(df.x_ft.isna().all())

    def test_duplicate_events_rejected(self):
        raw = fixture()
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            clean_shots(pd.concat([raw, raw.iloc[:1]]))

    def test_corrupt_archive_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'data/raw').mkdir(parents=True)
            (root / 'data/source.json').write_text((ROOT / 'data/source.json').read_text())
            name = json.loads((ROOT / 'data/source.json').read_text())['filename']
            (root / 'data/raw' / name).write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                load_shots(root)


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.df, _ = clean_shots(fixture())

    def test_temporal_split_has_no_game_leakage(self):
        train, test = chronological_split(self.df)
        self.assertLess(train.date.max(), test.date.min())
        self.assertFalse(set(train.GAME_ID) & set(test.GAME_ID))
        self.assertEqual(len(train) + len(test), len(self.df))

    def test_unseen_categories_and_missing_distance_predict(self):
        train, test = chronological_split(self.df)
        model = build_model().fit(train[FEATURES], train.SHOT_MADE_FLAG)
        test.loc[:, 'SHOT_ZONE_BASIC'] = 'Never seen in training'
        test.loc[:, 'PERIOD'] = 12
        test['SHOT_DISTANCE'] = np.nan
        p = model.predict_proba(test[FEATURES])[:, 1]
        self.assertTrue(np.isfinite(p).all())
        self.assertTrue(((p >= 0) & (p <= 1)).all())
        self.assertNotIn('SHOT_MADE_FLAG', FEATURES)
        self.assertNotIn('PLAYER_NAME', FEATURES)

    def test_known_evaluation_values(self):
        result = evaluate([0, 1], [0.25, 0.75])
        self.assertAlmostEqual(result['brier'], .0625)
        self.assertAlmostEqual(result['log_loss'], -np.log(.75))
        self.assertEqual(result['roc_auc'], 1)
        self.assertEqual(evaluate([0, 1], [.5, .5])['roc_auc'], .5)
        with self.assertRaises(ValueError):
            evaluate([0, 1], [0.2, np.nan])

    def test_preprocessing_uses_training_only(self):
        train, _ = chronological_split(self.df)
        model = build_model().fit(train[FEATURES], train.SHOT_MADE_FLAG)
        scaler = model.named_steps['features'].named_transformers_['distance'].named_steps['scale']
        self.assertAlmostEqual(scaler.mean_[0], train.SHOT_DISTANCE.mean())


class AnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.df, _ = clean_shots(fixture())
        self.df['expected'] = .4

    def test_display_calculation(self):
        result = summarize(self.df)
        self.assertEqual(result['attempts'], 100)
        self.assertEqual(result['makes'], 50)
        self.assertAlmostEqual(result['expected_makes'], 40)
        self.assertAlmostEqual(result['residual_makes'], 10)
        self.assertAlmostEqual(result['delta_pp'], 10)

    def test_filters_update_every_calculation(self):
        filtered = filter_shots(self.df, {'PERIOD': [1]})
        self.assertEqual(len(filtered), 25)
        self.assertEqual(summarize(filtered)['makes'], 0)
        self.assertAlmostEqual(summarize(filtered)['expected_makes'], 10)
        self.assertEqual(situations(filtered, minimum=10).iloc[0].attempts, 25)

    def test_empty_state_and_sample_threshold(self):
        empty = filter_shots(self.df, {'PLAYER_NAME': ['absent']})
        self.assertEqual(summarize(empty)['attempts'], 0)
        self.assertIsNone(summarize(empty)['actual_pct'])
        self.assertTrue(situations(empty).empty)
        self.assertIn('No zone', investigation(empty))
        self.assertTrue(situations(self.df, minimum=101).empty)

    def test_calibration_bins_conserve_sample(self):
        bins = calibration(self.df)
        self.assertEqual(bins.attempts.sum(), len(self.df))
        self.assertAlmostEqual(bins.iloc[0].actual, .5)

    def test_intervals_require_enough_games(self):
        one_game = self.df.iloc[:10]
        row = situations(one_game, minimum=1).iloc[0]
        self.assertTrue(np.isnan(row.interval_low))


if __name__ == '__main__':
    unittest.main()
