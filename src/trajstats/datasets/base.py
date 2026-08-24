"""Canonical trajectory schema shared by every dataset loader.

Stats and visualization code depends only on this schema, never on any
dataset-specific column names. To add support for a new dataset, subclass
`DatasetLoader` and implement `load()` to return a DataFrame with these
columns.
"""

from __future__ import annotations

import abc
from pathlib import Path

import numpy as np
import pandas as pd

# Column -> pandas dtype string. Every loader must produce all of these.
CANONICAL_COLUMNS: dict[str, str] = {
    "dataset": "string",
    "record_id": "string",
    "track_id": "string",
    "agent_type": "string",
    "frame_id": "int64",
    "timestamp_s": "float64",
    "x": "float64",
    "y": "float64",
    "vx": "float64",
    "vy": "float64",
}

# Columns that some loaders/agent types can populate but others cannot.
# Downstream code should use `.get()`-style access / `in df.columns` checks
# before relying on these.
OPTIONAL_COLUMNS: dict[str, str] = {
    "ax": "float64",
    "ay": "float64",
    "length": "float64",
    "width": "float64",
    "yaw_rad": "float64",
    "heading_rad": "float64",
    "cross_type": "string",
    "signal_violation": "string",
    "ped_class": "string",
}


def validate_trajectory_df(df: pd.DataFrame) -> None:
    """Raise ValueError if `df` does not satisfy the canonical schema.

    Checks that all required columns are present and that `x`/`y` are
    finite. Does not mutate `df`.
    """
    missing = [c for c in CANONICAL_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            f"Trajectory DataFrame is missing required columns: {missing}"
        )

    for col in ("x", "y"):
        if not np.isfinite(df[col].to_numpy(dtype="float64")).all():
            raise ValueError(f"Column '{col}' contains non-finite values")


class DatasetLoader(abc.ABC):
    """Interface every dataset loader implements.

    `load()` returns a DataFrame with (at minimum) the columns in
    `CANONICAL_COLUMNS`, one row per (track_id, frame_id).
    """

    @abc.abstractmethod
    def load(self, source_path: str | Path, record_id: str) -> pd.DataFrame:
        raise NotImplementedError

    def load_validated(self, source_path: str | Path, record_id: str) -> pd.DataFrame:
        df = self.load(source_path, record_id)
        validate_trajectory_df(df)
        return df
