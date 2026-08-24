"""Statistical analysis of pedestrian dwell/crossing duration ("timelength")
and related per-track movement metrics.

Operates only on the canonical trajectory schema (see
`trajstats.datasets.base`), so it works against any dataset's data, not just
SinD.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

SUMMARY_COLUMNS = ["duration_s", "path_length_m", "mean_speed_mps", "tortuosity"]


def compute_track_metrics(df: pd.DataFrame, agent_type: str = "pedestrian") -> pd.DataFrame:
    """Compute per-track movement metrics for all tracks of `agent_type`.

    Returns one row per (record_id, track_id) with:
      - duration_s: max(timestamp_s) - min(timestamp_s)
      - n_frames: number of rows for the track
      - path_length_m: sum of consecutive-point Euclidean distances
      - straight_line_displacement_m: distance between first and last point
      - tortuosity: path_length_m / straight_line_displacement_m (NaN if
        displacement is ~0, e.g. a stationary or single-frame track)
      - mean_speed_mps: path_length_m / duration_s (NaN if duration is ~0)
    """
    subset = df[df["agent_type"] == agent_type]
    rows = []

    for (record_id, track_id), group in subset.groupby(["record_id", "track_id"], sort=False):
        group = group.sort_values("frame_id")
        t = group["timestamp_s"].to_numpy()
        x = group["x"].to_numpy()
        y = group["y"].to_numpy()

        duration_s = float(t.max() - t.min()) if len(t) else 0.0
        n_frames = len(group)

        if len(x) > 1:
            dx = np.diff(x)
            dy = np.diff(y)
            path_length_m = float(np.sum(np.hypot(dx, dy)))
            straight_line_displacement_m = float(np.hypot(x[-1] - x[0], y[-1] - y[0]))
        else:
            path_length_m = 0.0
            straight_line_displacement_m = 0.0

        tortuosity = (
            path_length_m / straight_line_displacement_m
            if straight_line_displacement_m > 1e-9
            else np.nan
        )
        mean_speed_mps = path_length_m / duration_s if duration_s > 1e-9 else np.nan

        rows.append(
            {
                "record_id": record_id,
                "track_id": track_id,
                "duration_s": duration_s,
                "n_frames": n_frames,
                "path_length_m": path_length_m,
                "straight_line_displacement_m": straight_line_displacement_m,
                "tortuosity": tortuosity,
                "mean_speed_mps": mean_speed_mps,
            }
        )

    return pd.DataFrame(
        rows,
        columns=[
            "record_id", "track_id", "duration_s", "n_frames", "path_length_m",
            "straight_line_displacement_m", "tortuosity", "mean_speed_mps",
        ],
    )


def summarize(metrics_df: pd.DataFrame, column: str = "duration_s") -> dict:
    """Return summary statistics for one metrics column, ignoring NaNs."""
    values = metrics_df[column].dropna()
    if values.empty:
        return {
            "count": 0, "mean": np.nan, "median": np.nan, "std": np.nan,
            "min": np.nan, "p25": np.nan, "p75": np.nan, "p90": np.nan, "max": np.nan,
        }
    return {
        "count": int(values.count()),
        "mean": float(values.mean()),
        "median": float(values.median()),
        "std": float(values.std()),
        "min": float(values.min()),
        "p25": float(values.quantile(0.25)),
        "p75": float(values.quantile(0.75)),
        "p90": float(values.quantile(0.90)),
        "max": float(values.max()),
    }


def write_per_track_csv(metrics_df: pd.DataFrame, out_path: str | Path) -> None:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_df.to_csv(out_path, index=False)


def plot_duration_histogram(metrics_df: pd.DataFrame, out_path: str | Path, bins: int = 30) -> None:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    durations = metrics_df["duration_s"].dropna()
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(durations, bins=bins, color="#3b6fa0", edgecolor="white")
    ax.set_xlabel("Duration (s)")
    ax.set_ylabel("Track count")
    ax.set_title("Pedestrian track duration distribution")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def write_summary_report_md(
    metrics_df: pd.DataFrame,
    summaries: dict[str, dict],
    out_path: str | Path,
    record_id: str,
    histogram_filename: str | None = None,
) -> None:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# Pedestrian timelength report — {record_id}",
        "",
        f"Tracks analyzed: {len(metrics_df)}",
        "",
        "| Metric | Count | Mean | Median | Std | Min | P25 | P75 | P90 | Max |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for column, s in summaries.items():
        lines.append(
            f"| {column} | {s['count']} | {s['mean']:.3f} | {s['median']:.3f} | "
            f"{s['std']:.3f} | {s['min']:.3f} | {s['p25']:.3f} | {s['p75']:.3f} | "
            f"{s['p90']:.3f} | {s['max']:.3f} |"
        )

    if histogram_filename:
        lines += ["", f"![Duration histogram]({histogram_filename})"]

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_pedestrian_timelength_report(df: pd.DataFrame, record_id: str, out_dir: str | Path) -> Path:
    """Compute pedestrian track metrics and write a per-track CSV, a
    duration histogram PNG, and a Markdown summary report into `out_dir`.
    Returns the path to the Markdown report.
    """
    out_dir = Path(out_dir)
    metrics_df = compute_track_metrics(df, agent_type="pedestrian")

    csv_path = out_dir / "pedestrian_track_metrics.csv"
    hist_path = out_dir / "pedestrian_duration_histogram.png"
    report_path = out_dir / "pedestrian_timelength_report.md"

    write_per_track_csv(metrics_df, csv_path)
    plot_duration_histogram(metrics_df, hist_path)

    summaries = {col: summarize(metrics_df, col) for col in SUMMARY_COLUMNS}
    write_summary_report_md(
        metrics_df, summaries, report_path, record_id,
        histogram_filename=hist_path.name,
    )

    return report_path
