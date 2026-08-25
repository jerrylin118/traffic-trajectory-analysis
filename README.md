# traffic-trajectory-analysis

Statistical analysis of pedestrian crossing/dwell duration and static
visualization of vehicle + pedestrian trajectories at traffic intersections.
All analysis and plotting code works off one [canonical trajectory
schema](#canonical-trajectory-schema), so any dataset with a loader behind it
works the same way. Ships with loaders for two datasets ([SinD](#sind) and
[DUT](#dut)); adding another is a documented [extension
point](#adding-a-new-dataset).

## Installation

```bash
python -m venv .venv
.venv/Scripts/activate   # Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
pip install -e .
```

## Quickstart

Every command takes `--dataset` (default `sind`) and `--record` (a
dataset-specific record label — see [Supported
datasets](#supported-datasets)). Download a record's data, then analyze it:

```bash
trajstats download --dataset sind --record Tianjin/8_2_1
trajstats stats pedestrian-timelength --dataset sind --record Tianjin/8_2_1
trajstats plot trajectories --dataset sind --record Tianjin/8_2_1
```

`stats pedestrian-timelength` writes `output/<record>/pedestrian_timelength/`:
- `pedestrian_track_metrics.csv` — per-track duration, path length, displacement, tortuosity, mean speed
- `pedestrian_duration_histogram.png`
- `pedestrian_timelength_report.md` — summary stats table + embedded histogram

`plot trajectories` writes `output/<record>/trajectories_overlay.png`
(pedestrians vs. vehicles). Pass `--agent-types pedestrian car` to restrict to
specific agent types instead (written to `trajectories.png`).

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

## Supported datasets

### SinD

[SinD](https://github.com/SOTIF-AVLab/SinD) — a signalized Tianjin
intersection. `--record` is a `City/record_id` path under SinD's `Data/`
folder, e.g. `Tianjin/8_2_1` or `Tianjin/8_2_2`; the loader and downloader
work with any record, not just `8_2_1`.

```bash
trajstats download --dataset sind --record Tianjin/8_2_2
trajstats stats pedestrian-timelength --dataset sind --record Tianjin/8_2_2
```

SinD's CSVs are Git-LFS-backed in the source repo; the downloader fetches the
real LFS content over plain HTTP, so no `git`/`git-lfs` install is required.

### DUT

The [DUT vehicle-crowd-interaction
dataset](https://github.com/dongfang-steven-yang/vci-dataset-dut) (Dalian
University of Technology) — pedestrian/vehicle trajectories at unsignalized
campus crosswalks and shared spaces, a useful counterpart to SinD's
signalized intersection. `--record` is one of `intersection_01`..`intersection_17`
(crosswalks) or `roundabout_01`..`roundabout_11` (shared spaces).

```bash
trajstats download --dataset dut --record intersection_01
trajstats stats pedestrian-timelength --dataset dut --record intersection_01
trajstats plot trajectories --dataset dut --record intersection_01
```

DUT's CSVs are committed directly to GitHub (no Git LFS). It ships no
timestamp column, only a frame index, so `timestamp_s` is derived from the
dataset's fixed 23.98 fps. Vehicle rows carry a heading (`heading_rad`) and
scalar speed rather than a velocity vector; `vx`/`vy` are decomposed from
those. See `src/trajstats/datasets/dut.py`.

## Adding a new dataset

Two options, in `src/trajstats/datasets/`:

1. **`generic_csv.GenericCsvLoader`** — for a dataset that's already one CSV
   row per (track, frame): pass a `column_map` from the source's column
   names to the canonical ones.
2. **Write a dedicated loader** — subclass `datasets.base.DatasetLoader`,
   implement `load(source_path, record_id) -> pd.DataFrame` returning the
   canonical schema above. Use `datasets/sind.py` or `datasets/dut.py` as a
   template (`sind.py` shows how to join a separate per-track metadata file;
   `dut.py` shows deriving timestamps from a fixed fps and decomposing a
   heading + scalar speed into a velocity vector).

Then add it to `DATASET_LOADERS` in `src/trajstats/cli.py` to expose it via
`--dataset`, and if it needs a downloader, add one alongside
`download/sind_downloader.py` / `download/dut_downloader.py` and register it
in `DOWNLOADERS`.

## Output layout

Reports and plots are written under `output/<record_id>/...` so multiple
records' outputs don't collide.

## Data and output directories

`data/` (downloaded raw CSVs) and `output/` (generated reports/plots) are
gitignored — datasets are not redistributed in this repo; run the downloader
to populate `data/` locally.

## Tests

```bash
pytest tests/ -q
```

Runs fully offline against small synthetic fixtures under
`tests/fixtures/` — no network access or real dataset download required.

## License

MIT (see `LICENSE`).
