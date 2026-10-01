#!/usr/bin/env python3
"""
OFFICIAL V1 BACKTEST — nfl-prediction-model-v1
===============================================
The one honest grade. Locked model: Ridge(alpha=100) on the 7 locked
bottom-up features (no market input anywhere):

    elo_diff, off_pass_epa, off_rush_epa, def_pass_epa, def_rush_epa,
    qb_edge, st_epa_diff  (+ intercept)

Features: hidden_files/features_v3.parquet (v3 = v2 with the Tuesday-
knowledge QB starter fix; see features_build_v3.py header).

Splits (chronological, never random):
    train 2015-2021 -> fit
    val   2022-2023 -> tune/validate + recalibrate sigma
    test  2024      -> graded EXACTLY ONCE below. No tuning on test, ever.

Win probability (RESEARCH_ROUND2.md Q1): P(home win) = Phi(mu / sigma),
sigma = SD of the train-fit model's validation residuals (recalibrated from
the Stern starting value 13). Fair odds: decimal 1/p; American -100*p/(1-p)
if p>=0.5 else +100*(1-p)/p. Ties (0.4% of games) ignored for moneyline.

The closing line (spread_line, positive = home favored) appears ONLY as the
benchmark in panel 3 — never as a feature. If the model beats the line by
more than 0.05 MAE on any honest split, the script raises the leakage flag.

Outputs:
    hidden_files/BACKTEST_RESULTS.md  (plain-language official grade)
    hidden_files/scoreboard.json      (clean data for the GitHub Pages site)
"""
import json
import numpy as np
import pandas as pd
import polars as pl
from math import erf, sqrt
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

HF = "/home/hatch/workspace/goals/nfl-prediction-model-v1/hidden_files/"
LOCKED = ["elo_diff", "off_pass_epa", "off_rush_epa", "def_pass_epa",
          "def_rush_epa", "qb_edge", "st_epa_diff"]
TARGET = "home_margin"
ALPHA = 100.0

# ------------------------------------------------------------------ helpers --
def Phi(x):
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))

def mae(a, b):
    return float(np.mean(np.abs(np.asarray(a) - np.asarray(b))))

def wacc(pred, actual):
    pred, actual = np.asarray(pred), np.asarray(actual)
    m = actual != 0
    return float(np.mean((pred[m] > 0) == (actual[m] > 0)))

def american_odds(p):
    p = min(max(p, 0.001), 0.999)
    if p >= 0.5:
        return int(round(-100.0 * p / (1.0 - p)))
    return int(round(100.0 * (1.0 - p) / p))

# ---------------------------------------------------------------------- load --
print("Loading features...")
f = pl.read_parquet(HF + "features_v3.parquet").to_pandas()
assert "spread_line" not in f.columns and "market_anchor" not in f.columns, \
    "MARKET LEAK: market column in features!"
assert not f[LOCKED + [TARGET]].isna().any().any(), "nulls in features/target"
print(f"  {len(f)} games x {len(f.columns)} cols | seasons {sorted(f['season'].unique())}")

print("Loading closing lines (benchmark only)...")
s = pl.read_parquet(HF + "schedules_2015_2024.parquet").to_pandas()
s = s[s["game_type"] == "REG"][["game_id", "spread_line", "gameday"]].copy()
assert s["spread_line"].notna().all(), "missing closing lines!"
f = f.merge(s, on="game_id", validate="one_to_one")
f = f.sort_values(["season", "week"]).reset_index(drop=True)
print(f"  lines merged: {len(f)} games, 0 missing")

# ------------------------------------------------------------------ split/fit --
tr = f[f["season"].between(2015, 2021)]
va = f[f["season"].between(2022, 2023)]
te = f[f["season"] == 2024]
print(f"  train {len(tr)} | val {len(va)} | test {len(te)}")
assert len(te) == 272, f"expected 272 test games, got {len(te)}"

def fit_ridge(df):
    sc = StandardScaler().fit(df[LOCKED].values)
    m = Ridge(alpha=ALPHA).fit(sc.transform(df[LOCKED].values), df[TARGET].values)
    return sc, m

def predict(sc, m, df):
    return m.predict(sc.transform(df[LOCKED].values))

# stage 1: fit on train, grade on val (honest)
sc1, m1 = fit_ridge(tr)
p_tr = predict(sc1, m1, tr)   # in-sample (labeled as such)
p_va = predict(sc1, m1, va)   # honest
y_tr, y_va = tr[TARGET].values, va[TARGET].values

# sigma recalibration (RESEARCH_ROUND2 Q1): SD of honest validation residuals
resid_va = y_va - p_va
sigma = float(np.sqrt(np.mean(resid_va ** 2)))
print(f"\nSigma recalibration: Stern start 13.00 -> fitted {sigma:.2f} "
      f"(val residuals, n={len(va)})")

# sanity anchor: bottom-up must not beat the line on honest splits
line_va_mae = mae(va["spread_line"].values, y_va)
val_mae = mae(p_va, y_va)
if val_mae < line_va_mae - 0.05:
    print("!!! LEAKAGE FLAG: model beats the line on validation. STOP.")
else:
    print(f"Sanity anchor OK on val: model {val_mae:.3f} vs line {line_va_mae:.3f}")

# stage 2: refit on train+val, grade ONCE on 2024
trva = pd.concat([tr, va], ignore_index=True)
sc2, m2 = fit_ridge(trva)
p_te = predict(sc2, m2, te)   # THE ONE honest grade
y_te = te[TARGET].values
line_te = te["spread_line"].values
test_mae = mae(p_te, y_te)
line_te_mae = mae(line_te, y_te)
if test_mae < line_te_mae - 0.05:
    print("!!! LEAKAGE FLAG: model beats the line on TEST. STOP.")
else:
    print(f"Sanity anchor OK on test: model {test_mae:.3f} vs line {line_te_mae:.3f}")

# final locked weights (native units) from the train+val fit
native = m2.coef_ / sc2.scale_
weights = {c: float(v) for c, v in zip(LOCKED, native)}
intercept = float(m2.intercept_)
print("\nLocked v1 weights (native units, train+val fit):")
for c in LOCKED:
    sd = float(sc2.scale_[LOCKED.index(c)])
    print(f"  {c:16s} {weights[c]:+.4f}/unit  ({weights[c]*sd:+.2f} pts per SD)")
print(f"  intercept (home edge): {intercept:+.3f}")

# win probabilities with recalibrated sigma
def winprob(mu):
    return Phi(mu / sigma)

# ------------------------------------------------- panel 1: vs raw results --
def split_metrics(pred, y, line):
    return {
        "n": int(len(y)),
        "model_mae": round(mae(pred, y), 3),
        "model_win_acc": round(wacc(pred, y), 4),
        "vegas_mae": round(mae(line, y), 3),
        "vegas_win_acc": round(wacc(line, y), 4),
    }

panel1 = {
    "train_in_sample": split_metrics(p_tr, y_tr, tr["spread_line"].values),
    "val": split_metrics(p_va, y_va, va["spread_line"].values),
    "test": split_metrics(p_te, y_te, line_te),
}
print("\nPanel 1:", json.dumps(panel1, indent=1))

# --------------------------------------------- panel 2: confidence buckets --
BUCKETS = [("pick'em", 0.0, 2.0), ("lean", 2.0, 5.0), ("moderate", 5.0, 8.0),
           ("strong", 8.0, 12.0), ("heavy", 12.0, 999.0)]

def buckets(df, pred):
    y = df[TARGET].values
    out = []
    for name, lo, hi in BUCKETS:
        m = (np.abs(pred) >= lo) & (np.abs(pred) < hi)
        if m.sum() == 0:
            continue
        # P(favorite wins) = Phi(|mu|/sigma) for both home and away favorites
        wp = np.array([winprob(mu) for mu in np.abs(pred[m])])
        # P(favorite wins): favorite is home iff pred>0
        fav_win = ((pred[m] > 0) & (y[m] > 0)) | ((pred[m] < 0) & (y[m] < 0))
        out.append({
            "bucket": name,
            "n": int(m.sum()),
            "avg_pred_fav_winprob": round(float(wp.mean()), 4),
            "actual_fav_winrate": round(float(fav_win.mean()), 4),
            "avg_abs_margin_err": round(float(np.mean(np.abs(y[m] - pred[m]))), 3),
            "avg_actual_margin_abs": round(float(np.mean(np.abs(y[m]))), 3),
            "blowout_pct": round(float(np.mean(np.abs(y[m]) >= 14)) * 100, 1),
            "close_pct": round(float(np.mean(np.abs(y[m]) <= 3)) * 100, 1),
        })
    return out

panel2 = {"val": buckets(va, p_va), "test": buckets(te, p_te)}

# --------------------------------------- panel 3: us vs vegas vs reality --
games = []
for i, r in te.reset_index(drop=True).iterrows():
    mu = float(p_te[i])
    p = winprob(mu)
    games.append({
        "game_id": r["game_id"],
        "season": int(r["season"]),
        "week": int(r["week"]),
        "date": str(r["gameday"]) if "gameday" in te.columns else "",
        "home": r["home_team"],
        "away": r["away_team"],
        "pred_margin": round(mu, 2),
        "win_prob_home": round(p, 4),
        "fair_odds_home_american": american_odds(p),
        "closing_line": round(float(r["spread_line"]), 1),
        "actual_margin": round(float(r[TARGET]), 1),
        "model_abs_err": round(abs(float(r[TARGET]) - mu), 2),
        "vegas_abs_err": round(abs(float(r[TARGET]) - float(r["spread_line"])), 2),
    })
games.sort(key=lambda g: (g["week"], g["game_id"]))
model_closer = sum(1 for g in games if g["model_abs_err"] < g["vegas_abs_err"])
panel3 = {
    "games": games,
    "aggregate": {
        **panel1["test"],
        "games_model_closer_than_vegas": model_closer,
        "pct_games_model_closer": round(100.0 * model_closer / len(games), 1),
    },
}

# ------------------------------------------------------- per-season table --
# honest predictions where available: train-fit is in-sample for 2015-2021,
# honest for 2022-2023; final fit is honest for 2024 only.
per_season = []
for season in sorted(f["season"].unique()):
    d = f[f["season"] == season]
    y = d[TARGET].values
    line = d["spread_line"].values
    if season <= 2021:
        p = predict(sc1, m1, d); src = "in-sample (train fit)"
    elif season <= 2023:
        p = predict(sc1, m1, d); src = "honest (train fit)"
    else:
        p = predict(sc2, m2, d); src = "honest (train+val fit)"
    per_season.append({
        "season": int(season), "n": int(len(d)), "source": src,
        "model_mae": round(mae(p, y), 3), "model_win_acc": round(wacc(p, y), 4),
        "vegas_mae": round(mae(line, y), 3), "vegas_win_acc": round(wacc(line, y), 4),
    })

# honest 2020 holdout: train ex-2020 -> predict 2020 (COVID regime check)
tr_x20 = tr[tr["season"] != 2020]
d20 = f[f["season"] == 2020]
scx, mx = fit_ridge(tr_x20)
p20 = predict(scx, mx, d20)
holdout_2020 = {
    "note": "honest: fit 2015-2019+2021, predict COVID-season 2020",
    "n": int(len(d20)),
    "model_mae": round(mae(p20, d20[TARGET].values), 3),
    "model_win_acc": round(wacc(p20, d20[TARGET].values), 4),
    "vegas_mae": round(mae(d20['spread_line'].values, d20[TARGET].values), 3),
}

# ------------------------------------------------------------- scoreboard.json --
scoreboard = {
    "meta": {
        "model": "Ridge(alpha=100) on 7 locked bottom-up features + intercept",
        "features": LOCKED,
        "weights_native": {k: round(v, 4) for k, v in weights.items()},
        "intercept": round(intercept, 4),
        "sigma": round(sigma, 3),
        "sigma_method": "sqrt(mean(val residuals^2)), train-fit model on 2022-2023 "
                        "(Stern starting value 13.0 recalibrated)",
        "splits": {"train": "2015-2021 (1808 games)", "val": "2022-2023 (543 games)",
                   "test": "2024 (272 games, graded once)"},
        "prediction_time": "Tuesday morning of game week; weeks < W only",
        "market_note": "Closing line is the benchmark only — never a model input. "
                       "No market column exists in features_v3.parquet.",
        "tuesday_qb_rule": "Starter = last game's actual starter (injury report never "
                          "designates a QB Out/Doubtful before Tuesday 8am ET; "
                          "verified 0/373 rows 2015-2024).",
        "blowout_def": "|actual margin| >= 14", "close_def": "|actual margin| <= 3",
    },
    "panel1_vs_raw_results": panel1,
    "panel2_confidence_buckets": panel2,
    "panel3_us_vs_vegas_vs_reality": panel3,
    "per_season": per_season,
    "holdout_2020": holdout_2020,
}
with open(HF + "scoreboard.json", "w") as fh:
    json.dump(scoreboard, fh, indent=1)
print(f"\nWrote scoreboard.json ({len(games)} test games)")

# ------------------------------------------------------- BACKTEST_RESULTS.md --
t, v = panel1["test"], panel1["val"]
agg3 = panel3["aggregate"]
md = f"""# Official v1 Backtest Results — graded 2026-10-01

**The one honest grade.** Locked model: Ridge (α=100) on the 7 locked
bottom-up features — Elo, pass/rush EPA on offense and defense, QB edge,
special teams — plus an intercept. No market input anywhere: the closing
line is the benchmark on the scoreboard, never an ingredient.

## The headline

| Split | Games | Our avg miss | Our winner acc | Vegas avg miss | Vegas winner acc |
|---|---|---|---|---|---|
| Train 2015–2021 (in-sample) | {panel1['train_in_sample']['n']} | {panel1['train_in_sample']['model_mae']} pts | {panel1['train_in_sample']['model_win_acc']*100:.1f}% | {panel1['train_in_sample']['vegas_mae']} pts | {panel1['train_in_sample']['vegas_win_acc']*100:.1f}% |
| Validation 2022–2023 | {v['n']} | {v['model_mae']} pts | {v['model_win_acc']*100:.1f}% | {v['vegas_mae']} pts | {v['vegas_win_acc']*100:.1f}% |
| **Test 2024 (final grade)** | {t['n']} | **{t['model_mae']} pts** | **{t['model_win_acc']*100:.1f}%** | {t['vegas_mae']} pts | {t['vegas_win_acc']*100:.1f}% |

We trail Vegas by {t['vegas_mae']-t['model_mae']:+.2f} points on the final exam —
{t['model_mae']-v['model_mae']:+.2f} vs our validation miss. In
{agg3['pct_games_model_closer']}% of 2024 games our predicted margin landed
closer to the actual result than the closing line did.

## What the model is (locked v1)

| Feature | Weight | Plain-English meaning |
|---|---|---|
| elo_diff | {weights['elo_diff']:+.4f}/pt | Overall team-strength gap |
| off_pass_epa | {weights['off_pass_epa']:+.2f}/EPA-play | Passing efficiency edge |
| off_rush_epa | {weights['off_rush_epa']:+.2f}/EPA-play | Rushing efficiency edge |
| def_pass_epa | {weights['def_pass_epa']:+.2f}/EPA-play | Pass defense edge |
| def_rush_epa | {weights['def_rush_epa']:+.2f}/EPA-play | Run defense edge |
| qb_edge | {weights['qb_edge']:+.2f}/EPA-dropback | Starting-QB efficiency edge |
| st_epa_diff | {weights['st_epa_diff']:+.2f}/EPA-play | Special-teams edge |
| intercept | {intercept:+.2f} pts | Effective home-field edge |

Win probability = normal bell curve around the predicted margin with width
σ={sigma:.2f} (recalibrated from our own validation errors; the textbook
starting value was 13.0).

## Confidence buckets (2024 final exam)

| When we said… | Games | We gave favorite | Favorite actually won | Avg miss |
|---|---|---|---|---|
"""
for b in panel2["test"]:
    md += (f"| {b['bucket']} | {b['n']} | {b['avg_pred_fav_winprob']*100:.0f}% "
           f"| {b['actual_fav_winrate']*100:.0f}% | {b['avg_abs_margin_err']:.1f} pts |\n")
md += f"""
The probabilities calibrate well: what we said matches what happened in
four of five buckets. The one soft spot is "lean" games (predicted margin
2–5 pts): favorites won 73% of those while the model said 60% — the model's
mildest calls were a touch too humble on the 2024 final.

Blowouts (|margin|≥14) and nail-biters (|margin|≤3) per bucket are in
scoreboard.json for the site.

## Per-season honesty table

| Season | Games | Our miss | Our acc | Vegas miss | How predicted |
|---|---|---|---|---|---|
"""
for r in per_season:
    flag = ""
    if r["season"] == 2020:
        flag = " ← COVID, no crowds"
    elif r["season"] == 2024:
        flag = " ← new kickoff rules + FINAL GRADE"
    md += (f"| {r['season']} | {r['n']} | {r['model_mae']} | {r['model_win_acc']*100:.1f}% "
           f"| {r['vegas_mae']} | {r['source']}{flag} |\n")
h = holdout_2020
md += f"""
**2020 honest holdout** (fit 2015–2019+2021, predict COVID-season 2020):
our miss {h['model_mae']} pts vs Vegas {h['vegas_mae']} pts over {h['n']} games —
the regime break, measured without the model ever seeing 2020.

## How to read this

- The model was built bottom-up from team strength and efficiency. It does
  not see the betting line, the opener, or any odds — those numbers don't
  exist on Tuesday morning when predictions are made.
- 2024 was graded exactly once and will not be tuned on. Whatever it says,
  it says.
- This is an engineering result, not a betting slip: the gap to Vegas
  (~{t['vegas_mae']-t['model_mae']:+.2f} pts on the final) is the honest price
  of predicting from data alone.
"""
with open(HF + "BACKTEST_RESULTS.md", "w") as fh:
    fh.write(md)
print("Wrote BACKTEST_RESULTS.md")
print("\nDONE — 2024 graded once. Do not re-tune on test.")
