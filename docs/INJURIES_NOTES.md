# Injury report data notes — nflverse, 2015–2024

Pulled 2026-09-30 via `nflreadpy.load_injuries` (v0.1.5) into the goal venv.
File: `injuries_2015_2024.parquet` — **54,720 rows × 16 columns**.

## Per-season report counts
| Season | Reports |
|---|---|
| 2015 | 5,232 |
| 2016 | 5,115 |
| 2017 | 5,104 |
| 2018 | 5,133 |
| 2019 | 5,392 |
| 2020 | 5,661 |
| 2021 | 5,587 |
| 2022 | 5,682 |
| 2023 | 5,599 |
| 2024 | 6,215 |

No season is sparse in raw volume.

## Columns (16)
`season`, `game_type`, `team`, `week`, `gsis_id`, `position`, `full_name`, `first_name`,
`last_name`, `report_primary_injury`, `report_secondary_injury`, `report_status`,
`practice_primary_injury`, `practice_secondary_injury`, `practice_status`, `date_modified`.

## Practice participation & game status — confirmed present
- `practice_status`: values like "Did Not Participate In Practice", "Limited Participation in
  Practice", "Full Participation in Practice" (0.4% null on the paired injury field).
- `report_status`: final game status (Out / Doubtful / Questionable). **46.8% null — expected
  structure, not a defect:** each player has one row per practice day plus a final report row;
  only the final-report rows carry `report_status`.
- `date_modified` timestamps each row, so the latest row per player/week is the final word.

## Data quality flags
1. **2023 shows only 19 distinct weeks** vs 22 in 2021/2022/2024 (18 REG + 4 playoff = 22).
   Postseason injury weeks appear to be missing for 2023. Investigate before using 2023
   playoff injury data; regular-season weeks look complete.
2. **`season` and `week` are Float64** (e.g. `2015.0`) — a concat artifact. Cast to int before
   joining to schedules/pbp.
3. 2024 has the highest report volume (6,215) — consistent with larger rosters/practice-squad
   reporting, not an error.
4. `report_secondary_injury` 96.5% null / `practice_secondary_injury` 93.5% null — secondary
   injuries are rarely recorded; treat as optional, not core.

## Intended use
Raw material for the QB-availability / injury feature in the build-features stage
(e.g. starting QB out/doubtful flags). Timing rule to enforce later: only injury information
available *before* kickoff may feed a game's prediction — never the post-game report.
