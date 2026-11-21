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
