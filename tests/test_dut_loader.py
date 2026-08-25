import math
from pathlib import Path

import pytest

from trajstats.datasets.base import validate_trajectory_df
from trajstats.datasets.dut import FPS, load_dut_record

FIXTURES = Path(__file__).parent / "fixtures"
MINI = FIXTURES / "dut_intersection_01_mini"

RECORD_ID = "intersection_01"


def test_load_dut_record_returns_canonical_schema():
    df = load_dut_record(MINI, RECORD_ID)
    validate_trajectory_df(df)


def test_load_dut_record_row_counts():
    df = load_dut_record(MINI, RECORD_ID)
    ped = df[df["agent_type"] == "pedestrian"]
    veh = df[df["agent_type"] == "car"]

    assert len(ped) == 3 + 2
    assert len(veh) == 2 + 1


def test_track_ids_are_strings():
    df = load_dut_record(MINI, RECORD_ID)
    assert df["track_id"].map(type).eq(str).all()
    assert set(df.loc[df["agent_type"] == "pedestrian", "track_id"].unique()) == {"ped_0", "ped_1"}


def test_track_ids_unique_across_agent_types():
    """DUT's raw pedestrian and vehicle ids both start at 0 and collide;
    the loader must prefix them so a groupby on track_id alone (e.g. for
    plotting) never merges a pedestrian and a vehicle track.
    """
    df = load_dut_record(MINI, RECORD_ID)
    ped_ids = set(df.loc[df["agent_type"] == "pedestrian", "track_id"].unique())
    veh_ids = set(df.loc[df["agent_type"] == "car", "track_id"].unique())
    assert ped_ids.isdisjoint(veh_ids)


def test_timestamp_s_derived_from_frame_and_fps():
    df = load_dut_record(MINI, RECORD_ID)
    p0 = df[(df["agent_type"] == "pedestrian") & (df["track_id"] == "ped_0")].sort_values("frame_id")
    assert p0["timestamp_s"].iloc[0] == pytest.approx(1 / FPS)
    assert p0["timestamp_s"].iloc[-1] == pytest.approx(3 / FPS)


def test_vehicle_velocity_decomposed_from_heading_and_speed():
    df = load_dut_record(MINI, RECORD_ID)
    veh0 = df[(df["agent_type"] == "car") & (df["track_id"] == "veh_0")]
    assert veh0["vx"].tolist() == pytest.approx([4.0, 4.0])
    assert veh0["vy"].tolist() == pytest.approx([0.0, 0.0], abs=1e-9)

    veh1 = df[(df["agent_type"] == "car") & (df["track_id"] == "veh_1")]
    assert veh1["vx"].iloc[0] == pytest.approx(0.0, abs=1e-9)
    assert veh1["vy"].iloc[0] == pytest.approx(2.0)
    assert veh1["heading_rad"].iloc[0] == pytest.approx(math.pi / 2)


def test_missing_record_dir_raises():
    with pytest.raises(FileNotFoundError):
        load_dut_record(FIXTURES / "does_not_exist", RECORD_ID)
