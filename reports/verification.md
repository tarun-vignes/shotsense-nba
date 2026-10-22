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
| Git remote inspection | `origin` points to `https://github.com/tarun-vignes/shotsense-nba.git`; no push performed |

Streamlit AppTest exercised the complete initial dashboard, a team filter with changed displayed sample size, a player/team combination with no matches, reset restoring the original sample size, three chart elements, and an injected load failure with a recovery instruction. Constructed fixtures are confined to tests.

Non-failing test warnings came from Streamlit's use of the deprecated Altair theme API and expected bare-mode ScriptRunContext messages. A pandas test-fixture dtype warning was corrected after the suite. The workspace-global NumPy build failed before the isolated environment was created; all reported results use the working isolated environment.

No pixel-level visual browser inspection, mobile-device testing, public deployment, remote GitHub Actions execution, or Devpost submission has been performed. HTTP success checks server readiness; AppTest additionally checks Python app rendering and interactions, but does not establish browser appearance.
