#!/usr/bin/env python3
"""
v2 FEATURE INCREMENTAL-VALUE TESTS (BOTTOM-UP — NO MARKET FEATURE)
==================================================================
- Train: 2015-2021 REG (1,808 games). Validation: 2022-2023 REG (543 games).
- 2024 is NEVER loaded for metrics (locked test season).
- Base model: elo_diff + intercept (OLS). Each candidate (EPA splits as a
  group AND individually) is added to the base, refit on train, judged by
  validation MAE delta with paired p-values.
- Full model: keepers under Ridge; alpha chosen by TimeSeriesSplit CV *within
  train only*. Standardized coefficients reported.
- The closing line appears ONLY as a benchmark reference number (read from
  schedules) — it is never a feature.
- Sanity anchor: a pure bottom-up model should land ~10.0-10.5 val MAE, near
  the Elo-baseline reference (10.26), ~1 pt worse than the line (~9.3). If the
  joint model beats the line, STOP and check for leakage.
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, RidgeCV
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from scipy import stats as sstats

HF = "hidden_files/"
f = pd.read_parquet(HF + "features_v2.parquet")
assert "spread_line" not in f.columns and "market_anchor" not in f.columns, \
    "market feature leaked into v2 parquet!"
assert f["season"].max() <= 2024
tr = f[f["season"] <= 2021].copy()
va = f[(f["season"] >= 2022) & (f["season"] <= 2023)].copy()
assert len(tr) == 1808 and len(va) == 543, (len(tr), len(va))
print(f"train={len(tr)} val={len(va)} (2024 excluded from all metrics)")
print(f"v2 parquet columns ({len(f.columns)}): {list(f.columns)}")

y_tr, y_va = tr["home_margin"].values, va["home_margin"].values

# benchmark reference only (never a feature)
sched = pd.read_parquet(HF + "schedules_2015_2024.parquet")
sched = sched[sched["game_type"] == "REG"]
line_va = sched[(sched["season"] >= 2022) & (sched["season"] <= 2023)].sort_values(
    ["season", "week"]).reset_index(drop=True)
va_sorted = va.sort_values(["season", "week"]).reset_index(drop=True)
assert (line_va["game_id"].values == va_sorted["game_id"].values).all(), \
    "game ordering mismatch vs schedules"
line_mae = float(np.mean(np.abs(line_va["spread_line"].values - va_sorted["home_margin"].values)))
print(f"\nBENCHMARK (not a feature): closing line val MAE {line_mae:.3f}")

BASE = ["elo_diff"]
EPA4 = ["off_pass_epa", "off_rush_epa", "def_pass_epa", "def_rush_epa"]
CANDIDATES = {
    "epa_group(4)": EPA4,
    "off_pass_epa": ["off_pass_epa"],
    "off_rush_epa": ["off_rush_epa"],
    "def_pass_epa": ["def_pass_epa"],
    "def_rush_epa": ["def_rush_epa"],
    "qb_edge": ["qb_edge"],
    "st_epa_diff": ["st_epa_diff"],
    "success_rate_diff": ["success_rate_diff"],
    "int_epa_diff": ["int_epa_diff"],
    "recent_form": ["recent_form"],
    "wind": ["wind"],
    "rest_diff": ["rest_diff"],
    "situational(3)": ["is_division", "is_dome", "is_primetime"],
}

def mae(a, b): return float(np.mean(np.abs(a - b)))
def wacc(pred, actual):
    m = actual != 0
    return float(np.mean((pred[m] > 0) == (actual[m] > 0)))

def fit_eval(cols):
    Xtr, Xva = tr[cols].values, va[cols].values
    mdl = LinearRegression().fit(Xtr, y_tr)
    p = mdl.predict(Xva)
    ptr = mdl.predict(Xtr)
    return mae(p, y_va), wacc(p, y_va), mdl.coef_, mdl.intercept_, mae(ptr, y_tr), p

def paired_p(p_new, p_base):
    d = np.abs(y_va - p_base) - np.abs(y_va - p_new)  # + means new is better
    _, pv = sstats.ttest_1samp(d, 0.0)
    return float(np.mean(d)), float(pv)

print("\n--- Base: elo_diff + intercept (OLS) ---")
base_mae, base_acc, base_coef, base_int, base_mtr, p_base = fit_eval(BASE)
print(f"val MAE {base_mae:.3f} (train {base_mtr:.3f}) | win acc {base_acc:.3f} | "
      f"coef {base_coef[0]:.4f} | intercept {base_int:.3f}")
# hfa constant must be absorbed by intercept: verify it changes nothing
m_hfa, _, _, _, _, _ = fit_eval(BASE + ["hfa"])
print(f"base+hfa constant -> val MAE {m_hfa:.3f} (delta {m_hfa-base_mae:+.5f}; expect ~0)")

print("\n--- Incremental tests vs ELO base (OLS) ---")
results = {}
for name, cols in CANDIDATES.items():
    m, a, coef, inter, mtr, p = fit_eval(BASE + cols)
    d, pv = paired_p(p, p_base)
    results[name] = dict(mae=m, acc=a, dmae=m - base_mae, p=pv,
                         coef=dict(zip(cols, coef[1:])), inter=inter)
    cstr = ", ".join(f"{c}={v:+.3f}" for c, v in zip(cols, coef[1:]))
    print(f"{name:18s} val MAE {m:.3f} dMAE {m-base_mae:+.3f} paired-p {pv:.3f} "
          f"acc {a:.3f} | new coef: {cstr}")

# ---------------- joint ridge on keepers ----------------
# keeper rule (applied after seeing the table): keep features with dMAE<0, or
# correct sign + research backing + interpretability value. Decided below.
print("\n--- Joint ridge model ---")
KEEP = ["elo_diff"] + EPA4 + ["qb_edge", "st_epa_diff"]  # provisional; revised post-table
print(f"provisional keepers: {KEEP}")
sc = StandardScaler().fit(tr[KEEP].values)
Ztr, Zva = sc.transform(tr[KEEP].values), sc.transform(va[KEEP].values)
tscv = TimeSeriesSplit(n_splits=5)
ridge = RidgeCV(alphas=[0.1, 1.0, 10.0, 100.0, 1000.0], cv=tscv).fit(Ztr, y_tr)
p = ridge.predict(Zva)
vmae, vacc = mae(p, y_va), wacc(p, y_va)
print(f"Ridge alpha*={ridge.alpha_} -> val MAE {vmae:.3f} | win acc {vacc:.3f}")
print(f"  vs line benchmark {line_mae:.3f}: delta {vmae-line_mae:+.3f}")
stdcoef = pd.Series(ridge.coef_, index=KEEP).sort_values(key=np.abs, ascending=False)
print("\nPer-SD coefficients (pts of predicted margin per 1-SD move):")
print(stdcoef.round(3).to_string())
print(f"intercept: {ridge.intercept_:.3f}")
# native-unit coefs for the plain-English table
nat = ridge.coef_ / sc.scale_
print("\nNative-unit coefs:")
for c, v, s in zip(KEEP, nat, sc.scale_):
    print(f"  {c:16s} {v:+.4f} pts per unit  (1 SD = {s:.4f} -> {v*s:+.3f} pts/SD)")

# OLS sign sanity on keepers
ols = LinearRegression().fit(tr[KEEP].values, y_tr)
print("\nOLS keeper coefs (sign sanity):")
print(pd.Series(ols.coef_, index=KEEP).round(4).to_string())

if vmae < line_mae - 0.05:
    print("\n!!! SANITY FLAG: bottom-up model BEATS the closing line. "
          "Stop and check for leakage before believing this.")
else:
    print("\nSanity anchor OK: bottom-up model does not beat the line "
          f"({vmae:.3f} vs {line_mae:.3f}).")
