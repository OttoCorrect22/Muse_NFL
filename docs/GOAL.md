# NFL prediction model v1

Goal ID: goal_a17610a52ae6
Goal slug: nfl-prediction-model-v1

## Description
Build a first, finished version of an NFL game-prediction project: one league, one market (spread vs. closing line), with an honest historical backtest. Atlas handles the data pull, baseline, model, and backtest; you review and make the v2 ship/no-ship call. The point is shipping something complete, not beating the market.

## Setup notes (2026-09-29)
- User context: struggles to finish free-time projects (~12 unfinished, started from chatbot plans he didn't fully understand). Doesn't plan fully or break work into actionable tasks. This project is explicitly the pattern-breaker.
- Scope (anti-bloat): NFL regular-season games only, spread vs. closing line only. NO props, NO other leagues until v1 ships. Markets are efficient — this is an engineering project to FINISH, not a money printer. Say that plainly if scope drifts.
- Data: nflverse/nfldata games.csv (free, no API key; closing spread + total lines, 2000/2006-present). Use nflreadpy — nfl_data_py is deprecated. The Odds API free tier (500 credits/mo) reserved for later multi-book comparison, NOT v1.
- Model v1: simple online team-strength rating (margin rating, home-field, rest-days adjustments), compare predicted spread to closing line.
- Evaluation: chronological backtest, time-based splits, grade against the actual price available at prediction time; judge on closing-line value and flat-stake ROI.
- Division of labor: Atlas does tasks 1-5 on its own computer between sessions; user reviews and makes the ship/no-ship call on v2.
- User asked on 2026-09-27 for this fork (goal A: sports project vs goal B: general finishing-projects goal); picked A on 2026-09-29.

## v1 task list
1. Pull nflverse data (games.csv + play-by-play) and verify closing lines are present
2. Baselines vs ACTUAL game outcomes: always follow the closing line, always take the favorite (no home-team-picks baseline — user ruled it out as a strategy they'd never use)
   - Reference point (background Elo run, 1999–2026 window): bare Elo winner accuracy 63.2% (2020–2026) vs 66.8% for just picking the closing-line favorite; moneyline flat stakes −4.4% ROI. Picking winners is easy — beating the price is hard.
3. Build transparent linear-style model — every feature visible with its weight (Rithmm-style: features you can see, not a black box)
4. GUI model lab (interactive web dashboard): feature list with weights, sliders to adjust them, pick a game → see predicted spread vs closing line vs actual result
5. Run chronological backtest 2015–2024, judged on accuracy vs actual outcomes + closing-line value
6. Learn loop: review which features pull their weight, adjust, re-run — small iterations, no new leagues/markets until v1 works

## Injury data (2026-09-29)
- Historical/backtest: nflverse `load_injuries()` — official NFL injury reports, 2009+, practice participation + game status by player/team/week. Free, same venv. Pulling 2015–2024 overnight alongside pbp.
- Live/real-time (v2+): ESPN API and Sleeper API — free, no key, continuous injury + depth-chart updates. Paid feeds (Sportradar etc.) rejected for v1.
- Honesty rule applies: only injury info known before kickoff may inform a prediction. QB availability is the highest-leverage use (adjusts the QB edge feature).
- **Auto-updating QB availability (user idea 2026-09-29):** weights stay fixed (build-once rule intact) — the QB *input* updates automatically. Starter ruled out → feature swaps in backup's efficiency; questionable → blends by status probability. Depth charts 2015–2024 pulled (`depth_charts_2015_2024.parquet`, 369k rows) to identify backups. Home base shows it as an "injury adjustment" line on the game view: who swapped, why, and how the prediction moved.

## Scoreboard spec (user-defined 2026-09-30)
Three panels, all vs actual results AND vs the market:
1. **Vs. raw result:** winner accuracy, average margin error (MAE).
2. **Calibration buckets:** group games by predicted margin (pick'em / lean / moderate / strong / heavy); per bucket show win rate, average actual margin, blowout% and close-game%. Answers "when we say heavy favorite, how often and by how much?"
3. **Three-way (us vs Vegas vs reality):** per game — our predicted margin vs closing line vs actual; aggregate — our avg miss vs the line's avg miss. Margins convert to win probability/fair odds so it's apples-to-apples.
Reference (Elo baseline, 2020–2026): buckets calibrate cleanly (heavy: 77% win, +10.8 avg margin, 45% blowouts; pick'em: 49%); avg miss 10.26 pts vs Vegas 9.78 pts.

## Known regime breaks in the data (2026-09-29)
- **2020 COVID season:** no preseason, player opt-outs, empty stadiums — home-field advantage collapsed league-wide. HFA must be estimated excluding (or downweighting) 2020, or the model learns a lie.
- **2021:** lingering COVID effects (rescheduling, roster disruption) — keep, but watch.
- **2024 kickoff rules (dynamic kickoff):** changed touchback/return rates and starting field position. Special-teams and field-position features trained on 2015–2023 behave differently under the new rules — and 2024 is our TEST season, so the final grade doubles as a rule-change stress test.
- v1 handling: document the breaks, show per-season backtest performance in the home base so regime effects are visible, and treat COVID/kickoff adjustments as explicit learn-loop items — not silent tweaks.

## Evaluation methodology (2026-09-29)
- Chronological splits only, never random: train 2015–2021 (1,808 games) → validation 2022–2023 (543 games) → test 2024 (272 games). Test set stays locked until final grading.
- No lookahead: features for any game use only games played before it. Validation tunes slider defaults; test gives the one honest grade.
- 10-season window keeps us in the modern NFL era; older eras play a different game.
- Splits are shown in the home base in plain language ("trained on 2015–2021, tuned on 2022–2023, graded on 2024").

## ML engineering standards (2026-09-29)
- Functional pipeline: separate stages (load data → build features → train → backtest → report), each a standalone function with no lookahead leakage. Every stage's output is inspectable from the home base.
- Experiment tracking (MLflow-style): every run logs its features, weights, and backtest scores. The home base surfaces run history in plain language — compare runs, see what changed, roll back. Rigor of MLflow without ever opening its UI.
- v1 stays within interpretable model families (linear-style) so "see the weights" stays meaningful. Bake-offs across model families come in v2+.

## Plan refinement (2026-09-29)
- User asked to work out the plan TOGETHER before building. Data pull continues (raw material only, no model decisions).
- GUI-first: wants to SEE features and weights and TUNE them (modeled on Rithmm's custom model builder — factor sliders, backtest, performance tracking). The GUI lab is a core v1 deliverable, not an add-on.
- Baselines must be against ACTUAL game outcomes too, not just the line. Not trying to beat Vegas — measure what the model actually gets right.
- Explicit philosophy: start small, learn what we have, build on it. No get-rich-fast framing.
- Home-base dashboard design (Rithmm's visuals were inspiration only — our own design, no copying): FLAT features, not factor groups (user decision 2026-09-29 — grouping adds no predictive benefit, so keep it simple and honest). Each feature visible with its weight as a visual bar + slider; tap a feature to see what the data point actually is in plain language. Tabs: features / games / backtest. If we ever group features, we rename the concept — never "factors."
- Double-counting protection (the job grouping would have done) is handled by strict feature selection: every feature must add signal beyond the others, plus regularization.
- Weights are set ONCE when the model is built (user decision 2026-09-29) — never tuned per game. Changing weights = a new model version, backtested and logged in run history. Games tab is read-only: fixed model vs line vs actual.

## Feature-set lock decisions (2026-09-30 — SUPERSEDED, see bottom-up redesign below)
1. EPA split into pass/rush (offense and defense = 4 features), like pro models.
2. QB as its own separate feature (not folded into offense) — backed by nfelo's dedicated QB sub-model (~3.9 pts for a missing starter) and required for the injury auto-update design (fixed weight, swapping input).
3. Try both success-rate differential and interception-EPA differential; cut either if validation shows noise.
4. Situational flags (division, dome, primetime) included but with cautious small initial weights; validation decides.
Lock rule: every feature must add signal beyond line + Elo on 2022–2023 validation (ΔMAE), or it's cut. No feature survives on vibes.
Build kicked off 2026-09-30: feature pipeline + incremental tests → FEATURE_TESTS.md with keep/cut receipts. 2024 test season stays locked.

## Bottom-up redesign (user decision 2026-09-30, evening)
User rejected the closing line as a model feature — correct call, two reasons: (1) timing — the close doesn't exist until kickoff, so a model needing it can't produce a usable pregame prediction; (2) leakage — the close embeds late information (injury news, sharp money) unknowable at prediction time. Our own research flagged this rule (closing line as training feature = lookahead).
New v1 shape: PURE BOTTOM-UP. No market input of any kind (not the close, not the opener). Features: team strength + efficiency + situation from data only. The closing line stays as the BENCHMARK on the scoreboard (user's panel 3: us vs Vegas vs reality) — graded against, never built from.
Prediction time is now explicit: model runs weekly (assume Tuesday morning); Week W games use only games from weeks < W. No within-week games inform each other.
Honest expectation: bottom-up MAE ~10.0–10.5 (near the 10.26 Elo-baseline reference), roughly a point worse than the line's ~9.3. The project's value is showing its work + honest grading, never beating Vegas.
Feature tests rerun bottom-up (FEATURE_TESTS_V2.md): some cut features get a second trial without the line dominating — especially qb_edge (separate vs folded vs cut verdict needed for the injury-swap design). Previous line-anchored results kept on record in FEATURE_TESTS.md. 2024 test season still locked.

## v1 model LOCKED (2026-09-30, late night)
Locked 7 bottom-up features + intercept, Ridge(α=100), StandardScaler:
`elo_diff`, `off_pass_epa`, `off_rush_epa`, `def_pass_epa`, `def_rush_epa`, `qb_edge` (separate — v1 verdict reversed), `st_epa_diff`. No market input anywhere, ever.
Win probability: Stern method, P(home win) = Φ(μ/σ); σ=13 recalibrated from our own validation residuals. Fair odds in American format; pushes shown as a separate slice near key numbers (3, 7). See hidden_files/RESEARCH_ROUND2.md Q1–Q3.
Features live in `hidden_files/features_v3.parquet` (v3 = v2 + Tuesday-knowledge QB fix). Older artifacts kept intact (features_v2.parquet, FEATURE_TESTS.md/.md v2).

### Tuesday-knowledge QB rule (leak audit 2026-09-30)
v2's qb_edge used the game-week depth-chart QB1 — a snapshot of unknown timing. Audit of 3,980 team-weeks found 5 proven leaks (chart listed a backup elevated by a Wed–Fri Out designation) plus ~70 cases where the chart reflected mid-week changes with no pre-Tuesday signal. Decisive measurement: **0 of 373 REG QB Out/Doubtful rows (2015–2024) predate Tuesday 8am ET of their game week** (median stamp Friday). The injury report *never* speaks before Tuesday — so the Tuesday-honest starter is simply **last game's actual starter (most dropbacks)**; Week 1 = preseason chart; byes walk back to the most recent game. No injury lookup needed. Honestly misses ~12 new mid-week QB injuries/season + Monday benching/return news, exactly as a real Tuesday model would. Rule re-verified by a premise `assert` on every feature build. "Auto-update as news breaks" stays a v2-only vision (needs a live feed).

### Official backtest (approved 2026-09-30 — user opened 2024 for the final grade)
Train 2015–2021 → val 2022–2023 → **2024 graded exactly once, never tuned on**. Pipeline: hidden_files/backtest.py. Outputs: hidden_files/BACKTEST_RESULTS.md (plain-language official grade) + hidden_files/scoreboard.json (clean data for the site). Validation reference: Elo-only 9.840 MAE/62.7% acc; locked-7 ridge 9.722/63.6%; closing-line benchmark 9.322/67.1% (benchmark only, never a feature).
**Bedtime note:** if the 2024 grade comes back poor (meaningfully worse than 9.72 val MAE, or winner accuracy collapses), research reputable public bottom-up modelers for v2 ideas — user named "furnace picks" on X as the style reference. Learn from, do NOT copy. If the grade is solid, keep it as v2 backlog.

## Project home + deployment (2026-09-30)
- Home: GitHub repo **OttoCorrect22/Muse_NFL** (private; initial commit pushed: README, docs, scripts). Text files only — parquets excluded (data/README.md explains).
- Deployment decision: **GitHub Pages** (not Vercel) for the home-base dashboard when real numbers land.
- Essentials doc: files/v1-essentials.md — plain-language v1 summary (kept current as decisions land).
