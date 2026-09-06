const vscode = require('vscode');
const crypto = require('crypto');
const { STATUS_NAMES, DIFFICULTY_NAMES, TRACK_NAMES, QUESTION_TYPE_NAMES, LANGUAGE_NAMES } = require('./tree');

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

class LessonDashboard {
  constructor(onMessage) {
    this.onMessage = onMessage;
    this.panel = undefined;
    this.lesson = undefined;
    this.progress = undefined;
    this.state = {};
  }

  show(lesson, progress, state = {}) {
    this.lesson = lesson;
    this.progress = progress;
    this.state = state;
    if (!this.panel) {
      this.panel = vscode.window.createWebviewPanel(
        'embeddedTrainer.lesson',
        'Embedded Trainer',
        vscode.ViewColumn.Active,
        { enableScripts: true, retainContextWhenHidden: true }
      );
      this.panel.onDidDispose(() => {
        this.panel = undefined;
      });
      this.panel.webview.onDidReceiveMessage((message) => {
        if (this.lesson) {
          this.onMessage(message, this.lesson);
        }
      });
    } else {
      this.panel.reveal(vscode.ViewColumn.Active, true);
    }
    this.panel.title = `课程：${lesson.title}`;
    this.panel.webview.html = this.render();
  }

  update(lesson, progress, state = {}) {
    if (!this.panel || !this.lesson || this.lesson.id !== lesson.id) {
      return;
    }
    this.lesson = lesson;
    this.progress = progress;
    this.state = { ...this.state, ...state };
    this.panel.webview.html = this.render();
  }

  render() {
    const lesson = this.lesson;
    const progress = this.progress || {};
    const nonce = crypto.randomBytes(16).toString('hex');
    const status = progress.status || 'not-started';
    const statusClass = status === 'passed' ? 'passed' : status === 'in-progress' ? 'progress' : '';
    const tags = (lesson.knowledge || []).map((item) => `<span class="tag">${escapeHtml(item)}</span>`).join('');
    const prerequisites = (lesson.prerequisites || []).length
      ? lesson.prerequisites.map((item) => `<code>${escapeHtml(item)}</code>`).join('、')
      : '无';
    const hint = this.state.hint ? `<section class="notice"><strong>提示</strong><p>${escapeHtml(this.state.hint)}</p></section>` : '';
    const result = this.state.result
      ? `<section class="result ${this.state.result.ok ? 'ok' : 'bad'}"><strong>${this.state.result.ok ? '评测通过' : '评测未通过'}</strong><pre>${escapeHtml(this.state.result.text)}</pre></section>`
      : '';
    const isProgramming = ['programming', 'debugging'].includes(lesson.questionType);
    let question = '';
    if (!isProgramming && lesson.quiz) {
      let controls = '';
      if (lesson.questionType === 'single-choice') {
        controls = lesson.quiz.options.map((option) => `
          <label class="option"><input type="radio" name="quiz-answer" value="${escapeHtml(option.id)}"> <strong>${escapeHtml(option.id)}.</strong> ${escapeHtml(option.text)}</label>`).join('');
      } else if (lesson.questionType === 'true-false') {
        controls = `
          <label class="option"><input type="radio" name="quiz-answer" value="true"> 正确</label>
          <label class="option"><input type="radio" name="quiz-answer" value="false"> 错误</label>`;
      } else if (['fill-blank', 'code-reading'].includes(lesson.questionType)) {
        controls = lesson.quiz.blanks.map((blank, index) => `
          <label class="blank"><span>${escapeHtml(blank.label || `第 ${index + 1} 空`)}</span><input type="text" data-blank-index="${index}" autocomplete="off" spellcheck="false"></label>`).join('');
      }
      question = `
        <section class="question">
          <h2>题目</h2>
          <p>${escapeHtml(lesson.quiz.prompt)}</p>
          ${lesson.quiz.code ? `<pre><code>${escapeHtml(lesson.quiz.code)}</code></pre>` : ''}
          <form id="quiz-form" data-question-type="${escapeHtml(lesson.questionType)}">
            ${controls}
            <button type="submit">提交答案</button>
          </form>
        </section>`;
    }
    const actions = isProgramming
      ? `<button data-command="start">${status === 'not-started' ? '开始练习' : '打开代码'}</button>
         <button data-command="check">运行评测</button>
         <button class="secondary" data-command="hint">查看提示</button>
         <button class="secondary" data-command="instructions">完整题目</button>
         <button class="secondary" data-command="help">使用说明</button>`
      : `<button class="secondary" data-command="hint">查看提示</button>
         <button class="secondary" data-command="help">使用说明</button>`;

    return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'nonce-${nonce}';">
  <style>
    body { font-family: var(--vscode-font-family); color: var(--vscode-foreground); padding: 28px 36px; max-width: 900px; margin: auto; }
    .eyebrow { color: var(--vscode-descriptionForeground); font-size: 12px; letter-spacing: .08em; text-transform: uppercase; }
    h1 { margin: 8px 0 10px; font-size: 30px; }
    .summary { color: var(--vscode-descriptionForeground); font-size: 16px; line-height: 1.6; }
    .meta { display: flex; flex-wrap: wrap; gap: 10px; margin: 22px 0; }
    .chip, .tag { padding: 4px 9px; border-radius: 999px; background: var(--vscode-badge-background); color: var(--vscode-badge-foreground); font-size: 12px; }
    .status { border-left: 4px solid var(--vscode-descriptionForeground); background: var(--vscode-editor-inactiveSelectionBackground); padding: 14px 16px; margin: 22px 0; }
    .status.passed { border-color: var(--vscode-testing-iconPassed); }
    .status.progress { border-color: var(--vscode-progressBar-background); }
    .actions { display: flex; flex-wrap: wrap; gap: 10px; margin: 24px 0; }
    button { border: 0; padding: 9px 14px; cursor: pointer; color: var(--vscode-button-foreground); background: var(--vscode-button-background); border-radius: 3px; }
    button:hover { background: var(--vscode-button-hoverBackground); }
    button.secondary { color: var(--vscode-button-secondaryForeground); background: var(--vscode-button-secondaryBackground); }
    button.secondary:hover { background: var(--vscode-button-secondaryHoverBackground); }
    section { margin: 24px 0; }
    .notice, .result { padding: 14px 16px; border: 1px solid var(--vscode-widget-border); background: var(--vscode-textBlockQuote-background); }
    .result.ok { border-left: 4px solid var(--vscode-testing-iconPassed); }
    .result.bad { border-left: 4px solid var(--vscode-testing-iconFailed); }
    pre { white-space: pre-wrap; overflow-wrap: anywhere; max-height: 280px; overflow: auto; font-family: var(--vscode-editor-font-family); font-size: 12px; }
    code { font-family: var(--vscode-editor-font-family); }
    .tags { display: flex; flex-wrap: wrap; gap: 7px; }
    .question { padding: 18px; border: 1px solid var(--vscode-widget-border); border-radius: 5px; }
    .question > p { font-size: 16px; line-height: 1.7; white-space: pre-wrap; }
    #quiz-form { display: grid; gap: 10px; margin-top: 18px; }
    .option { display: block; padding: 10px 12px; border: 1px solid var(--vscode-input-border); border-radius: 4px; cursor: pointer; }
    .option:hover { background: var(--vscode-list-hoverBackground); }
    .blank { display: grid; gap: 6px; }
    input[type="text"] { color: var(--vscode-input-foreground); background: var(--vscode-input-background); border: 1px solid var(--vscode-input-border); padding: 8px; font-family: var(--vscode-editor-font-family); }
  </style>
</head>
<body>
  <div class="eyebrow">${escapeHtml(TRACK_NAMES[lesson.track] || lesson.track)} · ${escapeHtml(QUESTION_TYPE_NAMES[lesson.questionType] || lesson.questionType)} · ${escapeHtml(lesson.id)}</div>
  ${lesson.packId ? `<p>知识包：${escapeHtml(lesson.packId)} · ${escapeHtml(lesson.packVersion)}${lesson.needsTrust && isProgramming ? ' · 代码尚未获准执行（请使用“管理知识包”）' : ''}</p>` : ''}
  <h1>${escapeHtml(lesson.title)}</h1>
  <p class="summary">${escapeHtml(lesson.summary)}</p>
  <div class="meta">
    <span class="chip">${escapeHtml(LANGUAGE_NAMES[lesson.language] || lesson.language)}</span>
    <span class="chip">${escapeHtml(DIFFICULTY_NAMES[lesson.difficulty] || lesson.difficulty)}</span>
    <span class="chip">${escapeHtml(lesson.target)}</span>
  </div>
  <div class="status ${statusClass}">
    <strong>${escapeHtml(STATUS_NAMES[status] || status)}</strong>
    <div>已评测 ${Number(progress.attempts || 0)} 次</div>
  </div>
  <div class="actions">
    ${actions}
  </div>
  ${question}
  ${hint}
  ${result}
  <section>
    <h2>知识点</h2>
    <div class="tags">${tags || '未标注'}</div>
  </section>
  <section>
    <h2>前置课程</h2>
    <p>${prerequisites}</p>
  </section>
  <script nonce="${nonce}">
    const vscode = acquireVsCodeApi();
    document.querySelectorAll('[data-command]').forEach((button) => {
      button.addEventListener('click', () => vscode.postMessage({ command: button.dataset.command }));
    });
    const quizForm = document.getElementById('quiz-form');
    if (quizForm) {
      quizForm.addEventListener('submit', (event) => {
        event.preventDefault();
        const questionType = quizForm.dataset.questionType;
        let answer;
        if (questionType === 'fill-blank' || questionType === 'code-reading') {
          answer = [...quizForm.querySelectorAll('[data-blank-index]')].map((input) => input.value);
        } else {
          const selected = quizForm.querySelector('input[name="quiz-answer"]:checked');
          if (!selected) {
            return;
          }
          answer = questionType === 'true-false' ? selected.value === 'true' : selected.value;
        }
        vscode.postMessage({ command: 'submit', answer });
      });
    }
  </script>
</body>
</html>`;
  }
}

module.exports = { LessonDashboard };
