# Under2MB

A deployable file-compression dashboard. Upload a file, attempt format-preserving compression, and download the result in its original format when the compressor can meet the 2 MB target.

## Important limitation

**No compressor can guarantee every arbitrary file will become smaller than 2 MB while preserving its format and all content.** Some files are already compressed, encrypted, or contain too much data. This app reports when the target cannot be reached rather than pretending it succeeded. The upload limit is configurable.

## Supported formats

- **Images:** JPG/JPEG, PNG, WEBP, BMP, TIFF — recompressed with Pillow while keeping the same extension/format (some formats may not get smaller).
- **PDF:** optimized/re-written with PyMuPDF.
- **Office Open XML:** DOCX, PPTX, XLSX — ZIP container repacking (usually only a small improvement; embedded media is not destructively altered).
- **Other formats:** safely rejected with a clear message until a format-specific compressor is added. Renaming or wrapping a file in ZIP/GZIP is not presented as same-format compression.

## Run locally

Python 3.11+ recommended.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload
```

Open http://127.0.0.1:8000

## Deploy to Render

1. Push this repository to GitHub.
2. In Render, choose **New → Web Service** and connect the repository.
3. Render detects `render.yaml`, or enter:
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
4. Deploy. No database or persistent disk is required.

## Configuration

- `MAX_UPLOAD_MB`: maximum upload size in MB (default `100`).
- `TARGET_BYTES`: target output size (default `2097152`, exactly 2 MiB).

## Privacy

Files are processed in memory and temporary files are not intentionally persisted. Do not deploy this public service without adding authentication, rate limiting, request-size limits at the platform, and an abuse-control strategy. Avoid uploading confidential documents to any public instance.
