# Under2MB

A FastAPI file compressor that attempts to reduce supported files to a chosen target size while retaining the original filename extension/container where supported.

## Supported formats

- Video: MP4, MOV, M4V, MKV, WEBM, AVI
- Audio: MP3
- Images: JPG/JPEG, PNG, WEBP, BMP, TIFF
- PDF
- Office: DOCX, DOCM, PPTX, PPTM, XLSX, XLSM

## Large video uploads

Video uploads are streamed in 8 MiB chunks to temporary disk storage instead of being read entirely into RAM. FFprobe reads the duration, and FFmpeg calculates a target bitrate from the selected size and duration. It then tries lower audio bitrates and resolutions until the output is below the target. Temporary files are deleted automatically after the request finishes.

**Important limitations**
- Video compression is lossy and may reduce visual/audio quality.
- Not every video can fit under 2 MB. Duration and complexity matter; select 5 MB or 10 MB, or use a shorter clip if compression cannot meet the target.
- Large uploads can still be blocked by the hosting provider, reverse proxy, browser connection, temporary disk capacity, or memory/CPU limits before the application sees them.
- The included Render free plan has limited CPU/RAM and is not ideal for large video processing. A configured 5 GB application limit does not guarantee the hosting platform can accept or process 5 GB requests.
- Temporary processing files are not retained after processing. Do not upload sensitive files to a public instance.

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

- `MAX_UPLOAD_MB`: application-level maximum upload size (default 5120 in Render config).
- `TARGET_BYTES`: default target size in bytes (default 2097152, or 2 MiB).

The web UI allows targets of 500 KB, 1 MB, 2 MB, 5 MB and 10 MB.
