# Research Round 2 — 2026-09-30
Two questions for NFL v1. Plain-language answers first, evidence below.

---

## Conclusions (read this part)

**Q1 — Turning a predicted margin into win probability and fair odds.**
Use the textbook method: assume actual margins scatter around our predicted
margin with a bell curve (normal distribution) with standard deviation **σ = 13
points**, then win probability = the area of that curve above zero. Our own
2015–2023 data says the true number is 12.8 and it has not moved across eras
(12.82 for 2015–2019, 12.77 for 2020–2023), and the published literature says
13.5–13.86 — the choice barely changes any probability (under 1 point), so 13
is a fine v1 constant. One refinement the pipeline should apply: after the
official backtest, replace 13 with the *model's own* measured error spread
from validation — our predictions are worse than the line's, so borrowing the
line's spread slightly overstates our confidence. Handle pushes honestly:
about 13% of games land exactly on 3 and ~10% on 7 (measured in our data), so
a cover probability near those numbers must show the push slice separately
instead of pretending it is zero. Fancy alternatives (key-number-weighted
models) exist but only matter for *cover* probabilities near 3 and 7; for plain
win probability the simple bell curve is proven good enough. **This changes a
v1 design decision:** the scoreboard's win-probability/fair-odds column should
use σ fitted from our own validation residuals (13 as the starting value), not
a hardcoded literature number.

**Q2 — Can we honestly backtest the QB injury-swap?**
**Verdict: yes for v1, but only under a strict "Tuesday knowledge" rule — and
the full auto-update vision stays v2.** The concrete evidence from our own
injury file: 85% of final Out/Doubtful/Questionable designations land on
**Friday** (median 52 hours before kickoff), because that is when the NFL's
real reporting cycle produces them (practice reports Wed/Thu, final statuses
Friday). A Tuesday-morning prediction cannot honestly know them. Measuring it:
of 169 regular-season team-weeks where the starting QB was finally ruled Out,
**123 (73%) were new that week** — the QB was not Out/Doubtful the week
before, so last week's report gives no warning. That is ~12 games per season
(2.1% of starts) where using Friday's designation in a Tuesday backtest would
be lookahead, each one worth roughly 4 points of prediction swing. The honest
v1 rule is mechanical and auditable: **a QB's availability input = the latest
injury row timestamped before Tuesday 8am ET** (usually last week's final
status, plus the ~13% of designations that land Monday). That captures the
carryover injuries correctly and misses the new mid-week ones — exactly as a
real Tuesday model would. The "prediction updates itself the hour news
breaks" version needs a live feed and intra-week timing our historical file
cannot reconstruct, so it is v2-only. **Design decision:** v1 backtest uses the
Tuesday-knowledge injury rule; the scoreboard notes that ~12 new QB injuries
per season are invisible to a Tuesday model by construction.

---

## Q1 — Evidence

### (a) The SD: literature vs our data
- Stern (1991): margin ~ Normal(pregame spread, SD **13.86**). Still the
  cited basis for spread→win-prob conversion (via arXiv 2212.08116 summary).
- 2002–2011 study (arXiv 1211.4000): SD **13.588** around the line; chi-squared
  test says the normal curve is an adequate fit; their table shows normal-CDF
  win probs within ~1pp of empirical (e.g. spread 7: 69.7% model vs 68.9%
  actual).
- Recent practitioners (Sportsbook Review forum): "a standard deviation
  assumption of **13** is very accurate for the NFL."
- **Our data** (schedules 2015–2023, regular season, n=2,351): SD of
  (actual margin − closing spread) = **12.80**; 2015–2019: 12.82, 2020–2023:
  12.77. No meaningful era drift inside our window.
- Sensitivity: Φ(7/13.5)=69.8% vs Φ(7/13.86)=69.3% vs Φ(7/12.8)=70.8%. The
  whole literature band moves win probability by about a point. v1 can safely
  use 13.

### (b) Empirical alternatives — worth it for v1?
- Football margins are **lumpy**: in our data |margin|=3 is 14.7% of games,
  |margin|=7 is 8.7%, |margin|=10 is 5.0% — a smooth bell curve expects ~5%
  each. (Matches the independent measurement in roni-altshuler/nfl_predictor:
  14.82% / 9.08%, with fitted key-number weights w(3)=2.88, w(7)=1.83.)
- Consequence 1 (good for v1): for **win probability** the lumpiness nearly
  cancels out — integrating over half the number line washes the bumps away.
  Our check: normal CDF(13) vs empirical win rate by spread — spread 3: 58.8%
  vs 57.6% actual; spread 14: 85.0% vs 85.7%. Fine.
- Consequence 2 (the caveat): for **cover probability vs a posted line** near
  key numbers the bell curve drifts — our data at line 7: normal says 69.8%,
  actual 76.0%; at line 10: 77.1% vs 85.7% actual; at line 6: 67.2% vs 60.0%.
  Deviations up to ~6–9pp at exactly the numbers bettors care about.
- Verdict: v1 ships the normal CDF for win probability/fair odds (proven
  adequate). The key-number-weighted lattice model is the correct v2 upgrade
  for cover probabilities, not a v1 requirement.

### (c) Pushes, in probability terms
- Measured in our data: games landing exactly on the spread — **12.8% at
  spread 3.0** (n=196), **9.6% at 7.0**, **10.2% at 10.0**, 2.9% overall.
  (Corroborates the published "~8% of the market at −3" figure.)
- For **moneyline win probability** pushes are a non-issue: a tie is 0.4% of
  games in our data — fold it into "not a win" and note it, or ignore it.
- For **cover probability vs a posted line L**: report three numbers —
  P(cover) = 1 − Φ((L−μ)/σ), P(push) = empirical rate at L (12.8% at 3,
  ~10% at 7/10, ~3% elsewhere), P(fail) = the rest. Never let the bell curve
  silently assign the push mass to one side — on the most-bet number in the
  sport that is an 8–13% error by construction.

### (d) Recommended v1 formula + worked example
- Inputs: predicted margin μ (home − away, points), σ = 13 (recalibrate from
  validation residuals after the official backtest; document the fitted value).
- P(home wins) = Φ(μ/σ), where Φ is the standard normal CDF.
- Fair (no-vig) odds: decimal = 1/p. American: if p ≥ 0.5, −100·p/(1−p);
  if p < 0.5, +100·(1−p)/p. Away win prob = 1 − p (ties ~0.4% ignored, noted).
- Cover vs closing line L: P(cover) = 1 − Φ((L−μ)/σ), plus empirical push
  rate at L as above.
- **Worked example:** model predicts home by 4.5 (μ=4.5), σ=13.
  P(home win) = Φ(4.5/13) = Φ(0.346) = **63.5%**.
  Fair odds: decimal 1/0.635 = **1.57**; American **−174**
  (−100×0.635/0.365). Away: 36.5% → **+174** (100×0.635/0.365).
  Cover vs a closing line of home −3: 1 − Φ((3−4.5)/13) = Φ(0.115) =
  **54.6%**, with a **12.8%** push slice and 32.6% fail.
- Honesty note for the scoreboard: σ=13 describes outcomes around the
  *closing line*. Our model's errors run ~11% larger (MAE 10.3 vs 9.3), so
  using 13 understates our uncertainty slightly — the recalibration step
  above fixes this; until then, treat displayed win probabilities as a touch
  overconfident and say so.

---

## Q2 — Evidence (all from hidden_files/injuries_2015_2024.parquet)

### What the timestamps show
- 54,720 rows, zero null `date_modified` (UTC). Row timestamps cluster on
  **Wed/Thu/Fri** — the NFL's actual practice-report cycle — not on scrape
  day: 83% of final-status rows land Friday, median **52.6 hours before
  kickoff**. This is publication timing, usable as knowledge timing.
- QBs specifically: 827 QB player-weeks with a final status; 84.5% stamped
  Friday. Of 332 QB "Out" rows, only **12.7% predate the Tuesday 8am ET
  cutoff** of their game week.

### The carryover test (the decisive one)
- QB "Out" designations where the same QB was already Out/Doubtful the
  previous week (knowable Tuesday): 170/332 = **51%**.
- **New** Out designations (not Out/Doubtful last week): 162/332 = **49%** —
  decided during the current week's Wed–Fri cycle, after a Tuesday prediction.
  120 of those weren't on the injury report at all the prior week.
- Restricted to designated starters (depth-chart QB1, regular season):
  169 QB1-Out team-weeks, of which **123 (73%) are new** — 2.1% of all
  5,860 QB1 starts, ≈**12 per season**. With a missing starter worth ~4
  points of spread, each leaked swap is a material lookahead event.

### Verdict and the honest rule
- **Backtestable for v1** under the **Tuesday-knowledge rule**: QB
  availability input = latest injury row with `date_modified` ≤ Tuesday
  8am ET of the game week (in practice: last week's final status, plus rare
  Monday designations). Mechanical, auditable, zero leakage. It correctly
  handles carryover injuries (~30% of QB-Out team-weeks) and honestly misses
  the ~12 new ones per season — exactly as a real Tuesday model would.
- **Not honest**: feeding Friday final statuses into a Tuesday prediction
  (leaks ~12 high-leverage swaps/season). Also rejected: moving prediction
  time to Friday — it breaks the uniform weekly design (Thursday games would
  be ungradeable).
- **v2-only**: the "auto-update as news breaks" vision. Our file has weekly
  grain with publication-day timestamps; it cannot reconstruct intra-week
  news timing (e.g., "ruled out Wednesday 2pm"), so a live feed (ESPN/Sleeper)
  is required. That work is real but separate.
- Data caveats: 2023 is missing postseason injury weeks (regular season
  complete); `season`/`week` are Float64 (cast to int); depth-chart QB1
  matches the actual starter 88% (per the v1 feature report) — the 12% gap
  is in-season changes, the known limitation the injury work addresses.

---

## Sources
- Stern (1991) via https://arxiv.org/pdf/2212.08116.pdf — SD 13.86 normal model.
- https://arxiv.org/pdf/1211.4000 — 2002–2011 line-difference study, SD 13.588,
  normal-vs-empirical win-prob table.
- https://github.com/roni-altshuler/nfl_predictor/blob/HEAD/CLAUDE.md —
  margin lumpiness table, key-number weights w(k), push ≈8% at −3, "moneyline
  barely moves."
- https://github.com/dasilvadub/outlier/blob/HEAD/.agents/teamwork_preview_explorer_survey_3/report.md —
  key-number frequencies, push-prob adjustment rule
  (Absolute Win Prob = (1 − push_prob) × Conditional Win Prob).
- https://github.com/michaelschecht/my-prompt-library/blob/HEAD/site/library/3_Skills/Finance/sports-betting/SKILL.md —
  key numbers 3 (~15%) and 7 (~10%).
- https://www.sportsbookreview.com/forum/handicapper-think-tank/465577-standard-deviation-from-the-spread-in-nfl —
  practitioner SD ≈ 13.
- https://www.sportsbookreview.com/forum/handicapper-think-tank/477134-converting-nfl-predicted-scores-into-win-probabilities —
  spread→moneyline conversion discussion.
- Own data: hidden_files/schedules_2015_2024.parquet (2,351 REG games
  2015–2023; 2024 untouched), hidden_files/injuries_2015_2024.parquet,
  hidden_files/depth_charts_2015_2024.parquet, hidden_files/INJURIES_NOTES.md.
- Prior round: ~/workspace/research_notes/nfl-model-feature-structure-20260930-0230/report.md (Q3/Q4).
