# ShotSense

**Find the NBA shots worth a second look.** An interactive dashboard answering: *Which shot situations are outperforming or underperforming expectations, and what should a coach or analyst investigate?*

Prepared for AQX Sports Analytics Data Bowl 4.0. Repository: https://github.com/tarun-vignes/shotsense-nba.

## View in your browser

The public browser dashboard is deployed from `public/` through GitHub Pages:

**https://tarun-vignes.github.io/shotsense-nba/**

It needs no login or installation. Filter real held-out shots by season, team, player, zone, type and period; compare actual and expected shooting, inspect the shot map, and download situation tables. All 46,251 held-out shots are included. The model is fitted in Python at build time, not retrained in the browser. The full Streamlit application below additionally provides calibration charts and shot-level CSV exports.

### Player availability and empty filters

The pinned archive contains **568 players**. **485** have attempts in the held-out window, March 12–April 14, 2024; the other **83** have source shots only before that window. For example, Ja Morant and Zach LaVine occur in the archive but have no evaluation-period attempts. The **Which players are covered?** disclosure lists all training-only players and source attempt counts. Players absent from the archive are unavailable. Training shots are never presented as held-out results to fill a gap.

All 485 evaluation players are included without a player-level minimum. Filters intersect: a player on another team, a zone they did not shoot from, or an incompatible period/type can correctly return no shots. Browser options show counts after the other filters and disable zero-match choices; Streamlit options show stable total counts with contextual counts beneath selected fields. Empty selections have targeted recovery buttons, and Reset filters restores all evaluation shots. The minimum-attempt setting limits situation tables and zone findings, **not** player summaries. A low-sample player can have metrics even when no situation reaches that threshold.

To rebuild the browser dataset after changing the analysis, run `python scripts/reproduce.py` and `python scripts/build_public.py`, then `node --test tests/public.test.mjs` (Node 22+). Commit the generated `public/shots.json` along with the source. `.github/workflows/pages.yml` validates and deploys the public dashboard on pushes to `main`.

## Run locally

Use **Python 3.11–3.13** (verified on Windows with Python 3.13.12). From this folder in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open the Local URL printed by Streamlit, normally http://localhost:8501. No API keys, accounts, database, or data download are needed. The real, compressed dataset is included. First load validates 218,701 shots and trains the model; subsequent filter interactions use the cached analysis. Stop with Ctrl+C.

On macOS/Linux replace `.\.venv\Scripts\python.exe` with `.venv/bin/python`. `requirements.txt` pins direct dependencies; `requirements-lock.txt` records the complete tested Windows environment for exact package-version reference. To reproduce that environment on Python 3.13, install with `-r requirements-lock.txt` instead.

## What the app does

- Filters available seasons (this release has one), teams, players, shot zones, shot types and periods. Filters intersect; empty selections mean all values.
- Displays actual FG%, expected FG%, actual and expected makes, and residual makes with visible attempts, games and percentage-point units.
- Compares zones, plots shot locations, and ranks zones, players, teams, types or periods for investigation.
- Recomputes the finding, charts, calibration and downloadable tables for selected **held-out shots only**. The complete held-out model evaluation stays fixed and is labeled accordingly.
- Shows model coefficients, calibration, provenance, limitations, loading, empty and error states. Data errors never trigger hidden synthetic substitution.

The responsive Streamlit layout uses collapsible filters and scrollable tables. Shot locations are an explicit deterministic sample of up to 4,000 points for performance; all summaries use every selected attempt. The basket is the origin, locations are feet (upstream tenths of feet divided by ten), and shots outside the plotted half-court are counted in the caption. Zone comparisons remain available even when coordinates are missing.

## Real dataset and separate license

Publisher: **Vladislav Shufinskiy**, [NBA play-by-play and shotdetails archive](https://github.com/shufinskiy/nba_data). The publisher documents NBA statistics sources and provides public archive downloads for research. ShotSense downloads only the publisher's public GitHub file; it does not scrape or call NBA endpoints.

- File: `shotdetail_2023.tar.xz`, regular-season **2023–24** shot details, 2,812,692 bytes, bundled unmodified.
- Pinned upstream commit: `e829d4678be1e075f99e5d41a1c5f97089be446b`.
- [Exact public download](https://raw.githubusercontent.com/shufinskiy/nba_data/e829d4678be1e075f99e5d41a1c5f97089be446b/datasets/shotdetail_2023.tar.xz).
- SHA-256: `303e71f967c199568b345cd73a75e595f1f99532cca3e6ce59afb286b63f840d`.
- **Dataset license: Apache-2.0**, as published in the upstream repository; full license and documentation are preserved in `data/licenses/`. See [NOTICE](NOTICE) and [source manifest](data/source.json). The ShotSense MIT license does not replace the dataset license or grant rights in NBA trademarks.
- Observed coverage: October 24, 2023–April 14, 2024, 218,701 attempts in 1,230 game IDs. This is an archived dataset, not a live feed or an independent guarantee of exhaustive NBA coverage.
- Actual verified columns include game/event keys, player/team, make flag, attempted flag, shot distance, basic/area/range zone, 2PT/3PT type, action type, period, remaining period minutes/seconds, location and date. **There is no shot-clock time.** Remaining game-period time is not shot-clock time and is not substituted for it.

This is **not synthetic demo mode**. Small constructed test fixtures are used only for deterministic unit tests; all dashboard outcomes and report metrics come from the bundled real archive.

## Methodology

1. Verify the archive checksum before reading its named CSV in memory. Never extract arbitrary archive paths.
2. Require the observed schema and reject duplicate game/event keys. Exclude non-attempts, invalid outcomes, invalid dates, missing player/team/zone, unrecognized shot types, out-of-range distances and invalid periods. Missing coordinates are allowed. The actual audit retained **218,701 / 218,701** rows, with **0** dropped.
3. Sort distinct game dates; use the first 80% of dates for training and later dates for testing. This avoids splitting a game across samples. Training: **172,450 shots / 967 games**, October 24, 2023–March 11, 2024. Test: **46,251 shots / 263 games**, March 12–April 14, 2024. All dashboard data is test data.
4. Baseline: constant training make rate, **47.4874%**. Logistic regression: standardized distance, one-hot basic zone, 2PT/3PT shot type and period; L2 penalty with `C=1`, maximum 500 iterations, fixed random state 42. It converged in 34 iterations. No hyperparameter search uses test data. Numeric median imputation, scaling and category vocabulary are fitted only on training data. Unseen categories are ignored safely. There is no player/team identity or post-shot outcome input.
5. Expected makes = sum of predicted make probabilities. Residual makes = actual makes − expected makes. Difference in percentage points = 100 × residual makes / attempts. These are make counts and FG%, **not expected points**.
6. Grouped intervals sum residuals within each game, then use `1.96 × sample_SD(game residual totals) × sqrt(number of games)` around the total residual. They are approximate game-cluster intervals, conditional on the fitted model; no interval is shown below five games. They omit training/model uncertainty and are not multiple-comparison adjusted. They are exploratory, not formal discovery claims.

## Measured evaluation

Full held-out sample, generated by `python scripts/reproduce.py`:

| Predictor | Brier ↓ | Log loss ↓ | ROC AUC ↑ |
| --- | ---: | ---: | ---: |
| Constant training make rate | 0.24924 | 0.69163 | 0.50000 |
| Shot-context logistic regression | 0.23210 | 0.65643 | 0.64315 |

Brier improves by **0.01714** (about **6.88%** relative to baseline). Lower Brier/log loss means better probability predictions; AUC measures ranking and does not establish calibration. The app displays calibration over ten fixed probability bins; `reports/calibration.csv` contains the full held-out curve.

The largest absolute zone residual with at least 30 attempts is **Restricted Area: +126.7 makes across 13,193 attempts (+1.0 percentage point)**. This is a measured descriptive lead. Investigate whether shooter mix, defensive pressure, or other omitted context explains it before changing strategy. It is not proof of repeatable overperformance. Other zone results and approximate intervals are in `reports/zones.csv`.

Machine-readable results: [evaluation](reports/evaluation.json), [coefficients](reports/coefficients.csv), [zone comparisons](reports/zones.csv). Reports are derived artifacts and can be regenerated offline.

## Reproduce and verify

```powershell
.\.venv\Scripts\python.exe scripts/reproduce.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip check
```

To restore the bundled archive, if missing or corrupted (requires public internet access):

```powershell
.\.venv\Scripts\python.exe scripts/download_data.py
```

The downloader checks the pinned SHA-256 before writing. It does not silently switch sources or update seasons.

**Verified locally:** all **16 tests passed**, covering real archive loading, corruption, schema, invalid rows, duplicate keys, unseen features and missing distance, chronological separation, training-only preprocessing, known evaluation values, displayed residual arithmetic, filter calculations, calibration/sample conservation, sample thresholds, interval behavior, and Streamlit interactions (filter, empty selection, reset, load failure). `pip check` passed. The application CI and GitHub Pages deployment both completed successfully on GitHub Actions. Two additional Node tests passed for browser calculations and parity with Python results. Headless interaction tests exercise the app; no visual browser or mobile-device inspection has been performed. See [verification record](reports/verification.md) for the local server smoke-check outcome.

## Limits

One historical season and one temporal holdout do not establish future or cross-season performance. Defense, defender distance, shooter skill, injuries, fatigue, shot-clock pressure, score margin and possession context are unavailable or unused. A simple additive model misses nonlinear and interaction effects; correlated distance/zone/type coefficients are not causal. Identities are omitted intentionally, so player ability can appear as residual performance. Ranking many groups creates selection bias and small samples can look extreme. Three-point makes receive the same weight as two-point makes; shot choice should consider expected points and possession outcomes before using this tool to advise strategy.

No fitted model pickle is loaded, no user credentials are stored, and no live external services are required at runtime.

## Project layout

```text
app.py                    Streamlit interface
shotsense/                Validation, model, filter and summary functions
scripts/                  Checksum-verified download and offline reproduction
data/raw/                 Pinned real-data archive
data/licenses/            Upstream license, README and field documentation
reports/                  Measured evaluation, coefficients, calibration, zones
public/                   Public browser dashboard and generated held-out data
tests/                    Core, headless UI and browser-calculation tests
docs/                     Event verification and submission/demo draft
.github/workflows/        CI configuration
```

## GitHub and Devpost handoff

This folder is a standalone Git repository on `main`, with `origin` set to `https://github.com/tarun-vignes/shotsense-nba.git`. The existing initial README commit is preserved in its history. For later updates, from this folder:

```powershell
git status
git add .
git commit -m "Update ShotSense dashboard"
git push -u origin main
```

The repository is public. If the remote has new commits, inspect and reconcile history first; do not force-push. The `.venv` folder and secrets are ignored. The bundled archive is small enough for ordinary Git.

Optional full Streamlit hosting: connect the public repository to Streamlit Community Cloud, choose `main`, `app.py`, and Python 3.13, and install from `requirements.txt`. This requires your account and is separate from the public GitHub Pages dashboard.

**Students only: you must verify your eligibility; this project does not claim you qualify.** The stated deadline is **November 1, 2026**. Official overview/rules requests returned 403 and the supplied discovery URL could not be read, so full edition 4.0 rules and the exact cutoff/timezone remain unverified. The software matches the supplied sports-analytics, insight, presentation, and open-source requirements; check the current rules before submission. See [event verification](docs/event-verification.md) and the ready-to-edit [submission description/demo script](docs/submission.md). Record an actual demo, add screenshots or a hosted URL if required, and submit to Devpost personally. GitHub publication and public dashboard deployment are authorized by the entrant. No organizer message or Devpost submission was performed.
