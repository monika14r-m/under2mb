// ui.js
// DOM rendering helpers. Keeps main.js focused on orchestration/state.

export function bytesToMB(bytes) {
  return (bytes / (1024 * 1024)).toFixed(2);
}

export function formatBytes(bytes) {
  return `${bytesToMB(bytes)} MB`;
}

export function isAcceptedFile(file, acceptedExt, acceptedMime) {
  return acceptedExt.test(file.name) || acceptedMime.test(file.type);
}

/**
 * Create and append a table row for a queued item, returning references
 * to the cells that will need to update as processing completes.
 */
export function renderRow(listEl, item) {
  const row = document.createElement("div");
  row.className = "row";
  row.id = `row-${item.id}`;

  const thumb = document.createElement("img");
  thumb.className = "thumb";
  thumb.alt = "";
  const reader = new FileReader();
  reader.onload = (e) => {
    thumb.src = e.target.result;
  };
  reader.readAsDataURL(item.file);

  const name = document.createElement("div");
  name.className = "name";
  name.title = item.name;
  name.textContent = item.name;

  const orig = document.createElement("div");
  orig.textContent = formatBytes(item.origSize);

  const compressed = document.createElement("div");
  compressed.textContent = "—";

  const status = document.createElement("div");
  status.className = "status working";
  status.textContent = "Working…";

  const action = document.createElement("div");
  action.textContent = "—";

  row.append(thumb, name, orig, compressed, status, action);
  listEl.appendChild(row);

  return { row, compressed, status, action };
}

/**
 * Update a row's compressed-size / status / download-link cells based on
 * the current state of `item`.
 */
export function updateRow(item, statusText) {
  const { compressed, status, action } = item.els;

  compressed.textContent = item.resultSize != null ? formatBytes(item.resultSize) : "—";

  const statusClass =
    item.status === "ok"
      ? "ok"
      : item.status === "skip"
      ? "skip"
      : item.status === "err"
      ? "err"
      : "working";
  status.className = `status ${statusClass}`;
  status.textContent = statusText;

  action.innerHTML = "";
  if (item.resultBlob) {
    const a = document.createElement("a");
    a.className = "dl";
    a.textContent = "Download";
    a.href = URL.createObjectURL(item.resultBlob);
    a.download = item.name;
    action.appendChild(a);
  }
}

export function clearRows(listEl) {
  listEl.querySelectorAll(".row:not(.head)").forEach((r) => r.remove());
}
