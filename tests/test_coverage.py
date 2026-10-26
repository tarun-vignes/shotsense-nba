"""Audit every player/team against the pinned archive, not hand-picked stars."""
import json
import unittest
from collections import Counter
from shotsense.data import ROOT, load_shots
from shotsense.model import chronological_split


class CoverageTests(unittest.TestCase):
    def test_public_export_matches_every_source_evaluation_player_and_team(self):
        shots, audit, _ = load_shots()
        train, held_out = chronological_split(shots)
        data = json.loads((ROOT / 'public/shots.json').read_text(encoding='utf-8'))
        labels = data['labels']
        actual = Counter((labels['PLAYER_NAME'][row[2]], labels['TEAM_NAME'][row[1]]) for row in data['rows'])
        expected = Counter(zip(held_out.PLAYER_NAME, held_out.TEAM_NAME))
        self.assertEqual(actual, expected)
        self.assertEqual(audit['dropped_rows'], 0)
        absent = set(shots.PLAYER_NAME) - set(held_out.PLAYER_NAME)
        self.assertEqual({row['player'] for row in data['coverage']['training_only_players']}, absent)
        for row in data['coverage']['training_only_players']:
            source = shots.loc[shots.PLAYER_NAME.eq(row['player'])]
            self.assertEqual(len(source), row['source_attempts'])
            self.assertEqual(str(source.date.max().date()), row['last_date'])
            self.assertTrue(source.date.max() < held_out.date.min())
        self.assertEqual(len(train) + len(held_out), len(shots))


if __name__ == '__main__':
    unittest.main()
