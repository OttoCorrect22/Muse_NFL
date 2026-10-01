# data/

Derived datasets for the v1 model. Small files live here; large raw files do
not (GitHub's 100 MB limit) — regenerate them with the scripts.

## In this folder
- `features_v2.parquet` — 2,623 games × 26 columns, the locked bottom-up
  feature set. Zero nulls, no market columns by design.
- `schedules_2015_2024.parquet` — game schedules + closing lines (benchmark
  only, never a feature).
- `injuries_2015_2024.parquet` — weekly injury reports with timestamps.
- `depth_charts_2015_2024.parquet` — weekly depth charts (QB1 coverage).

## Excluded (too large for GitHub)
- `pbp_2015_2024.parquet` (122 MB) — every play, 2015–2024. Regenerate with
  `scripts/features_build_v2.py` (pulls via nflreadpy) or download from the
  local project archive.

All files are reproducible from `scripts/` — the scripts are the source of
truth, the parquets are convenience.
