import asyncio
import io
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import app as service


class RecordingUpload:
    def __init__(self, payload: bytes):
        self.stream = io.BytesIO(payload)
        self.read_sizes = []
        self.closed = False

    async def read(self, size: int = -1) -> bytes:
        self.read_sizes.append(size)
        return self.stream.read(size)

    async def close(self) -> None:
        self.closed = True


def test_stream_upload_to_path_uses_bounded_chunks(tmp_path):
    payload = b"a" * 2500
    upload = RecordingUpload(payload)
    destination = tmp_path / "input.mp3"

    uploaded = asyncio.run(
        service.stream_upload_to_path(upload, destination, 3000, chunk_size=1024)
    )

    assert uploaded == len(payload)
    assert destination.read_bytes() == payload
    assert upload.closed
    assert upload.read_sizes
    assert max(upload.read_sizes) == 1024


def test_stream_upload_to_path_rejects_over_limit_and_closes_upload(tmp_path):
    upload = RecordingUpload(b"123456")
    destination = tmp_path / "input.mp3"

    with pytest.raises(HTTPException) as error:
        asyncio.run(
            service.stream_upload_to_path(
                upload,
                destination,
                5,
                chunk_size=4,
                limit_detail="MP3 upload limit exceeded.",
            )
        )

    assert error.value.status_code == 413
    assert error.value.detail == "MP3 upload limit exceeded."
    assert upload.closed


def test_compress_mp3_file_runs_ffmpeg_against_disk_source(monkeypatch, tmp_path):
    source = tmp_path / "input.mp3"
    source.write_bytes(b"source MP3 bytes")
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        Path(command[-1]).write_bytes(b"encoded MP3")
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr("shutil.which", lambda _name: "/usr/bin/ffmpeg")
    monkeypatch.setattr(subprocess, "run", fake_run)

    output = service.compress_mp3_file(source, target_bytes=100)

    assert output.read_bytes() == b"encoded MP3"
    assert calls[0][0][calls[0][0].index("-i") + 1] == str(source)
    assert calls[0][1]["timeout"] == 180


def test_compress_mp3_file_fails_if_all_bitrates_miss_target(monkeypatch, tmp_path):
    source = tmp_path / "input.mp3"
    source.write_bytes(b"source MP3 bytes")
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        Path(command[-1]).write_bytes(b"12345")
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr("shutil.which", lambda _name: "/usr/bin/ffmpeg")
    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(ValueError, match="still could not reach the target"):
        service.compress_mp3_file(source, target_bytes=5)

    assert len(calls) == 5


def test_mp3_api_streams_source_and_returns_bounded_download(monkeypatch):
    monkeypatch.setattr(service, "MAX_BUFFERED_UPLOAD_BYTES", 2 * 1024 * 1024)
    payload = b"ID3" + b"a" * (600 * 1024)
    observed = {}

    def fake_compress(source: Path, target_bytes: int) -> Path:
        assert source.is_file()
        observed["source_size"] = source.stat().st_size
        observed["target_bytes"] = target_bytes
        output = source.with_name("compressed.mp3")
        output.write_bytes(b"ID3-compressed")
        return output

    monkeypatch.setattr(service, "compress_mp3_file", fake_compress)
    client = TestClient(service.app)

    response = client.post(
        "/api/compress",
        data={"target_mb": "0.5"},
        files={"file": ("voice.mp3", payload, "audio/mpeg")},
    )

    assert response.status_code == 200
    assert response.content == b"ID3-compressed"
    assert response.headers["content-type"] == "audio/mpeg"
    assert response.headers["x-output-filename"] == "voice.mp3"
    assert response.headers["x-output-size"] == str(len(response.content))
    assert 'filename="voice.mp3"' in response.headers["content-disposition"]
    assert observed == {"source_size": len(payload), "target_bytes": 512 * 1024}


def test_mp3_api_rejects_uploads_over_configured_limit(monkeypatch):
    monkeypatch.setattr(service, "MAX_BUFFERED_UPLOAD_BYTES", 1024 * 1024)
    client = TestClient(service.app)
    payload = b"a" * (1024 * 1024 + 1)

    response = client.post(
        "/api/compress",
        data={"target_mb": "2"},
        files={"file": ("large.mp3", payload, "audio/mpeg")},
    )

    assert response.status_code == 413
    assert "MP3 uploads are limited" in response.json()["detail"]


def test_mp3_under_target_skips_ffmpeg(monkeypatch):
    payload = b"ID3-small-audio"

    def unexpected_compression(*_args, **_kwargs):
        raise AssertionError("FFmpeg should not run for an MP3 already below target.")

    monkeypatch.setattr(service, "compress_mp3_file", unexpected_compression)
    client = TestClient(service.app)

    response = client.post(
        "/api/compress",
        data={"target_mb": "0.5"},
        files={"file": ("small.mp3", payload, "audio/mpeg")},
    )

    assert response.status_code == 200
    assert response.content == payload
    assert response.headers["content-type"] == "audio/mpeg"


def test_mp3_api_returns_422_when_encoded_output_cannot_meet_target(monkeypatch):
    monkeypatch.setattr(service, "MAX_BUFFERED_UPLOAD_BYTES", 2 * 1024 * 1024)

    def fail_compression(_source: Path, _target_bytes: int) -> Path:
        raise ValueError("MP3 could not reach the selected size target.")

    monkeypatch.setattr(service, "compress_mp3_file", fail_compression)
    client = TestClient(service.app)
    payload = b"ID3" + b"a" * (600 * 1024)

    response = client.post(
        "/api/compress",
        data={"target_mb": "0.5"},
        files={"file": ("voice.mp3", payload, "audio/mpeg")},
    )

    assert response.status_code == 422
    assert "could not reach the selected size target" in response.json()["detail"]
