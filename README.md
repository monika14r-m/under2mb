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

## Upload safety limits

- MAX_UPLOAD_MB is the application-level limit for video uploads (default 5120 MB). Video data is streamed to temporary disk storage.
- MAX_BUFFERED_UPLOAD_MB limits image, audio, PDF, and Office uploads that are currently processed in memory (default 128 MB). This prevents a large non-video request from exhausting the server's RAM.
- Office archives are additionally limited by MAX_OFFICE_UNCOMPRESSED_MB (default 128 MB total), MAX_OFFICE_MEMBER_MB (default 64 MB per entry), and MAX_OFFICE_ENTRIES (default 10000). Members are copied in chunks, and both declared and actual expansion are checked.
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
- `TARGET_BYTES`: default target size in bytes (default 2097152, or 2 MiB).

The web UI allows targets of 500 KB, 1 MB, 2 MB, 5 MB and 10 MB.
