"""Run with: python -m streamlit run app.py"""
import json
import altair as alt
import pandas as pd
import streamlit as st
from shotsense.data import ROOT, load_shots
from shotsense.model import fit_analysis, calibration
from shotsense.analytics import filter_shots, summarize, situations, investigation

st.set_page_config(page_title='ShotSense | NBA shot intelligence', page_icon='🏀', layout='wide')
st.markdown('''<style>
.stApp {background:#f5f7fb;color:#18293e}
.block-container {padding-top:2.2rem;max-width:1450px}
h1,h2,h3 {letter-spacing:-.035em;color:#10243b}
div[data-testid="stMetric"] {background:white;border:1px solid #dce3ed;border-radius:14px;padding:20px}
section[data-testid="stSidebar"] {background:#eaf0f6}
.eyebrow {font-size:12px;font-weight:700;letter-spacing:.15em;color:#22726c}
.intro {font-size:19px;color:#516173;max-width:880px}
</style>''', unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def analysis(archive_stamp):
    df, audit, source = load_shots()
    test, report, coefficients = fit_analysis(df)
    missing = df.loc[~df.PLAYER_NAME.isin(test.PLAYER_NAME.unique())]
    coverage = {'source_players': df.PLAYER_NAME.nunique(),
                'training_only': missing.groupby('PLAYER_NAME').size().to_dict()}
    return test, report, coefficients, audit, source, coverage


def main():
    st.markdown('<div class="eyebrow">SHOTSENSE / NBA ANALYTICS LAB</div>', unsafe_allow_html=True)
    st.title('Find the shots worth a second look.')
    st.markdown('<p class="intro">Which shot situations are outperforming or underperforming expectations, and what should a coach or analyst investigate?</p>', unsafe_allow_html=True)
    try:
        manifest = json.loads((ROOT / 'data/source.json').read_text())
        stamp = (ROOT / 'data/raw' / manifest['filename']).stat().st_mtime_ns
        with st.spinner('Validating real shot data and fitting the training-only model…'):
            shots, report, coefficients, audit, source, coverage = analysis(stamp)
    except Exception as error:
        st.error(f'Shot data could not be loaded: {error}')
        st.info('Restore the bundled archive with `python scripts/download_data.py`, then restart. No synthetic data is substituted.')
        return

    st.caption(f"REAL DATA · 2023–24 regular season archive · Held-out dates {report['test_start']} to {report['test_end']} · {len(shots):,} evaluation attempts")
    st.sidebar.title('Explore the evidence')
    st.sidebar.caption('All charts use held-out shots. Empty selections mean all available values. Filters intersect. Option counts are total held-out shots; counts beneath selections apply the other active filters.')
    fields = [('season', 'Season'), ('TEAM_NAME', 'Team'), ('PLAYER_NAME', 'Player'),
              ('SHOT_ZONE_BASIC', 'Shot zone'), ('SHOT_TYPE', 'Shot type'), ('period_label', 'Period')]
    selections = {}
    current = {field: st.session_state.get(field, []) for field, _ in fields}
    # Keep selections visible, even when incompatible; never silently reset them.
    for field, label in fields:
        counts = filter_shots(shots, {name: values for name, values in current.items() if name != field})[field].value_counts()
        totals = shots[field].value_counts()
        selections[field] = st.sidebar.multiselect(label, sorted(shots[field].unique()), key=field,
            format_func=lambda value, totals=totals: f'{value} ({totals.get(value, 0):,} shots)')
        if selections[field]:
            st.sidebar.caption('With other filters: ' + '; '.join(f'{value}: {counts.get(value, 0):,} shots' for value in selections[field]))
    minimum = st.sidebar.slider('Minimum attempts per situation', 10, 200, 30, 10)
    def reset_filters():
        for field, _ in fields:
            st.session_state[field] = []
    st.sidebar.button('Reset filters', on_click=reset_filters)
    selected = filter_shots(shots, selections)
    active = ' · '.join(f"{label}: {', '.join(selections[field])}" for field, label in fields if selections[field]) or 'All available held-out shots'
    st.caption('ACTIVE FILTERS — ' + active)
    with st.expander('Which players are covered?'):
        st.write(f"{shots.PLAYER_NAME.nunique()} of {coverage['source_players']} source players have held-out attempts. {len(coverage['training_only'])} appear only in the training dates. Players absent from the archive cannot be shown. Training shots are not mixed into evaluation.")
        st.write('Training-only players (source attempts): ' + '; '.join(f'{name} ({count:,})' for name, count in coverage['training_only'].items()))
        st.caption('The minimum-attempt threshold affects situation tables, not player availability or summary metrics.')
    if selected.empty:
        st.warning('No shots match these filters. Clear a player, team, or situation filter to broaden your view.')
        def clear_filter(field):
            st.session_state[field] = []
        for field, label in fields:
            if selections[field]:
                count = len(filter_shots(shots, {name: values for name, values in selections.items() if name != field}))
                if count:
                    st.button(f'Clear {label.lower()} — show {count:,} shots', key=f'clear-{field}', on_click=clear_filter, args=(field,))
        return
    total = summarize(selected)
    st.info(investigation(selected, minimum))
    a, b, c, d = st.columns(4)
    a.metric('Shot attempts', f"{total['attempts']:,}", help='Selected held-out field goal attempts; free throws excluded.')
    b.metric('Actual FG%', f"{total['actual_pct']:.1f}%", help=f"{total['makes']:,} makes")
    c.metric('Expected FG%', f"{total['expected_pct']:.1f}%", help='Mean shot-make probability, not expected points.')
    d.metric('Makes above expectation', f"{total['residual_makes']:+.1f}", f"{total['delta_pp']:+.1f} pp", delta_color='off')
    st.caption(f"{total['makes']:,} actual makes vs {total['expected_makes']:,.1f} expected makes · {selected.GAME_ID.nunique():,} games · FG% = field goal make percentage · pp = percentage points")

    explore, model_tab, source_tab = st.tabs(['Situation explorer', 'Model & evaluation', 'Data & attribution'])
    with explore:
        left, right = st.columns([1.15, 1])
        zones = situations(selected, minimum=minimum)
        with left:
            st.subheader('Where outcomes diverge')
            st.caption(f'Shot-zone comparison · zones with ≥{minimum} attempts · hover for sample sizes')
            if zones.empty:
                st.info('No zone reaches the minimum sample size. Lower the threshold or broaden the filters.')
            else:
                long = zones.melt(id_vars=['situation', 'attempts'], value_vars=['actual_pct', 'expected_pct'], var_name='outcome', value_name='FG%')
                long['outcome'] = long.outcome.map({'actual_pct': 'Actual', 'expected_pct': 'Expected'})
                chart = alt.Chart(long).mark_bar(cornerRadiusEnd=3).encode(
                    y=alt.Y('situation:N', title=None), yOffset='outcome:N',
                    x=alt.X('FG%:Q', scale=alt.Scale(domain=[0, 100]), title='Field goal make rate (%)'),
                    color=alt.Color('outcome:N', scale=alt.Scale(domain=['Actual', 'Expected'], range=['#167d8d', '#c4cfdd']), title=None),
                    tooltip=['situation:N', 'outcome:N', alt.Tooltip('FG%:Q', format='.1f'), 'attempts:Q']).properties(height=340)
                st.altair_chart(chart, use_container_width=True)
        with right:
            st.subheader('Shot locations')
            coords = selected.loc[selected.x_ft.between(-25, 25) & selected.y_ft.between(-5.25, 42)].copy()
            clipped = len(selected) - len(coords)
            if coords.empty:
                st.info('No usable half-court coordinates in this selection. Zone results remain available.')
            else:
                sample = coords.sample(min(4000, len(coords)), random_state=42).copy()
                sample['Outcome'] = sample.SHOT_MADE_FLAG.map({1: 'Made', 0: 'Missed'})
                points = alt.Chart(sample).mark_circle(size=15, opacity=.4).encode(
                    x=alt.X('x_ft:Q', title='Feet left / right of basket', scale=alt.Scale(domain=[-25, 25])),
                    y=alt.Y('y_ft:Q', title='Feet from basket toward midcourt', scale=alt.Scale(domain=[-5.25, 42])),
                    color=alt.Color('Outcome:N', scale=alt.Scale(domain=['Made', 'Missed'], range=['#167d8d', '#de8651'])),
                    tooltip=['PLAYER_NAME:N', 'SHOT_ZONE_BASIC:N', 'Outcome:N', alt.Tooltip('expected:Q', format='.1%'), 'SHOT_DISTANCE:Q'])
                rim = alt.Chart(pd.DataFrame({'x': [0], 'y': [0]})).mark_point(shape='circle', size=160, color='#18293e').encode(x='x:Q', y='y:Q')
                st.altair_chart((points + rim).properties(height=340), use_container_width=True)
                st.caption(f"Basket at (0, 0). Showing {len(sample):,} of {len(coords):,} half-court shots; {clipped:,} outside view or missing coordinates. All calculations use every selected attempt.")

        st.subheader('Investigation queue')
        grouping = st.selectbox('Compare situations by', ['Shot zone', 'Shot type', 'Period', 'Player', 'Team'])
        group = {'Shot zone': 'SHOT_ZONE_BASIC', 'Shot type': 'SHOT_TYPE', 'Period': 'period_label', 'Player': 'PLAYER_NAME', 'Team': 'TEAM_NAME'}[grouping]
        table = situations(selected, group, minimum)
        if table.empty:
            st.info('No situation meets the sample threshold.')
        else:
            st.dataframe(table.round(2), use_container_width=True, hide_index=True)
        st.caption('Residual makes = actual − expected. Interval bounds are approximate 95% game-cluster intervals on residual makes; fewer than 5 games yields no interval. These omit model uncertainty and are not corrected for searching many groups. Small samples and extreme rankings can reflect chance.')
        st.download_button('Download filtered situation table (CSV)', table.to_csv(index=False), 'shotsense-situations.csv', 'text/csv')
        st.download_button('Download selected held-out shots (CSV)', selected[['season', 'date', 'GAME_ID', 'PLAYER_NAME', 'TEAM_NAME', 'SHOT_ZONE_BASIC', 'SHOT_TYPE', 'PERIOD', 'SHOT_DISTANCE', 'SHOT_MADE_FLAG', 'expected']].to_csv(index=False), 'shotsense-selected-shots.csv', 'text/csv')

    with model_tab:
        st.subheader('A transparent expectation, tested on later games')
        st.write('Logistic regression uses shot distance (feet, standardized), zone, two- versus three-point type, and period. Categorical fields are one-hot encoded. Shot-clock time is absent and is not inferred from time remaining in the period. Player and team identities are excluded so residuals can flag shooter and team differences.')
        st.write(f"Training: {report['train_start']}–{report['train_end']} ({report['train_rows']:,} attempts, {report['train_games']:,} games). Evaluation: {report['test_start']}–{report['test_end']} ({report['test_rows']:,} attempts, {report['test_games']:,} games). The first 80% of distinct game dates train the model; later dates test it. No game appears in both splits. No test-driven tuning or refitting.")
        metric_rows = []
        for name in ['baseline', 'model']:
            metric_rows.append({'Predictor': 'Constant training FG% baseline' if name == 'baseline' else 'Shot-context logistic regression', **report[name]})
        st.dataframe(pd.DataFrame(metric_rows).round(5), use_container_width=True, hide_index=True)
        improvement = report['baseline']['brier'] - report['model']['brier']
        st.write(f"Brier change versus baseline: {improvement:+.5f} (positive means improvement). Brier and log loss measure probability error; lower is better. ROC AUC measures ranking; higher is better. These metrics use the complete held-out set and stay fixed when filters change.")
        st.subheader('Calibration for the selected shots')
        cal = calibration(selected)
        curve = alt.Chart(cal).mark_line(point=True, color='#167d8d').encode(x=alt.X('predicted:Q', scale=alt.Scale(domain=[0, 1]), title='Mean predicted make probability'), y=alt.Y('actual:Q', scale=alt.Scale(domain=[0, 1]), title='Observed make fraction'), tooltip=['attempts:Q', alt.Tooltip('predicted:Q', format='.3f'), alt.Tooltip('actual:Q', format='.3f')])
        diagonal = alt.Chart(pd.DataFrame({'p': [0, 1]})).mark_line(color='#9caabc', strokeDash=[5, 5]).encode(x='p:Q', y='p:Q')
        st.altair_chart((curve + diagonal).properties(height=270), use_container_width=True)
        st.caption('Ten fixed probability bins; empty bins omitted. Dashed diagonal = perfect calibration. Few attempts per bin can produce unstable rates.')
        with st.expander('Inspect model coefficients'):
            st.write(f"Intercept: {report['intercept']:.5f}. logit(p) = intercept + sum(coefficient × encoded feature). L2 regularization, C=1. Distance coefficient is per training standard deviation. Correlated zone/type/distance terms are not independent causal effects.")
            st.dataframe(coefficients.round(5), use_container_width=True, hide_index=True)
        st.warning('Use this as a film-review triage tool. Historical archive coverage may be incomplete; it is not a current NBA feed. Defense, fatigue, injuries, score margin, and shooter skill are omitted. Residuals reflect omitted context and randomness as well as performance. FG% does not measure possession value or reward three-pointers with extra points. Do not convert this ranking directly into shot-selection advice.')

    with source_tab:
        st.subheader('Real data. Reproducible provenance.')
        st.markdown('[NBA shot detail archive — Vladislav Shufinskiy](https://github.com/shufinskiy/nba_data), originally collected from NBA statistics sources by the publisher. Dataset: **Apache-2.0**; ShotSense code: **MIT**. Upstream license and documentation are included in `data/licenses/`. No live NBA requests or scraping occur in this application.')
        st.write(f"Validated {audit['valid_rows']:,} of {audit['input_rows']:,} rows; removed {audit['dropped_rows']:,} invalid rows. Exact observed dates and evaluation counts are reported above; the season label does not establish complete coverage.")
        st.json(source)
        st.caption('Reproduce: python scripts/reproduce.py · Test: python -m unittest discover -s tests -v')
        st.markdown('Prepared for [AQX Sports Analytics Data Bowl 4.0](https://aqxanalyticsfour.devpost.com/). Student eligibility must be verified by the entrant. This project is not affiliated with or endorsed by the NBA.')


if __name__ == '__main__':
    main()
