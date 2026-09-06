// Runs only inside the webview. Keep independent of Node and VS Code host APIs.
function dashboardClient() {
  const vscode = acquireVsCodeApi();
  const lessonId = document.body.dataset.lessonId;
  const quizForm = document.getElementById('quiz-form');
  const activity = document.getElementById('activity-status');
  const controls = [...document.querySelectorAll('button, input')];
  const saved = vscode.getState();
  const previous = saved && saved.lessonId === lessonId ? saved : {};
  let busy = false;

  function readAnswer() {
    if (!quizForm) return undefined;
    const questionType = quizForm.dataset.questionType;
    if (questionType === 'fill-blank' || questionType === 'code-reading') {
      return [...quizForm.querySelectorAll('[data-blank-index]')].map((input) => input.value);
    }
    const selected = quizForm.querySelector('input[name="quiz-answer"]:checked');
    if (!selected) return undefined;
    return questionType === 'true-false' ? selected.value === 'true' : selected.value;
  }

  function saveDraft() {
    vscode.setState({ lessonId, answer: readAnswer(), scrollY: window.scrollY, focusId: document.activeElement?.id });
  }

  function setBusy(value) {
    busy = value;
    controls.forEach((control) => { control.disabled = busy; });
    document.body.setAttribute('aria-busy', String(busy));
    activity.textContent = busy ? '正在处理，请稍候…' : '';
  }

  function send(command, answer) {
    if (busy) return;
    saveDraft();
    setBusy(true);
    vscode.postMessage({ command, lessonId, ...(answer === undefined ? {} : { answer }) });
  }

  if (quizForm) {
    quizForm.querySelectorAll('[data-blank-index]').forEach((input, index) => {
      if (Array.isArray(previous.answer) && typeof previous.answer[index] === 'string') input.value = previous.answer[index];
    });
    quizForm.querySelectorAll('input[name="quiz-answer"]').forEach((input) => {
      input.checked = previous.answer !== undefined && input.value === String(previous.answer);
    });
    quizForm.addEventListener('input', saveDraft);
    quizForm.addEventListener('change', saveDraft);
    quizForm.addEventListener('submit', (event) => {
      event.preventDefault();
      if (!quizForm.reportValidity()) return;
      const answer = readAnswer();
      if (answer !== undefined) send('submit', answer);
    });
  }
  document.querySelectorAll('[data-command]').forEach((button) => {
    button.addEventListener('click', () => send(button.dataset.command));
  });
  window.addEventListener('message', (event) => {
    if (event.data?.command === 'busy') setBusy(Boolean(event.data.busy));
  });
  window.addEventListener('scroll', saveDraft, { passive: true });
  setBusy(document.body.dataset.busy === 'true');
  // A catalog refresh replaces the document. Ask the host again in case the
  // previous document received the completion message while this one loaded.
  vscode.postMessage({ command: 'ready', lessonId });
  requestAnimationFrame(() => {
    if (previous.focusId) document.getElementById(previous.focusId)?.focus({ preventScroll: true });
    if (Number.isFinite(previous.scrollY)) window.scrollTo(0, previous.scrollY);
  });
}

module.exports = { dashboardClient };
