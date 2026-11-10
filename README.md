# Under2MB

A FastAPI file compressor that attempts to reduce supported files to a chosen target size while retaining the original filename extension/container where supported.

## Supported formats

- Video: MP4, MOV, M4V, MKV, WEBM, AVI
- Audio: MP3
- Images: JPG/JPEG, PNG, WEBP, BMP, TIFF
- PDF
- Office: DOCX, DOCM, PPTX, PPTM, XLSX, XLSM

## Features

- Live upload progress in the browser, followed by a separate server-side compression status.
- Health endpoint at `/health` for deployment health checks.
- Capabilities endpoint at `/api/capabilities` listing supported formats, target sizes, and configured upload limit.
- Large video uploads are streamed to temporary disk storage in 8 MiB chunks rather than loaded into RAM.
- Non-video uploads have a separate memory-aware size limit; Office ZIP archives are protected against excessive expansion and entry counts.

## Runtime architecture and deployment

The Render service defined in `render.yaml` builds `Dockerfile`, whose command starts `uvicorn app:app`. That means the Render upload interface is the FastAPI root route in `app.py`, which serves the embedded `INDEX` page and sends conversions to the same file's `/api/compress` endpoint.

The repository also contains a separate browser-only interface in root `index.html` with `main.js` and `imageCompressor.js`. Those files are not mounted or served by the Render FastAPI container. The similarly named `app (3).py` is not referenced by the Docker command. Keep changes to the Render upload/conversion flow in `app.py` and its tests rather than maintaining a second implementation in these separate entry points.

The automated test workflow is `.github/workflows/tests.yml`. The root-level `deploy.yml` is outside GitHub Actions' required `.github/workflows/` directory and is not an Actions workflow.

## Upload safety limits

- MAX_UPLOAD_MB is the application-level limit for video uploads (default 5120 MB). Video data is streamed to temporary disk storage.
- MAX_BUFFERED_UPLOAD_MB limits image, audio, PDF, and Office uploads that are currently processed in memory (default 128 MB). This prevents a large non-video request from exhausting the server's RAM.
- Office archives are additionally limited by MAX_OFFICE_UNCOMPRESSED_MB (default 128 MB total), MAX_OFFICE_MEMBER_MB (default 64 MB per entry), and MAX_OFFICE_ENTRIES (default 10000). Members are copied in chunks, and both declared and actual expansion are checked.
- Image decoding is limited by MAX_IMAGE_PIXELS (default 20,000,000 pixels). The app checks dimensions before loading pixel data and returns HTTP 422 for larger images that require processing; resize them before retrying.
- These are application limits; hosting-provider request, disk, memory, and timeout limits still apply.

## Large video uploads

Video uploads are streamed in 8 MiB chunks to temporary disk storage instead of being read entirely into RAM. FFprobe reads the duration, and FFmpeg calculates a target bitrate from the selected size and duration. It then tries lower audio bitrates and resolutions until the output is below the target. Temporary files are deleted automatically after the request finishes.

**Important limitations**
- Video compression is lossy and may reduce visual/audio quality.
- Not every video can fit under 2 MB. Duration and complexity matter; select 5 MB or 10 MB, or use a shorter clip if compression cannot meet the target.
- Large uploads can still be blocked by the hosting provider, reverse proxy, browser connection, temporary disk capacity, or memory/CPU limits before the application sees them.
- The included Render free plan has limited CPU/RAM and is not ideal for large video processing. A configured 5 GB application limit does not guarantee the hosting platform can accept or process 5 GB requests.
- Temporary processing files are not retained after processing. Do not upload sensitive files to a public instance.
- Upload progress measures transfer to the server; it does not estimate encoding progress. Server-side video encoding can take additional time.

## Run locally

Requires Python 3.11+ and FFmpeg/FFprobe installed on the system.

```bash
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 8000
```

For Docker:

```bash
docker build -t under2mb .
docker run --rm -p 8000:8000 -e MAX_UPLOAD_MB=5120 under2mb
```

## Configuration

- `MAX_UPLOAD_MB`: application-level video upload size limit (default 5120 in Render config).
- `MAX_BUFFERED_UPLOAD_MB`: maximum upload size for non-video formats processed in memory (default 128).
- `MAX_OFFICE_UNCOMPRESSED_MB`, `MAX_OFFICE_MEMBER_MB`, `MAX_OFFICE_ENTRIES`: Office archive expansion and entry-count safeguards (defaults 128 MB, 64 MB, and 10000).
- `MAX_IMAGE_PIXELS`: maximum decoded image pixel count for compression/conversion (default 20,000,000).
- `TARGET_BYTES`: default target size in bytes (default 2097152, or 2 MiB).

The web UI allows targets of 500 KB, 1 MB, 2 MB, 5 MB and 10 MB.

## Image format conversion

The Render web compressor supports optional image conversion in addition to format-preserving compression:

- PNG to JPG/JPEG (transparent pixels are composited onto a white background because JPEG does not support transparency).
- JPG/JPEG to PNG (the output is a real PNG image, not a renamed JPEG).
- Keep the original image format.

Choose the output format and target size in the Render web interface. Conversion is performed by Pillow, and the resulting file is checked against the selected target before download. JPEG conversion can reduce quality; PNG conversion preserves pixel values and transparency but may need dimension reduction to fit a strict size target. Not every image can fit below 2 MB without significant quality or dimension changes, so the app reports a clear error rather than returning an oversized file.

API-level regression tests verify the actual downloaded image encoding, extension, MIME type, reported byte count, transparency handling, and the 422 failure path when the target cannot be met.
