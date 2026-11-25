import io

from fastapi.testclient import TestClient

import app as service


client = TestClient(service.app)


def upload(filename: str = "photo.jpg", output_format: str = "original", target_mb: str = "2"):
    return client.post(
        "/api/compress",
        data={"target_mb": target_mb, "output_format": output_format},
        files={"file": (filename, io.BytesIO(b"small test payload"), "application/octet-stream")},
    )


def test_rejects_unsupported_target_size():
    response = upload(target_mb="3")

    assert response.status_code == 400
    assert "Choose a supported target size" in response.json()["detail"]


def test_rejects_unknown_output_format():
    response = upload(output_format="gif")

    assert response.status_code == 400
    assert "Choose original format, JPG/JPEG, or PNG" in response.json()["detail"]


def test_conversion_is_restricted_to_image_uploads():
    response = upload(filename="document.pdf", output_format="jpeg")

    assert response.status_code == 400
    assert "Format conversion is currently available for images only" in response.json()["detail"]



def test_empty_upload_returns_bad_request():
    response = client.post(
        "/api/compress",
        data={"target_mb": "2"},
        files={"file": ("empty.jpg", b"", "image/jpeg")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "The uploaded file is empty."



def test_unsupported_extension_without_suffix_is_rejected():
    response = client.post(
        "/api/compress",
        data={"target_mb": "2"},
        files={"file": ("payload", b"data", "application/octet-stream")},
    )

    assert response.status_code == 415



def test_small_upload_returns_original_bytes_and_download_metadata():
    payload = b"small-file-content"
    response = client.post(
        "/api/compress",
        data={"target_mb": "2"},
        files={"file": ("note.pdf", payload, "application/pdf")},
    )

    assert response.status_code == 200
    assert response.content == payload
    assert response.headers["x-output-filename"] == "note.pdf"
    assert response.headers["x-output-size"] == str(len(payload))
    assert response.headers["cache-control"] == "no-store"



def test_path_components_are_removed_from_output_filename():
    response = client.post(
        "/api/compress",
        data={"target_mb": "2"},
        files={"file": ("../../private/note.pdf", b"small", "application/pdf")},
    )

    assert response.status_code == 200
    assert response.headers["x-output-filename"] == "note.pdf"
    assert 'filename="note.pdf"' in response.headers["content-disposition"]



def test_invalid_image_conversion_returns_unprocessable_entity():
    response = client.post(
        "/api/compress",
        data={"target_mb": "0.5", "output_format": "jpeg"},
        files={"file": ("broken.png", b"not an image", "image/png")},
    )

    assert response.status_code == 422
    assert "could not be processed" in response.json()["detail"]



def test_download_filename_sanitizes_windows_paths_and_control_chars():
    assert service.safe_download_filename("C:\\private\\note\r\n.pdf") == "note__.pdf"
    assert service.safe_download_filename("photo📷.pdf") == "photo_.pdf"
    assert service.safe_download_filename('bad"name.pdf') == "bad_name.pdf"
    assert service.safe_download_filename("  ") == "download.bin"


def test_windows_path_is_normalized_in_download_headers():
    response = client.post(
        "/api/compress",
        data={"target_mb": "2"},
        files={"file": (r"C:\Users\private\note.pdf", b"small", "application/pdf")},
    )

    assert response.status_code == 200
    assert response.headers["x-output-filename"] == "note.pdf"
    assert response.headers["content-disposition"] == 'attachment; filename="note.pdf"'


def test_non_ascii_filename_uses_ascii_safe_download_headers():
    response = client.post(
        "/api/compress",
        data={"target_mb": "2"},
        files={"file": ("photo📷.pdf", b"small", "application/pdf")},
    )

    assert response.status_code == 200
    assert response.headers["x-output-filename"] == "photo_.pdf"
    assert response.headers["content-disposition"] == 'attachment; filename="photo_.pdf"'
