"""Headless Streamlit interaction tests; no external browser or service needed."""
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from shotsense.data import ROOT


class AppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = str(ROOT / 'app.py')

    def test_dashboard_filter_empty_and_reset(self):
        app = AppTest.from_file(self.app, default_timeout=180).run()
        self.assertEqual(len(app.exception), 0)
        all_attempts = app.metric[0].value
        app.multiselect(key='TEAM_NAME').select('Atlanta Hawks').run()
        self.assertEqual(len(app.exception), 0)
        self.assertNotEqual(app.metric[0].value, all_attempts)
        app.multiselect(key='TEAM_NAME').set_value([]).run()
        app.multiselect(key='PLAYER_NAME').select('Stephen Curry').run()
        app.multiselect(key='TEAM_NAME').select('Boston Celtics').run()
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any('No shots match' in item.value for item in app.warning))
        app.button(key='clear-TEAM_NAME').click().run()
        self.assertGreater(int(app.metric[0].value.replace(',', '')), 0)
        self.assertEqual(app.multiselect(key='PLAYER_NAME').value, ['Stephen Curry'])
        next(button for button in app.button if button.label == 'Reset filters').click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.metric[0].value, all_attempts)
        self.assertEqual(len(app.get('arrow_vega_lite_chart')), 3)

    def test_load_error_is_actionable(self):
        with patch('shotsense.data.load_shots', side_effect=ValueError('test unavailable')):
            # Clear shared cache so a previous success cannot mask this failure.
            import streamlit as st
            st.cache_data.clear()
            app = AppTest.from_file(self.app, default_timeout=180).run()
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any('could not be loaded' in item.value for item in app.error))


if __name__ == '__main__':
    unittest.main()
