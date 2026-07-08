# Image Compressor

A lightweight, dependency-free (aside from JSZip via CDN) client-side tool
that compresses **PNG / JPG / JPEG** images down to a target size — 2MB by
default — and returns each file in its **original format**. Everything runs
in the browser; no files are ever uploaded to a server.

![license](https://img.shields.io/badge/license-MIT-blue.svg)

## Features

- 🖼️ Drag-and-drop or click-to-browse for PNG/JPG/JPEG files (multiple at once)
- 🎚️ Adjustable target size limit (default 2MB)
- ⚡ Smart per-format strategy:
  - **JPEG** — progressively lowers quality (90% → 10%), then reduces resolution if still too large
  - **PNG** — progressively reduces resolution (PNG is lossless, so there's no quality knob to turn)
- ✅ Files already under the limit are left untouched
- 📦 Download files individually or all together as a `.zip`
- 🔒 100% client-side — no backend, no uploads, no tracking
- 🧩 Clean module structure — easy to extend or reuse pieces independently

## Project structure

```
image-compressor/
├── index.html                  # Markup only
├── css/
│   └── style.css               # All styling
├── js/
│   ├── config.js                # Shared constants (limits, quality steps)
│   ├── imageCompressor.js       # Core compression engine (pure logic, no DOM deps beyond canvas)
│   ├── zipExport.js             # JSZip wrapper for "download all" button
│   ├── ui.js                    # DOM rendering helpers
│   └── main.js                  # Entry point — wires events to logic
├── assets/
│   └── favicon.svg
├── .github/
│   └── workflows/
│       └── deploy.yml           # Auto-deploy to GitHub Pages on push to main
├── package.json                 # Optional dev-server scripts (no build step needed)
├── .gitignore
├── LICENSE
└── README.md
```

## Getting started

### Option 1 — just open it
Because the app uses native ES modules (`<script type="module">`), most
browsers require it to be served over `http://` rather than opened directly
via `file://`. The quickest way:

```bash
git clone https://github.com/YOUR_USERNAME/image-compressor.git
cd image-compressor
npm start
```

This runs a zero-config static server (via `npx http-server`) and prints a
local URL (typically `http://localhost:8080`). No `npm install` or build step
is required — `npm start` just launches a plain static file server.

### Option 2 — any static server
Any static file server works fine, for example:

```bash
python3 -m http.server 8080
```

Then open `http://localhost:8080`.

## Deploying to GitHub Pages

This repo includes a ready-to-go GitHub Actions workflow
(`.github/workflows/deploy.yml`) that publishes the site to GitHub Pages
automatically on every push to `main`.

To enable it:
1. Push this repo to GitHub.
2. Go to **Settings → Pages** in your repository.
3. Under **Build and deployment**, set **Source** to **GitHub Actions**.
4. Push to `main` (or run the workflow manually from the **Actions** tab).

Your site will then be live at `https://YOUR_USERNAME.github.io/image-compressor/`.

## How the compression works

- **JPEG**: The image is redrawn to a `<canvas>` and re-encoded via
  `canvas.toBlob(..., "image/jpeg", quality)` at decreasing quality levels.
  If it's still above the limit at the lowest quality step, the canvas
  dimensions are also scaled down (in ~10% steps) until the target is met.
- **PNG**: PNG encoding in the browser is lossless with no quality parameter,
  so the only lever available is resolution. The image is scaled down in
  small steps and re-encoded as PNG until it fits under the limit (with a
  floor so it won't shrink into an unusable postage stamp).

## Extending it

The compression engine (`js/imageCompressor.js`) has no DOM-rendering logic
in it — it just takes a file, a MIME type, and a byte limit, and returns a
blob. That makes it straightforward to:
- move it into a Web Worker for smoother UI while processing many/large files
- add WebP as an output option
- swap in a smarter PNG strategy (e.g. color-depth reduction via a library
  like `UPNG.js`) instead of pure resolution scaling

## License

MIT — see [LICENSE](./LICENSE).
