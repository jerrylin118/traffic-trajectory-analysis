from unittest.mock import patch

import pytest

from trajstats.download.dut_downloader import (
    REQUIRED_FILE_SUFFIXES,
    download_dut_record,
)
from trajstats.download.sind_downloader import DownloadError, FileFetchStatus


class FakeResponse:
    def __init__(self, status_code=200, content=b"col_a,col_b\n1,2\n"):
        self.status_code = status_code
        self._content = content

    @property
    def ok(self):
        return 200 <= self.status_code < 400

    def iter_content(self, chunk_size=None):
        yield self._content


def test_download_all_success(tmp_path):
    with patch("trajstats.download.sind_downloader.requests.get", return_value=FakeResponse(200)):
        result = download_dut_record("intersection_01", dest_dir=tmp_path)

    assert result.ok
    for suffix in REQUIRED_FILE_SUFFIXES:
        filename = f"intersection_01{suffix}"
        assert result.statuses[filename] == FileFetchStatus.DOWNLOADED
        assert (tmp_path / "intersection_01" / filename).exists()


def test_download_required_file_404_raises(tmp_path):
    def fake_get(url, timeout=None, stream=None):
        if "traj_veh_filtered" in url:
            return FakeResponse(404)
        return FakeResponse(200)

    with patch("trajstats.download.sind_downloader.requests.get", side_effect=fake_get):
        with pytest.raises(DownloadError):
            download_dut_record("intersection_01", dest_dir=tmp_path)


def test_download_skips_existing_file_without_overwrite(tmp_path):
    record_dir = tmp_path / "intersection_01"
    record_dir.mkdir(parents=True)
    existing = record_dir / "intersection_01_traj_ped_filtered.csv"
    existing.write_text("already,here\n1,2\n", encoding="utf-8")

    calls = []

    def fake_get(url, timeout=None, stream=None):
        calls.append(url)
        return FakeResponse(200)

    with patch("trajstats.download.sind_downloader.requests.get", side_effect=fake_get):
        result = download_dut_record("intersection_01", dest_dir=tmp_path, overwrite=False)

    assert result.statuses["intersection_01_traj_ped_filtered.csv"] == FileFetchStatus.SKIPPED_EXISTS
    assert existing.read_text(encoding="utf-8") == "already,here\n1,2\n"
    assert not any("traj_ped_filtered" in url for url in calls)
