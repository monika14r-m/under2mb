import io
import unittest
from unittest.mock import patch

from PIL import Image

import app as service
from app import convert_compress_image


def make_image(fmt, mode="RGB", size=(128, 96), color=None):
    image = Image.new(mode, size, color or ("red" if mode != "RGBA" else (255, 0, 0, 0)))
    buffer = io.BytesIO()
    image.save(buffer, format=fmt)
    return buffer.getvalue()


class ImageConversionTests(unittest.TestCase):
    def test_png_to_jpeg_outputs_real_jpeg(self):
        source = make_image("PNG", "RGBA", color=(20, 80, 160, 255))
        result = convert_compress_image(source, "jpeg", 2 * 1024 * 1024)
        with Image.open(io.BytesIO(result)) as output:
            self.assertEqual(output.format, "JPEG")
            self.assertEqual(output.mode, "RGB")

    def test_transparent_png_to_jpeg_uses_white_background(self):
        source = make_image("PNG", "RGBA", size=(8, 8), color=(255, 0, 0, 0))
        result = convert_compress_image(source, "jpeg", 2 * 1024 * 1024)
        with Image.open(io.BytesIO(result)) as output:
            pixel = output.convert("RGB").getpixel((4, 4))
            self.assertGreaterEqual(min(pixel), 235)

    def test_jpeg_to_png_outputs_real_png(self):
        source = make_image("JPEG")
        result = convert_compress_image(source, "png", 2 * 1024 * 1024)
        with Image.open(io.BytesIO(result)) as output:
            self.assertEqual(output.format, "PNG")

    def test_conversion_rejects_oversized_image_before_decoding(self):
        source = make_image("PNG", size=(12, 12))
        with patch.object(service, "MAX_IMAGE_PIXELS", 100), patch.object(
            Image.Image, "load", side_effect=AssertionError("pixel data must not be decoded")
        ):
            with self.assertRaisesRegex(ValueError, "100-pixel processing limit"):
                convert_compress_image(source, "jpeg", 2 * 1024 * 1024)

    def test_format_preserving_compression_rejects_oversized_image_before_decoding(self):
        source = make_image("PNG", size=(12, 12))
        with patch.object(service, "MAX_IMAGE_PIXELS", 100), patch.object(
            Image.Image, "load", side_effect=AssertionError("pixel data must not be decoded")
        ):
            with self.assertRaisesRegex(ValueError, "100-pixel processing limit"):
                service.compress_image(source, ".png")

    def test_conversion_respects_target_or_fails(self):
        source = make_image("PNG", size=(1200, 900))
        result = convert_compress_image(source, "jpeg", 2 * 1024 * 1024)
        self.assertLess(len(result), 2 * 1024 * 1024)
        with self.assertRaises(ValueError):
            convert_compress_image(source, "png", 1)

if __name__ == "__main__":
    unittest.main()
