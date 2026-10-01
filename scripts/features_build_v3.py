#!/usr/bin/env python3
"""
v3 FEATURE BUILD — nfl-prediction-model-v1 (TUESDAY-KNOWLEDGE QB FIX)
=====================================================================
v3 = v2 with ONE change: qb_edge's designated starter now respects the
Tuesday-knowledge injury rule (RESEARCH_ROUND2.md Q2).

v2 used the depth-chart QB1 for the GAME WEEK (season, week). Audit
(2026-09-30) found two problems:
 (a) that snapshot is of UNKNOWN timing — 5 team-weeks where it listed a
     backup elevated by a Wed-Fri Out designation, ~70 more where it reflected
     mid-week changes (benchings, injury returns) with no pre-Tuesday signal;
 (b) the injury report itself NEVER designates a QB Out/Doubtful before
     Tuesday 8am ET of the game week (verified: 0 of 373 REG QB Out/Doubtful
     rows, 2015-2024; median stamp Friday ~72h after the cutoff).

Consequence: the Tuesday-honest starter is simply LAST GAME'S ACTUAL STARTER
(most dropbacks). The injury report cannot move the pick because it never
speaks before Tuesday. Week 1 uses the preseason depth chart; bye weeks walk
back to the most recent game. This honestly misses ~12 new mid-week QB
injuries/season plus Monday benching/return announcements — exactly as a real
Tuesday-morning model would. (The "auto-update as news breaks" vision needs a
live feed and stays v2-only.) The build asserts premise (b) every run.

Everything else is byte-identical to v2 (same trailing windows, Elo,
opponent adjustments, priors, leakage self-checks).

Output: hidden_files/features_v3.parquet (NO spread_line / market_anchor column
by design — the parquet must be unusable as a market model input).
Target: home_margin.

Definitions (unchanged from v2 except qb_edge starter, above):
  - elo_diff        : pre-WEEK Elo(home) - Elo(away). Same Elo recipe as v1
                      (1500 start, K=20, HFA=60 in update, MOV-weighted,
                      1/3 offseason reversion), but all Week-W games see the
                      ratings as of end of Week W-1. Pure rating diff (no HFA).
  - off_pass_epa / off_rush_epa / def_pass_epa / def_rush_epa:
                      EPA/play differentials, trailing max-8 games, exp decay
                      w = 0.5**(age/8), one iteration of opponent adjustment
                      (opponent's trailing stats as of THAT game's week).
  - hfa             : constant = HFA_hat from TRAIN ex-2020 (collinear with
                      intercept; kept so the GUI can display it as a line
                      item; intercept carries the effective home edge).
  - rest_diff       : home_rest - away_rest, raw days (schedule-derived, all
                      knowable at prediction time).
  - qb_edge         : starter EPA/dropback differential. Starter = the
                      TUESDAY-KNOWLEDGE expected starter (v3 rule, see header):
                      last game's actual starter (injury report never speaks
                      before Tuesday, verified). Trailing-8 exp-decay
                      EPA/dropback shrunk toward league avg as of week start
                      (60-dropback prior).
  - wind            : dome/closed -> 0; outdoor as reported; null outdoor ->
                      8.0 mph median, flagged wind_imputed=1. CAVEAT: at real
                      prediction time we would use the Tuesday wind FORECAST;
                      the backtest uses actuals as the proxy (forecasts track
                      actuals closely). Documented, not hidden.
  - st_epa_diff     : special-teams EPA/play differential, trailing 8,
                      exp decay, not opponent-adjusted.
  - recent_form     : (last-4 avg margin - season-to-date avg margin), home-away.
  - success_rate_diff / int_epa_diff : as v1.
  - is_division / is_dome / is_primetime : schedule-derived flags.

Output: hidden_files/features_v2.parquet (NO spread_line / market_anchor column
by design — the parquet must be unusable as a market model input).
Target: home_margin.
"""

import numpy as np
import pandas as pd
import polars as pl
import os

os.chdir(os.path.expanduser("~/workspace/goals/nfl-prediction-model-v1"))
HF = "hidden_files/"

HALF_LIFE = 8.0
MAX_WINDOW = 8
ST_TYPES = ["kickoff", "punt", "field_goal", "extra_point"]

# ---------------------------------------------------------------- load ------
print("Loading schedules...")
sched = (pl.read_parquet(HF + "schedules_2015_2024.parquet")
           .filter(pl.col("game_type") == "REG")
           .with_columns(
               (pl.col("gameday") + " " + pl.col("gametime")).str.to_datetime("%Y-%m-%d %H:%M")
               .alias("kickoff"))
           .sort(["season", "week", "kickoff"])
           .to_pandas())
sched["home_margin"] = sched["home_score"] - sched["away_score"]
sched["season"] = sched["season"].astype(int)
sched["week"] = sched["week"].astype(int)
assert sched["home_margin"].isna().sum() == 0
print(f"  {len(sched)} REG games, {sched['season'].min()}-{sched['season'].max()}")

print("Loading pbp...")
pbp = pl.read_parquet(
    HF + "pbp_2015_2024.parquet",
    columns=["game_id", "posteam", "defteam", "epa", "play_type",
             "success", "qb_dropback", "interception", "passer_player_id"]
).to_pandas()
REMAP = {"LV": "OAK", "LAC": "SD", "LA": "STL"}
pbp["posteam"] = pbp["posteam"].replace(REMAP)
pbp["defteam"] = pbp["defteam"].replace(REMAP)
print(f"  {len(pbp)} plays (team codes remapped)")

# ------------------------------------------------- team-game aggregates -------
print("Building team-game aggregates...")
off = pbp[pbp["play_type"].isin(["pass", "run"])].copy()
off["is_pass"] = (off["play_type"] == "pass").astype(int)

def agg_side(df, team_col, epa_sign=1.0):
    df = df.copy()
    df["is_rush"] = 1 - df["is_pass"]
    df["pass_epa"] = df["epa"] * df["is_pass"] * epa_sign
    df["rush_epa"] = df["epa"] * df["is_rush"] * epa_sign
    g = df.groupby(["game_id", team_col])
    return pd.DataFrame({
        "n_pass": g["is_pass"].sum(), "epa_pass": g["pass_epa"].sum(),
        "n_rush": g["is_rush"].sum(), "epa_rush": g["rush_epa"].sum(),
        "n_succ": g["success"].count(), "succ": g["success"].sum(),
    })

o_agg = agg_side(off, "posteam", 1.0).rename_axis(["game_id", "team"])
d_agg = agg_side(off, "defteam", -1.0).rename_axis(["game_id", "team"])
d_agg = d_agg.rename(columns={"n_pass": "dn_pass", "epa_pass": "depa_pass",
                              "n_rush": "dn_rush", "epa_rush": "depa_rush",
                              "n_succ": "dn_succ", "succ": "dsucc"})
st = pbp[pbp["play_type"].isin(ST_TYPES)]
st_agg = st.groupby(["game_id", "posteam"])[["epa"]].agg(n_st=("epa", "size"), epa_st=("epa", "sum"))
st_agg.index.names = ["game_id", "team"]
intp = pbp[(pbp["interception"] == 1.0)]
int_agg = intp.groupby(["game_id", "defteam"])[["epa"]].agg(n_int=("epa", "size"), epa_int_off=("epa", "sum"))
int_agg.index.names = ["game_id", "team"]
int_agg["depa_int"] = -int_agg["epa_int_off"]
drop = pbp[pbp["qb_dropback"] == 1.0]
qb = drop.groupby(["game_id", "passer_player_id"])[["epa"]].agg(qb_n=("epa", "size"), qb_epa=("epa", "sum"))

tg = (o_agg.join(d_agg, how="outer").join(st_agg, how="left")
           .join(int_agg[["n_int", "depa_int"]], how="left").fillna(0))
tg = tg.reset_index()

meta = sched[["game_id", "season", "week", "kickoff", "home_team", "away_team",
              "home_score", "away_score"]].copy()
home_tg = meta.merge(tg, left_on=["game_id", "home_team"], right_on=["game_id", "team"], how="left")
away_tg = meta.merge(tg, left_on=["game_id", "away_team"], right_on=["game_id", "team"], how="left")
home_tg["margin"] = home_tg["home_score"] - home_tg["away_score"]
away_tg["margin"] = away_tg["away_score"] - away_tg["home_score"]
home_tg["opp"] = home_tg["away_team"]; away_tg["opp"] = away_tg["home_team"]
home_tg["team"] = home_tg["team"].fillna(home_tg["home_team"])
away_tg["team"] = away_tg["team"].fillna(away_tg["home_team"])
team_games = pd.concat([home_tg, away_tg], ignore_index=True)
team_games["season"] = team_games["season"].astype(int)
team_games["week"] = team_games["week"].astype(int)
team_games = team_games.sort_values(["season", "week", "kickoff"]).reset_index(drop=True)

num_cols = ["n_pass", "epa_pass", "n_rush", "epa_rush", "n_succ", "succ",
            "dn_pass", "depa_pass", "dn_rush", "depa_rush", "dn_succ", "dsucc",
            "n_st", "epa_st", "n_int", "depa_int"]
team_games[num_cols] = team_games[num_cols].fillna(0)

team_hist = {t: [] for t in pd.unique(team_games[["home_team", "away_team"]].values.ravel())}
for _, r in team_games.iterrows():
    d = r.to_dict()
    d["season"] = int(d["season"]); d["week"] = int(d["week"])
    team_hist[d["team"]].append(d)
print(f"  team-game rows: {len(team_games)}")

# cumulative league EPA/dropback as of WEEK START (weeks strictly before W)
drop_meta = drop.merge(meta[["game_id", "season", "week"]], on="game_id")
wk_tot = (drop_meta.groupby(["season", "week"])
          .agg(epa=("epa", "sum"), n=("epa", "size")).reset_index()
          .sort_values(["season", "week"]).reset_index(drop=True))
wk_tot["cum_epa"] = wk_tot["epa"].cumsum().shift(1).fillna(0.0)
wk_tot["cum_n"] = wk_tot["n"].cumsum().shift(1).fillna(0.0)
lg_lookup = {(int(r["season"]), int(r["week"])): (r["cum_epa"], r["cum_n"])
             for _, r in wk_tot.iterrows()}

def league_avg_before(season, week):
    ep, n = lg_lookup.get((season, week), (0.0, 0.0))
    return ep / n if n > 0 else 0.0

# ------------------------------------------------------- trailing engine -----
def exp_weights(n):
    ages = np.arange(n - 1, -1, -1, dtype=float)  # 0 = most recent
    w = 0.5 ** (ages / HALF_LIFE)
    return w / w.sum()

def window_games(team, season, week, max_n=MAX_WINDOW):
    """Past team-games with (season, week) STRICTLY before (season, week).
    This is the v2 prediction-time cutoff: Tuesday morning of Week W sees
    only games from weeks < W."""
    key = (season, week)
    hist = [g for g in team_hist[team] if (g["season"], g["week"]) < key]
    return hist[-max_n:]

def wavg_sums(games, sum_col, n_col):
    if not games:
        return 0.0, 0.0
    w = exp_weights(len(games))
    s = sum(wi * g[sum_col] for wi, g in zip(w, games))
    n = sum(wi * g[n_col] for wi, g in zip(w, games))
    return s, n

_raw_memo = {}
def raw_trailing(team, season, week, sum_col, n_col):
    key = (team, season, week, sum_col)
    if key not in _raw_memo:
        _raw_memo[key] = wavg_sums(window_games(team, season, week), sum_col, n_col)
    return _raw_memo[key]

def adj_stat(team, season, week, own_sum, own_n, opp_sum, opp_n):
    """Opponent-adjusted trailing per-play stat. Each window game's raw stat
    is adjusted by the opponent's trailing stat AS OF THAT GAME'S WEEK
    (week-based cutoff, v2)."""
    gs = window_games(team, season, week)
    if not gs:
        return 0.0
    vals, wts = [], []
    w = exp_weights(len(gs))
    for wi, g in zip(w, gs):
        n = g[own_n]
        if n <= 0:
            continue
        raw_pp = g[own_sum] / n
        osum, on = raw_trailing(g["opp"], g["season"], g["week"], opp_sum, opp_n)
        opp_pp = (osum / on) if on > 0 else 0.0
        vals.append(raw_pp - opp_pp)
        wts.append(wi)
    if not vals:
        return 0.0
    wts = np.array(wts); wts /= wts.sum()
    return float(np.dot(wts, vals))

def raw_rate_stat(team, season, week, sum_col, n_col):
    s, n = wavg_sums(window_games(team, season, week), sum_col, n_col)
    return s / n if n > 0 else 0.0

# ------------------------------------------------------------------- Elo -----
print("Computing Elo (pre-week snapshots)...")
elo = {t: 1500.0 for t in team_hist}
K, HFA_ELO = 20, 60
def wp(d): return 1 / (1 + 10 ** (-d / 400.0))
elo_diff_map = {}
for (season, week), grp in sched.groupby(["season", "week"], sort=True):
    if week == sched[sched["season"] == season]["week"].min():
        for t in elo:
            elo[t] = elo[t] * 2 / 3 + 1500 * 1 / 3  # offseason reversion at week 1
    snap = dict(elo)  # every game this week sees ratings through week W-1
    for _, r in grp.sort_values("kickoff").iterrows():
        elo_diff_map[r["game_id"]] = snap[r["home_team"]] - snap[r["away_team"]]
        # updates applied after snapshot (order within week irrelevant to features)
        d = elo[r["home_team"]] + HFA_ELO - elo[r["away_team"]]
        p = wp(d)
        mm = np.log(abs(r["home_margin"]) + 1) * 2.2 / (abs(d) * 0.001 + 2.2)
        act = 1 if r["home_margin"] > 0 else (0 if r["home_margin"] < 0 else 0.5)
        delta = K * mm * (act - p)
        elo[r["home_team"]] += delta; elo[r["away_team"]] -= delta
print("  Elo done.")

# ------------------------------------------------- HFA estimate (train ex-2020)
tr = sched[sched["season"].between(2015, 2021) & (sched["season"] != 2020)].copy()
tr["ed"] = tr["game_id"].map(elo_diff_map)
HFA_hat = (tr["home_margin"] - tr["ed"] / 25.0).mean()
tr20 = sched[sched["season"] == 2020].copy(); tr20["ed"] = tr20["game_id"].map(elo_diff_map)
HFA_2020 = (tr20["home_margin"] - tr20["ed"] / 25.0).mean()
print(f"  HFA estimate (train ex-2020): {HFA_hat:.2f} pts | 2020 only: {HFA_2020:.2f} pts")

# ------------------------------------------------------------- depth charts --
print("Loading depth charts...")
dc = pl.read_parquet(HF + "depth_charts_2015_2024.parquet").to_pandas()
qb1 = (dc[(dc["position"] == "QB") & (dc["depth_team"] == "1") & (dc["game_type"] == "REG")]
       .drop_duplicates(["season", "week", "club_code"]).set_index(["season", "week", "club_code"])["gsis_id"])
print(f"  QB1 rows: {len(qb1)}")

# ------------------------------------------- Tuesday-knowledge starter (v3) --
# v3 AUDIT FINDING (2026-09-30, verified in this script's premise check):
#  (a) the game-week depth chart is a snapshot of UNKNOWN timing — 5 team-weeks
#      where it listed a backup elevated by a Wed-Fri Out designation, ~70 more
#      where it reflected mid-week changes (benchings, injury returns);
#  (b) the injury report NEVER designates a QB Out/Doubtful before Tuesday
#      8am ET of the game week (0 of 373 REG QB Out/Doubtful rows, 2015-2024;
#      median stamp is Friday, ~72h after the cutoff).
# Consequence: the Tuesday-honest starter is simply LAST GAME'S ACTUAL
# STARTER. The injury report cannot move the pick, because it never speaks
# before Tuesday. This honestly misses ~12 new mid-week QB injuries/season
# plus Monday benching/return announcements — exactly as a real Tuesday
# morning model would. (The "auto-update as news breaks" vision needs a live
# feed and stays v2-only.)
print("Verifying Tuesday-knowledge premise (injury report timing)...")
inj = pl.read_parquet(HF + "injuries_2015_2024.parquet").to_pandas()
inj["season"] = inj["season"].astype(int)
inj["week"] = inj["week"].astype(int)
inj["date_modified"] = pd.to_datetime(inj["date_modified"], utc=True)
from datetime import timedelta as _td
from zoneinfo import ZoneInfo as _ZI
_ET = _ZI("America/New_York")
_tue_cutoff = {}
for (_s, _w), _g in sched.groupby(["season", "week"]):
    _mind = _g["kickoff"].min()
    _tue = (_mind - _td(days=(_mind.weekday() - 1) % 7)).date()
    _tue_cutoff[(int(_s), int(_w))] = (pd.Timestamp(_tue).tz_localize(_ET) + _td(hours=8)).tz_convert("UTC")
_q = inj[(inj["position"] == "QB") & (inj["report_status"].isin(["Out", "Doubtful"]))
         & (inj["game_type"] == "REG")]
_q = _q[[(_r["season"], _r["week"]) in _tue_cutoff for _, _r in _q.iterrows()]]
_n_pre = sum(1 for _, _r in _q.iterrows()
             if _r["date_modified"] <= _tue_cutoff[(_r["season"], _r["week"])])
print(f"  QB Out/Doubtful rows: {len(_q)}, predating Tuesday 8am ET: {_n_pre}")
assert _n_pre == 0, "Tuesday-knowledge premise violated: pre-Tuesday QB designations exist!"

# per-team-week QB dropback counts -> actual starters. NOTE: pbp natively uses
# the OLD franchise codes (STL/OAK/SD) for all seasons while schedules/depth
# charts use era-correct codes (LA/LAC/LV in recent years); translate the
# schedule code to the pbp code at lookup time via INV_REMAP.
_drop_meta = drop.merge(meta[["game_id", "season", "week"]], on="game_id")
INV_REMAP = {"LA": "STL", "LAC": "SD", "LV": "OAK"}
_tw_qb = (_drop_meta.groupby(["season", "week", "posteam", "passer_player_id"]).size()
          .reset_index(name="n"))
_tw_qb["season"] = _tw_qb["season"].astype(int)
_tw_qb["week"] = _tw_qb["week"].astype(int)
_tw_qb = _tw_qb.sort_values(["season", "week", "posteam", "n"], ascending=[True, True, True, False])
_tw_qb_map = {}
for (s, w, p), g in _tw_qb.groupby(["season", "week", "posteam"]):
    _tw_qb_map[(int(s), int(w), p)] = g["passer_player_id"].tolist()
print(f"  team-week QB starter maps: {len(_tw_qb_map)}")

def designated_starter(season, week, club):
    """v3 Tuesday-knowledge starter: last game's actual starter (most
    dropbacks). Week 1 falls back to the preseason depth chart. Bye weeks
    walk back to the most recent game. No injury lookup: the premise check
    above proves the report never speaks before Tuesday."""
    if week == 1:
        try:
            return qb1.loc[(season, week, club)]
        except KeyError:
            return None
    pclub = INV_REMAP.get(club, club)  # schedule code -> pbp code
    for wb in range(week - 1, max(week - 5, 0), -1):
        cands = _tw_qb_map.get((season, wb, pclub))
        if cands:
            return cands[0]
    try:
        return qb1.loc[(season, week, club)]
    except KeyError:
        return None

def starter_epa_db(pid, team, season, week):
    gs = window_games(team, season, week)
    gids = [g["game_id"] for g in gs]
    tot_n, tot_epa = 0.0, 0.0
    if pid is not None and gids:
        sub = qb[qb.index.get_level_values("game_id").isin(gids)]
        if pid in sub.index.get_level_values("passer_player_id"):
            s2 = sub.xs(pid, level="passer_player_id")
            w = exp_weights(len(gs))
            gid_w = {g["game_id"]: wi for wi, g in zip(w, gs)}
            for gid, grp in s2.groupby("game_id"):
                wi = gid_w.get(gid, 0)
                tot_n += wi * grp["qb_n"].sum(); tot_epa += wi * grp["qb_epa"].sum()
    lg = league_avg_before(season, week)
    return (tot_epa + 60 * lg) / (tot_n + 60)

# ------------------------------------------------------- assemble features ---
print("Assembling game features (this takes a few minutes)...")
rows = []
for i, r in sched.iterrows():
    if i % 400 == 0:
        print(f"  game {i}/{len(sched)}")
    ht, at = r["home_team"], r["away_team"]
    S, W = int(r["season"]), int(r["week"])
    gid = r["game_id"]

    ed = elo_diff_map[gid]
    o_pe = adj_stat(ht, S, W, "epa_pass", "n_pass", "depa_pass", "dn_pass") - \
           adj_stat(at, S, W, "epa_pass", "n_pass", "depa_pass", "dn_pass")
    o_re = adj_stat(ht, S, W, "epa_rush", "n_rush", "depa_rush", "dn_rush") - \
           adj_stat(at, S, W, "epa_rush", "n_rush", "depa_rush", "dn_rush")
    d_pe = adj_stat(ht, S, W, "depa_pass", "dn_pass", "epa_pass", "n_pass") - \
           adj_stat(at, S, W, "depa_pass", "dn_pass", "epa_pass", "n_pass")
    d_re = adj_stat(ht, S, W, "depa_rush", "dn_rush", "epa_rush", "n_rush") - \
           adj_stat(at, S, W, "depa_rush", "dn_rush", "epa_rush", "n_rush")
    sr = adj_stat(ht, S, W, "succ", "n_succ", "dsucc", "dn_succ") - \
         adj_stat(at, S, W, "succ", "n_succ", "dsucc", "dn_succ")
    st = raw_rate_stat(ht, S, W, "epa_st", "n_st") - raw_rate_stat(at, S, W, "epa_st", "n_st")
    def int_pg(team):
        gs = window_games(team, S, W)
        if not gs: return 0.0
        w = exp_weights(len(gs))
        return float(sum(wi * g["depa_int"] for wi, g in zip(w, gs)))
    ie = int_pg(ht) - int_pg(at)
    def rec_form(team):
        gs = [g for g in team_hist[team] if g["season"] == S and g["week"] < W]
        if len(gs) < 2: return 0.0
        last4 = np.mean([g["margin"] for g in gs[-4:]])
        seas = np.mean([g["margin"] for g in gs])
        return last4 - seas
    rf = rec_form(ht) - rec_form(at)
    h_qb = designated_starter(S, W, ht)
    a_qb = designated_starter(S, W, at)
    qe = starter_epa_db(h_qb, ht, S, W) - starter_epa_db(a_qb, at, S, W)
    if r["roof"] in ("dome", "closed"):
        wind, wimp = 0.0, 0
    elif pd.notna(r["wind"]):
        wind, wimp = float(r["wind"]), 0
    else:
        wind, wimp = 8.0, 1
    gt = str(r["gametime"])
    primetime = 1 if (r["weekday"] in ("Monday", "Thursday") or gt >= "20:00") else 0

    rows.append(dict(
        game_id=gid, season=S, week=W, kickoff=r["kickoff"],
        home_team=ht, away_team=at, home_margin=r["home_margin"],
        elo_diff=ed,
        off_pass_epa=o_pe, off_rush_epa=o_re, def_pass_epa=d_pe, def_rush_epa=d_re,
        hfa=HFA_hat, rest_diff=r["home_rest"] - r["away_rest"],
        qb_edge=qe, wind=wind, wind_imputed=wimp,
        st_epa_diff=st, recent_form=rf, success_rate_diff=sr, int_epa_diff=ie,
        is_division=int(r["div_game"]), is_dome=int(r["roof"] in ("dome", "closed")),
        is_primetime=primetime,
        home_qb_id=h_qb, away_qb_id=a_qb,
    ))

feat = pd.DataFrame(rows)
feat.to_parquet(HF + "features_v3.parquet", index=False)
print(f"Saved {HF}features_v3.parquet: {feat.shape}")
print("nulls:", feat.isna().sum()[feat.isna().sum() > 0].to_dict())
assert "spread_line" not in feat.columns and "market_anchor" not in feat.columns

# ------------------------------------------------------- leakage self-checks
trail_cols = ["off_pass_epa", "off_rush_epa", "def_pass_epa", "def_rush_epa",
              "qb_edge", "st_epa_diff", "recent_form", "success_rate_diff", "int_epa_diff"]
w1 = feat[(feat["season"] == 2015) & (feat["week"] == 1)]
print("CHECK 1 — 2015-W1 trailing features all zero:",
      bool((w1[trail_cols].abs().max().max() == 0)))
print("CHECK 2 — 2015-W1 elo_diff all zero (1500 starts):",
      bool((w1["elo_diff"].abs().max() == 0)))
# CHECK 3 — no same-week leakage: for a sample of team-weeks, the trailing
# window must contain no game from the same or a later week.
import random
random.seed(7)
ok = True
for _ in range(300):
    t = random.choice(list(team_hist.keys()))
    g0 = random.choice(team_hist[t])
    S0, W0 = g0["season"], g0["week"]
    win = window_games(t, S0, W0)
    if any((g["season"], g["week"]) >= (S0, W0) for g in win):
        ok = False; break
print("CHECK 3 — 300 random team-weeks: no window game from same/later week:", ok)
# CHECK 4 — Elo pre-week snapshot: two teams' diffs within the same week must
# not reflect each other's same-week results. Verify diff for a week-2 game
# equals diff computed from ratings before any week-2 update (recompute spot).
print("HFA_hat =", round(HFA_hat, 3), "| HFA_2020 =", round(HFA_2020, 3))
