from pathlib import Path

import matplotlib

matplotlib.use("Agg")

from trajstats.datasets.sind import load_sind_record
from trajstats.viz.trajectories import (
    plot_all_trajectories,
    plot_pedestrian_vehicle_overlay,
    plot_single_track,
)

FIXTURES = Path(__file__).parent / "fixtures"
MINI = FIXTURES / "sind_8_2_1_mini"
RECORD_ID = "Tianjin/8_2_1"


def _df():
    return load_sind_record(MINI, RECORD_ID)


def test_plot_all_trajectories_writes_png(tmp_path):
    out_path = tmp_path / "all.png"
    plot_all_trajectories(_df(), out_path)
    assert out_path.exists() and out_path.stat().st_size > 0


def test_plot_all_trajectories_filtered_by_agent_type(tmp_path):
    out_path = tmp_path / "ped_only.png"
    plot_all_trajectories(_df(), out_path, agent_types=["pedestrian"])
    assert out_path.exists() and out_path.stat().st_size > 0


def test_plot_all_trajectories_color_by_track_id(tmp_path):
    out_path = tmp_path / "by_track.png"
    plot_all_trajectories(_df(), out_path, color_by="track_id")
    assert out_path.exists() and out_path.stat().st_size > 0


def test_plot_single_track_writes_png(tmp_path):
    out_path = tmp_path / "p1.png"
    plot_single_track(_df(), "P1", out_path)
    assert out_path.exists() and out_path.stat().st_size > 0


def test_plot_single_track_with_velocity_arrows(tmp_path):
    out_path = tmp_path / "p3_arrows.png"
    plot_single_track(_df(), "P3", out_path, show_velocity_arrows=True)
    assert out_path.exists() and out_path.stat().st_size > 0


def test_plot_single_track_unknown_id_raises(tmp_path):
    import pytest

    with pytest.raises(ValueError):
        plot_single_track(_df(), "does-not-exist", tmp_path / "missing.png")


def test_plot_pedestrian_vehicle_overlay_writes_png(tmp_path):
    out_path = tmp_path / "overlay.png"
    plot_pedestrian_vehicle_overlay(_df(), out_path)
    assert out_path.exists() and out_path.stat().st_size > 0
