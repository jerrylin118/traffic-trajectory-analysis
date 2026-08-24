from pathlib import Path

import pytest

from trajstats.datasets.base import validate_trajectory_df
from trajstats.datasets.sind import (
    load_sind_record,
    load_sind_recording_metas,
    load_sind_traffic_lights,
)

FIXTURES = Path(__file__).parent / "fixtures"
MINI = FIXTURES / "sind_8_2_1_mini"
NO_TL = FIXTURES / "sind_no_traffic_light"

RECORD_ID = "Tianjin/8_2_1"


def test_load_sind_record_returns_canonical_schema():
    df = load_sind_record(MINI, RECORD_ID)
    validate_trajectory_df(df)  # should not raise


def test_load_sind_record_row_counts():
    df = load_sind_record(MINI, RECORD_ID)
    ped = df[df["agent_type"] == "pedestrian"]
    veh = df[df["agent_type"].isin(["car", "bus"])]

    assert len(ped) == 3 + 11 + 31  # P1 + P2 + P3
    assert len(veh) == 5 + 5  # car + bus


def test_track_ids_are_strings():
    df = load_sind_record(MINI, RECORD_ID)
    assert df["track_id"].map(type).eq(str).all()
    assert set(df.loc[df["agent_type"] == "pedestrian", "track_id"].unique()) == {"P1", "P2", "P3"}
    assert set(df.loc[df["agent_type"] == "car", "track_id"].unique()) == {"1"}


def test_timestamp_s_derived_from_timestamp_ms():
    df = load_sind_record(MINI, RECORD_ID)
    p3 = df[(df["agent_type"] == "pedestrian") & (df["track_id"] == "P3")].sort_values("frame_id")
    assert p3["timestamp_s"].iloc[0] == pytest.approx(0.0)
    assert p3["timestamp_s"].iloc[-1] == pytest.approx(15.0)


def test_pedestrian_class_joined_from_meta():
    df = load_sind_record(MINI, RECORD_ID)
    p1 = df[(df["agent_type"] == "pedestrian") & (df["track_id"] == "P1")]
    assert (p1["ped_class"] == "pedestrian").all()


def test_vehicle_meta_joined():
    df = load_sind_record(MINI, RECORD_ID)
    bus = df[df["track_id"] == "2"]
    assert (bus["cross_type"] == "LeftTurn").all()
    assert (bus["signal_violation"] == "red-light running").all()

    car = df[df["track_id"] == "1"]
    assert (car["cross_type"] == "StraightCross").all()
    assert (car["signal_violation"] == "No violation of traffic lights").all()


def test_missing_record_dir_raises():
    with pytest.raises(FileNotFoundError):
        load_sind_record(FIXTURES / "does_not_exist", RECORD_ID)


def test_load_sind_traffic_lights_present():
    tl = load_sind_traffic_lights(MINI, RECORD_ID)
    assert tl is not None
    assert "Traffic light 1" in tl.columns
    assert len(tl) == 4


def test_load_sind_traffic_lights_absent_returns_none():
    tl = load_sind_traffic_lights(NO_TL, RECORD_ID)
    assert tl is None


def test_load_sind_recording_metas():
    meta = load_sind_recording_metas(MINI)
    assert meta is not None
    assert meta["City"] == "Tianjin"


def test_load_sind_recording_metas_absent_returns_none():
    meta = load_sind_recording_metas(NO_TL)
    assert meta is None
