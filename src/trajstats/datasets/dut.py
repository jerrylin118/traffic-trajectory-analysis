"""Loader for the DUT vehicle-crowd-interaction dataset
(https://github.com/dongfang-steven-yang/vci-dataset-dut).

Works for any DUT record ("intersection_01".."intersection_17" -- marked
crosswalks at an unsignalized intersection -- or "roundabout_01".."roundabout_11"
-- a shared space). Point `load_dut_record` at a local directory containing
the record's two filtered-trajectory CSVs (as produced by
`trajstats.download.dut_downloader.download_dut_record`) and a logical
`record_id` label.

DUT's CSVs carry no timestamp column, only a frame index; `timestamp_s` is
derived from the dataset's fixed recording frame rate (23.98 fps, per the
dataset README). Vehicle rows carry a heading (`psi_est`, radians) and a
scalar longitudinal speed (`vel_est`) rather than a velocity vector, so
`vx`/`vy` are decomposed from those via the standard heading convention
(angle from the +x axis, counterclockwise).
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

from .base import DatasetLoader

FPS = 23.98

PED_COLUMNS = [
    "dataset", "record_id", "track_id", "agent_type", "frame_id",
    "timestamp_s", "x", "y", "vx", "vy",
]
VEH_COLUMNS = [
    "dataset", "record_id", "track_id", "agent_type", "frame_id",
    "timestamp_s", "x", "y", "vx", "vy", "heading_rad",
]


def _ped_filename(record_id: str) -> str:
    return f"{Path(record_id).name}_traj_ped_filtered.csv"


def _veh_filename(record_id: str) -> str:
    return f"{Path(record_id).name}_traj_veh_filtered.csv"


def _load_pedestrians(record_dir: Path, record_id: str) -> pd.DataFrame:
    tracks_path = record_dir / _ped_filename(record_id)
    if not tracks_path.exists():
        return pd.DataFrame(columns=PED_COLUMNS)

    tracks = pd.read_csv(tracks_path)
    tracks["dataset"] = "dut"
    tracks["record_id"] = record_id
    # DUT's pedestrian and vehicle ids are both small integers starting at 0
    # and are only unique *within* their own file, not across the record
    # (unlike SinD's "P1"/"1" split) -- prefix so track_id stays unique
    # within the record, as the canonical schema requires.
    tracks["track_id"] = "ped_" + tracks["id"].astype(str)
    tracks["agent_type"] = "pedestrian"
    tracks["frame_id"] = tracks["frame"].astype("int64")
    tracks["timestamp_s"] = tracks["frame"] / FPS
    tracks["x"] = tracks["x_est"]
    tracks["y"] = tracks["y_est"]
    tracks["vx"] = tracks["vx_est"]
    tracks["vy"] = tracks["vy_est"]

    return tracks[PED_COLUMNS]


def _load_vehicles(record_dir: Path, record_id: str) -> pd.DataFrame:
    tracks_path = record_dir / _veh_filename(record_id)
    if not tracks_path.exists():
        return pd.DataFrame(columns=VEH_COLUMNS)

    tracks = pd.read_csv(tracks_path)
    tracks["dataset"] = "dut"
    tracks["record_id"] = record_id
    tracks["track_id"] = "veh_" + tracks["id"].astype(str)
    tracks["agent_type"] = "car"
    tracks["frame_id"] = tracks["frame"].astype("int64")
    tracks["timestamp_s"] = tracks["frame"] / FPS
    tracks["x"] = tracks["x_est"]
    tracks["y"] = tracks["y_est"]
    tracks["heading_rad"] = tracks["psi_est"]
    tracks["vx"] = tracks["vel_est"] * tracks["psi_est"].apply(math.cos)
    tracks["vy"] = tracks["vel_est"] * tracks["psi_est"].apply(math.sin)

    return tracks[VEH_COLUMNS]


def load_dut_record(record_dir: str | Path, record_id: str) -> pd.DataFrame:
    """Load one DUT record directory into the canonical trajectory schema.

    `record_dir` is a local directory containing the record's two CSVs
    (e.g. `data/intersection_01/`). `record_id` is a caller-supplied
    logical label for the record (typically the same name used to
    download it, e.g. "intersection_01").
    """
    record_dir = Path(record_dir)
    if not record_dir.is_dir():
        raise FileNotFoundError(f"DUT record directory not found: {record_dir}")

    pedestrians = _load_pedestrians(record_dir, record_id)
    vehicles = _load_vehicles(record_dir, record_id)

    combined = pd.concat([pedestrians, vehicles], ignore_index=True, sort=False)
    combined["frame_id"] = combined["frame_id"].astype("int64")
    return combined


class DutLoader(DatasetLoader):
    def load(self, source_path: str | Path, record_id: str) -> pd.DataFrame:
        return load_dut_record(source_path, record_id)
