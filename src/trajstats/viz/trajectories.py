"""Static matplotlib visualization of trajectories from the canonical schema.

All functions take the canonical DataFrame plus an explicit output path and
write a PNG; none call `plt.show()` or return `Figure` objects, keeping them
simple to use from scripts and the CLI.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

VEHICLE_AGENT_TYPES = {"car", "truck", "bus", "motorcycle", "bicycle", "tricycle"}


def _assign_colors(categories: list[str]) -> dict[str, tuple]:
    """Stable category -> color mapping, sorted for reproducibility across runs."""
    ordered = sorted(categories)
    cmap = plt.get_cmap("tab20")
    return {cat: cmap(i % 20) for i, cat in enumerate(ordered)}


def plot_all_trajectories(
    df: pd.DataFrame,
    out_path: str | Path,
    agent_types: list[str] | None = None,
    color_by: str = "agent_type",
    title: str | None = None,
    figsize: tuple[float, float] = (10, 10),
    alpha: float = 0.6,
    linewidth: float = 0.8,
) -> None:
    """Plot every track's (x, y) path as a line, colored by `color_by`
    (one of "agent_type" or "track_id"). If `agent_types` is given, only
    those agent types are plotted.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    plot_df = df if agent_types is None else df[df["agent_type"].isin(agent_types)]

    colors = _assign_colors(plot_df[color_by].astype(str).unique().tolist())

    fig, ax = plt.subplots(figsize=figsize)
    seen_labels = set()
    for (record_id, track_id), group in plot_df.groupby(["record_id", "track_id"], sort=False):
        group = group.sort_values("frame_id")
        category = str(group[color_by].iloc[0])
        label = category if category not in seen_labels else None
        seen_labels.add(category)
        ax.plot(
            group["x"], group["y"],
            color=colors[category], alpha=alpha, linewidth=linewidth, label=label,
        )

    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_aspect("equal", adjustable="datalim")
    ax.set_title(title or "Trajectories")
    if len(seen_labels) <= 20:
        ax.legend(loc="best", fontsize="small", markerscale=2)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_single_track(
    df: pd.DataFrame,
    track_id: str,
    out_path: str | Path,
    show_velocity_arrows: bool = False,
    figsize: tuple[float, float] = (8, 8),
) -> None:
    """Plot one track's path, marking its start (green) and end (red)."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    group = df[df["track_id"] == str(track_id)].sort_values("frame_id")
    if group.empty:
        raise ValueError(f"No rows found for track_id={track_id!r}")

    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(group["x"], group["y"], color="#3b6fa0", linewidth=1.2)
    ax.scatter(group["x"].iloc[0], group["y"].iloc[0], color="green", zorder=3, label="start")
    ax.scatter(group["x"].iloc[-1], group["y"].iloc[-1], color="red", zorder=3, label="end")

    if show_velocity_arrows and "vx" in group.columns and "vy" in group.columns:
        step = max(1, len(group) // 20)
        sampled = group.iloc[::step]
        ax.quiver(
            sampled["x"], sampled["y"], sampled["vx"], sampled["vy"],
            angles="xy", scale_units="xy", scale=1, color="gray", alpha=0.6, width=0.003,
        )

    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_aspect("equal", adjustable="datalim")
    ax.set_title(f"Track {track_id}")
    ax.legend(loc="best", fontsize="small")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_pedestrian_vehicle_overlay(
    df: pd.DataFrame,
    out_path: str | Path,
    figsize: tuple[float, float] = (10, 10),
) -> None:
    """Overlay pedestrian and vehicle trajectories, grouped into exactly
    two visual classes ("pedestrian" vs "vehicle") regardless of how many
    specific vehicle agent_types are present.
    """
    plot_df = df.copy()
    plot_df["agent_class"] = plot_df["agent_type"].apply(
        lambda t: "pedestrian" if t == "pedestrian" else "vehicle"
    )
    plot_all_trajectories(
        plot_df, out_path, color_by="agent_class",
        title="Pedestrian and vehicle trajectories", figsize=figsize,
    )
