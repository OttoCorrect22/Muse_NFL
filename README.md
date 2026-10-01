# NFL Prediction Model v1

A finished, honest NFL game-prediction project. One league (NFL), one question:
**can we predict the final score margin from team data alone — no betting lines
as inputs — and how far behind Vegas do we land?**

Regular season only. This is an engineering project to *finish*, not a money
printer.

## How it works

Every Tuesday morning, the model predicts the coming week's games using only
data from games already played — never the future:

1. **Load data** — 10 seasons of real games (2015–2024): schedules, every play,
   injuries, depth charts (via [nflverse](https://github.com/nflverse)).
2. **Build features** — 7 locked features: Elo team strength, pass/rush
   efficiency (offense + defense), QB edge, special teams, plus home field.
3. **Train** — 2015–2021. **Tune** — 2022–2023. **Final exam** — 2024 (locked).
4. **Grade** — the scoreboard: us vs. the Vegas closing line vs. actual results.

The model is linear and interpretable: every feature has a visible weight in
plain points. No black boxes. No market input of any kind — the closing line
is the benchmark we're graded against, never an ingredient.

## Repo layout

- `docs/v1-essentials.md` — the whole project in plain language (start here)
- `docs/GOAL.md` — the working plan and decision log
- `docs/FEATURE_TESTS_V2.md` — how each feature earned its place (bottom-up)
- `docs/RESEARCH_ROUND2.md` — margin→probability math; injury-timing feasibility
- `docs/RESEARCH_FEATURE_STRUCTURE.md` — earlier research on feature design
- `docs/DATA_NOTES.md`, `PBP_NOTES.md`, `INJURIES_NOTES.md` — data provenance
- `scripts/features_build_v2.py` — reproducible feature builder (weekly
  Tuesday-morning cutoffs, zero lookahead)
- `scripts/feature_tests_v2.py` — incremental validation tests
- `data/` — small derived datasets; see `data/README.md` for what's excluded
  and why

## Status

v1 in progress: features locked (7, bottom-up), official backtest + real
scoreboard next, 2024 held as the locked final grade.
