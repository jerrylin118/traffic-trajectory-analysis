"""Downloads DUT dataset record files (https://github.com/dongfang-steven-yang/vci-dataset-dut).

Unlike SinD, DUT's filtered trajectory CSVs are committed directly to the
GitHub repo (not Git-LFS-backed), so a plain HTTP GET against
raw.githubusercontent.com is enough.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .sind_downloader import DownloadError, FileFetchStatus, _fetch_one

DUT_OWNER = "dongfang-steven-yang"
DUT_REPO = "vci-dataset-dut"
DUT_REF = "master"
BASE_URL = f"https://raw.githubusercontent.com/{DUT_OWNER}/{DUT_REPO}/{DUT_REF}/data/trajectories_filtered"

# Both files exist for every record ("intersection_01".."intersection_17",
# "roundabout_01".."roundabout_11") -- crossings and shared spaces alike
# include both pedestrians and vehicles.
REQUIRED_FILE_SUFFIXES = [
    "_traj_ped_filtered.csv",
    "_traj_veh_filtered.csv",
]


@dataclass
class DownloadResult:
    record_path: str
    dest_dir: Path
    statuses: dict[str, FileFetchStatus] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return all(status == FileFetchStatus.DOWNLOADED or status == FileFetchStatus.SKIPPED_EXISTS
                    for status in self.statuses.values())


def download_dut_record(
    record_path: str,
    dest_dir: str | Path = "data",
    overwrite: bool = False,
) -> DownloadResult:
    """Download one DUT record's pedestrian + vehicle trajectory CSVs into
    `dest_dir/record_path/`.

    `record_path` is the record's base name under DUT's
    `data/trajectories_filtered/` folder, e.g. "intersection_01" or
    "roundabout_03".
    """
    dest_dir = Path(dest_dir) / record_path
    result = DownloadResult(record_path=record_path, dest_dir=dest_dir)

    filenames = [f"{record_path}{suffix}" for suffix in REQUIRED_FILE_SUFFIXES]

    for filename in filenames:
        url = f"{BASE_URL}/{filename}"
        status = _fetch_one(url, dest_dir / filename, overwrite)
        result.statuses[filename] = status
        if status == FileFetchStatus.ERROR:
            result.errors[filename] = f"Request failed for {url}"

    missing = [
        name for name in filenames
        if result.statuses.get(name) not in (FileFetchStatus.DOWNLOADED, FileFetchStatus.SKIPPED_EXISTS)
    ]
    if missing:
        raise DownloadError(
            f"Failed to download required DUT files for record "
            f"'{record_path}': {missing}. "
            f"Statuses: { {k: v.value for k, v in result.statuses.items()} }"
        )

    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download a DUT dataset record's CSV files."
    )
    parser.add_argument("--record", required=True, help="e.g. intersection_01")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = download_dut_record(args.record, dest_dir=args.data_dir, overwrite=args.overwrite)
    except DownloadError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    for filename, status in result.statuses.items():
        print(f"{filename}: {status.value}")
    print(f"Saved to {result.dest_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
