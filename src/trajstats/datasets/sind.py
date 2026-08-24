"""Loader for the SinD dataset (https://github.com/SOTIF-AVLab/SinD).

Works for any SinD record folder (e.g. "Tianjin/8_2_1", "Tianjin/8_2_2", or
records from other cities that follow the same file layout), not just the
one this project was built against. Point `load_sind_record` at a local
directory containing the record's CSVs (as produced by
`trajstats.download.sind_downloader.download_sind_record`) and a logical
`record_id` label.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .base import DatasetLoader

PED_TRACKS_FILE = "Ped_smoothed_tracks.csv"
PED_META_FILE = "Ped_tracks_meta.csv"
VEH_TRACKS_FILE = "Veh_smoothed_tracks.csv"
VEH_META_FILE = "Veh_tracks_meta.csv"
RECORDING_META_FILE = "recording_metas.csv"


def _traffic_light_filename(record_id: str) -> str:
    """The TrafficLight CSV name embeds only the last path segment of the
    record id, e.g. record_id="Tianjin/8_2_1" -> "TrafficLight_8_2_1.csv".
    """
    folder_name = Path(record_id).name
    return f"TrafficLight_{folder_name}.csv"


def _load_pedestrians(record_dir: Path, record_id: str) -> pd.DataFrame:
    tracks_path = record_dir / PED_TRACKS_FILE
    if not tracks_path.exists():
        return pd.DataFrame(
            columns=[
                "dataset", "record_id", "track_id", "agent_type", "frame_id",
                "timestamp_s", "x", "y", "vx", "vy", "ax", "ay", "ped_class",
            ]
        )

    tracks = pd.read_csv(tracks_path)
    tracks["track_id"] = tracks["track_id"].astype(str)

    meta_path = record_dir / PED_META_FILE
    if meta_path.exists():
        meta = pd.read_csv(meta_path)
        meta = meta.rename(columns={"trackId": "track_id", "class": "ped_class"})
        meta["track_id"] = meta["track_id"].astype(str)
        tracks = tracks.merge(meta[["track_id", "ped_class"]], on="track_id", how="left")
    else:
        tracks["ped_class"] = pd.NA

    tracks["dataset"] = "sind"
    tracks["record_id"] = record_id
    tracks["timestamp_s"] = tracks["timestamp_ms"] / 1000.0

    return tracks[
        [
            "dataset", "record_id", "track_id", "agent_type", "frame_id",
            "timestamp_s", "x", "y", "vx", "vy", "ax", "ay", "ped_class",
        ]
    ]


def _load_vehicles(record_dir: Path, record_id: str) -> pd.DataFrame:
    tracks_path = record_dir / VEH_TRACKS_FILE
    if not tracks_path.exists():
        return pd.DataFrame(
            columns=[
                "dataset", "record_id", "track_id", "agent_type", "frame_id",
                "timestamp_s", "x", "y", "vx", "vy", "ax", "ay",
                "length", "width", "yaw_rad", "heading_rad",
                "cross_type", "signal_violation",
            ]
        )

    tracks = pd.read_csv(tracks_path)
    tracks["track_id"] = tracks["track_id"].astype(str)

    meta_path = record_dir / VEH_META_FILE
    if meta_path.exists():
        meta = pd.read_csv(meta_path)
        meta = meta.rename(
            columns={
                "trackId": "track_id",
                "CrossType": "cross_type",
                "Signal_Violation_Behavior": "signal_violation",
            }
        )
        meta["track_id"] = meta["track_id"].astype(str)
        tracks = tracks.merge(
            meta[["track_id", "cross_type", "signal_violation"]],
            on="track_id",
            how="left",
        )
    else:
        tracks["cross_type"] = pd.NA
        tracks["signal_violation"] = pd.NA

    tracks["dataset"] = "sind"
    tracks["record_id"] = record_id
    tracks["timestamp_s"] = tracks["timestamp_ms"] / 1000.0

    return tracks[
        [
            "dataset", "record_id", "track_id", "agent_type", "frame_id",
            "timestamp_s", "x", "y", "vx", "vy", "ax", "ay",
            "length", "width", "yaw_rad", "heading_rad",
            "cross_type", "signal_violation",
        ]
    ]


def load_sind_record(record_dir: str | Path, record_id: str) -> pd.DataFrame:
    """Load one SinD record directory into the canonical trajectory schema.

    `record_dir` is a local directory containing the record's CSVs (e.g.
    `data/Tianjin/8_2_1/`). `record_id` is a caller-supplied logical label
    for the record, typically the same path used to download it (e.g.
    "Tianjin/8_2_1") — it is threaded through the output so multiple
    records can be concatenated without collisions.
    """
    record_dir = Path(record_dir)
    if not record_dir.is_dir():
        raise FileNotFoundError(f"SinD record directory not found: {record_dir}")

    pedestrians = _load_pedestrians(record_dir, record_id)
    vehicles = _load_vehicles(record_dir, record_id)

    combined = pd.concat([pedestrians, vehicles], ignore_index=True, sort=False)
    combined["frame_id"] = combined["frame_id"].astype("int64")
    return combined


def load_sind_recording_metas(record_dir: str | Path) -> dict | None:
    """Return the single-row recording_metas.csv as a dict, or None if absent."""
    record_dir = Path(record_dir)
    meta_path = record_dir / RECORDING_META_FILE
    if not meta_path.exists():
        return None
    meta = pd.read_csv(meta_path)
    if meta.empty:
        return None
    return meta.iloc[0].to_dict()


def load_sind_traffic_lights(record_dir: str | Path, record_id: str) -> pd.DataFrame | None:
    """Return the TrafficLight_<record>.csv contents, or None if the file
    is absent. This file is record-dependent and not always present, so
    its absence is not an error.
    """
    record_dir = Path(record_dir)
    tl_path = record_dir / _traffic_light_filename(record_id)
    if not tl_path.exists():
        return None
    return pd.read_csv(tl_path)


class SindLoader(DatasetLoader):
    def load(self, source_path: str | Path, record_id: str) -> pd.DataFrame:
        return load_sind_record(source_path, record_id)
