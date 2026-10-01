# NFL Prediction Model v1 — The Essentials

*Plain-language capture of the project. Last updated 2026-09-30.*

## What we're building
A finished, honest NFL game-prediction project. One league (NFL), one question: **can we predict the final score margin better than just reading the betting line?** Regular season only. This is an engineering project to *finish* — not a money printer. Nobody beats the Vegas closing line consistently, and we're not pretending to.

## How it works (the pipeline)
Every Tuesday morning, the model predicts the coming week's games using only data from games already played — never the future. It works in four steps:

1. **Load data** — 10 seasons of real games (2015–2024): schedules, every play, injuries, depth charts.
2. **Build features** — a short list of team stats (see below), each one a number like "Kansas City passes 0.12 points-per-play better than average."
3. **Train** — the model learns how much each feature matters by studying 2015–2021.
4. **Backtest** — we grade it on 2022–2023 (tuning years), then give it one final exam on 2024, which stays locked and untouched until then.

The model is **linear and interpretable**: every feature has a visible weight in plain points. No black boxes.

## The features (final list pending retest, 2026-09-30)
Candidates: team strength (Elo rating), passing/rushing efficiency on offense and defense, special teams, QB efficiency, home-field advantage. Each one must *earn* its place by improving predictions on 2022–2023 — or it's cut. The first test round is being redone bottom-up (see Decisions).

## How it's graded (the scoreboard)
Three panels, always us vs. Vegas vs. reality:
1. **Against the raw result** — did we pick the winner? By how many points did we miss?
2. **Confidence buckets** — when we say "heavy favorite," how often are we right, and by how much?
3. **Three-way** — our predicted margin vs. the closing line vs. the actual final score, per game and on average.

## Key decisions (the project's memory)
- **Bottom-up only (2026-09-30).** The Vegas line is *not* a model input — it doesn't exist until kickoff, and using it would be cheating (it contains late information). It's the benchmark we're graded against, never an ingredient.
- **Flat features, not factor groups (2026-09-30).** Research found no evidence grouped "factors" predict better; flat features are more transparent.
- **Strict no-lookahead.** Every prediction uses only pre-kickoff information. Non-negotiable.
- **Chronological splits.** Train 2015–2021, tune 2022–2023, final exam 2024 (locked).
- **2020 excluded from home-field estimates.** Empty stadiums erased home advantage (+1.70 pts normally, −0.03 in 2020 — measured in our own data).
- **2024 kickoff rule change.** Treated as a stress test; performance shown per season.
- **Build-once rule.** Changing a weight creates a new locked model version and reruns the backtest. Never tuned per game.
- **QB injury auto-update (design, resolved 2026-09-30).** The model's weights stay fixed; the *input* updates — starter ruled out → backup's efficiency swaps in. Honest-backtest verdict: v1 uses a strict **Tuesday-knowledge rule** — starter = last game's actual starter (verified: the injury report never designates a QB Out/Doubtful before Tuesday 8am ET, 0/373 rows 2015–2024, so no injury lookup is needed or allowed). ~12 new mid-week QB injuries/season are invisible by construction, exactly as a real Tuesday model would experience. The "updates the hour news breaks" version needs a live feed → v2-only.
- **Margin → win probability (resolved 2026-09-30).** Textbook bell-curve method with σ recalibrated from our own validation errors (12.68; started at 13.0). Pushes shown as their own slice near key numbers (3, 7).

## Official v1 grade (graded 2026-10-01, final — 2024 will not be tuned on)
Locked model: Ridge (α=100) on the 7 bottom-up features. **Final exam (2024, 272 games): our average miss 9.91 pts, winners right 68.0%** — vs the closing line's 9.61 pts / 71.3%. We trail Vegas by 0.30 pts (validation was 9.72, so the final is in line with expectations); our predicted margin landed closer than the line in 44.5% of games. Win probabilities calibrate well (predicted 53/60/69/78/86% vs actual 51/73/70/79/87% across buckets); the one soft spot is mild "lean" calls (2–5 pt favorites won 73% vs 60% predicted). Full writeup: hidden_files/BACKTEST_RESULTS.md; site data: hidden_files/scoreboard.json.

## What's real vs. mock right now
- **Real:** all data (verified), the official v1 backtest (numbers above), the feature-test methodology.
- **Mock:** the home base Build and Games tabs (placeholder weights until the real model is wired in). The Scoreboard tab shows real baseline numbers as a preview.

## What's next
1. Wire real numbers into the home base (replacing mockups).
2. Ship/no-ship call on v2.
3. (v2 backlog) Reputable public bottom-up modeler research for v2 ideas (user named "furnace picks" on X as the style reference) — learn from, never copy. v2-only: live injury auto-update feed, both EPA4 signs revisited, the "lean"-bucket humility.
