import io
import os
import zipfile
from pathlib import Path
from typing import Optional

import fitz
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, Response
from PIL import Image, UnidentifiedImageError

app = FastAPI(title="Under2MB", docs_url=None, redoc_url=None)
TARGET_BYTES = int(os.getenv("TARGET_BYTES", str(2 * 1024 * 1024)))
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "100"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
OFFICE_EXTS = {".docx", ".pptx", ".xlsx", ".docm", ".pptm", ".xlsm"}
IMAGE_FORMATS = {
    ".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG",
    ".webp": "WEBP", ".bmp": "BMP", ".tif": "TIFF", ".tiff": "TIFF",
}

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
.drop{min-height:245px;border:1.5px dashed #4c4e59;border-radius:16px;display:flex;align-items:center;justify-content:center;text-align:center;padding:26px;cursor:pointer;transition:.2s;background:#ffffff03}.drop.over{border-color:var(--accent);background:#c7f36b0b}.upload-icon{width:54px;height:54px;border-radius:17px;background:#c7f36b18;color:var(--accent);display:grid;place-items:center;margin:0 auto 14px;font-size:25px}.drop h2{font-size:18px;margin:0 0 5px}.drop p{color:var(--muted);margin:0 0 15px;font-size:13px}.btn{border:0;border-radius:11px;padding:12px 17px;background:var(--accent);color:#171a11;font-weight:800;cursor:pointer;font-size:14px}.btn:disabled{opacity:.5;cursor:not-allowed}.subtle{font-size:12px;color:var(--muted);margin-top:14px}.file-row{display:flex;align-items:center;gap:13px;padding:15px 0;border-bottom:1px solid var(--line);margin-top:6px}.file-icon{width:44px;height:48px;display:grid;place-items:center;border-radius:10px;background:#292b33;color:var(--accent);font-size:11px;font-weight:800}.file-info{flex:1;min-width:0}.file-name{font-weight:650;overflow-wrap:anywhere}.file-meta{font-size:12px;color:var(--muted)}.remove{background:transparent;color:var(--muted);border:0;cursor:pointer;font-size:19px}.actions{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:18px;flex-wrap:wrap}.status{margin-top:18px;border-radius:12px;padding:14px;background:#22242a;color:var(--muted);display:none;overflow-wrap:anywhere}.status.show{display:block}.status.ok{color:#d7ff9b;background:#25301c}.status.bad{color:#ffb2b2;background:#351f23}.progress{height:4px;background:#343640;border-radius:9px;margin-top:12px;overflow:hidden;display:none}.progress span{display:block;width:35%;height:100%;background:var(--accent);animation:move 1s infinite alternate}@keyframes move{to{transform:translateX(180%)}}.features{display:grid;grid-template-columns:repeat(3,1fr);gap:13px;margin:22px auto 0;max-width:760px}.feature{border:1px solid var(--line);border-radius:15px;padding:17px;background:#ffffff03}.feature b{display:block;font-size:13px;margin:6px 0}.feature p{font-size:12px;color:var(--muted);margin:0}.foot{max-width:760px;margin:23px auto 0;color:#858793;font-size:12px;text-align:center}.foot strong{color:#c3c4cb}@media(max-width:600px){.top{margin-bottom:46px}.features{grid-template-columns:1fr}.panel{padding:13px}.hero h1{letter-spacing:-2px}.actions .btn{width:100%}}
</style>
</head>
<body><main class="wrap">
<header class="top"><div class="brand">under<span>2</span>mb<span>.</span></div><div class="pill">PRIVATE · FORMAT-AWARE</div></header>
<section class="hero"><div class="eyebrow">LESS WEIGHT. SAME FORMAT.</div><h1>Your files, <span style="color:var(--accent)">lighter.</span></h1><p>Compress supported files toward 2 MB, then download in the original file format. If a file can't reach the target safely, we'll tell you.</p></section>
<section class="panel">
<div class="drop" id="drop"><div><div class="upload-icon">↑</div><h2>Drop your file here</h2><p>or select a file from your device</p><button class="btn" id="choose" type="button">Choose file</button><div class="subtle">Up to MAXMB MB per file · JPG, PNG, WEBP, TIFF, PDF, DOCX, PPTX, XLSX</div></div></div>
<input id="file" type="file" hidden>
<div id="picked" style="display:none"><div class="file-row"><div class="file-icon" id="ext">FILE</div><div class="file-info"><div class="file-name" id="filename"></div><div class="file-meta" id="filesize"></div></div><button class="remove" id="remove" title="Remove file" aria-label="Remove file">×</button></div>
<div class="actions"><span class="subtle" style="margin:0">Target output: under 2 MB</span><button class="btn" id="compress">Compress file ↗</button></div></div>
<div class="progress" id="progress"><span></span></div><div class="status" id="status" role="status" aria-live="polite"></div>
</section>
<section class="features"><div class="feature"><span>↘</span><b>Format-aware</b><p>Downloads keep the original extension and file format.</p></div><div class="feature"><span>◎</span><b>Honest results</b><p>No fake success if a file remains above the size target.</p></div><div class="feature"><span>⌁</span><b>Short-lived processing</b><p>Files are processed in memory, not stored in an account.</p></div></section>
<div class="foot"><strong>Note:</strong> Not every file can be reduced below 2 MB without losing content or changing format. Office files may compress only slightly. Avoid uploading sensitive documents to a public deployment.</div>
</main>
<script>
const MAXMB=MAXMB_VALUE;
const fileInput=document.querySelector('#file'), drop=document.querySelector('#drop'), picked=document.querySelector('#picked'), statusBox=document.querySelector('#status'), progress=document.querySelector('#progress');
let selected=null;
function fmt(n){if(n<1024)return n+' B';if(n<1048576)return (n/1024).toFixed(1)+' KB';return (n/1048576).toFixed(2)+' MB'}
function showStatus(msg,kind=''){statusBox.className='status show '+kind;statusBox.textContent=msg}
function setFile(f){if(!f)return;selected=f;document.querySelector('#filename').textContent=f.name;document.querySelector('#filesize').textContent=fmt(f.size);document.querySelector('#ext').textContent=(f.name.split('.').pop()||'FILE').slice(0,5).toUpperCase();picked.style.display='block';statusBox.className='status';if(f.size>MAXMB*1048576)showStatus(`This file is larger than the ${MAXMB} MB upload limit.`,'bad')}
function clearFile(){selected=null;fileInput.value='';picked.style.display='none';statusBox.className='status';progress.style.display='none'}
document.querySelector('#choose').onclick=()=>fileInput.click();drop.onclick=e=>{if(e.target.id!=='choose')fileInput.click()};fileInput.onchange=()=>setFile(fileInput.files[0]);document.querySelector('#remove').onclick=clearFile;
for(const ev of ['dragenter','dragover'])drop.addEventListener(ev,e=>{e.preventDefault();drop.classList.add('over')});for(const ev of ['dragleave','drop'])drop.addEventListener(ev,e=>{e.preventDefault();drop.classList.remove('over')});drop.addEventListener('drop',e=>setFile(e.dataTransfer.files[0]));
document.querySelector('#compress').onclick=async()=>{if(!selected)return;if(selected.size>MAXMB*1048576){showStatus(`This file exceeds the ${MAXMB} MB upload limit.`,'bad');return}
const btn=document.querySelector('#compress');btn.disabled=true;progress.style.display='block';showStatus('Compressing your file…');
try{const fd=new FormData();fd.append('file',selected);const res=await fetch('/api/compress',{method:'POST',body:fd});const type=res.headers.get('content-type')||'';if(!res.ok||type.includes('application/json')){const data=await res.json();throw new Error(data.detail||'Compression failed.')}
const blob=await res.blob();const outName=res.headers.get('X-Output-Filename')||selected.name;const size=Number(res.headers.get('X-Output-Size')||blob.size);if(size>=2097152)throw new Error(`The compressed result is ${fmt(size)}, still above 2 MB. No download was produced. Try a smaller file or a format-specific optimization.`);const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=outName;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);showStatus(`Done — ${fmt(selected.size)} → ${fmt(size)}. Your download is ready.`,'ok')
}catch(e){showStatus(e.message||'Something went wrong.','bad')}finally{btn.disabled=false;progress.style.display='none'}
};
</script></body></html>""".replace("MAXMB_VALUE", "__MAXMB__").replace("MAXMB MB", "__MAXMB__ MB")

@app.get("/", response_class=HTMLResponse)
def home():
    return HTMLResponse(INDEX.replace("__MAXMB__", str(MAX_UPLOAD_MB)))

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

def compress_pdf(data: bytes) -> bytes:
    doc = fitz.open(stream=data, filetype="pdf")
    try:
        out = doc.tobytes(garbage=4, deflate=True, clean=True, deflate_images=True, deflate_fonts=True)
    finally:
        doc.close()
    return out

def repack_office(data: bytes) -> bytes:
    src = io.BytesIO(data)
    dest = io.BytesIO()
    with zipfile.ZipFile(src, "r") as zin, zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zout:
        for item in zin.infolist():
            payload = zin.read(item.filename)
            # Keep package member paths and payloads unchanged; repack with deflate.
            info = zipfile.ZipInfo(item.filename, date_time=item.date_time)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = item.external_attr
            info.create_system = item.create_system
            zout.writestr(info, payload, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return dest.getvalue()

@app.post("/api/compress")
async def compress(file: UploadFile = File(...)):
    name = Path(file.filename or "upload.bin").name
    ext = Path(name).suffix.lower()
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if not data:
        raise HTTPException(400, "The uploaded file is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"File exceeds the {MAX_UPLOAD_MB} MB upload limit.")
    if len(data) < TARGET_BYTES:
        # Return unchanged data if already under target, preserving original format exactly.
        out = data
    elif ext in IMAGE_FORMATS:
        try:
            out = compress_image(data, ext)
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise HTTPException(422, "This image could not be processed. The file may be damaged or unsupported.") from exc
    elif ext == ".pdf":
        try:
            out = compress_pdf(data)
        except Exception as exc:
            raise HTTPException(422, "This PDF could not be optimized. It may be damaged, encrypted, or unsupported.") from exc
    elif ext in OFFICE_EXTS:
        try:
            out = repack_office(data)
        except (zipfile.BadZipFile, KeyError, OSError) as exc:
            raise HTTPException(422, "This Office file is invalid or damaged.") from exc
    else:
        raise HTTPException(415, f"Format {ext or '(no extension)'} is not supported for format-preserving compression yet.")
    if len(out) >= TARGET_BYTES:
        raise HTTPException(422, f"Best-effort compression produced {len(out) / 1048576:.2f} MB, which is still not under 2 MB. No file was returned.")
    headers = {
        "X-Output-Filename": name,
        "X-Output-Size": str(len(out)),
        "Content-Disposition": f'attachment; filename="{name.replace(chr(34), "")}"',
        "Cache-Control": "no-store",
    }
    media = {
        ".pdf": "application/pdf", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".webp": "image/webp", ".bmp": "image/bmp",
        ".tif": "image/tiff", ".tiff": "image/tiff",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }.get(ext, "application/octet-stream")
    return Response(content=out, media_type=media, headers=headers)
