# Local verification — October 22, 2026

Environment: Windows, Python 3.13.12, isolated `.venv`; dependency versions in `requirements-lock.txt`.

| Check | Observed result |
| --- | --- |
| `python scripts/reproduce.py` | Passed; generated evaluation, coefficients, calibration and zone CSVs from the pinned real archive |
| `python -m unittest discover -s tests -v` | **16 tests passed**; includes headless Streamlit UI interaction and error tests |
| `python -m pip check` | Passed: No broken requirements found |
| `python -m streamlit run app.py --server.headless true --server.address 127.0.0.1 --server.port 8501` | Server launched and printed local URL |
| HTTP `GET /` | **200**, Streamlit HTML, 1,837 bytes |
| HTTP `GET /_stcore/health` | **200**, body `ok` |
| Git remote inspection | `origin` points to `https://github.com/tarun-vignes/shotsense-nba.git`; publication was authorized in a later turn; see below |

Streamlit AppTest exercised the complete initial dashboard, a team filter with changed displayed sample size, a player/team combination with no matches, reset restoring the original sample size, three chart elements, and an injected load failure with a recovery instruction. Constructed fixtures are confined to tests.

Non-failing test warnings came from Streamlit's use of the deprecated Altair theme API and expected bare-mode ScriptRunContext messages. A pandas test-fixture dtype warning was corrected after the suite. The workspace-global NumPy build failed before the isolated environment was created; all reported results use the working isolated environment.

The initial local handoff had no public deployment or remote CI execution. See the subsequent publication checks below. No pixel-level visual browser inspection, mobile-device testing, or Devpost submission has been performed. HTTP success checks server readiness; AppTest additionally checks Python app rendering and interactions, but does not establish browser appearance.


## Authorized public publication ? October 22, 2026

- Preserved upstream initial commit `d6ccfcd` and published application commit `2e1861d` to `main` at https://github.com/tarun-vignes/shotsense-nba.
- Enabled GitHub Pages through the repository's Actions workflow. Public URL: https://tarun-vignes.github.io/shotsense-nba/ .
- Anonymous HTTP checks returned **200** for the HTML page (6,106 bytes), `app.mjs`, `analytics.mjs`, `styles.css`, `shots.json` (2,174,996 bytes), and the dataset license.
- Parsed the public JSON response: **46,251 real held-out shots**, `synthetic: false`.
- Re-ran the **16 Python/UI tests: all passed**. Added **2 Node tests: both passed**, covering browser arithmetic, filters, sample thresholds and parity with Python Brier/residual/interval results.
- The public dashboard needs no login or Python installation. It uses precomputed probabilities from the exact Python pipeline; filtering and summaries run in the browser. The Streamlit application additionally provides calibration charts and shot-level exports.
- Public deployment workflow: https://github.com/tarun-vignes/shotsense-nba/actions/runs/39840439021 .
- Python/data CI workflow: https://github.com/tarun-vignes/shotsense-nba/actions/runs/39840439207 . Both application CI and the public deployment workflow completed successfully.
