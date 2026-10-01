# v2 Feature Validation Report — 2026-09-30 (BOTTOM-UP REDESIGN)

**What changed and why:** the user ruled that no market input of any kind
belongs in the model — the closing line doesn't exist until kickoff, so it
can't be a prediction-time input, and it's lookahead bias in training. v2 is
pure bottom-up: team strength + efficiency + situation from data only. The
closing line stays as the BENCHMARK on the scoreboard, never as a feature.
This report supersedes the v1 feature tests (kept in `FEATURE_TESTS.md`);
v1 artifacts are untouched.

**Prediction time is now explicit:** the model runs once per week (assumed
Tuesday morning). For any game in Week W, every feature uses only games from
weeks strictly before W. No within-week game informs another.

**How it was tested:** same data and splits as v1 — fit on 2015–2021
(1,808 games), judged on 2022–2023 (543 games). 2024 was not touched for any
metric and stays locked for the final grade. Linear models only (OLS for
incremental tests, ridge for the joint model).

## The headline finding

**The bottom-up model works and lands where it should.** Elo alone misses by
9.84 points per game on validation; adding efficiency features brings that to
**9.72**, with winner accuracy rising from 62.7% to **63.6%**. The closing-line
benchmark sits at 9.32 / 67.1% — we trail Vegas by 0.40 points, roughly what
the research predicts for an honest bottom-up model (our Elo-baseline
reference was 10.26 on a wider window). Nothing here beats the line, and the
leakage checks all pass, so this is a real result, not an artifact.

In plain words: v1 was "start from Vegas's number and nudge it." v2 is "build
the number from scratch out of team strength and efficiency, then see how far
behind Vegas we land." The 0.4-point gap is the honest price of predicting
from data alone — and it's exactly the gap the scoreboard was designed to show.

## (a) Incremental test results

ΔMAE = validation MAE change vs. the Elo-only base (negative = better).
Base: elo_diff + intercept → **val MAE 9.840, win acc 62.7%**.
Benchmark (reference only, never a feature): closing line → 9.322 / 67.1%.

| Feature / group | ΔMAE vs Elo base | paired p | Coef sign | Verdict |
|---|---|---|---|---|
| EPA splits ×4 (group) | −0.063 | 0.140 | all + | **KEEP** |
| off_pass_epa (alone) | −0.057 | **0.040** | + | **KEEP** — the one statistically significant feature |
| off_rush_epa (alone) | −0.010 | 0.779 | + | **KEEP** (group member, user's chosen split) |
| def_pass_epa (alone) | −0.000 | 0.961 | + | **KEEP** — weakest link, flagged, watched |
| def_rush_epa (alone) | +0.012 | 0.315 | + | **KEEP** (group member, correct sign) |
| qb_edge | −0.035 | 0.091 | + | **KEEP as separate feature** — see §c |
| st_epa_diff | −0.021 | 0.530 | + | **KEEP** |
| success_rate_diff | −0.042 | 0.348 | + | CUT (duplicates pass EPA) |
| rest_diff | −0.017 | 0.161 | + | CUT for now (retest capped/asymmetric later) |
| recent_form | −0.005 | 0.777 | + | CUT |
| int_epa_diff | +0.015 | 0.361 | − (wrong) | CUT |
| wind | +0.001 | 0.927 | ~0 | CUT (margin model; moves totals, not margins) |
| situational ×3 | +0.019 | 0.448 | mixed | CUT |

**Reading the table:** without the line dominating everything, the efficiency
features finally show their own signal. Offensive pass EPA is the star —
statistically significant on its own (p=0.040), the only feature to clear that
bar. The four EPA splits together shave 0.06 off the miss. Everything kept
has the correct sign; everything cut is noise, a duplicate, or pointed the
wrong way.

**Why each CUT:**
- *success_rate_diff* — helped a touch alone (−0.042) but correlates 0.50 with
  pass EPA; it says the same thing twice. Same verdict as v1.
- *rest_diff* — faint signal (−0.017, p=0.161) in raw-days linear form.
  Research says the real effect is capped/asymmetric (±1.5 pts for big rest
  edges). Cut for v1, retest with that specification later.
- *recent_form, int_epa_diff (wrong sign), wind, situational flags* — no
  signal, same as v1. Wind's dome=0 plumbing is kept in the build for a
  future totals model.

## (b) Proposed LOCKED bottom-up feature list (7 features, ridge α=100)

| # | Feature | Fitted weight | Plain-English meaning |
|---|---|---|---|
| 1 | elo_diff | +0.029 pts per Elo point (≈ +3.9 pts per typical 133-pt gap) | Overall team-strength gap, full-history rating |
| 2 | off_pass_epa | +3.29 pts per EPA/play (≈ +0.7 pts per typical edge) | Passing efficiency edge, recent & opponent-adjusted |
| 3 | off_rush_epa | +6.61 pts per EPA/play (≈ +0.9 pts per typical edge) | Rushing efficiency edge |
| 4 | def_pass_epa | +2.06 pts per EPA/play (≈ +0.5 pts per typical edge) | Pass defense edge — weakest link, watched |
| 5 | def_rush_epa | +3.97 pts per EPA/play (≈ +0.5 pts per typical edge) | Run defense edge |
| 6 | qb_edge | +5.98 pts per EPA/dropback (≈ +0.4 pts per typical edge) | Starting-QB efficiency edge — the injury-swap input |
| 7 | st_epa_diff | +6.68 pts per EPA/play (≈ +1.0 pts per typical edge) | Special-teams edge — biggest non-Elo effect |
| — | intercept | +1.49 pts | Effective home-field edge |

Locked-model validation: **MAE 9.722, winner accuracy 63.6%** vs. the
line benchmark 9.322 / 67.1% (gap +0.40 pts). Per-standard-deviation effects
show the model's anatomy honestly: Elo dominates (3.9 pts/SD), then special
teams (1.0), the rushing splits (0.9/0.5), passing splits (0.7/0.5), and QB
(0.4). The intercept carries the home edge (+1.49); the separate hfa constant
was verified to change MAE by exactly +0.00000 — absorbed, as expected.

## (c) Verdict on qb_edge: KEEP as a separate feature (v1 verdict reversed)

v1 cut qb_edge as its own term because next to the closing line its
coefficient flipped to the *wrong sign* (−1.77) — textbook double-counting
(the line already prices QB). The v2 retest, with no line in the model, tells
a different story:

- Coefficient is now **positive and sensible** (+9.89 alone, +5.98 under
  ridge) — the sign flip is gone.
- It **improves validation MAE** (−0.035, p=0.091) on top of Elo.
- Under ridge it coexists fine with off_pass_epa (both keep correct signs:
  +3.29 and +5.98), despite their 0.80 correlation — the shrinkage handles
  the overlap instead of corrupting the model.

So the evidence now supports what the user originally wanted: **QB stays its
own feature**, which is also what the injury auto-update design needs — the
weight stays locked while the *input* swaps from starter to backup when news
breaks. Caveat stated openly: qb_edge and pass EPA overlap heavily (0.80
correlation); the model leans on ridge to split the credit. If the learn
loop later shows instability, folding remains an option — but today's
evidence says separate.

## (d) Definition changes vs v1

1. **No market feature.** `spread_line`/`market_anchor` are not in
   `features_v2.parquet` at all — the file cannot be used to fit a
   market-anchored model by accident. The line is read from schedules only
   as a benchmark number.
2. **Week-based prediction cutoff** (the core rebuild). v1 used "kickoff
   strictly before this game's kickoff." v2 uses "(season, week) strictly
   before this game's (season, week)" for everything: trailing windows,
   opponent adjustments (opponent's stats as of *that game's* week), Elo
   (every Week-W game sees ratings through Week W−1 — pre-week snapshot, no
   within-week updates leak across games), QB trailing efficiency, and the
   league-average priors for QB shrinkage (cumulative through week W−1).
3. **Elo is now a pure bottom-up rating.** Same recipe (1500 start, K=20,
   HFA=60 in updates, MOV-weighted, 1/3 offseason reversion), but Week 1
   each season applies the offseason reversion and all games in a week share
   the pre-week snapshot.
4. **Wind caveat made explicit.** The backtest uses actual game-day wind as
   a proxy; at real prediction time (Tuesday morning) we would use the wind
   *forecast*. Forecasts track actuals closely, so this is a mild proxy, not
   a leak — but it is documented, not hidden. (Wind was cut from the model
   anyway; the dome=0 plumbing stays for a future totals model.)
5. **Injury/QB inputs are start-of-week by construction.** The designated
   starter comes from the week's depth chart; no late-week injury news can
   enter. (No injury adjustment was tested in v2 — that phase comes later.)

## (e) Caveats

- **Leakage checks passed:** 2015 Week 1 trailing features and Elo diffs are
  all exactly zero; 300 random team-weeks verified no window game comes from
  the same or a later week; the joint model does not beat the line
  (9.722 vs 9.322 — the sanity anchor held).
- **def_pass_epa is the weakest link** (ΔMAE −0.000 alone, p=0.961). Kept
  because the user chose the pass/rush split, its ridge sign is correct, and
  the group helps — but it is first on the watch list in the learn loop.
- **rest_diff** is second on the retest list, with the capped/asymmetric
  (±1.5 pts) specification the research recommends.
- **2024 was excluded from every metric** (features are built for its 272
  games so the backtest can use them later, but no number in this report
  touches them).
- Early-season teams have thin trailing windows (noisier estimates); Elo,
  with full history, compensates — same as v1.
- Neutral-site games keep the HFA constant (small sample; same caveat as v1).

## Artifacts

- `hidden_files/features_v2.parquet` — 2,623 games × 26 cols, zero nulls, no
  market columns by design.
- `hidden_files/features_build_v2.py` — reproducible build (all choices in
  the header, leakage self-checks at the end).
- `hidden_files/feature_tests_v2.py` — incremental tests + ridge fit.

## Recommended next steps (for the parent agent)

1. Confirm the locked 7-feature bottom-up list with the user (and the
   qb_edge-as-separate-feature verdict, which reverses v1).
2. Then: official backtest pipeline + scoreboard on the locked model, with
   2024 as the final locked grade — the line appears there as the benchmark,
   per the user's three-panel scoreboard spec.
