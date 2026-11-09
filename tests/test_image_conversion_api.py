import io

from fastapi.testclient import TestClient
from PIL import Image

import app as service


client = TestClient(service.app)
TARGET_BYTES = 2 * 1024 * 1024


def make_image(fmt: str, mode: str, color, size=(24, 24)) -> bytes:
    image = Image.new(mode, size, color)
    buffer = io.BytesIO()
    image.save(buffer, format=fmt)
    return buffer.getvalue()


def post_conversion(filename: str, content: bytes, mime: str, output_format: str):
    return client.post(
        "/api/compress",
        data={"target_mb": "2", "output_format": output_format},
        files={"file": (filename, content, mime)},
    )


def assert_download_contract(response, *, filename: str, mime: str):
    assert response.status_code == 200
    assert response.headers["content-type"] == mime
    assert response.headers["x-output-filename"] == filename
    assert f'filename="{filename}"' in response.headers["content-disposition"]
    assert int(response.headers["x-output-size"]) == len(response.content)
    assert len(response.content) < TARGET_BYTES


def test_png_to_jpeg_api_returns_matching_download_and_flattens_alpha():
    source = make_image("PNG", "RGBA", (240, 20, 10, 0))

    response = post_conversion("transparent.png", source, "image/png", "jpeg")

    assert_download_contract(response, filename="transparent.jpg", mime="image/jpeg")
    with Image.open(io.BytesIO(response.content)) as result:
        assert result.format == "JPEG"
        assert result.mode == "RGB"
        # Transparent pixels are deliberately composited onto white for JPEG.
        assert min(result.getpixel((12, 12))) >= 235


def test_jpeg_to_png_api_returns_matching_download_and_real_png():
    source = make_image("JPEG", "RGB", (20, 80, 160))

    response = post_conversion("photo.jpeg", source, "image/jpeg", "png")

    assert_download_contract(response, filename="photo.png", mime="image/png")
    with Image.open(io.BytesIO(response.content)) as result:
        assert result.format == "PNG"


def test_jpg_alias_to_png_api_returns_matching_download_and_real_png():
    source = make_image("JPEG", "RGB", (120, 60, 30))

    response = post_conversion("photo.jpg", source, "image/jpeg", "png")

    assert_download_contract(response, filename="photo.png", mime="image/png")
    with Image.open(io.BytesIO(response.content)) as result:
        assert result.format == "PNG"


def test_png_output_preserves_transparency():
    image = Image.new("RGBA", (16, 16), (240, 20, 10, 0))
    image.putpixel((0, 0), (10, 80, 160, 255))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")

    response = post_conversion("alpha.png", buffer.getvalue(), "image/png", "png")

    assert_download_contract(response, filename="alpha.png", mime="image/png")
    with Image.open(io.BytesIO(response.content)) as result:
        assert result.format == "PNG"
        assert result.mode == "RGBA"
        assert result.getpixel((12, 12))[3] == 0
        assert result.getpixel((0, 0))[3] == 255


def test_conversion_target_failure_returns_clear_422_without_download(monkeypatch):
    def fail_conversion(_data, _format, _target):
        raise ValueError(
            "This image could not reach the selected size target, even after reducing quality or dimensions. "
            "Try a larger target size."
        )

    monkeypatch.setattr(service, "convert_compress_image", fail_conversion)
    source = make_image("PNG", "RGB", (20, 80, 160))

    response = client.post(
        "/api/compress",
        data={"target_mb": "0.5", "output_format": "jpeg"},
        files={"file": ("photo.png", source, "image/png")},
    )

    assert response.status_code == 422
    assert "could not reach the selected size target" in response.json()["detail"]
