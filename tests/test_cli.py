import shutil
from pathlib import Path

from trajstats.cli import build_parser, main

FIXTURES = Path(__file__).parent / "fixtures"
MINI = FIXTURES / "sind_8_2_1_mini"
RECORD_ID = "Tianjin/8_2_1"


def _make_data_dir(tmp_path: Path) -> Path:
    data_dir = tmp_path / "data"
    dest = data_dir / RECORD_ID
    shutil.copytree(MINI, dest)
    return data_dir


def test_build_parser_download():
    args = build_parser().parse_args(["download", "--record", "Tianjin/8_2_1"])
    assert args.command == "download"
    assert args.record == "Tianjin/8_2_1"
    assert args.data_dir == "data"


def test_build_parser_stats_pedestrian_timelength():
    args = build_parser().parse_args(
        ["stats", "pedestrian-timelength", "--record", "Tianjin/8_2_1"]
    )
    assert args.command == "stats"
    assert args.stats_command == "pedestrian-timelength"
    assert args.dataset == "sind"


def test_build_parser_plot_trajectories():
    args = build_parser().parse_args(
        ["plot", "trajectories", "--record", "Tianjin/8_2_1", "--agent-types", "pedestrian", "car"]
    )
    assert args.command == "plot"
    assert args.plot_command == "trajectories"
    assert args.agent_types == ["pedestrian", "car"]


def test_main_stats_pedestrian_timelength_end_to_end(tmp_path):
    data_dir = _make_data_dir(tmp_path)
    out_dir = tmp_path / "output"

    rc = main([
        "stats", "pedestrian-timelength",
        "--record", RECORD_ID,
        "--data-dir", str(data_dir),
        "--out-dir", str(out_dir),
    ])

    assert rc == 0
    report = out_dir / RECORD_ID / "pedestrian_timelength" / "pedestrian_timelength_report.md"
    assert report.exists() and report.stat().st_size > 0


def test_main_plot_trajectories_end_to_end(tmp_path):
    data_dir = _make_data_dir(tmp_path)
    out_dir = tmp_path / "output"

    rc = main([
        "plot", "trajectories",
        "--record", RECORD_ID,
        "--data-dir", str(data_dir),
        "--out-dir", str(out_dir),
    ])

    assert rc == 0
    out_path = out_dir / RECORD_ID / "trajectories_overlay.png"
    assert out_path.exists() and out_path.stat().st_size > 0


def test_main_plot_trajectories_with_agent_types(tmp_path):
    data_dir = _make_data_dir(tmp_path)
    out_dir = tmp_path / "output"

    rc = main([
        "plot", "trajectories",
        "--record", RECORD_ID,
        "--data-dir", str(data_dir),
        "--out-dir", str(out_dir),
        "--agent-types", "pedestrian",
    ])

    assert rc == 0
    out_path = out_dir / RECORD_ID / "trajectories.png"
    assert out_path.exists() and out_path.stat().st_size > 0
