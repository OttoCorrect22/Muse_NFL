# Play-by-play data notes — nflverse, 2015–2024

Pulled 2026-09-30 via `nflreadpy.load_pbp` (v0.1.5) into the goal venv.
File: `pbp_2015_2024.parquet` — **483,605 rows × 372 columns**.

## Per-season play counts
| Season | Plays |
|---|---|
| 2015 | 48,122 |
| 2016 | 47,651 |
| 2017 | 47,245 |
| 2018 | 47,109 |
| 2019 | 47,260 |
| 2020 | 47,705 |
| 2021 | 49,922 |
| 2022 | 49,434 |
| 2023 | 49,665 |
| 2024 | 49,492 |

Counts are stable across seasons; the 2021+ bump reflects the 17-game schedule. No season is sparse.

## Coverage sanity
- 10/10 seasons present (2015–2024).
- 2,743 distinct `game_id` — matches the schedule pull (2,743 games), so no games are missing from the play level.
- 21 distinct weeks/season 2015–2020 (17 REG + 4 playoff), 22 weeks/season 2021–2024 (18 REG + 4 playoff).

## Key columns for feature work — all present
`game_id`, `season`, `week`, `posteam`, `defteam`, `epa`, `wp`, `qtr`, `down`, `ydstogo`,
`play_type`, `passer_player_id`, `rusher_player_id`, `receiver_player_id`
(+ `_player_name` variants), `roof`, `surface`, `temp`, `wind`, `stadium`.

## EPA quality
- Overall EPA null rate: ~1.1% per season (non-scoring plays such as timeouts/kneel-downs — expected).
- On pass/run plays only: **0% null** in every season (1 play in 2019). EPA is complete where it matters.

## Weather columns — expected gaps, not defects
- `temp` and `wind`: 34.2% null — dome/indoor games. `wind` is integer mph when present.
- `roof`, `surface`: 0% null.
- Implication: wind-based features need a "dome = 0 wind" treatment, not a null drop.

## Schema quirk (handled)
- Seasons had a dtype mismatch on `goal_to_go` (Int32 vs Float64), so the concat used
  `diagonal_relaxed`. Downstream code should not assume uniform int dtypes on that column.

## Intended use
Raw material only. Feature building (EPA differentials, success rate, etc.) happens in the
pipeline's build-features stage with strict no-lookahead ordering. No features or models were
built in this pull.
