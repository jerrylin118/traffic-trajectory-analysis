"""Downloads SinD dataset record files without requiring git or git-lfs.

SinD's CSVs are stored via Git LFS in the GitHub repo
https://github.com/SOTIF-AVLab/SinD. GitHub serves the actual LFS-backed
file content (not the small LFS pointer text) from
`media.githubusercontent.com/media/<owner>/<repo>/<ref>/<path>`, so a plain
HTTP GET against that host is enough to fetch real CSV bytes.
"""

from __future__ import annotations

import argparse
import enum
import sys
from dataclasses import dataclass, field
from pathlib import Path

import requests

SIND_OWNER = "SOTIF-AVLab"
SIND_REPO = "SinD"
SIND_REF = "main"
BASE_URL = f"https://media.githubusercontent.com/media/{SIND_OWNER}/{SIND_REPO}/{SIND_REF}/Data"

# The actual trajectory data every record has; required for load_sind_record
# to produce anything.
REQUIRED_FILES = [
    "Ped_smoothed_tracks.csv",
    "Veh_smoothed_tracks.csv",
]

# Per-track metadata that enriches the canonical schema (ped_class,
# cross_type, signal_violation) when present, but is not present for every
# record (e.g. some non-Tianjin records ship only the two files above) —
# the loader already falls back to nulls for these, so a missing file here
# must not fail the download.
OPTIONAL_FILES = [
    "Ped_tracks_meta.csv",
    "Veh_tracks_meta.csv",
    "recording_metas.csv",
]


class FileFetchStatus(enum.Enum):
    DOWNLOADED = "downloaded"
    SKIPPED_EXISTS = "skipped_exists"
    NOT_FOUND = "not_found"
    ERROR = "error"


class DownloadError(RuntimeError):
    pass


@dataclass
class DownloadResult:
    record_path: str
    dest_dir: Path
    statuses: dict[str, FileFetchStatus] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        """True if every *required* file downloaded or already existed."""
        return all(
            self.statuses.get(name) in (FileFetchStatus.DOWNLOADED, FileFetchStatus.SKIPPED_EXISTS)
            for name in REQUIRED_FILES
        )


def _traffic_light_filename(record_path: str) -> str:
    folder_name = Path(record_path).name
    return f"TrafficLight_{folder_name}.csv"


def _fetch_one(url: str, dest_path: Path, overwrite: bool) -> FileFetchStatus:
    if dest_path.exists() and not overwrite:
        return FileFetchStatus.SKIPPED_EXISTS

    try:
        response = requests.get(url, timeout=60, stream=True)
    except requests.RequestException:
        return FileFetchStatus.ERROR

    if response.status_code == 404:
        return FileFetchStatus.NOT_FOUND
    if not response.ok:
        return FileFetchStatus.ERROR

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(dest_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=1 << 16):
            f.write(chunk)
    return FileFetchStatus.DOWNLOADED


def download_sind_record(
    record_path: str,
    dest_dir: str | Path = "data",
    overwrite: bool = False,
) -> DownloadResult:
    """Download one SinD record's CSVs into `dest_dir/record_path/`.

    `record_path` is the path under SinD's `Data/` folder, e.g.
    "Tianjin/8_2_1". Downloads the 2 required trajectory CSVs plus the
    per-track metadata files and the record-dependent
    `TrafficLight_<folder>.csv`, all of which are treated as optional: not
    every SinD record ships them (their filenames and presence vary by
    record), and the loader already tolerates their absence. A 404 (or
    other failure) for a required file is collected and raised as a single
    `DownloadError` after all files have been attempted, so the caller sees
    the complete picture rather than stopping at the first failure.
    """
    dest_dir = Path(dest_dir) / record_path
    result = DownloadResult(record_path=record_path, dest_dir=dest_dir)

    optional_files = list(OPTIONAL_FILES) + [_traffic_light_filename(record_path)]
    all_files = list(REQUIRED_FILES) + optional_files

    for filename in all_files:
        url = f"{BASE_URL}/{record_path}/{filename}"
        status = _fetch_one(url, dest_dir / filename, overwrite)
        result.statuses[filename] = status
        if status == FileFetchStatus.ERROR:
            result.errors[filename] = f"Request failed for {url}"

    missing_required = [
        name
        for name in REQUIRED_FILES
        if result.statuses.get(name) not in (FileFetchStatus.DOWNLOADED, FileFetchStatus.SKIPPED_EXISTS)
    ]
    if missing_required:
        raise DownloadError(
            f"Failed to download required SinD files for record "
            f"'{record_path}': {missing_required}. "
            f"Statuses: { {k: v.value for k, v in result.statuses.items()} }"
        )

    for filename in optional_files:
        if result.statuses.get(filename) == FileFetchStatus.NOT_FOUND:
            print(
                f"Note: {filename} not found for record '{record_path}' "
                f"(this file is optional and not present for every record).",
                file=sys.stderr,
            )

    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download a SinD dataset record's CSV files."
    )
    parser.add_argument("--record", required=True, help="e.g. Tianjin/8_2_1")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = download_sind_record(args.record, dest_dir=args.data_dir, overwrite=args.overwrite)
    except DownloadError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    for filename, status in result.statuses.items():
        print(f"{filename}: {status.value}")
    print(f"Saved to {result.dest_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
