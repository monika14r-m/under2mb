// zipExport.js
// Thin wrapper around the globally-loaded JSZip library (loaded via CDN
// script tag in index.html) so the rest of the app doesn't touch the
// global `JSZip` directly.

/**
 * Build a zip file from a list of { name, blob } entries and trigger a
 * browser download.
 * @param {{name: string, blob: Blob}[]} entries
 * @param {string} zipFileName
 */
export async function downloadAsZip(entries, zipFileName = "compressed_images.zip") {
  if (typeof JSZip === "undefined") {
    throw new Error("JSZip failed to load — check your internet connection.");
  }

  const zip = new JSZip();
  for (const { name, blob } of entries) {
    zip.file(name, blob);
  }

  const content = await zip.generateAsync({ type: "blob" });
  const url = URL.createObjectURL(content);

  const a = document.createElement("a");
  a.href = url;
  a.download = zipFileName;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
