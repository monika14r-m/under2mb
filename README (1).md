# Under2MB

A deployable, format-aware file-compression dashboard. Upload a supported file, attempt compression, and download the result in the same format when it can meet the configured output target.

## Supported formats

- **Images:** JPG/JPEG, PNG, WEBP, BMP, TIFF — recompressed with Pillow.
- **PDF:** rewritten and optimized with PyMuPDF.
- **Office Open XML:** DOCX, PPTX, XLSX and macro-enabled DOCM, PPTM, XLSM — ZIP repacking only; reductions may be small.
- **MP3 audio:** re-encoded using FFmpeg at progressively lower bitrates. This is **lossy compression** and may reduce audio quality.
- **Video:** MP4, MOV, M4V, MKV, WEBM and AVI — re-encoded with FFmpeg using progressively lower quality settings and frame sizes. The output keeps the same filename extension/container where supported, but video/audio quality may decrease.
- Unsupported formats are rejected instead of being renamed or wrapped as if that were format-specific compression.

## Important limitations

No compressor can guarantee every file will fit below a target size while preserving all content and quality. The app returns an explicit error when it cannot reach the target.

For MP3, the backend tries 128, 96, 64, 48, then 32 kbps. Longer audio may still exceed the target at 32 kbps.

For video, the backend tries multiple quality and resolution combinations. Some videos still cannot fit the target; large videos may take a long time or time out. Keep the original because video and audio are re-encoded lossily.

## Run locally

Python 3.11+ recommended. FFmpeg must be installed and available on `PATH` for MP3 and video compression.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload
```

Open http://127.0.0.1:8000.

### Install FFmpeg

- **Windows:** install FFmpeg and add its `bin` folder to `PATH`.
- **macOS:** `brew install ffmpeg`
- **Debian/Ubuntu:** `sudo apt-get install ffmpeg`

## Deploy to Render

1. Connect this repository as a Render Web Service.
2. Build command: `pip install -r requirements.txt`
3. Start command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
4. Ensure FFmpeg is available on the Render runtime for MP3 and video compression. The included Dockerfile installs FFmpeg, so use Docker deployment.

## Configuration

- `MAX_UPLOAD_MB`: maximum upload size in MB (default `100`).
- `TARGET_BYTES`: target output size in bytes (default `2097152`, 2 MiB).

## Privacy and deployment safety

Files are processed in memory or temporary working storage for audio transcoding; temporary audio/video files are removed when processing ends. Before making this public, add authentication, rate limiting, platform-layer upload limits, and abuse controls. Do not upload sensitive files to a public instance.
