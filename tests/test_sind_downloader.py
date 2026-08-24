from unittest.mock import patch

import pytest

from trajstats.download.sind_downloader import (
    DownloadError,
    FileFetchStatus,
    REQUIRED_FILES,
    _traffic_light_filename,
    download_sind_record,
)


class FakeResponse:
    def __init__(self, status_code=200, content=b"col_a,col_b\n1,2\n"):
        self.status_code = status_code
        self._content = content

    @property
    def ok(self):
        return 200 <= self.status_code < 400

    def iter_content(self, chunk_size=None):
        yield self._content


def test_traffic_light_filename_derivation():
    assert _traffic_light_filename("Tianjin/8_2_1") == "TrafficLight_8_2_1.csv"
    assert _traffic_light_filename("Tianjin/8_2_2") == "TrafficLight_8_2_2.csv"


def test_download_all_success(tmp_path):
    with patch("trajstats.download.sind_downloader.requests.get", return_value=FakeResponse(200)):
        result = download_sind_record("Tianjin/8_2_1", dest_dir=tmp_path)

    assert result.ok
    for filename in REQUIRED_FILES:
        assert result.statuses[filename] == FileFetchStatus.DOWNLOADED
        assert (tmp_path / "Tianjin/8_2_1" / filename).exists()


def test_download_optional_traffic_light_404_does_not_raise(tmp_path):
    def fake_get(url, timeout=None, stream=None):
        if "TrafficLight" in url:
            return FakeResponse(404)
        return FakeResponse(200)

    with patch("trajstats.download.sind_downloader.requests.get", side_effect=fake_get):
        result = download_sind_record("Tianjin/8_2_1", dest_dir=tmp_path)

    assert result.ok
    assert result.statuses["TrafficLight_8_2_1.csv"] == FileFetchStatus.NOT_FOUND
    assert not (tmp_path / "Tianjin/8_2_1" / "TrafficLight_8_2_1.csv").exists()


def test_download_missing_meta_files_does_not_raise(tmp_path):
    """Some SinD records (e.g. Chongqing/6_22_NR_1) ship only the two
    smoothed-tracks CSVs and no per-track meta files at all — this must
    not fail the download since the loader tolerates missing meta files.
    """
    def fake_get(url, timeout=None, stream=None):
        if "_tracks_meta" in url or "recording_metas" in url or "TrafficLight" in url:
            return FakeResponse(404)
        return FakeResponse(200)

    with patch("trajstats.download.sind_downloader.requests.get", side_effect=fake_get):
        result = download_sind_record("Chongqing/6_22_NR_1", dest_dir=tmp_path)

    assert result.ok
    assert result.statuses["Ped_smoothed_tracks.csv"] == FileFetchStatus.DOWNLOADED
    assert result.statuses["Veh_smoothed_tracks.csv"] == FileFetchStatus.DOWNLOADED
    assert result.statuses["Ped_tracks_meta.csv"] == FileFetchStatus.NOT_FOUND
    assert result.statuses["Veh_tracks_meta.csv"] == FileFetchStatus.NOT_FOUND
    assert result.statuses["recording_metas.csv"] == FileFetchStatus.NOT_FOUND


def test_download_required_file_404_raises(tmp_path):
    def fake_get(url, timeout=None, stream=None):
        if "Veh_smoothed_tracks" in url:
            return FakeResponse(404)
        return FakeResponse(200)

    with patch("trajstats.download.sind_downloader.requests.get", side_effect=fake_get):
        with pytest.raises(DownloadError):
            download_sind_record("Tianjin/8_2_1", dest_dir=tmp_path)


def test_download_skips_existing_file_without_overwrite(tmp_path):
    record_dir = tmp_path / "Tianjin/8_2_1"
    record_dir.mkdir(parents=True)
    existing = record_dir / "recording_metas.csv"
    existing.write_text("already,here\n1,2\n", encoding="utf-8")

    calls = []

    def fake_get(url, timeout=None, stream=None):
        calls.append(url)
        return FakeResponse(200)

    with patch("trajstats.download.sind_downloader.requests.get", side_effect=fake_get):
        result = download_sind_record("Tianjin/8_2_1", dest_dir=tmp_path, overwrite=False)

    assert result.statuses["recording_metas.csv"] == FileFetchStatus.SKIPPED_EXISTS
    assert existing.read_text(encoding="utf-8") == "already,here\n1,2\n"
    assert not any("recording_metas" in url for url in calls)
