export function byId(id) {
  return document.getElementById(id);
}

export function setHtml(el, html) {
  if (!el) return;
  el.innerHTML = html;
}

export function escapeHtml(str) {
  return String(str)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

export function show(el) {
  if (!el) return;
  el.classList.remove("d-none");
}

export function hide(el) {
  if (!el) return;
  el.classList.add("d-none");
}

export function renderAlert({ type = "info", title = "", message = "" }) {
  const safeTitle = escapeHtml(title);
  const safeMsg = escapeHtml(message);
  return `
    <div class="alert alert-${type} mb-3" role="alert">
      ${title ? `<div class="fw-bold mb-1">${safeTitle}</div>` : ""}
      <div>${safeMsg}</div>
    </div>
  `;
}
