# Submission materials

These are draft materials for the entrant to review and submit manually after checking the current rules. GitHub publication and public demo deployment are authorized; no Devpost submission has been performed.

## Title
ShotSense — NBA shots worth a second look

## Short description
An interpretable NBA shot analytics dashboard that compares actual makes with held-out expectations and helps coaches and analysts choose what to investigate next.

## Project description
Shooting percentage alone mixes shot quality and execution. ShotSense asks which situations are outperforming or underperforming the outcomes expected from distance, zone, shot type, and period.

We use Vladislav Shufinskiy's public 2023–24 NBA shot-detail archive, distributed under Apache-2.0. A logistic regression is fitted only on the first 80% of distinct game dates and evaluated on later games against a constant training make-rate baseline. The dashboard explores held-out shots exclusively. It exposes coefficients, Brier score, log loss, ROC AUC, calibration, and the data audit. Shot-clock time is not available and is omitted.

Analysts can filter players, teams, zones, periods, and shot types, then inspect shot locations and compare actual with expected outcomes. Residual makes, sample sizes, and approximate game-cluster intervals form an investigation queue. A large residual is a prompt to check shooter mix, defense, and film; it is not evidence of a causal effect or a prediction of future performance.

The app runs locally, includes its pinned dataset, and makes no live NBA requests. Code is MIT licensed; data retains its separate Apache-2.0 license. Exact measured results live in `reports/evaluation.json` and the README.

## Suggested 2–3 minute demo
1. Start the app and state the question. Identify the real data source and held-out date range.
2. Read the live key finding and explain actual minus expected makes.
3. Filter a team and a shot zone. Show that counts, rates, location plot, calibration and queue update.
4. Compare a player or period; explain sample thresholds and why rankings warrant investigation, not immediate coaching changes.
5. Open Model & evaluation: describe the time split, constant baseline, measured probability errors and omitted context.
6. Show attribution, reproducibility instructions and repository. End with limits and a realistic next step: validate findings on another season with richer defensive context.

## Links and remaining assets
- Intended repository: https://github.com/tarun-vignes/shotsense-nba.git — project repository.
- Public browser demo: https://tarun-vignes.github.io/shotsense-nba/ . Full Streamlit app also runs locally.
- Record and attach your actual demo; capture screenshots from your running app.
- Verify student eligibility and the precise November 1, 2026 cutoff; see `docs/event-verification.md`.
- Review and disclose AI assistance if required by the rules. This project was built with Codex assistance.
- Submit personally on Devpost after checking the current submission form.
