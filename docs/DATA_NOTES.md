# DATA_NOTES — nflverse schedules pull (Task 1)

Pulled: 2026-09-29. Purpose: verify closing spread/total line coverage for NFL regular-season v1 (spread vs closing line only).

## What was pulled
- File: `schedules_2015_2024.parquet` (polars DataFrame written to parquet; 2,743 rows × 46 columns).
- Source: nflverse games/schedules data — full history back to 1999 was available, but only seasons **2015–2024** were kept per the v1 backtest window.
- Upstream URL: https://github.com/nflverse/nflverse-data/releases/download/schedules/games.parquet
  (nflverse's `games.csv` / schedules release, based on Lee Sharpe's games file).

## Library & reproduction
- Library: **nflreadpy** version **0.1.5** (`pip install nflreadpy`; Python 3.12 venv at `hidden_files/venv/`).
- **Do NOT use nfl_data_py** — it is deprecated/archived; nflreadpy is its successor.
- Commands:
  ```python
  import nflreadpy as nfl
  from nflreadpy.config import update_config
  update_config(timeout=600, cache_mode="file")  # default 30s timeout can time out on first download
  sched = nfl.load_schedules(seasons=list(range(2015, 2025)))  # returns a polars DataFrame
  sched.write_parquet("schedules_2015_2024.parquet")
  ```
- Note: first download hit a transient GitHub read timeout at the default 30s setting; raising `timeout` fixed it. The file is also cached at `~/.cache/nflreadpy`.

## Line columns (the important ones)
- `spread_line` (float) — **closing** spread line. Positive = home team favored (e.g. +3.0 means home −3).
- `total_line` (float) — **closing** total (over/under) line.
- `away_moneyline`, `home_moneyline` (int) — closing moneylines, American odds.
- `away_spread_odds`, `home_spread_odds`, `under_odds`, `over_odds` — vig on the lines.
- Grading math used by the community: `home_margin = home_score - away_score`; `ats_margin = home_margin - spread_line`; `ats_margin > 0` → home covered, `< 0` → away covered, `== 0` → push.
- Caveat: these behave as **closing** lines (community measurement: mean abs gap ~0.2 pts vs captured close, ~1.0 pt vs captured opener). They are NOT timestamped closes from a specific book — treat as near-close consensus. Do not pretend they were knowable days before kickoff (e.g., do not use a closing line as a mid-week feature without a lag).

## Row counts per season (game_type = REG only)
| season | REG games |
|---|---|
| 2015 | 256 |
| 2016 | 256 |
| 2017 | 256 |
| 2018 | 256 |
| 2019 | 256 |
| 2020 | 256 |
| 2021 | 272 |
| 2022 | 271 |
| 2023 | 272 |
| 2024 | 272 |
| **total REG** | **2,623** |

Full file also contains: 40 DIV, 50 WC, 10 SB, 20 CON games (playoffs + Pro Bowl-era games), 2,743 rows total.

## Data-quality issues / missing values (REG games)
- `spread_line`: **0 missing** across all 10 seasons (2,623/2,623 populated).
- `total_line`: **0 missing** across all 10 seasons.
- `away_spread_odds`/`home_spread_odds`/`under_odds`/`over_odds`: **0 missing**.
- Moneylines: 1 missing value in 2017 (`away_moneyline`/`home_moneyline` null for exactly one REG game) — irrelevant for v1 since v1 grades spread only.
- 2022 has 271 REG games, not 272: the cancelled Week 17 Bills @ Bengals game (Damar Hamlin) is simply absent from the data (never played, never graded). No null-score rows exist. This is correct and expected — do not impute.
- `gameday` is a string column (`YYYY-MM-DD`); `gametime` is a string (`HH:MM`). Convert to datetimes if ordering by kickoff.

## Impact on v1 scope
- Everything needed for "spread vs closing line, NFL regular season" is present and fully populated for 2015–2024: 2,623 gradable games.
- `game_type == "REG"` is the clean filter for the v1 dataset. Playoff games (DIV/WC/SB) exist in the file but are out of v1 scope.
- No play-by-play pulled yet — that's Task for later (features). Schedules alone suffice for the baseline (always-follow-the-line) backtest and for grading the model.
