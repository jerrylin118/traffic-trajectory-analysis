"""Config-driven loader for other traffic-intersection datasets.

Use this when a new dataset already stores one row per (track, frame) in a
single CSV (or one CSV per agent type) and only needs its column names
mapped onto the canonical schema — no custom parsing logic required. For
anything more involved (multiple files to join, unit conversions beyond a
simple scale factor, etc.), write a dedicated loader instead, following
`trajstats.datasets.sind.SindLoader` as a template.

Example:

    loader = GenericCsvLoader(
        column_map={
            "id": "track_id",
            "type": "agent_type",
            "frame": "frame_id",
            "t": "timestamp_s",
            "pos_x": "x",
            "pos_y": "y",
            "vel_x": "vx",
            "vel_y": "vy",
        },
    )
    df = loader.load_validated("some_dataset/record_001.csv", record_id="record_001")
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .base import CANONICAL_COLUMNS, DatasetLoader


class GenericCsvLoader(DatasetLoader):
    """Loads a single CSV and renames columns onto the canonical schema.

    `column_map` maps source column name -> canonical column name for any
    columns that don't already match. `dataset_name` is written into the
    `dataset` column (defaults to the source file's stem).
    `xy_scale` multiplies `x`/`y` (and `vx`/`vy` if present) by a constant,
    useful when a source dataset's coordinates aren't already in meters.
    """

    def __init__(
        self,
        column_map: dict[str, str] | None = None,
        dataset_name: str | None = None,
        xy_scale: float = 1.0,
    ) -> None:
        self.column_map = column_map or {}
        self.dataset_name = dataset_name
        self.xy_scale = xy_scale

    def load(self, source_path: str | Path, record_id: str) -> pd.DataFrame:
        source_path = Path(source_path)
        df = pd.read_csv(source_path)
        df = df.rename(columns=self.column_map)

        missing = [c for c in CANONICAL_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(
                f"{source_path}: after applying column_map, still missing "
                f"required canonical columns: {missing}. Add entries to "
                f"column_map for these."
            )

        df["dataset"] = self.dataset_name or source_path.stem
        df["record_id"] = record_id
        df["track_id"] = df["track_id"].astype(str)
        df["frame_id"] = df["frame_id"].astype("int64")

        if self.xy_scale != 1.0:
            for col in ("x", "y", "vx", "vy"):
                if col in df.columns:
                    df[col] = df[col] * self.xy_scale

        return df
