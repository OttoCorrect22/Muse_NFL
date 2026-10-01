# v1 Feature Validation Report — 2026-09-30

**Question we set out to answer:** which features earn a place in the v1 model?
The lock rule: *a feature stays only if it improves predictions on top of the
closing line and Elo — or has a clear, honest reason to stay anyway.*

**How it was tested:** every feature was built with strict no-lookahead (only
games played before kickoff), fit on 2015–2021 (1,808 games), and judged on
2022–2023 (543 games). The 2024 season was not touched for any metric — it stays
locked for the final grade. Models are linear only (OLS for the incremental
tests, ridge for the joint model).

## The headline finding

**On 2022–2023, nothing beats the closing line.** The line alone misses by
9.32 points on average; every feature we tried left that number essentially
unchanged (all differences are statistical noise). This is not a failure of the
test — it is the expected result. Our own research found that no public model
beats a sharp closing line (538's Elo hits ~51% ATS; the nfelo project lost
0.16% against the close). The line already contains most of what EPA, Elo, and
QB stats know — our correlations confirm it (line↔Elo 0.82, line↔pass EPA 0.51).

So v1's honest shape is: **start from the line, add small, well-shrunk
adjustments, and report the gap to Vegas plainly.** The scoreboard the user
designed ("us vs. Vegas vs. reality") will show us ~0.0–0.4 pts behind the
line. That IS the v1 result — an interpretable model that explains *why* it
thinks what it thinks, graded honestly.

## (a) Incremental test results

ΔMAE = validation MAE change vs. the base (negative = better). The paired
p-value says how likely a change this size is pure noise.

| Feature / group | ΔMAE vs line+Elo | paired p | Verdict |
|---|---|---|---|
| EPA splits ×4 (pass/rush, off/def) | −0.00 | 0.89 | **KEEP** — see note |
| rest_diff (days) | +0.00 | 0.56 | CUT (retest w/ better spec) |
| qb_edge (starter EPA/dropback) | +0.01 | 0.14 | **CUT as separate feature** |
| wind (mph) | +0.00 | 0.85 | CUT (margin model) |
| st_epa_diff (special teams) | −0.00 | 0.95 | **KEEP** — see note |
| recent_form | +0.00 | 0.48 | CUT |
| success_rate_diff | +0.01 | 0.65 | CUT (duplicates pass EPA) |
| int_epa_diff (defense) | +0.01 | 0.48 | CUT (duplicates pass defense) |
| situational ×3 (division/dome/primetime) | +0.01 | 0.60 | CUT |
| elo_diff (added to line-only) | +0.04 | 0.07 | **KEEP** — see note |

Reading the table: no feature clears the bar on MAE — every ΔMAE rounds to
zero and every p-value says "noise." The verdicts below combine the test with
sign checks, redundancy analysis, and the research.

**Why KEEP anything, then?** Three reasons, stated openly rather than smuggled:
1. The product needs visible, interpretable features (the whole point of the
   home base). A "model" that is literally just the line has no weights to
   show and nothing to learn from.
2. Ridge shrinkage (α=100) does the cutting *softly and automatically* —
   redundant features get near-zero weights instead of corrupting the model.
3. The kept features all have the **correct sign** and research backing; the
   cut ones don't (wrong signs from double-counting, or no signal at all).

**Why each CUT:**
- *qb_edge* — the most instructive cut. It correlates 0.80 with offensive pass
  EPA, and when paired with the line its coefficient flips to the **wrong
  sign** (−1.77): classic double-counting. Independent research found the same
  thing (per-QB ratings add nothing once team EPA is in the model). The user's
  instinct was right to ask. **Recommendation: fold QB into offense** — do not
  keep it as its own linear term. (The injury-swap idea survives separately:
  when a starter is ruled out, the *inputs* to the EPA features change; that's
  an input update, not a separate feature.)
- *success_rate_diff* — correlates 0.50 with pass EPA; says the same thing twice.
- *int_epa_diff* — wrong sign under ridge; its information already lives in
  defensive pass EPA.
- *recent_form* — no signal (correlation 0.04 with margin; wrong sign).
- *wind* — no signal **for margin** (correlation −0.004). Research says wind
  moves *totals*, not margins. Kept the dome=0 plumbing for a future totals
  model; cut from v1.
- *situational flags* — no signal; is_dome is 0.62-correlated with wind
  (structural: domes have zero wind).
- *rest_diff* — no signal in raw-days linear form. Research says the real
  effect is capped/asymmetric (±1.5 pts for big edges). Retest later with that
  specification; cut for v1.

**Why each KEEP (judgment calls, flagged as such):**
- *market_anchor* — the anchor. 4.78 pts of prediction per standard deviation.
  The model starts from Vegas's number; everything else is a small adjustment.
- *elo_diff* — the non-market team-strength signal (+0.88 pts/SD, correct
  sign). Strictly, it didn't improve MAE on this window (p=0.07 toward a small
  *hurt* — within noise). Kept because: computable for every game (no thin
  early-season windows), independent of the week's line, and the GUI needs a
  "how good is this team" input. Watched in the learn loop.
- *EPA splits ×4* — the user's chosen pass/rush split, kept as decided. All
  four have correct signs at α=100 with sensible magnitudes (rush ≈ pass on
  both sides: +0.38/+0.41 off, +0.01/+0.42 def). Note def_pass_epa's weight is
  ~0 — the model is honestly saying pass defense adds nothing beyond the rest.
- *st_epa_diff* — largest non-line effect (+0.83 pts/SD, correct sign),
  research-backed, and the one to watch into the 2024 kickoff-rule season.

## (b) Proposed LOCKED feature list (7 features)

| # | Feature | Fitted weight (ridge α=100) | Plain-English meaning |
|---|---|---|---|
| 1 | market_anchor | +0.78 pts per point of line | Where Vegas set the line — the starting point |
| 2 | elo_diff | +0.0066 pts per Elo point | Overall team-strength gap |
| 3 | off_pass_epa | +1.76 pts per EPA/play | Passing efficiency edge |
| 4 | off_rush_epa | +3.00 pts per EPA/play | Rushing efficiency edge |
| 5 | def_pass_epa | +0.04 pts per EPA/play (≈0) | Pass defense edge — model says ~nothing here |
| 6 | def_rush_epa | +3.10 pts per EPA/play | Run defense edge |
| 7 | st_epa_diff | +5.63 pts per EPA/play | Special-teams edge |
| — | intercept | +1.49 pts | Effective home-field edge |

Locked-model validation: **MAE 9.36, winner accuracy 67.8%** vs. line-only
9.32 / 67.1%. In words: our model is a slightly-shrunk line plus small
adjustments, 0.04 pts behind Vegas on this window — a gap indistinguishable
from noise, reported honestly.

## (c) Definition choices and caveats

- **No-lookahead construction:** every trailing feature uses games with kickoff
  strictly before the game's kickoff (datetime-ordered, so Thursday games
  correctly inform the following Sunday's games). Verified: all trailing
  features are exactly 0 for 2015 Week 1 (no history exists yet).
- **Trailing windows:** max 8 games, exponential decay with 8-game half-life
  (weight halves every 8 games). Windows span seasons; prior-season games decay
  naturally. Early-season teams with thin history get noisier estimates —
  Elo (full history) compensates.
- **Opponent adjustment (one iteration):** the 4 EPA splits and success rate
  are adjusted by what each past opponent typically allowed *as of that game*.
  ST EPA, INT EPA, recent form, and QB edge are raw — documented choice, not
  an oversight (adjustment matters most for efficiency stats).
- **Elo:** matches the reference proof-of-concept exactly (1500 start, K=20,
  HFA=60 in updates, MOV-weighted, 1/3 offseason reversion). The stored
  feature is the *pure* rating differential — the reference's stored value
  bundled HFA in, but we keep HFA separate to avoid double-counting.
- **HFA estimate:** **+1.70 pts** from train excluding 2020; **−0.03 pts** for
  2020 alone. The COVID home-field collapse is vivid in our own data —
  excluding 2020 was the right call. As a *constant* feature it is absorbed by
  the intercept (proven: adding it changes MAE by +0.0000), so it is not a
  separate fitted feature; the intercept (+1.49) carries the home edge.
- **QB starter logic:** depth-chart QB1 by (season, week, club); fallback =
  most dropbacks in the trailing window (needed for 0 games — charts cover
  99.6% of team-weeks). Designated starter matched the *actual* game starter
  88% of the time; the 12% gap is mostly in-season changes (injury/benching) —
  the documented limitation the injury-swap work will address. Starter
  efficiency is trailing EPA/dropback shrunk toward the league average (60-
  dropback prior). **No injury adjustment in these tests** — that is tested
  separately later.
- **Wind:** dome/closed roof → 0; outdoor as reported; 171 outdoor games
  (mostly 2022–2023) have no wind in either schedules or pbp → imputed to
  8.0 mph (league-median outdoor wind), flagged in `wind_imputed`. Max
  recorded: 71 mph.
- **Rest:** raw days from schedules (home−away, range ±8, 920 nonzero games).
  Capping is a model-stage decision; the linear raw form showed no signal.
- **Situational flags:** is_division from `div_game`; is_dome = roof in
  {dome, closed}; is_primetime = Mon/Thu or kickoff ≥ 20:00 ET.
- **Team-code fix:** pbp uses LV/LAC/LA while schedules use era-correct
  OAK/SD/STL — remapped before aggregating (first build silently missed 64
  games; caught and fixed).
- **2024:** features are built for all 272 games (needed later) but 2024 was
  excluded from every metric in this report.

## Artifacts

- `hidden_files/features_v1.parquet` — 2,623 games × 27 cols, zero nulls.
- `hidden_files/features_build.py` — reproducible build (all choices in header).
- `hidden_files/feature_tests.py` — incremental tests + ridge fit.

## Recommended next steps (for the parent agent)

1. Confirm the locked 7-feature list with the user (biggest judgment call:
   keeping Elo + EPA splits despite no MAE win — the honest "why").
2. Confirm the qb_edge fold decision (user was indifferent; evidence says fold).
3. Then: official backtest pipeline + scoreboard on the locked model, with
   2024 as the final locked grade.
