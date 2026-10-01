# NFL Model Feature Structure: Flat Features vs Grouped Factors

Research date: 2026-09-30. Method: index-based research (browser_search/browser_open); no live-browser verification was needed or performed since all claims concern published methodology descriptions. Confidence flags: `index` unless noted. Sources that corroborate each other are noted.

## Summary

Across serious NFL spread-prediction approaches I found **three structural patterns**, not one:

1. **Flat feature vectors fed to ML models** — nflverse's `fastrmodels` win-probability models (12 flat play-state features); open-source XGBoost/ensemble pipelines on nflverse data (e.g., wadefuller's 140-feature predictor, organized into "buckets" that are documentation only); Kaggle-style pipelines.
2. **Grouped factors with weights** — Rithmm (factors like Offense/Defense/Tempo with user slider weights); Massey-Peabody (exactly four factors: rushing, passing, scoring, play success, weighted by predictive ability); nfelo's `nfelounits` (per-unit EPA ratings translated to Elo with empirically learned per-unit coefficients); FTN DVOA (offense/defense/special-teams sub-ratings that sum because they're point-denominated); a practitioner model weighting pass/rush × off/def components 40/25/12/8/5/10.
3. **Single composite ratings** — FiveThirtyEight Elo, nfelo, SRS: one number per team, spread ≈ rating difference (+ HFA).

On grouped-vs-flat: **I found no published evidence that grouping features into named factors improves predictive accuracy versus feeding the same information flat.** The arguments and designs encountered frame grouping as an interpretability/tunability/organizational choice (Rithmm's CEO explicitly: factors + sliders exist so bettors can "validate" gut instinct; feature "buckets" in READMEs are documentation). The one statistical argument for group-awareness is about *regularization of collinear blocks* (a practitioner's diagnosis that 90 correlated team-quality features should be "penalised as a group" — group-lasso-style), which is a modeling technique, not evidence that grouped features predict better than flat ones. For linear/additive models, grouping is a structured form of dimensionality reduction; for tree/GBM ensembles the model sees flat features regardless of how the UI groups them.

The most consistently predictive individual features: the **market spread line itself** (strongest single feature; market is near-efficient), **Elo differential**, **EPA/play differentials** (offense/defense, pass/rush splits), **success rate**, **DVOA/DAVE differentials**, **trailing point-differential trends**, **home-field advantage** (~1–1.7 pts, venue-specific), **rest differential**, **wind/weather**, and **QB value/availability**.

**Recommendation for a transparent, tunable model: a hybrid** — a grouped factor layer (Offense, Defense, Special Teams/Field position, Situational: HFA + rest + weather, Market anchor) with user-adjustable weights (sliders) initialized to backtested optimal values, each factor computed from a small set of visible flat features (EPA differentials, success rates, Elo, rest days, wind). Rationale: the decomposition mirrors how points are actually produced (additive, point-denominated), keeps the model explainable and tunable, avoids dumping ~100 collinear features on a non-technical user, and the statistical evidence supports grouped structure mainly as regularization/interpretability — which is exactly what this use case needs.

---

## Q1. What feature structures do serious NFL prediction approaches use?

### A. Academic literature: small-parameter, latent-strength models (grouped by construction)

- **Stern (1991)**: NFL score margin ≈ Normal(pregame point spread, SD ≈ 13.86; more recent estimates ~13.5). This is the basis for spread→win-probability conversion in most pregame models. (via arXiv 2212.08116 summary — `index`)
- **Harville (1980)**: linear model with home-field advantage + a season-long team performance measure; moderate success. (via CMU project report "Beating the NFL Football Point Spread," http://www.cs.cmu.edu/~epxing/Class/10701-06f/project-reports/gimpel.pdf — `index`)
- **Glickman & Stern, "A State-Space Model for National Football League Scores"** (https://www.glicko.net/research/nfl.pdf): dynamic state-space model — each team's latent strength evolves week to week, shrinks across offseasons, estimates HFA, and carries posterior uncertainty into margin forecasts. A small 1993 holdout slightly beat the quoted Vegas line on MAE/MSE, but the authors flagged injuries as missing information; the sample is far too small/old to establish a modern edge. (summary via https://github.com/oddsphereai-sketch/oddsphere/blob/HEAD/docs/model-audits/2026-08-19-football-data-and-research-r2.md — `index`)
- Takeaway: academic models are low-dimensional team-strength + HFA structures — effectively grouped (one latent strength per team, occasionally split into offense/defense), never large flat feature vectors.

### B. Power-rating systems

- **FiveThirtyEight NFL Elo**: one rating per team (mean 1505). Win prob = 1/(10^(−EloDiff/400)+1); "Vegas-style" spread ≈ EloDiff/25. Rating updates incorporate margin of victory, home field, strength of schedule, and prior-season ratings with mean reversion. Nate Silver's backtest: ~51% ATS — below the 52.4% break-even. Structure: **single composite** (no factor groups). (https://github.com/michellepellon/nfl-data-stack/blob/HEAD/docs/fivethirtyeight_comparison.md; https://mysportsanalysis.com/blogs/sports-fivethirtyeight/introducing-nfl-elo-ratings-1 — `index`)
- **nfelo** (greerreNFL, fully transparent benchmark): takes the 538 Elo framework and adds grouped components — win-total-market-implied initial ratings, a custom HFA model, a QB performance/availability model (nfeloqb), rest/weather adjustments, and "market reversion" (regress model spread toward the Vegas spread, bet only residual divergence). Even so: +0.34% edge vs the opener, **−0.16% vs the close** — it does not beat the closing line. (https://github.com/greerreNFL/nfelo; summarized at https://github.com/gesmith0606/nfl_data_engineering/blob/HEAD/.planning/SOTA_RESEARCH.md — `index`)
- **nfelounits** (same author): genuinely **grouped-factor architecture** — per-unit (pass/rush/special-teams) EPA ratings, opponent-adjusted, translated into Elo via an `EloTranslator` where "each unit has a coefficient controlling its contribution," weights learned empirically (`EloOptimizer`), summed to one Elo rating; a `GameContext` layer applies weather (wind/temp sigmoid curves reducing expected EPA) and location effects distributed across units with learned shares. (https://github.com/greerrenfl/nfelounits/blob/HEAD/Model/README.md — `index`)
- **FTN DVOA** (successor of Football Outsiders DVOA): play-level, opponent- and situation-adjusted value over average, computed separately for **offense, defense, and special teams**, then translated into points so the units are additive (total = off + def + ST). **DAVE** blends the preseason forecast with current DVOA (e.g., Week 3 2026: 65% preseason weight for offense, 90% for defense/ST) — an explicit shrinkage/grouping design for early-season small samples. WEIGHTED DVOA downweights early games. (https://ftnfantasy.com/nfl/week-3-dvoa-san-francisco-keeps-sailing; http://ftnfantasy.com/nfl/dvoa-explainer — `index`)

### C. Open-source nflverse/nflfastR projects

- **nflverse `fastrmodels` win-probability models**: a **flat list of 12 play-state features** (pregame spread decayed by elapsed time, 2nd-half kickoff receipt, home flag, time remaining, score differential, down/distance/field position, timeouts) into XGBoost. No factor grouping. (Note: in-game WP, adjacent to but not the same task as pregame spread prediction.) (https://github.com/sportsdataverse/nfl-data/blob/HEAD/docs/models/wp_spread.md — `index`)
- **wadefuller/nfl_predictor**: **140 flat features** fed to a production ensemble, documented in "buckets" (Metadata, Market data, Performance data) — the buckets are organizational; the model sees one flat vector. Features include Pinnacle spread line, 538 Elo, trailing 8-week point-differential and win% trends, ATS residuals, Pythagorean wins, offensive EPA. (https://github.com/wadefuller/nfl_predictor/blob/HEAD/README.md — `index`)
- **cyclonesundevil NFL predictor**: online additive team-rating model with components {margin rating, offensive points tendency, defensive points allowed tendency, home-field adjustment, rest-days adjustment, league baseline} — **grouped additive components**. (https://github.com/cyclonesundevil/microcomp-it-website/blob/HEAD/backend/NFL_PREDICTOR.md — `index`)
- **howlscastle97/nfl-model-hq** (Bayesian margin prediction): flat features — EWMA point differential, EPA aggregates, QB familiarity, rest, division, indoor. Tested a per-QB rating; it helped the linear model but added ~nothing on the deployed ensemble, "the likeliest reading is that the ensemble already extracts quarterback quality from team EPA, CPOE and qb_fam_diff together" — evidence that correlated extra features add no signal. (https://github.com/howlscastle97/nfl-model-hq/blob/HEAD/CLAUDE.md — `index`)
- **decohn/nfl-spread-pools**: minimalist — predicts final margin from **two features**: (a) the point spread, (b) DAVE differential between teams; RF/linear/SVR. Claims DAVE is "the best predictor of future NFL team performance that I've encountered." (https://github.com/decohn/nfl-spread-pools/blob/HEAD/README.md — `index`)

### D. Betting-model write-ups (Pinnacle-adjacent, Action Network-style, independent quants)

- **Massey-Peabody** (Rufus Peabody, independent pro bettor; documented at massey-peabody.com, quoted at https://ramsfansunited.com/viewtopic.php?t=13431): **grouped by design** — "only four statistics – one each for rushing, passing, scoring and play success," built bottom-up from play-level data, "finding the appropriate weight for them in our model," with weights chosen **by predictive ability, not explanatory power**. MP lines = rating difference + standard HFA + rest adjustments (byes/Thursday), regressed toward the market; 55.4% lifetime ATS on a selective subset — "selectivity is the edge, not the model." (corroborated by https://github.com/gesmith0606/nfl_data_engineering/blob/HEAD/.planning/SOTA_RESEARCH.md — `index`, two sources)
- **Practitioner model (fourty2se7en/nfl-card)**: explicitly grouped with fixed weights — power ratings from opponent-adjusted EPA + success rate via ridge regression, **split pass/rush × offense/defense, weighted 40/25/12/8/5/10**, exponential recency decay (8-game half-life), validated at r = 0.935 vs actual point differentials; venue-specific HFA (league compressed to ~1.0–1.7); wind-only weather adjustments; rest differential capped at ±1.5 pts; per-game variance for spread/moneyline conversion; an Elo cross-check built from scores only (no EPA) so disagreement is informative (r = 0.906 with main model). (https://github.com/fourty2se7en/nfl-card/blob/HEAD/SKILL.md — `index`)
- **Market-efficiency context** (Pinnacle-relevant): Pinnacle closing line r² ≈ 0.997 to outcomes; break-even 52.4% at −110; the honest success metric is **CLV vs the opener** (sharp pros sustain 2–5%). No publicly documented reproducible method beats a sharp closing line. (https://github.com/gesmith0606/nfl_data_engineering/blob/HEAD/.planning/SOTA_RESEARCH.md; https://github.com/kontainer-sh/bundesliga-predictor/blob/HEAD/docs/research/2026-08-20-closing-line.md; https://www.sportsbookreview.com/forum/handicapper-think-tank/475316-the-misunderstanding-of-beating-the-closing-line — `index`, three sources agree)
- **Rithmm** (consumer product; CEO Megan Lanham quoted in Sports Business Journal, 2023-06-08): factor list (basketball example: offense, defense, tempo, fouls, 3-pointers), "each factor has a slider bar to weigh the importance you place… Those weights go into our predictive models." Affiliate writeups describe NFL-style models as bundles of underlying metrics per factor (e.g., Offense = points, efficiency). Grouped factors + user weights + backtest. (https://www.sportsbusinessjournal.com/SB-Blogs/SBJ-Power-Up/2023/06/08/; https://www.rithmm.com/sports-betting-picks/liberty-vs-sun-ai-predictions-and-wnba-bet-picks-today — `index`, two sources)
- Kaggle note: recent Kaggle NFL competitions (Big Data Bowl 2025/2026) are player-tracking trajectory tasks, not spread prediction — not applicable. Older spread-prediction Kaggle/GitHub projects (e.g., nzeisenberg/nfl_project, breissic/nfl-betting-model) use flat feature sets with standard classifiers (logistic/SVM/RF/MLP) or plain Elo; nothing methodologically distinctive on grouping. (https://github.com/nzeisenberg/nfl_project; https://github.com/breissic/nfl-betting-model — `index`)

---

## Q2. Grouped vs flat: performance evidence or UX choice?

**Bottom line: grouping is overwhelmingly a user-experience / interpretability / organizational choice in the sources found — not a demonstrated predictive-performance win.** The breakdown:

**Evidence that grouping is UX/organizational:**
1. **Rithmm** — the product's own CEO frames factors + sliders as a way for bettors to "validate" gut instinct, i.e., tunability and trust, not accuracy. No published backtest compares grouped-factor vs flat-feature versions of the same model. Marketing pages, not methodology docs. (`index`)
2. **Feature "buckets" in ML pipelines** (wadefuller's 140 features; gesmith0606's planned 200+ features in 6 groups: team/player/situational/temporal/market/historical; nerdfootballai's 5 categories) — the groups are documentation; the model ingests one flat vector. Grouping changes nothing mathematically. (`index`)
3. **DVOA's off/def/ST split and nfelounits' unit structure** — the grouping is intrinsic to the *rating construction* (point-denominated units sum cleanly), and the per-unit weights are then either fixed or empirically learned. The performance claim is about the resulting composite, not about grouping beating an equivalent flat model.

**The one statistical argument for group-awareness:**
4. **ryanpmcintire/nfl_py3 diagnosis** — with ~90 features, "every team-quality column in the model is a restatement of the line" (spread_line r = 0.804 with point-diff trend, 0.758 with Elo diff, 0.696 with offensive EPA/play diff). The proposed fix: "penalise the block as a group while leaving spread_line itself unpenalised, so that the market's own estimate is carried by the market column and the team-quality columns can only add what the market has not priced." This is a **group-lasso-style regularization argument**: related features form a collinear block and should be shrunk *together*. It improves model *behavior* (avoiding double-counting), not proof that grouped factors out-predict flat features given the same info. (https://github.com/ryanpmcintire/nfl_py3/blob/HEAD/docs/spread_hole_diagnosis.md — `index`)

**Supporting considerations:**
5. For **linear/additive models**, grouping ≈ structured dimensionality reduction with shrinkage (DVOA→DAVE blending is exactly this for early-season noise). For **tree/GBM ensembles**, the model sees flat features regardless of UI grouping — grouping cannot change predictions, only presentation. (methodological reasoning grounded in sources 4, J, and the flat-pipeline sources above)
6. A feature-validation checklist widely echoed by practitioners: a new feature must (a) work out-of-sample, (b) be available pregame, (c) be stable, (d) **add signal beyond Elo** ("many features are just proxies for team quality"), (e) rest on 3+ seasons. This cuts against naive flat feature-stacking: most individual stats are redundant with a composite rating. (https://github.com/michaelschecht/my-prompt-library/blob/HEAD/site/library/3_Skills/Finance/odds-modeling/SKILL.md — `index`)
7. **No head-to-head test found**: no paper or write-up I found compares "same information, grouped factors vs flat features" on holdout ATS performance. Massey-Peabody's success (55.4% selective) is attributed to *selectivity*, and nfelo's transparency exercise shows even a well-built grouped model can't beat the close.

**Summary table:**

| Approach | Structure | Grouping role |
|---|---|---|
| 538 Elo / nfelo / SRS | Single composite rating | n/a (maximal grouping — one number) |
| Massey-Peabody | 4 grouped factors, weights by predictive ability | Model-structural; weights learned |
| nfelounits | Per-unit EPA → Elo via learned coefficients | Model-structural; shrinkage + interpretability |
| FTN DVOA/DAVE | Off/def/ST sub-ratings, point-additive | Rating construction; DAVE = shrinkage |
| nfl-card practitioner model | Pass/rush × off/def @ 40/25/12/8/5/10 + HFA + weather + rest | Model-structural, fixed transparent weights |
| Rithmm | Named factors + user sliders | UX/tunability; no perf. evidence published |
| nflverse fastrmodels; wadefuller 140-feat; Kaggle-style | Flat feature vectors → XGBoost/ensembles | Grouping = documentation only |
| Academic (Stern; Glickman–Stern) | Latent team strength + HFA | Grouped by construction (low-dim) |

---

## Q3. Most common and predictive individual features for NFL spread prediction

Recurring across sources (ordered roughly by consensus importance):

1. **The market spread line itself** — the single strongest feature (r ≈ 0.80 with point-differential trends; Pinnacle close r² ≈ 0.997 to outcomes). Used as a feature (nflfastR `spread_time`, wadefuller, decohn) or as the reversion anchor (nfelo "market reversion," Massey-Peabody regression toward market). (multiple sources)
2. **Elo rating differential** (538-style, MOV-adjusted) — r ≈ 0.758 with the line; the standard team-strength composite. (ryanpmcintire; 538; nfelo)
3. **EPA per play differentials** — offensive and defensive, often split pass/rush; the most-cited play-level efficiency feature (nfl-card 40/25/12/8/5/10 weights; wadefuller `off_epa`; howlscastle; rice tests show EPA dominates DVOA's success baseline and yards/play as a standalone rating).
4. **Success rate** (share of plays with positive EPA) — paired with EPA in most pipelines.
5. **DVOA / DAVE differentials** — opponent- and situation-adjusted efficiency; DAVE adds preseason-prior shrinkage (decohn's "best predictor of future team performance"; ontapsportsnet uses avg of DVOA + EPA/play + success rate as unit rankings).
6. **Trailing point-differential / win% trends** (EWMA or 8-game windows) — r ≈ 0.804 (diff) with the line; the "scoreboard" baseline any rating must beat (rice: "point differential earns its place as a reference: any rating that cannot beat it is not doing anything").
7. **Home-field advantage** — now small and venue-specific (~1.0–1.7 pts league-wide; up to ~2.0–2.2 in SEA/KC/DEN/BUF/NO/GB/BAL/PIT; ~0.8–1.0 for LA teams/JAX/LV/ATL). Older flat-3 assumptions are stale. (nfl-card; 538 uses ~52 Elo pts ≈ 2 pts)
8. **Rest differential** (days since last game; bye/Thursday edges) — capped at ~±1.5 pts; used by Massey-Peabody, cyclonesundevil predictor, nfl-card.
9. **Weather — wind** — the only weather variable consistently validated (10–15 mph → total −1.5; 15–20 → −3.0; 20+ → −5.0); precipitation and extreme cold are second-order. (nfl-card; nfelounits weather sigmoids)
10. **QB value / availability** — EPA per dropback edge (~10 pts of spread per 1.0 EPA/dropback edge per edgedesksports measurement); QB absence ≈ 3.9 pts; nfelo's nfeloqb; 538's QB adjustment. The single biggest injury signal; other injuries are mostly noise at public-data resolution.
11. **Turnover-related features** — tricky: turnover *margin* is mostly noise (game-to-game persistence r ≈ 0.077; "anyone reading turnover margin as skill is reading noise"), but interception *EPA* carries real forward information (dropping it costs log-loss in rice tests). Use rates/EPA, not margins.
12. **Special-teams EPA** — counts ~1:1 with offensive EPA per play (rice: +0.0034 log-loss improvement, largest single improvement in their battery); DVOA treats it as a third unit.
13. **Situational flags** — division game, indoor/dome, primetime: small, commonly included as indicators.
14. **Line movement / market features** (opener→current drift, steam, reverse line movement) — among the most predictive for ATS *outcomes*, but only legitimate as features if observable at bet time; using the *closing* line as a training feature is leakage (msellin whitepaper's DRIFT-FEATURE-NOT-A-TRAINING-FEATURE rule).

Features that repeatedly **fail** validation: raw points/yards totals (descriptive, not predictive), turnover margin, ATS trends ("point_diff_ats_season" is tracked but as a *residual to explain*, not a predictor), venue-specific HFA estimated from small samples, rivalry/motivation narratives.

---

## Q4. Recommended structure for a transparent, tunable model for non-technical users

**Recommendation: a hybrid — grouped factors on top, a small flat feature set underneath, additive math throughout.**

**Concrete design:**

- **Factor layer (what the user sees and tunes): 5–6 sliders**, each 0–100%, initialized to backtested-optimal weights:
  1. **Offense** (pass efficiency + rush efficiency + success rate)
  2. **Defense** (pass defense + rush defense + pressure/turnover creation)
  3. **Situational** (home-field/venue + rest differential + division flag)
  4. **Environment** (wind/weather + indoor)
  5. **Quarterback** (QB EPA edge + availability adjustment)
  6. **Market anchor** (Vegas spread as a shrinkage target — the nfelo/Massey-Peabody "regress toward market" step)
- **Feature layer (visible, read-only or advanced):** each factor shows its 3–6 constituent flat features with fixed, published sub-weights (e.g., Offense = 40% pass EPA/play diff + 25% rush EPA/play diff + 12% success-rate diff…, mirroring the nfl-card 40/25/12/8/5/10 scheme; all features as *differentials* home−away, opponent-adjusted, recency-weighted with ~8-game half-life).
- **Combination:** weighted sum of factor scores → expected margin → spread; margin ÷ ~13.5 (Stern's SD) → cover probabilities via normal (or empirical) distribution; show each factor's point contribution ("Offense: +2.3 pts") so the user sees *why*.
- **Slider semantics:** moving a slider re-weights that factor's point contribution and the model renormalizes; display the backtested-optimal position as the default detent, so tuning is "deviate from the data-driven baseline deliberately," exactly Rithmm's UX but with the baseline weights published.

**Reasoning, tied to the evidence:**
1. **Grouping matches the domain's additive structure.** Points are produced by offense, prevented by defense, modulated by situation — and point-denominated units (DVOA, nfelounits' EPA units) sum cleanly. A linear factor model is therefore not a simplification imposed on the data; it's the data's natural shape (DVOA, Massey-Peabody, nfl-card all converge here).
2. **No predictive penalty is expected from grouping.** Q2 found no evidence that grouped factors underperform flat features given the same information; the risk of flat stacking is collinear double-counting (ryanpmcintire's diagnosis), which grouping-plus-shrinking directly addresses. For a non-technical user, 140 flat features are uninterpretable and mostly redundant with Elo anyway (feature-validation rule #4).
3. **Tunability requires factors, not features.** A user can reason about "I think defense matters more this week" (Rithmm's validated UX insight); they cannot reason about "increase the weight on diff_def_epa_per_play by 0.2." Sliders must sit at the factor level to be meaningful.
4. **Transparency requires published sub-weights and per-factor point contributions.** nfelo/nfelounits and Massey-Peabody are the models for this: every weight is stated, every adjustment is in points. Avoid black-box ensembles (XGBoost/RF) as the *presented* model — they can run underneath for calibration, but the user's mental model should be the additive factor equation.
5. **Honest expectations must be built in.** No public model beats the Pinnacle close (nfelo: −0.16% vs close; 538: ~51% ATS). The product promise should be "a transparent, tunable read on the game plus disciplined comparison to the market" (CLV vs opener as the scoreboard), not "beats Vegas." The Market-anchor factor makes this honesty structural: the model *starts* from the market's number and only deviates on its factor disagreements.

**What the evidence says not to do:** a pure flat-feature ML dump (uninterpretable, collinear, adds nothing beyond Elo per the validation checklist); a pure single-rating model (not tunable); sliders on dozens of individual features (cognitively unusable — Rithmm's lesson is that ~5 factors is the right granularity).

---

## Could not verify / open questions

1. **No head-to-head evidence** that grouped-factor models outperform flat-feature models (or vice versa) holding information constant — this comparison appears never to have been published. The Q2 conclusion ("grouping is mainly UX/organizational") rests on the *absence* of contrary evidence plus the regularization argument, not on a direct test.
2. **Rithmm's actual model internals** are proprietary; the factor/slider description comes from the CEO's press interview and affiliate marketing pages, not methodology documentation. Whether their factors are predictive groupings or pure UI is unverifiable from public sources.
3. **Massey-Peabody's exact four statistics and weights** are summarized from a forum quotation of their methodology page and a secondary research note; the primary page (massey-peabody.com) was not fetched directly.
4. **Kaggle** has no current NFL spread-prediction competition (Big Data Bowl is now player-tracking), so that leg of the mission rests on older GitHub projects rather than a live leaderboard.
5. All findings are `index`-level (search-result and fetched-page text); no live interaction with any model or app was performed. Quantitative claims (e.g., 55.4% ATS, r = 0.935) are as-reported by their authors without independent replication.

## Sources

- Academic: Stern (1991) via https://arxiv.org/pdf/2212.08116.pdf; Harville (1980)/Gimpel via http://www.cs.cmu.edu/~epxing/Class/10701-06f/project-reports/gimpel.pdf; Glickman & Stern state-space model via https://www.glicko.net/research/nfl.pdf and literature summary https://github.com/oddsphereai-sketch/oddsphere/blob/HEAD/docs/model-audits/2026-08-19-football-data-and-research-r2.md
- Power ratings: https://github.com/michellepellon/nfl-data-stack/blob/HEAD/docs/fivethirtyeight_comparison.md; https://mysportsanalysis.com/blogs/sports-fivethirtyeight/introducing-nfl-elo-ratings-1; https://github.com/greerreNFL/nfelo; https://github.com/greerrenfl/nfelounits/blob/HEAD/Model/README.md; https://ftnfantasy.com/nfl/week-3-dvoa-san-francisco-keeps-sailing; http://ftnfantasy.com/nfl/dvoa-explainer
- Open-source nflverse: https://github.com/sportsdataverse/nfl-data/blob/HEAD/docs/models/wp_spread.md; https://github.com/wadefuller/nfl_predictor/blob/HEAD/README.md; https://github.com/cyclonesundevil/microcomp-it-website/blob/HEAD/backend/NFL_PREDICTOR.md; https://github.com/howlscastle97/nfl-model-hq/blob/HEAD/CLAUDE.md; https://github.com/decohn/nfl-spread-pools/blob/HEAD/README.md; https://github.com/akushwarrior/rice/blob/HEAD/docs/matchup_scoreboard.md
- Betting write-ups / practitioners: https://ramsfansunited.com/viewtopic.php?t=13431 (Massey-Peabody methodology quote); https://github.com/gesmith0606/nfl_data_engineering/blob/HEAD/.planning/SOTA_RESEARCH.md; https://github.com/fourty2se7en/nfl-card/blob/HEAD/SKILL.md; https://github.com/ryanpmcintire/nfl_py3/blob/HEAD/docs/spread_hole_diagnosis.md; https://github.com/michaelschecht/my-prompt-library/blob/HEAD/site/library/3_Skills/Finance/odds-modeling/SKILL.md; https://www.sportsbusinessjournal.com/SB-Blogs/SBJ-Power-Up/2023/06/08/ (Rithmm); https://www.rithmm.com/sports-betting-picks/liberty-vs-sun-ai-predictions-and-wnba-bet-picks-today
- Market efficiency / CLV: https://github.com/kontainer-sh/bundesliga-predictor/blob/HEAD/docs/research/2026-08-20-closing-line.md; https://www.sportsbookreview.com/forum/handicapper-think-tank/475316-the-misunderstanding-of-beating-the-closing-line

Working notes: notes/sources-batch1.md, notes/sources-batch2.md, notes/sources-batch3.md, notes/sources-batch4.md
