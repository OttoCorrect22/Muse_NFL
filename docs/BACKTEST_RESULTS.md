# Official v1 Backtest Results — graded 2026-10-01

**The one honest grade.** Locked model: Ridge (α=100) on the 7 locked
bottom-up features — Elo, pass/rush EPA on offense and defense, QB edge,
special teams — plus an intercept. No market input anywhere: the closing
line is the benchmark on the scoreboard, never an ingredient.

## The headline

| Split | Games | Our avg miss | Our winner acc | Vegas avg miss | Vegas winner acc |
|---|---|---|---|---|---|
| Train 2015–2021 (in-sample) | 1808 | 10.285 pts | 64.1% | 10.013 pts | 65.3% |
| Validation 2022–2023 | 543 | 9.724 pts | 63.6% | 9.322 pts | 67.1% |
| **Test 2024 (final grade)** | 272 | **9.907 pts** | **68.0%** | 9.61 pts | 71.3% |

We trail Vegas by 0.30 points on the final exam —
0.18 worse than our validation miss. In
44.5% of 2024 games our predicted margin landed
closer to the actual result than the closing line did.

## What the model is (locked v1)

| Feature | Weight | Plain-English meaning |
|---|---|---|
| elo_diff | +0.0268/pt | Overall team-strength gap |
| off_pass_epa | +3.88/EPA-play | Passing efficiency edge |
| off_rush_epa | +6.28/EPA-play | Rushing efficiency edge |
| def_pass_epa | +2.72/EPA-play | Pass defense edge |
| def_rush_epa | +3.28/EPA-play | Run defense edge |
| qb_edge | +6.43/EPA-dropback | Starting-QB efficiency edge |
| st_epa_diff | +6.90/EPA-play | Special-teams edge |
| intercept | +1.69 pts | Effective home-field edge |

Win probability = normal bell curve around the predicted margin with width
σ=12.68 (recalibrated from our own validation errors; the textbook
starting value was 13.0).

## Confidence buckets (2024 final exam)

| When we said… | Games | We gave favorite | Favorite actually won | Avg miss |
|---|---|---|---|---|
| pick'em | 67 | 53% | 51% | 9.8 pts |
| lean | 102 | 60% | 73% | 9.5 pts |
| moderate | 60 | 69% | 70% | 8.7 pts |
| strong | 28 | 78% | 79% | 12.4 pts |
| heavy | 15 | 86% | 87% | 13.3 pts |

The probabilities calibrate well: what we said matches what happened in
four of five buckets. The one soft spot is "lean" games (predicted margin
2–5 pts): favorites won 73% of those while the model said 60% — the model's
mildest calls were a touch too humble on the 2024 final.

Blowouts (|margin|≥14) and nail-biters (|margin|≤3) per bucket are in
scoreboard.json for the site.

## Per-season honesty table

| Season | Games | Our miss | Our acc | Vegas miss | How predicted |
|---|---|---|---|---|---|
| 2015 | 256 | 10.345 | 58.6% | 10.127 | in-sample (train fit) |
| 2016 | 256 | 9.212 | 65.0% | 9.02 | in-sample (train fit) |
| 2017 | 256 | 10.673 | 66.0% | 10.094 | in-sample (train fit) |
| 2018 | 256 | 10.333 | 64.2% | 9.979 | in-sample (train fit) |
| 2019 | 256 | 10.266 | 67.1% | 10.211 | in-sample (train fit) |
| 2020 | 256 | 9.962 | 65.5% | 9.83 | in-sample (train fit) ← COVID, no crowds |
| 2021 | 272 | 11.148 | 62.4% | 10.781 | in-sample (train fit) |
| 2022 | 271 | 9.017 | 64.3% | 8.742 | honest (train fit) |
| 2023 | 272 | 10.429 | 62.9% | 9.901 | honest (train fit) |
| 2024 | 272 | 9.907 | 68.0% | 9.61 | honest (train+val fit) ← new kickoff rules + FINAL GRADE |

**2020 honest holdout** (fit 2015–2019+2021, predict COVID-season 2020):
our miss 9.98 pts vs Vegas 9.83 pts over 256 games —
the regime break, measured without the model ever seeing 2020.

## How to read this

- The model was built bottom-up from team strength and efficiency. It does
  not see the betting line, the opener, or any odds — those numbers don't
  exist on Tuesday morning when predictions are made.
- 2024 was graded exactly once and will not be tuned on. Whatever it says,
  it says.
- This is an engineering result, not a betting slip: the gap to Vegas
  (~0.30 pts on the final) is the honest price
  of predicting from data alone.
