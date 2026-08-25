"""Command-line interface: download / stats / plot subcommands."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .datasets.dut import DutLoader
from .datasets.sind import SindLoader
from .download.dut_downloader import download_dut_record
from .download.sind_downloader import DownloadError, download_sind_record
from .stats.pedestrian_timelength import run_pedestrian_timelength_report
from .viz.trajectories import plot_all_trajectories, plot_pedestrian_vehicle_overlay

# Dataset dispatch. Add an entry here (and a matching loader in
# trajstats.datasets) to support a new dataset from the CLI.
DATASET_LOADERS = {
    "sind": SindLoader(),
    "dut": DutLoader(),
}

# Download dispatch: dataset name -> (record, dest_dir, overwrite) -> a
# result object exposing `.statuses` (dict[str, FileFetchStatus]) and
# `.dest_dir`. Raises DownloadError on failure.
DOWNLOADERS = {
    "sind": download_sind_record,
    "dut": download_dut_record,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="trajstats")
    sub = parser.add_subparsers(dest="command", required=True)

    p_dl = sub.add_parser("download", help="Download a dataset record's CSV files")
    p_dl.add_argument("--dataset", default="sind", choices=list(DOWNLOADERS))
    p_dl.add_argument(
        "--record", required=True,
        help="e.g. Tianjin/8_2_1 (sind) or intersection_01 (dut)",
    )
    p_dl.add_argument("--data-dir", default="data")
    p_dl.add_argument("--overwrite", action="store_true")

    p_stats = sub.add_parser("stats", help="Statistical analysis")
    stats_sub = p_stats.add_subparsers(dest="stats_command", required=True)

    p_stats_ped = stats_sub.add_parser("pedestrian-timelength")
    p_stats_ped.add_argument("--dataset", default="sind", choices=list(DATASET_LOADERS))
    p_stats_ped.add_argument("--record", required=True, help="e.g. Tianjin/8_2_1")
    p_stats_ped.add_argument("--data-dir", default="data")
    p_stats_ped.add_argument("--out-dir", default="output")

    p_plot = sub.add_parser("plot", help="Static trajectory visualization")
    plot_sub = p_plot.add_subparsers(dest="plot_command", required=True)

    p_plot_traj = plot_sub.add_parser("trajectories")
    p_plot_traj.add_argument("--dataset", default="sind", choices=list(DATASET_LOADERS))
    p_plot_traj.add_argument("--record", required=True, help="e.g. Tianjin/8_2_1")
    p_plot_traj.add_argument("--data-dir", default="data")
    p_plot_traj.add_argument("--out-dir", default="output")
    p_plot_traj.add_argument(
        "--agent-types", nargs="*", default=None,
        help="Restrict to these agent types (e.g. pedestrian car). Default: all.",
    )

    return parser


def _record_source_dir(data_dir: str, record: str) -> Path:
    return Path(data_dir) / record


def _cmd_download(args: argparse.Namespace) -> int:
    downloader = DOWNLOADERS[args.dataset]
    try:
        result = downloader(args.record, dest_dir=args.data_dir, overwrite=args.overwrite)
    except DownloadError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    for filename, status in result.statuses.items():
        print(f"{filename}: {status.value}")
    print(f"Saved to {result.dest_dir}")
    return 0


def _cmd_stats_pedestrian_timelength(args: argparse.Namespace) -> int:
    loader = DATASET_LOADERS[args.dataset]
    source_dir = _record_source_dir(args.data_dir, args.record)
    df = loader.load_validated(source_dir, args.record)

    out_dir = Path(args.out_dir) / args.record / "pedestrian_timelength"
    report_path = run_pedestrian_timelength_report(df, args.record, out_dir)
    print(f"Report written to {report_path}")
    return 0


def _cmd_plot_trajectories(args: argparse.Namespace) -> int:
    loader = DATASET_LOADERS[args.dataset]
    source_dir = _record_source_dir(args.data_dir, args.record)
    df = loader.load_validated(source_dir, args.record)

    out_dir = Path(args.out_dir) / args.record
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.agent_types:
        out_path = out_dir / "trajectories.png"
        plot_all_trajectories(df, out_path, agent_types=args.agent_types)
    else:
        out_path = out_dir / "trajectories_overlay.png"
        plot_pedestrian_vehicle_overlay(df, out_path)

    print(f"Plot written to {out_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "download":
        return _cmd_download(args)
    if args.command == "stats" and args.stats_command == "pedestrian-timelength":
        return _cmd_stats_pedestrian_timelength(args)
    if args.command == "plot" and args.plot_command == "trajectories":
        return _cmd_plot_trajectories(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
