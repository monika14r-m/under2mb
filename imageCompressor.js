// imageCompressor.js
// Pure compression logic — no DOM references here, so it's independently
// testable and reusable (e.g. from a Node/CLI context with a DOM shim, or a
// future web worker).

import {
  JPEG_QUALITY_STEPS,
  RESIZE_SCALE_STEP,
  MAX_RESIZE_ATTEMPTS_JPEG,
  MAX_RESIZE_ATTEMPTS_PNG,
  MIN_DIMENSION_PX,
} from "./config.js";

/**
 * Load a File/Blob into an HTMLImageElement.
 * @param {Blob} fileOrBlob
 * @returns {Promise<HTMLImageElement>}
 */
function loadImage(fileOrBlob) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(fileOrBlob);
    const img = new Image();
    img.onload = () => {
      resolve(img);
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("Could not decode image"));
    };
    img.src = url;
  });
}

/**
 * Draw an image onto a new canvas at the given dimensions.
 */
function drawToCanvas(img, width, height) {
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(img, 0, 0, width, height);
  return canvas;
}

/**
 * Wrap canvas.toBlob in a Promise.
 */
function canvasToBlob(canvas, mime, quality) {
  return new Promise((resolve) => {
    if (quality !== undefined) {
      canvas.toBlob((b) => resolve(b), mime, quality);
    } else {
      canvas.toBlob((b) => resolve(b), mime);
    }
  });
}

/**
 * Compress a JPEG: lower quality first, then shrink resolution if the
 * lowest quality setting still isn't small enough.
 */
async function compressJpeg(img, limitBytes) {
  let width = img.naturalWidth;
  let height = img.naturalHeight;
  let bestBlob = null;

  for (const quality of JPEG_QUALITY_STEPS) {
    const canvas = drawToCanvas(img, width, height);
    const blob = await canvasToBlob(canvas, "image/jpeg", quality);
    if (blob) {
      bestBlob = blob;
      if (blob.size <= limitBytes) return bestBlob;
    }
  }

  // Still too big at the lowest quality — start shrinking dimensions too.
  for (let attempt = 0; attempt < MAX_RESIZE_ATTEMPTS_JPEG; attempt++) {
    width = Math.max(1, Math.round(width * RESIZE_SCALE_STEP));
    height = Math.max(1, Math.round(height * RESIZE_SCALE_STEP));
    const canvas = drawToCanvas(img, width, height);
    const blob = await canvasToBlob(canvas, "image/jpeg", JPEG_QUALITY_STEPS.at(-1));
    if (blob) {
      bestBlob = blob;
      if (blob.size <= limitBytes) return bestBlob;
    }
  }

  return bestBlob;
}

/**
 * Compress a PNG: since PNG is lossless (no quality knob), the only lever
 * is resolution. Shrink progressively until it fits or we hit the floor.
 */
async function compressPng(img, limitBytes) {
  let width = img.naturalWidth;
  let height = img.naturalHeight;
  let bestBlob = null;

  for (let attempt = 0; attempt < MAX_RESIZE_ATTEMPTS_PNG; attempt++) {
    const canvas = drawToCanvas(img, width, height);
    const blob = await canvasToBlob(canvas, "image/png");
    if (blob) {
      bestBlob = blob;
      if (blob.size <= limitBytes) return bestBlob;
    }

    width = Math.max(1, Math.round(width * RESIZE_SCALE_STEP));
    height = Math.max(1, Math.round(height * RESIZE_SCALE_STEP));
    if (width < MIN_DIMENSION_PX || height < MIN_DIMENSION_PX) break;
  }

  return bestBlob;
}

/**
 * Compress an image file/blob down toward a target size, preserving its
 * original format.
 *
 * @param {File|Blob} file
 * @param {string} mimeType - "image/jpeg" or "image/png"
 * @param {number} limitBytes - target size ceiling in bytes
 * @returns {Promise<Blob>} the best blob achieved (may still exceed limitBytes
 *   for extreme cases, e.g. a 1x1 image that is still "too big" isn't
 *   realistic, but very high-entropy tiny images could resist compression)
 */
export async function compressImage(file, mimeType, limitBytes) {
  const img = await loadImage(file);
  if (mimeType === "image/jpeg") {
    return compressJpeg(img, limitBytes);
  }
  return compressPng(img, limitBytes);
}
