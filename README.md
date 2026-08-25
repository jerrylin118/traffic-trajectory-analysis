# traffic-trajectory-analysis

Statistical analysis of pedestrian crossing/dwell duration and static
visualization of vehicle + pedestrian trajectories from traffic-intersection
datasets. Built primarily around the [SinD dataset](https://github.com/SOTIF-AVLab/SinD)
(Tianjin intersection, record `8_2_1`), but designed to work with any SinD
record and, via a documented extension point, other trajectory datasets.

## Installation

```bash
python -m venv .venv
.venv/Scripts/activate   # Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
pip install -e .
```

## Quickstart

Download a SinD record's data (fetched directly from the SinD GitHub repo's
Git-LFS-backed CSVs, no `git`/`git-lfs` required):

```bash
trajstats download --record Tianjin/8_2_1
```

Compute pedestrian timelength statistics:

```bash
trajstats stats pedestrian-timelength --record Tianjin/8_2_1
```

Writes `output/Tianjin/8_2_1/pedestrian_timelength/`:
- `pedestrian_track_metrics.csv` — per-track duration, path length, displacement, tortuosity, mean speed
- `pedestrian_duration_histogram.png`
- `pedestrian_timelength_report.md` — summary stats table + embedded histogram

Plot trajectories:

```bash
trajstats plot trajectories --record Tianjin/8_2_1
```

Writes `output/Tianjin/8_2_1/trajectories_overlay.png` (pedestrians vs.
vehicles). Pass `--agent-types pedestrian car` to restrict to specific agent
types instead (written to `trajectories.png`).

## Canonical trajectory schema

All stats and visualization code operates on one schema, produced by a
dataset-specific loader (see `src/trajstats/datasets/base.py`):

| Column | Type | Meaning |
|---|---|---|
| `dataset` | string | Source dataset name, e.g. `"sind"` |
| `record_id` | string | Logical record label, e.g. `"Tianjin/8_2_1"` |
| `track_id` | string | Unique id within a record |
| `agent_type` | string | `"pedestrian"`, `"car"`, `"bus"`, etc. |
| `frame_id` | int | Frame index within the record |
| `timestamp_s` | float | Seconds since record start |
| `x`, `y` | float | Position in meters |
| `vx`, `vy` | float | Velocity in m/s |

Optional columns (present when the source data has them): `ax`, `ay`,
`length`, `width`, `yaw_rad`, `heading_rad`, `cross_type`,
`signal_violation`, `ped_class`.

## Analyzing another SinD record

Point `--record` at any other `City/record_id` path under SinD's `Data/`
folder (e.g. a different Tianjin recording, or another city) — the loader
and downloader are not hardcoded to `8_2_1`:

```bash
trajstats download --record Tianjin/8_2_2
trajstats stats pedestrian-timelength --record Tianjin/8_2_2
```

## The DUT dataset (unsignalized intersection)

Also built in: the [DUT vehicle-crowd-interaction dataset](https://github.com/dongfang-steven-yang/vci-dataset-dut)
(Dalian University of Technology) — pedestrian/vehicle trajectories at
unsignalized campus crosswalks (`intersection_01`..`intersection_17`) and
shared spaces (`roundabout_01`..`roundabout_11`), a useful counterpart to
SinD's signalized Tianjin intersection. Its CSVs are committed directly to
GitHub (no Git LFS), so `--dataset dut` downloads and loads the same way:

```bash
trajstats download --dataset dut --record intersection_01
trajstats stats pedestrian-timelength --dataset dut --record intersection_01
trajstats plot trajectories --dataset dut --record intersection_01
```

DUT ships no timestamp column, only a frame index, so `timestamp_s` is
derived from the dataset's fixed 23.98 fps. Vehicle rows carry a heading
(`heading_rad`) and scalar speed rather than a velocity vector; `vx`/`vy`
are decomposed from those. See `src/trajstats/datasets/dut.py`.

## Adding a new (non-SinD) dataset

Two options, in `src/trajstats/datasets/`:

1. **`generic_csv.GenericCsvLoader`** — for a dataset that's already one CSV
   row per (track, frame): pass a `column_map` from the source's column
   names to the canonical ones.
2. **Write a dedicated loader** — subclass `datasets.base.DatasetLoader`,
   implement `load(source_path, record_id) -> pd.DataFrame` returning the
   canonical schema above. Use `datasets/sind.py` as a template (it also
   shows how to join a separate per-track metadata file).

Then add it to `DATASET_LOADERS` in `src/trajstats/cli.py` to expose it via
`--dataset`.

## Output layout

Reports and plots are written under `output/<record_id>/...` so multiple
records' outputs don't collide.

## Data and output directories

`data/` (downloaded raw CSVs) and `output/` (generated reports/plots) are
gitignored — the dataset itself is not redistributed in this repo; run the
downloader to populate `data/` locally.

## Tests

```bash
pytest tests/ -q
```

Runs fully offline against small synthetic fixtures under
`tests/fixtures/` — no network access or real dataset download required.

## License

MIT (see `LICENSE`).
