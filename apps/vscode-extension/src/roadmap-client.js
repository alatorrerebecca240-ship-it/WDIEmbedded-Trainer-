// Webview-only controller. Stores unfinished notes locally in the webview state.
function roadmapClient() {
  const vscode = acquireVsCodeApi();
  const viewId = document.body.dataset.viewId;
  const routeKey = document.body.dataset.routeKey;
  const previous = vscode.getState();
  const state = previous?.routeKey === routeKey ? previous : { routeKey, drafts: {}, open: [], scroll: 0 };
  let busy = false;
  const status = document.getElementById('camp-status');
  const controls = [...document.querySelectorAll('button, textarea, input')];
  function persist() {
    state.open = [...document.querySelectorAll('details[open]')].map((d) => d.id);
    state.scroll = window.scrollY;
    vscode.setState(state);
  }
  function setBusy(value) {
    busy = value;
    for (const control of controls) control.disabled = value || control.dataset.unavailable === 'true';
    document.body.setAttribute('aria-busy', String(value));
    status.textContent = value ? '正在处理…' : '';
  }
  function send(command, payload = {}) {
    if (busy) return;
    persist(); setBusy(true); vscode.postMessage({ command, viewId, ...payload });
  }
  for (const form of document.querySelectorAll('[data-stage-form]')) {
    const id = form.dataset.stageForm;
    const note = form.querySelector('textarea'), check = form.querySelector('input[type="checkbox"]');
    if (state.drafts[id]) { note.value = state.drafts[id].reflection; check.checked = state.drafts[id].confirmed; }
    form.addEventListener('input', () => { state.drafts[id] = { reflection: note.value, confirmed: check.checked }; persist(); });
    form.addEventListener('submit', (event) => { event.preventDefault(); if (form.reportValidity()) send('save', { stageId: id, reflection: note.value, confirmed: check.checked }); });
  }
  for (const button of document.querySelectorAll('[data-command]')) button.addEventListener('click', () => send(button.dataset.command, { lessonId: button.dataset.lessonId }));
  for (const button of document.querySelectorAll('[data-stage-target]')) button.addEventListener('click', () => {
    if (busy) return;
    const detail = document.getElementById(button.dataset.stageTarget);
    if (detail) { detail.open = true; detail.scrollIntoView({ block: 'start' }); persist(); }
  });
  for (const detail of document.querySelectorAll('details')) {
    if (previous?.routeKey === routeKey) detail.open = state.open.includes(detail.id);
    detail.addEventListener('toggle', persist);
  }
  window.addEventListener('message', (event) => {
    if (event.data?.command === 'busy') setBusy(Boolean(event.data.busy));
    if (event.data?.command === 'saved') { delete state.drafts[event.data.stageId]; persist(); }
    if (event.data?.command === 'error') { setBusy(false); status.textContent = event.data.text; }
  });
  window.addEventListener('scroll', persist, { passive: true });
  requestAnimationFrame(() => window.scrollTo(0, state.scroll || 0));
  vscode.postMessage({ command: 'ready', viewId });
}
module.exports = { roadmapClient };
