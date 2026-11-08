import io
import os
import zipfile
from pathlib import Path
from typing import Optional

import fitz
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, Response
from PIL import Image, UnidentifiedImageError

app = FastAPI(title="Under2MB", docs_url=None, redoc_url=None)
TARGET_BYTES = int(os.getenv("TARGET_BYTES", str(2 * 1024 * 1024)))
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "5120"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
MAX_BUFFERED_UPLOAD_MB = int(os.getenv("MAX_BUFFERED_UPLOAD_MB", "128"))
MAX_BUFFERED_UPLOAD_BYTES = MAX_BUFFERED_UPLOAD_MB * 1024 * 1024
MAX_OFFICE_UNCOMPRESSED_MB = int(os.getenv("MAX_OFFICE_UNCOMPRESSED_MB", "128"))
MAX_OFFICE_UNCOMPRESSED_BYTES = MAX_OFFICE_UNCOMPRESSED_MB * 1024 * 1024
MAX_OFFICE_MEMBER_MB = int(os.getenv("MAX_OFFICE_MEMBER_MB", "64"))
MAX_OFFICE_MEMBER_BYTES = min(MAX_OFFICE_UNCOMPRESSED_BYTES, MAX_OFFICE_MEMBER_MB * 1024 * 1024)
MAX_OFFICE_ENTRIES = int(os.getenv("MAX_OFFICE_ENTRIES", "10000"))
OFFICE_EXTS = {".docx", ".pptx", ".xlsx", ".docm", ".pptm", ".xlsm"}
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi"}
IMAGE_FORMATS = {
    ".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG",
    ".webp": "WEBP", ".bmp": "BMP", ".tif": "TIFF", ".tiff": "TIFF",
}
SUPPORTED_EXTS = set(IMAGE_FORMATS) | OFFICE_EXTS | VIDEO_EXTS | {".mp3", ".pdf"}

INDEX = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#101114">
<title>Under2MB — File compression</title>
<style>
:root{color-scheme:dark;--bg:#101114;--panel:#191a20;--line:#30313a;--muted:#9b9da9;--text:#f5f5f7;--accent:#c7f36b;--danger:#ff8f8f}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 50% -20%,#292c31 0,transparent 55%),var(--bg);color:var(--text);font:15px/1.5 Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif}
.wrap{max-width:980px;margin:auto;padding:30px 22px 70px}.top{display:flex;align-items:center;justify-content:space-between;margin-bottom:70px}.brand{font-weight:800;letter-spacing:-.8px;font-size:20px}.brand span{color:var(--accent)}.pill{font-size:12px;border:1px solid var(--line);padding:7px 11px;border-radius:999px;color:var(--muted)}
.hero{text-align:center;margin-bottom:34px}.eyebrow{color:var(--accent);font-size:12px;letter-spacing:2px;font-weight:750}.hero h1{font-size:clamp(38px,7vw,66px);line-height:1.02;letter-spacing:-3px;margin:14px 0}.hero p{color:var(--muted);max-width:570px;margin:0 auto}
.panel{background:rgba(25,26,32,.94);border:1px solid var(--line);border-radius:22px;padding:22px;max-width:760px;margin:0 auto;box-shadow:0 22px 70px #0003}
.drop{min-height:245px;border:1.5px dashed #4c4e59;border-radius:16px;display:flex;align-items:center;justify-content:center;text-align:center;padding:26px;cursor:pointer;transition:.2s;background:#ffffff03}.drop.over{border-color:var(--accent);background:#c7f36b0b}.upload-icon{width:54px;height:54px;border-radius:17px;background:#c7f36b18;color:var(--accent);display:grid;place-items:center;margin:0 auto 14px;font-size:25px}.drop h2{font-size:18px;margin:0 0 5px}.drop p{color:var(--muted);margin:0 0 15px;font-size:13px}.btn{border:0;border-radius:11px;padding:12px 17px;background:var(--accent);color:#171a11;font-weight:800;cursor:pointer;font-size:14px}.btn:disabled{opacity:.5;cursor:not-allowed}.subtle{font-size:12px;color:var(--muted);margin-top:14px}.file-row{display:flex;align-items:center;gap:13px;padding:15px 0;border-bottom:1px solid var(--line);margin-top:6px}.file-icon{width:44px;height:48px;display:grid;place-items:center;border-radius:10px;background:#292b33;color:var(--accent);font-size:11px;font-weight:800}.file-info{flex:1;min-width:0}.file-name{font-weight:650;overflow-wrap:anywhere}.file-meta{font-size:12px;color:var(--muted)}.remove{background:transparent;color:var(--muted);border:0;cursor:pointer;font-size:19px}.actions{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:18px;flex-wrap:wrap}.status{margin-top:18px;border-radius:12px;padding:14px;background:#22242a;color:var(--muted);display:none;overflow-wrap:anywhere}.status.show{display:block}.status.ok{color:#d7ff9b;background:#25301c}.status.bad{color:#ffb2b2;background:#351f23}.progress-label{font-size:12px;color:var(--muted);text-align:center;margin-top:8px;min-height:18px}
.progress{height:4px;background:#343640;border-radius:9px;margin-top:12px;overflow:hidden;display:none}.progress span{display:block;width:35%;height:100%;background:var(--accent);animation:move 1s infinite alternate}@keyframes move{to{transform:translateX(180%)}}.features{display:grid;grid-template-columns:repeat(3,1fr);gap:13px;margin:22px auto 0;max-width:760px}.feature{border:1px solid var(--line);border-radius:15px;padding:17px;background:#ffffff03}.feature b{display:block;font-size:13px;margin:6px 0}.feature p{font-size:12px;color:var(--muted);margin:0}.foot{max-width:760px;margin:23px auto 0;color:#858793;font-size:12px;text-align:center}.foot strong{color:#c3c4cb}@media(max-width:600px){.top{margin-bottom:46px}.features{grid-template-columns:1fr}.panel{padding:13px}.hero h1{letter-spacing:-2px}.actions .btn{width:100%}}
</style>
</head>
<body><main class="wrap">
<header class="top"><div class="brand">under<span>2</span>mb<span>.</span></div><div class="pill">PRIVATE · FORMAT-AWARE</div></header>
<section class="hero"><div class="eyebrow">LESS WEIGHT. SAME FORMAT.</div><h1>Your files, <span style="color:var(--accent)">lighter.</span></h1><p>Compress supported files toward your chosen size, then download in the original file format. If a file can't reach the target safely, we'll tell you.</p></section>
<section class="panel">
<div class="drop" id="drop"><div><div class="upload-icon">↑</div><h2>Drop your file here</h2><p>or select a file from your device</p><button class="btn" id="choose" type="button">Choose file</button><div class="subtle">Videos up to MAXVIDEO_LIMIT · other files up to MAXBUFFERED_LIMIT · MP4, MOV, M4V, MKV, WEBM, AVI, MP3, PDF, JPG, PNG, WEBP, BMP, TIFF, DOCX, DOCM, PPTX, PPTM, XLSX, XLSM</div></div></div>
<div class="actions" style="margin:0 0 14px"><label for="target" style="color:var(--muted);font-size:13px">Target maximum size</label><select id="target" style="background:#22242a;color:var(--text);border:1px solid var(--line);border-radius:10px;padding:10px 12px"><option value="0.5">500 KB</option><option value="1">1 MB</option><option value="2" selected>2 MB</option><option value="5">5 MB</option><option value="10">10 MB</option></select><label for="outputFormat" style="color:var(--muted);font-size:13px">Image output</label><select id="outputFormat" style="background:#22242a;color:var(--text);border:1px solid var(--line);border-radius:10px;padding:10px 12px"><option value="original">Keep original</option><option value="jpeg">JPG / JPEG</option><option value="png">PNG</option></select></div>
<input id="file" type="file" accept=".mp3,.mp4,.mov,.m4v,.mkv,.webm,.avi,.pdf,.jpg,.jpeg,.png,.webp,.bmp,.tif,.tiff,.docx,.pptx,.xlsx,.docm,.pptm,.xlsm" hidden>
<div id="picked" style="display:none"><div class="file-row"><div class="file-icon" id="ext">FILE</div><div class="file-info"><div class="file-name" id="filename"></div><div class="file-meta" id="filesize"></div></div><button class="remove" id="remove" title="Remove file" aria-label="Remove file">×</button></div>
<div class="actions"><span class="subtle" style="margin:0">Target: under <span id="targetLabel">2 MB</span></span><button class="btn" id="compress">Compress file ↗</button></div></div>
<div class="progress" id="progress"><span></span></div><div class="progress-label" id="progressLabel" aria-live="polite"></div><div class="status" id="status" role="status" aria-live="polite"></div>
</section>
<section class="features"><div class="feature"><span>↘</span><b>Format-aware</b><p>Downloads keep the original extension and file format.</p></div><div class="feature"><span>◎</span><b>Honest results</b><p>No fake success if a file remains above the size target.</p></div><div class="feature"><span>⌁</span><b>Short-lived processing</b><p>Files use temporary processing storage and are deleted after processing.</p></div></section>
<div class="foot"><strong>Note:</strong> Not every file can be reduced below 2 MB without losing content or changing format. Office files may compress only slightly. Avoid uploading sensitive documents to a public deployment.</div>
</main>
<script>
const MAXVIDEO_MB=__MAXVIDEO_MB__;
const MAXBUFFERED_MB=__MAXBUFFERED_MB__;
const VIDEO_EXTS=new Set(['.mp4','.mov','.m4v','.mkv','.webm','.avi']);
function uploadLimitFor(file){
  const dot=file.name.lastIndexOf('.');
  const ext=dot>=0?file.name.slice(dot).toLowerCase():'';
  const isVideo=VIDEO_EXTS.has(ext);
  const mb=isVideo?MAXVIDEO_MB:MAXBUFFERED_MB;
  const label=mb>=1024?(mb/1024)+' GB':mb+' MB';
  return {bytes:mb*1048576,label};
}
const fileInput=document.querySelector('#file'), drop=document.querySelector('#drop'), picked=document.querySelector('#picked'), statusBox=document.querySelector('#status'), progress=document.querySelector('#progress'), targetInput=document.querySelector('#target');
const targetLabel=document.querySelector('#targetLabel'), outputFormatInput=document.querySelector('#outputFormat');
targetInput.addEventListener('change',()=>{targetLabel.textContent=targetInput.value==='0.5'?'500 KB':targetInput.value+' MB'});
let selected=null;
function fmt(n){if(n<1024)return n+' B';if(n<1048576)return (n/1024).toFixed(1)+' KB';return (n/1048576).toFixed(2)+' MB'}
function showStatus(msg,kind=''){statusBox.className='status show '+kind;statusBox.textContent=msg}
function setFile(f){if(!f)return;selected=f;document.querySelector('#filename').textContent=f.name;document.querySelector('#filesize').textContent=fmt(f.size);document.querySelector('#ext').textContent=(f.name.split('.').pop()||'FILE').slice(0,5).toUpperCase();picked.style.display='block';statusBox.className='status';const limit=uploadLimitFor(f);if(f.size>limit.bytes)showStatus(`This file is larger than the ${limit.label} upload limit for this format.`,'bad')}
function clearFile(){selected=null;fileInput.value='';picked.style.display='none';statusBox.className='status';progress.style.display='none'}
document.querySelector('#choose').onclick=()=>fileInput.click();drop.onclick=e=>{if(e.target.id!=='choose')fileInput.click()};fileInput.onchange=()=>setFile(fileInput.files[0]);document.querySelector('#remove').onclick=clearFile;
for(const ev of ['dragenter','dragover'])drop.addEventListener(ev,e=>{e.preventDefault();drop.classList.add('over')});for(const ev of ['dragleave','drop'])drop.addEventListener(ev,e=>{e.preventDefault();drop.classList.remove('over')});drop.addEventListener('drop',e=>setFile(e.dataTransfer.files[0]));
document.querySelector('#compress').onclick=()=>{
if(!selected)return;
const uploadLimit=uploadLimitFor(selected);
if(selected.size>uploadLimit.bytes){showStatus(`This file exceeds the ${uploadLimit.label} upload limit for this format.`,'bad');return}
const btn=document.querySelector('#compress'),label=document.querySelector('#progressLabel');
btn.disabled=true;progress.style.display='block';label.textContent='Preparing upload…';showStatus('Uploading your file…');
const fd=new FormData();fd.append('file',selected);fd.append('target_mb',targetInput.value);fd.append('output_format',outputFormatInput.value);
const xhr=new XMLHttpRequest();xhr.open('POST','/api/compress');xhr.responseType='blob';
xhr.upload.onprogress=e=>{if(e.lengthComputable){const pct=Math.round(e.loaded/e.total*100);label.textContent=pct<100?`Uploading… ${pct}%`:'Upload complete — compressing on the server…';const bar=progress.querySelector('span');if(bar)bar.style.width=pct+'%'}};
xhr.upload.onload=()=>{label.textContent='Upload complete — compressing on the server…';showStatus('Your file is uploaded. Compression is in progress…')};
xhr.onload=async()=>{
try{
if(xhr.status<200||xhr.status>=300){
let message='Compression failed.';
try{const raw=await xhr.response.text();const parsed=JSON.parse(raw);message=parsed.detail||message}catch{}
throw new Error(message)
}
const blob=xhr.response;const outName=xhr.getResponseHeader('X-Output-Filename')||selected.name;const size=Number(xhr.getResponseHeader('X-Output-Size')||blob.size);const targetBytes=Number(targetInput.value)*1048576;
if(size>=targetBytes)throw new Error(`The compressed result is ${fmt(size)}, still above the selected ${targetLabel.textContent} target. No download was produced.`);
const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=outName;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
showStatus(`Done — ${fmt(selected.size)} → ${fmt(size)}. Your download is ready.`,'ok');label.textContent='Compression complete.'
}catch(e){showStatus(e.message||'Something went wrong.','bad');label.textContent=''}
finally{btn.disabled=false;progress.style.display='none'}
};
xhr.onerror=()=>{showStatus('Network error during upload or compression. Please retry.','bad');btn.disabled=false;progress.style.display='none';label.textContent=''};
xhr.onabort=()=>{showStatus('Upload was cancelled.','bad');btn.disabled=false;progress.style.display='none';label.textContent=''};
xhr.send(fd);
};
</script></body></html>""".replace("MAXMB_VALUE", "__MAXMB__").replace("MAXMB MB", "__MAXMB__ MB")

@app.get("/health")
def health():
    """Lightweight health check for the hosting platform."""
    return {"status": "ok"}


@app.get("/api/capabilities")
def capabilities():
    """Expose supported formats and configured upload/target limits to clients."""
    return {
        "formats": {
            "images": sorted(IMAGE_FORMATS.keys()),
            "audio": [".mp3"],
            "video": sorted(VIDEO_EXTS),
            "documents": [".pdf"],
            "office": sorted(OFFICE_EXTS),
        },
        "max_upload_mb": MAX_UPLOAD_MB,
        "max_video_upload_mb": MAX_UPLOAD_MB,
        "max_buffered_upload_mb": min(MAX_UPLOAD_MB, MAX_BUFFERED_UPLOAD_MB),
        "target_sizes_mb": [0.5, 1, 2, 5, 10],
        "video_requires_ffmpeg": True,
    }


@app.get("/", response_class=HTMLResponse)
def home():
    video_limit_label = f"{MAX_UPLOAD_MB / 1024:g} GB" if MAX_UPLOAD_MB >= 1024 else f"{MAX_UPLOAD_MB} MB"
    buffered_limit_mb = min(MAX_UPLOAD_MB, MAX_BUFFERED_UPLOAD_MB)
    buffered_limit_label = f"{buffered_limit_mb / 1024:g} GB" if buffered_limit_mb >= 1024 else f"{buffered_limit_mb} MB"
    page = (
        INDEX.replace("__MAXVIDEO_MB__", str(MAX_UPLOAD_MB))
        .replace("__MAXBUFFERED_MB__", str(buffered_limit_mb))
        .replace("MAXVIDEO_LIMIT", video_limit_label)
        .replace("MAXBUFFERED_LIMIT", buffered_limit_label)
    )
    return HTMLResponse(page)

def compress_image(data: bytes, ext: str) -> bytes:
    with Image.open(io.BytesIO(data)) as img:
        fmt = IMAGE_FORMATS[ext]
        output = io.BytesIO()
        if fmt == "JPEG":
            if img.mode not in ("RGB", "L"):
                if "A" in img.getbands():
                    bg = Image.new("RGB", img.size, "white")
                    bg.paste(img, mask=img.getchannel("A"))
                    img = bg
                else:
                    img = img.convert("RGB")
            img.save(output, format=fmt, quality=82, optimize=True, progressive=True)
        elif fmt == "PNG":
            img.save(output, format=fmt, optimize=True, compress_level=9)
        elif fmt == "WEBP":
            img.save(output, format=fmt, quality=82, method=6)
        elif fmt == "BMP":
            img.save(output, format=fmt)
        elif fmt == "TIFF":
            img.save(output, format=fmt, compression="tiff_lzw")
        return output.getvalue()


def convert_compress_image(data: bytes, output_format: str, target_bytes: int) -> bytes:
    """Convert an image to JPEG or PNG and reduce dimensions/quality to meet a size target."""
    fmt = "JPEG" if output_format == "jpeg" else "PNG"
    with Image.open(io.BytesIO(data)) as source:
        source.load()
        image = source.copy()
    if fmt == "JPEG" and image.mode not in ("RGB", "L"):
        # JPEG has no alpha channel; composite transparent pixels onto white.
        if "A" in image.getbands() or "transparency" in image.info:
            rgba = image.convert("RGBA")
            background = Image.new("RGB", rgba.size, "white")
            background.paste(rgba, mask=rgba.getchannel("A"))
            image = background
        else:
            image = image.convert("RGB")
    elif fmt == "PNG" and image.mode not in ("1", "L", "LA", "P", "RGB", "RGBA", "I", "I;16", "F"):
        image = image.convert("RGBA" if "A" in image.getbands() else "RGB")

    # Try sensible quality levels first; progressively downscale only if needed.
    scales = [1.0, 0.85, 0.70, 0.55, 0.40, 0.30]
    qualities = [88, 80, 72, 64, 55, 45, 35] if fmt == "JPEG" else [None]
    for scale in scales:
        candidate = image
        if scale < 1:
            dimensions = (max(1, int(image.width * scale)), max(1, int(image.height * scale)))
            candidate = image.resize(dimensions, Image.Resampling.LANCZOS)
        for quality in qualities:
            output = io.BytesIO()
            if fmt == "JPEG":
                candidate.save(output, format="JPEG", quality=quality, optimize=True, progressive=True)
            else:
                candidate.save(output, format="PNG", optimize=True, compress_level=9)
            result = output.getvalue()
            if len(result) < target_bytes:
                return result
    raise ValueError("This image could not reach the selected size target, even after reducing quality or dimensions. Try a larger target size.")


def compress_mp3(data: bytes, target_bytes: int) -> bytes:
    """Re-encode MP3 audio at progressively lower bitrates."""
    import shutil
    import subprocess
    import tempfile

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("MP3 compression requires FFmpeg, but FFmpeg is not installed on this server.")

    bitrates = ["128k", "96k", "64k", "48k", "32k"]
    with tempfile.TemporaryDirectory(prefix="under2mb-") as tmp:
        source = Path(tmp) / "input.mp3"
        source.write_bytes(data)
        last_error = ""
        for bitrate in bitrates:
            output = Path(tmp) / f"output-{bitrate}.mp3"
            command = [
                ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                "-i", str(source), "-vn", "-codec:a", "libmp3lame",
                "-b:a", bitrate, "-map_metadata", "0", str(output),
            ]
            try:
                run = subprocess.run(command, capture_output=True, text=True, timeout=180, check=False)
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError("MP3 compression timed out. Try a shorter audio file.") from exc
            if run.returncode != 0 or not output.exists():
                last_error = (run.stderr or "FFmpeg could not decode this MP3.").strip()[-500:]
                continue
            result = output.read_bytes()
            if len(result) < target_bytes:
                return result
        if last_error:
            raise RuntimeError("FFmpeg could not process this MP3: " + last_error)
        raise ValueError("MP3 was re-encoded at 128, 96, 64, 48 and 32 kbps but still could not reach the target size.")



def compress_video_file(source: Path, output: Path, ext: str, target_bytes: int) -> Path:
    """
    Compress a video from disk instead of loading the source into RAM.
    Bitrate is calculated from duration and target size, then reduced if necessary.
    This is much more suitable for large uploads than repeatedly trying CRF settings.
    """
    import json
    import shutil
    import subprocess

    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise RuntimeError("Video compression requires FFmpeg and FFprobe on the server.")

    probe = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "json", str(source)],
        capture_output=True, text=True, timeout=120, check=False
    )
    if probe.returncode != 0:
        detail = (probe.stderr or "The video metadata could not be read.").strip()[-400:]
        raise RuntimeError("Could not inspect this video: " + detail)
    try:
        duration = float(json.loads(probe.stdout)["format"]["duration"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("The video duration could not be determined.") from exc
    if not duration or duration <= 0:
        raise ValueError("The video has no valid duration.")

    # Keep room for container overhead and variable bitrate peaks.
    total_budget_bps = max(24000, int((target_bytes * 8 * 0.88) / duration))
    if ext == ".webm":
        video_codec, audio_codec = "libvpx-vp9", "libopus"
    elif ext == ".avi":
        video_codec, audio_codec = "mpeg4", "libmp3lame"
    else:
        video_codec, audio_codec = "libx264", "aac"

    # Lower audio rate first, then scale down if the duration makes the target tight.
    audio_rates = [32000, 24000, 16000, 0]
    max_heights = [720, 480, 360, 240, 144]
    last_error = ""

    for audio_bps in audio_rates:
        video_bps = total_budget_bps - audio_bps
        if video_bps < 8000:
            continue
        for max_height in max_heights:
            vf = (
                f"scale='trunc(iw*min(1,{max_height}/ih)/2)*2':"
                f"'trunc(ih*min(1,{max_height}/ih)/2)*2'"
            )
            command = [
                ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                "-i", str(source), "-map", "0:v:0", "-map", "0:a:0?",
                "-vf", vf, "-c:v", video_codec, "-b:v", str(video_bps),
                "-maxrate", str(max(video_bps, 8000)), "-bufsize", str(max(video_bps * 2, 16000)),
                "-threads", "2",
            ]
            if ext == ".webm":
                command += ["-deadline", "realtime", "-cpu-used", "6", "-row-mt", "1"]
            elif ext == ".avi":
                command += ["-qmin", "2", "-qmax", "31"]
            else:
                command += ["-preset", "veryfast", "-pix_fmt", "yuv420p"]
            if audio_bps:
                command += ["-c:a", audio_codec, "-b:a", str(audio_bps)]
            else:
                command += ["-an"]
            command += ["-map_metadata", "0"]
            if ext in {".mp4", ".m4v", ".mov"}:
                command += ["-movflags", "+faststart"]
            command.append(str(output))
            try:
                result = subprocess.run(
                    command, capture_output=True, text=True, timeout=1800, check=False
                )
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError(
                    "Video compression exceeded the 30-minute processing limit. "
                    "Try a shorter video or choose a larger target size."
                ) from exc
            if result.returncode != 0 or not output.exists() or output.stat().st_size == 0:
                last_error = (result.stderr or "FFmpeg could not encode this video.").strip()[-500:]
                continue
            if output.stat().st_size < target_bytes:
                return output
            output.unlink(missing_ok=True)

    if last_error:
        raise RuntimeError("FFmpeg could not process this video: " + last_error)
    raise ValueError(
        "This video is too long or complex to fit under the selected size target. "
        "Choose a larger target (5 or 10 MB), or use a shorter clip. "
        "A 2 MB target is not realistic for every video, especially long clips."
    )

def compress_pdf(data: bytes) -> bytes:
    doc = fitz.open(stream=data, filetype="pdf")
    try:
        out = doc.tobytes(garbage=4, deflate=True, clean=True, deflate_images=True, deflate_fonts=True)
    finally:
        doc.close()
    return out

def repack_office(data: bytes) -> bytes:
    """Repack an Office ZIP while bounding archive expansion and entry count."""
    src = io.BytesIO(data)
    dest = io.BytesIO()
    with zipfile.ZipFile(src, "r") as zin, zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zout:
        entries = zin.infolist()
        if len(entries) > MAX_OFFICE_ENTRIES:
            raise ValueError(f"Office archive contains too many entries (limit: {MAX_OFFICE_ENTRIES}).")

        declared_total = 0
        actual_total = 0
        for item in entries:
            if item.flag_bits & 0x1:
                raise ValueError("Encrypted Office archives are not supported.")
            if item.file_size > MAX_OFFICE_MEMBER_BYTES:
                raise ValueError(
                    f"An Office archive entry exceeds the {MAX_OFFICE_MEMBER_MB} MB per-entry limit."
                )
            declared_total += item.file_size
            if declared_total > MAX_OFFICE_UNCOMPRESSED_BYTES:
                raise ValueError(
                    f"Office archive expands beyond the {MAX_OFFICE_UNCOMPRESSED_MB} MB uncompressed-size limit."
                )

            # Stream each member into the output archive. Do not call zin.read(),
            # which would allocate the full uncompressed member in memory.
            info = zipfile.ZipInfo(item.filename, date_time=item.date_time)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = item.external_attr
            info.create_system = item.create_system
            member_actual = 0
            with zin.open(item, "r") as source, zout.open(info, "w") as target:
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    member_actual += len(chunk)
                    actual_total += len(chunk)
                    if member_actual > MAX_OFFICE_MEMBER_BYTES:
                        raise ValueError(
                            f"An Office archive entry exceeds the {MAX_OFFICE_MEMBER_MB} MB per-entry limit."
                        )
                    if actual_total > MAX_OFFICE_UNCOMPRESSED_BYTES:
                        raise ValueError(
                            f"Office archive expands beyond the {MAX_OFFICE_UNCOMPRESSED_MB} MB uncompressed-size limit."
                        )
                    target.write(chunk)
            if member_actual != item.file_size:
                raise ValueError("Office archive entry size does not match its metadata.")
    return dest.getvalue()

@app.post("/api/compress")
async def compress(file: UploadFile = File(...), target_mb: float = Form(2.0), output_format: str = Form("original")):
    allowed_targets = {0.5, 1.0, 2.0, 5.0, 10.0}
    if target_mb not in allowed_targets:
        raise HTTPException(400, "Choose a supported target size: 500 KB, 1 MB, 2 MB, 5 MB, or 10 MB.")
    target_bytes = int(target_mb * 1024 * 1024)
    if output_format not in {"original", "jpeg", "png"}:
        raise HTTPException(400, "Choose original format, JPG/JPEG, or PNG.")
    name = Path(file.filename or "upload.bin").name
    ext = Path(name).suffix.lower()
    input_ext = ext
    if output_format != "original" and ext not in IMAGE_FORMATS:
        raise HTTPException(400, "Format conversion is currently available for images only.")
    if output_format == "jpeg":
        ext = ".jpg"
        name = str(Path(name).with_suffix(".jpg"))
    elif output_format == "png":
        ext = ".png"
        name = str(Path(name).with_suffix(".png"))
    if ext not in SUPPORTED_EXTS:
        await file.close()
        raise HTTPException(415, f"Format {ext or '(no extension)'} is not supported for format-preserving compression yet.")

    # Large videos are streamed to temporary disk storage, not buffered in RAM.
    if ext in VIDEO_EXTS:
        import tempfile
        with tempfile.TemporaryDirectory(prefix="under2mb-upload-") as tmp:
            source = Path(tmp) / ("input" + ext)
            output = Path(tmp) / ("compressed" + ext)
            uploaded = 0
            with source.open("wb") as destination:
                while True:
                    chunk = await file.read(8 * 1024 * 1024)
                    if not chunk:
                        break
                    uploaded += len(chunk)
                    if uploaded > MAX_UPLOAD_BYTES:
                        await file.close()
                        raise HTTPException(413, f"File exceeds the {MAX_UPLOAD_MB} MB video upload limit.")
                    destination.write(chunk)
            await file.close()
            if uploaded == 0:
                raise HTTPException(400, "The uploaded file is empty.")
            if uploaded < target_bytes:
                out = source.read_bytes()
            else:
                try:
                    compress_video_file(source, output, ext, target_bytes)
                    out = output.read_bytes()
                except ValueError as exc:
                    raise HTTPException(422, str(exc)) from exc
                except RuntimeError as exc:
                    raise HTTPException(503, str(exc)) from exc

            if len(out) >= target_bytes:
                target_label = "500 KB" if target_mb == 0.5 else f"{target_mb:g} MB"
                raise HTTPException(422, f"Compressed video is {len(out) / 1048576:.2f} MB, still above the {target_label} target.")
            media = {
                ".mp4": "video/mp4", ".m4v": "video/x-m4v", ".mov": "video/quicktime",
                ".mkv": "video/x-matroska", ".webm": "video/webm", ".avi": "video/x-msvideo",
            }.get(ext, "application/octet-stream")
            safe_name = name.replace('"', "")
            return Response(
                content=out, media_type=media,
                headers={
                    "X-Output-Filename": name,
                    "X-Output-Size": str(len(out)),
                    "Content-Disposition": f'attachment; filename="{safe_name}"',
                    "Cache-Control": "no-store",
                }
            )

    # Non-video formats are processed in memory, so enforce a separate bound.
    buffered_limit_bytes = min(MAX_UPLOAD_BYTES, MAX_BUFFERED_UPLOAD_BYTES)
    buffered_limit_mb = buffered_limit_bytes // (1024 * 1024)
    data = await file.read(buffered_limit_bytes + 1)
    await file.close()
    if not data:
        raise HTTPException(400, "The uploaded file is empty.")
    if len(data) > buffered_limit_bytes:
        raise HTTPException(
            413,
            f"Non-video files are limited to {buffered_limit_mb} MB because they are processed in memory. "
            f"Video uploads can use the {MAX_UPLOAD_MB} MB video limit.",
        )
    if input_ext in IMAGE_FORMATS and output_format != "original":
        try:
            out = convert_compress_image(data, output_format, target_bytes)
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise HTTPException(422, str(exc) if isinstance(exc, ValueError) else "This image could not be processed. The file may be damaged or unsupported.") from exc
    elif len(data) < target_bytes:
        # Return unchanged data if already under target, preserving original format exactly.
        out = data
    elif input_ext in IMAGE_FORMATS:
        try:
            out = compress_image(data, input_ext)
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise HTTPException(422, "This image could not be processed. The file may be damaged or unsupported.") from exc
    elif ext == ".mp3":
        try:
            out = compress_mp3(data, target_bytes)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(503, str(exc)) from exc
    elif ext in VIDEO_EXTS:
        try:
            out = compress_video(data, ext, target_bytes)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(503, str(exc)) from exc
    elif ext == ".pdf":
        try:
            out = compress_pdf(data)
        except Exception as exc:
            raise HTTPException(422, "This PDF could not be optimized. It may be damaged, encrypted, or unsupported.") from exc
    elif ext in OFFICE_EXTS:
        try:
            out = repack_office(data)
        except ValueError as exc:
            raise HTTPException(413, str(exc)) from exc
        except (zipfile.BadZipFile, KeyError, OSError, RuntimeError) as exc:
            raise HTTPException(422, "This Office file is invalid or damaged.") from exc
    else:
        raise HTTPException(415, f"Format {ext or '(no extension)'} is not supported for format-preserving compression yet.")
    if len(out) >= target_bytes:
        target_label = "500 KB" if target_mb == 0.5 else f"{target_mb:g} MB"
        raise HTTPException(422, f"Best-effort compression produced {len(out) / 1048576:.2f} MB, which is still not under the selected {target_label} target. No file was returned.")
    headers = {
        "X-Output-Filename": name,
        "X-Output-Size": str(len(out)),
        "Content-Disposition": f'attachment; filename="{name.replace(chr(34), "")}"',
        "Cache-Control": "no-store",
    }
    media = {
        ".pdf": "application/pdf", ".mp3": "audio/mpeg", ".mp4": "video/mp4", ".m4v": "video/x-m4v",
        ".mov": "video/quicktime", ".mkv": "video/x-matroska", ".webm": "video/webm", ".avi": "video/x-msvideo",
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".webp": "image/webp", ".bmp": "image/bmp",
        ".tif": "image/tiff", ".tiff": "image/tiff",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }.get(ext, "application/octet-stream")
    return Response(content=out, media_type=media, headers=headers)