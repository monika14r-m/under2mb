from io import BytesIO
import zipfile

import pytest
from fastapi.testclient import TestClient

import app as service


def make_archive(entries):
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in entries:
            archive.writestr(name, payload)
    return buffer.getvalue()


def test_repack_office_preserves_member_contents():
    source = make_archive([
        ("[Content_Types].xml", b"<Types/>"),
        ("word/document.xml", b"<document>hello</document>"),
    ])

    result = service.repack_office(source)

    with zipfile.ZipFile(BytesIO(result)) as archive:
        assert archive.read("[Content_Types].xml") == b"<Types/>"
        assert archive.read("word/document.xml") == b"<document>hello</document>"
        assert archive.getinfo("word/document.xml").compress_type == zipfile.ZIP_DEFLATED


def test_repack_office_rejects_too_many_entries(monkeypatch):
    monkeypatch.setattr(service, "MAX_OFFICE_ENTRIES", 1)
    source = make_archive([("one.xml", b"1"), ("two.xml", b"2")])

    with pytest.raises(ValueError, match="too many entries"):
        service.repack_office(source)


def test_repack_office_rejects_total_uncompressed_size(monkeypatch):
    monkeypatch.setattr(service, "MAX_OFFICE_MEMBER_BYTES", 32)
    monkeypatch.setattr(service, "MAX_OFFICE_UNCOMPRESSED_BYTES", 8)
    source = make_archive([("word/document.xml", b"x" * 9)])

    with pytest.raises(ValueError, match="uncompressed-size limit"):
        service.repack_office(source)


def test_repack_office_rejects_oversized_member(monkeypatch):
    monkeypatch.setattr(service, "MAX_OFFICE_MEMBER_BYTES", 8)
    monkeypatch.setattr(service, "MAX_OFFICE_MEMBER_MB", 1)
    monkeypatch.setattr(service, "MAX_OFFICE_UNCOMPRESSED_BYTES", 32)
    source = make_archive([("word/document.xml", b"x" * 9)])

    with pytest.raises(ValueError, match="per-entry limit"):
        service.repack_office(source)


def test_non_video_uploads_obey_memory_limit(monkeypatch):
    monkeypatch.setattr(service, "MAX_UPLOAD_BYTES", 1024 * 1024)
    monkeypatch.setattr(service, "MAX_BUFFERED_UPLOAD_BYTES", 4)
    monkeypatch.setattr(service, "MAX_BUFFERED_UPLOAD_MB", 1)
    client = TestClient(service.app)

    response = client.post(
        "/api/compress",
        data={"target_mb": "2"},
        files={"file": ("sample.pdf", b"12345", "application/pdf")},
    )

    assert response.status_code == 413
    assert "processed in memory" in response.json()["detail"]


def test_unsupported_extension_is_rejected():
    client = TestClient(service.app)

    response = client.post(
        "/api/compress",
        data={"target_mb": "2"},
        files={"file": ("payload.zip", b"ignored", "application/zip")},
    )

    assert response.status_code == 415


def test_capabilities_reports_video_and_buffered_limits():
    client = TestClient(service.app)

    response = client.get("/api/capabilities")

    assert response.status_code == 200
    payload = response.json()
    assert payload["max_video_upload_mb"] == service.MAX_UPLOAD_MB
    assert payload["max_buffered_upload_mb"] == min(service.MAX_UPLOAD_MB, service.MAX_BUFFERED_UPLOAD_MB)
