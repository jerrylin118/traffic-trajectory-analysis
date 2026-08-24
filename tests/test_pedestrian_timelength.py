from pathlib import Path

import pytest

from trajstats.datasets.sind import load_sind_record
from trajstats.stats.pedestrian_timelength import (
    compute_track_metrics,
    run_pedestrian_timelength_report,
    summarize,
)

FIXTURES = Path(__file__).parent / "fixtures"
MINI = FIXTURES / "sind_8_2_1_mini"
RECORD_ID = "Tianjin/8_2_1"


@pytest.fixture
def metrics_df():
    df = load_sind_record(MINI, RECORD_ID)
    return compute_track_metrics(df, agent_type="pedestrian")


def test_compute_track_metrics_row_per_track(metrics_df):
    assert set(metrics_df["track_id"]) == {"P1", "P2", "P3"}
    assert len(metrics_df) == 3


def test_compute_track_metrics_durations(metrics_df):
    by_id = metrics_df.set_index("track_id")
    assert by_id.loc["P1", "duration_s"] == pytest.approx(1.0)
    assert by_id.loc["P2", "duration_s"] == pytest.approx(5.0)
    assert by_id.loc["P3", "duration_s"] == pytest.approx(15.0)


def test_compute_track_metrics_path_length_and_displacement(metrics_df):
    by_id = metrics_df.set_index("track_id")
    # Each fixture track moves in a straight line along x, 1m per 0.5s step.
    assert by_id.loc["P1", "path_length_m"] == pytest.approx(2.0)
    assert by_id.loc["P1", "straight_line_displacement_m"] == pytest.approx(2.0)
    assert by_id.loc["P1", "tortuosity"] == pytest.approx(1.0)
    assert by_id.loc["P1", "mean_speed_mps"] == pytest.approx(2.0)

    assert by_id.loc["P3", "path_length_m"] == pytest.approx(30.0)
    assert by_id.loc["P3", "mean_speed_mps"] == pytest.approx(2.0)


def test_summarize_duration(metrics_df):
    s = summarize(metrics_df, "duration_s")
    assert s["count"] == 3
    assert s["mean"] == pytest.approx((1.0 + 5.0 + 15.0) / 3)
    assert s["median"] == pytest.approx(5.0)
    assert s["min"] == pytest.approx(1.0)
    assert s["max"] == pytest.approx(15.0)


def test_summarize_empty_column_does_not_raise():
    import pandas as pd

    empty = pd.DataFrame({"duration_s": []})
    s = summarize(empty, "duration_s")
    assert s["count"] == 0


def test_run_pedestrian_timelength_report_writes_files(tmp_path):
    df = load_sind_record(MINI, RECORD_ID)
    report_path = run_pedestrian_timelength_report(df, RECORD_ID, tmp_path)

    assert report_path.exists()
    assert report_path.stat().st_size > 0

    csv_path = tmp_path / "pedestrian_track_metrics.csv"
    hist_path = tmp_path / "pedestrian_duration_histogram.png"
    assert csv_path.exists() and csv_path.stat().st_size > 0
    assert hist_path.exists() and hist_path.stat().st_size > 0

    content = report_path.read_text(encoding="utf-8")
    assert RECORD_ID in content
    assert "duration_s" in content
