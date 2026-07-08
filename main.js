// main.js
// Entry point: wires DOM events to the compression engine and UI renderer.
// Loaded from index.html as <script type="module">.

import { DEFAULT_LIMIT_MB, ACCEPTED_EXTENSIONS, ACCEPTED_MIME } from "./config.js";
import { compressImage } from "./imageCompressor.js";
import { downloadAsZip } from "./zipExport.js";
import { isAcceptedFile, renderRow, updateRow, clearRows } from "./ui.js";

const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const listEl = document.getElementById("list");
const emptyMsg = document.getElementById("emptyMsg");
const limitInput = document.getElementById("limitInput");
const downloadZipBtn = document.getElementById("downloadZipBtn");
const clearBtn = document.getElementById("clearBtn");

limitInput.value = DEFAULT_LIMIT_MB;

/** @type {Array<Object>} */
let items = [];
let counter = 0;

function currentLimitBytes() {
  const limitMB = parseFloat(limitInput.value) || DEFAULT_LIMIT_MB;
  return limitMB * 1024 * 1024;
}

function updateToolbar() {
  const anyDone = items.some((i) => i.resultBlob);
  downloadZipBtn.disabled = !anyDone;
  clearBtn.disabled = items.length === 0;
}

async function processItem(item) {
  const limitBytes = currentLimitBytes();

  try {
    if (item.origSize <= limitBytes) {
      item.resultBlob = item.file;
      item.resultSize = item.origSize;
      item.status = "skip";
      updateRow(item, "Already under limit");
      updateToolbar();
      return;
    }

    const blob = await compressImage(item.file, item.type, limitBytes);
    item.resultBlob = blob;
    item.resultSize = blob.size;
    item.status = blob.size <= limitBytes ? "ok" : "warn";
    updateRow(item, blob.size <= limitBytes ? "Compressed" : "Reduced (still above limit)");
  } catch (err) {
    console.error(err);
    item.status = "err";
    updateRow(item, `Failed: ${err.message}`);
  }
  updateToolbar();
}

function handleFiles(fileList) {
  const files = Array.from(fileList).filter((f) =>
    isAcceptedFile(f, ACCEPTED_EXTENSIONS, ACCEPTED_MIME)
  );
  if (files.length === 0) return;

  emptyMsg.style.display = "none";

  for (const file of files) {
    const id = `f${counter++}`;
    const item = {
      id,
      file,
      name: file.name,
      type: file.type || (file.name.toLowerCase().endsWith(".png") ? "image/png" : "image/jpeg"),
      origSize: file.size,
      resultBlob: null,
      resultSize: null,
      status: "working",
    };
    items.push(item);
    item.els = renderRow(listEl, item);
    processItem(item);
  }

  updateToolbar();
}

// --- Event wiring -----------------------------------------------------

dropzone.addEventListener("click", () => fileInput.click());
dropzone.addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    fileInput.click();
  }
});
dropzone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropzone.classList.add("drag");
});
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("drag"));
dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.classList.remove("drag");
  handleFiles(e.dataTransfer.files);
});

fileInput.addEventListener("change", (e) => handleFiles(e.target.files));

clearBtn.addEventListener("click", () => {
  items = [];
  clearRows(listEl);
  emptyMsg.style.display = "block";
  updateToolbar();
});

downloadZipBtn.addEventListener("click", async () => {
  const entries = items
    .filter((i) => i.resultBlob)
    .map((i) => ({ name: i.name, blob: i.resultBlob }));
  try {
    await downloadAsZip(entries);
  } catch (err) {
    console.error(err);
    alert(err.message);
  }
});

limitInput.addEventListener("change", () => {
  // Re-run every item against the new limit.
  items.forEach((item) => {
    item.status = "working";
    updateRow(item, "Working…");
    processItem(item);
  });
});
