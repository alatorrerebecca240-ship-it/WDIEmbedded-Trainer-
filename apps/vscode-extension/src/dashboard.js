const vscode = require('vscode');
const crypto = require('crypto');
const fs = require('node:fs');
const path = require('node:path');
const { dashboardClient } = require('./dashboard-client');
const { STATUS_NAMES, DIFFICULTY_NAMES, TRACK_NAMES, QUESTION_TYPE_NAMES, LANGUAGE_NAMES } = require('./tree');

const styles = fs.readFileSync(path.join(__dirname, '../media/dashboard.css'), 'utf8');
const commands = new Set(['start', 'check', 'hint', 'instructions', 'help', 'packages', 'submit']);
const symbols = {
  code: '<path d="m6 5-4 3 4 3m4-6 4 3-4 3M9 3 7 13"/>',
  play: '<path d="m5 3 8 5-8 5z"/>',
  book: '<path d="M8 4v10M8 4C5 2 3 2 1.5 3v9C4 11 6 12 8 14c2-2 4-3 6.5-2V3C13 2 11 2 8 4Z"/>',
  hint: '<path d="M6 12h4m-4 2h4M5 10c0-2-2-2-2-5a5 5 0 0 1 10 0c0 3-2 3-2 5Z"/>',
  help: '<circle cx="8" cy="8" r="6.5"/><path d="M6 6a2 2 0 1 1 3 1.7C8 8.2 8 8.5 8 9m0 2v.5"/>',
  package: '<path d="m8 1 6 3.5v7L8 15l-6-3.5v-7L8 1Zm0 7 6-3.5M8 8 2 4.5M8 8v7M5 2.8l6 3.4v3"/>',
  check: '<path d="m3 8 3 3 7-7"/>',
  close: '<path d="m4 4 8 8m0-8-8 8"/>',
  terminal: '<path d="m2 4 4 4-4 4m6 0h6"/>',
  circuit: '<path d="M5 1v3m6-3v3M5 12v3m6-3v3M1 5h3m8 0h3M1 11h3m8 0h3M4 4h8v8H4zM6 6h4v4H6z"/>'
};

function icon(name) {
  return `<svg class="icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.25" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${symbols[name] || symbols.code}</svg>`;
}

function escapeHtml(value) {
  return String(value ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
}

function button(command, label, symbol, secondary = true) {
  return `<button type="button" class="${secondary ? 'secondary' : 'primary'}" data-command="${command}">${icon(symbol)}<span>${label}</span></button>`;
}

class LessonDashboard {
  constructor(onMessage) {
    this.onMessage = onMessage;
    this.panel = undefined;
    this.lesson = undefined;
    this.progress = undefined;
    this.state = {};
    this.pending = false;
  }

  show(lesson, progress, state = {}) {
    this.state = this.lesson?.id === lesson.id ? { ...this.state, ...state } : state;
    this.lesson = lesson;
    this.progress = progress;
    if (!this.panel) {
      this.panel = vscode.window.createWebviewPanel(
        'embeddedTrainer.lesson', 'Embedded Trainer', vscode.ViewColumn.Active,
        { enableScripts: true, retainContextWhenHidden: true, localResourceRoots: [] }
      );
      this.panel.onDidDispose(() => { this.panel = undefined; });
      this.panel.webview.onDidReceiveMessage((message) => this.handleMessage(message));
    } else {
      this.panel.reveal(vscode.ViewColumn.Active, true);
    }
    this.panel.title = `课程：${lesson.title}`;
    this.panel.webview.html = this.render();
    this.renderedPending = this.pending;
  }

  async handleMessage(message) {
    if (message?.command === 'ready' && message.lessonId === this.lesson?.id) {
      this.panel?.webview.postMessage({ command: 'busy', busy: this.pending });
      return;
    }
    // Reject delayed messages from a previous lesson and duplicate submissions.
    if (!message || !this.lesson || !commands.has(message.command)
      || message.lessonId !== this.lesson.id || this.pending) return;
    const lesson = this.lesson;
    this.pending = true;
    this.panel?.webview.postMessage({ command: 'busy', busy: true });
    try {
      await this.onMessage(message, lesson);
    } catch (error) {
      this.update(lesson, this.progress, {
        result: { ok: false, text: error instanceof Error ? error.message : String(error) }
      });
    } finally {
      this.pending = false;
      this.panel?.webview.postMessage({ command: 'busy', busy: false });
    }
  }

  update(lesson, progress, state = {}) {
    if (!this.panel || !this.lesson || this.lesson.id !== lesson.id) return;
    const nextState = { ...this.state, ...state };
    if (this.renderedPending === this.pending && this.lesson === lesson && JSON.stringify(this.progress) === JSON.stringify(progress)
      && JSON.stringify(this.state) === JSON.stringify(nextState)) return;
    this.lesson = lesson;
    this.progress = progress;
    this.state = nextState;
    this.panel.webview.html = this.render();
    this.renderedPending = this.pending;
  }

  render() {
    const lesson = this.lesson;
    const progress = this.progress || {};
    const nonce = crypto.randomBytes(16).toString('hex');
    const status = progress.status || 'not-started';
    const statusClass = status === 'passed' ? 'passed' : status === 'in-progress' ? 'progress' : 'idle';
    const isProgramming = ['programming', 'debugging'].includes(lesson.questionType);
    const tags = (lesson.knowledge || []).map((item) => `<span class="tag">${escapeHtml(item)}</span>`).join('');
    const prerequisites = (lesson.prerequisites || []).map((item) => `<li><code>${escapeHtml(item)}</code></li>`).join('');
    const hintButton = (lesson.hints || []).length ? button('hint', '查看提示', 'hint') : '';
    const hint = this.state.hint ? `<section class="notice" aria-labelledby="hint-title"><h2 id="hint-title">${icon('hint')}分级提示</h2><p>${escapeHtml(this.state.hint)}</p></section>` : '';
    const result = this.state.result
      ? `<section class="result ${this.state.result.ok ? 'ok' : 'bad'}" aria-labelledby="result-title" role="status">
          <h2 id="result-title">${icon(this.state.result.ok ? 'check' : 'close')}${this.state.result.ok ? (isProgramming ? '评测通过' : '回答正确') : (isProgramming ? '评测未通过' : '本次提交未通过')}</h2>
          <pre tabindex="0" aria-label="${isProgramming ? '评测输出' : '作答反馈'}">${escapeHtml(this.state.result.text)}</pre>
        </section>` : '';

    let question;
    if (!isProgramming && lesson.quiz) {
      let controls = '';
      if (lesson.questionType === 'single-choice') {
        controls = lesson.quiz.options.map((option, index) => `<label class="option">
          <input id="answer-${index}" type="radio" name="quiz-answer" value="${escapeHtml(option.id)}" required>
          <span class="option-key">${escapeHtml(option.id)}</span><span>${escapeHtml(option.text)}</span></label>`).join('');
      } else if (lesson.questionType === 'true-false') {
        controls = [['true', '正确'], ['false', '错误']].map(([value, label], index) => `<label class="option">
          <input id="answer-${index}" type="radio" name="quiz-answer" value="${value}" required><span>${label}</span></label>`).join('');
      } else if (['fill-blank', 'code-reading'].includes(lesson.questionType)) {
        controls = lesson.quiz.blanks.map((blank, index) => `<label class="blank" for="answer-${index}">
          <span>${escapeHtml(blank.label || `第 ${index + 1} 空`)}</span><input id="answer-${index}" type="text" data-blank-index="${index}" autocomplete="off" spellcheck="false" required></label>`).join('');
      }
      question = `<section class="question" aria-labelledby="question-title">
        <div class="section-heading"><h2 id="question-title">${icon('book')}题目</h2><span class="section-label">EXERCISE</span></div>
        <p class="prompt">${escapeHtml(lesson.quiz.prompt)}</p>
        ${lesson.quiz.code ? `<div class="code-block"><div class="code-title">${icon('code')}阅读代码<span>只读 · 不执行</span></div><pre tabindex="0" aria-label="题目代码"><code>${escapeHtml(lesson.quiz.code)}</code></pre></div>` : ''}
        <form id="quiz-form" data-question-type="${escapeHtml(lesson.questionType)}">
          <fieldset><legend>${['fill-blank', 'code-reading'].includes(lesson.questionType) ? '填写答案' : '选择一个答案'}</legend><div class="answer-fields">${controls}</div></fieldset>
          <div class="actions"><button type="submit" class="primary">${icon('check')}<span>提交答案</span></button>${hintButton}</div>
        </form>
      </section>`;
    } else {
      question = `<section class="question" aria-labelledby="question-title">
        <div class="section-heading"><h2 id="question-title">${icon('code')}${isProgramming ? '编程工作区' : '课程内容'}</h2><span class="section-label">WORKSPACE</span></div>
        <p class="workbench-copy">${isProgramming ? '在编辑器中实现，在这里验证。' : '打开完整题目开始学习。'}</p>
        ${isProgramming ? `<ol class="workflow"><li><span class="step-number">01</span><span>阅读题目<small>确认输入、输出与要求</small></span></li><li><span class="step-number">02</span><span>编写代码<small>修改自己的练习副本</small></span></li><li><span class="step-number">03</span><span>运行评测<small>查看测试与编译反馈</small></span></li></ol>` : ''}
        <div class="actions">${isProgramming ? button('start', status === 'not-started' ? '开始练习' : '打开代码', 'code', status !== 'not-started') + button('check', '运行评测', 'play', status === 'not-started') : ''}${button('instructions', '完整题目', 'book')}${hintButton}</div>
        ${isProgramming ? `<p class="footnote">${icon('terminal')}评测在后台运行，无需打开终端。练习副本不会被题库更新覆盖。</p>` : ''}
      </section>`;
    }

    return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; base-uri 'none'; form-action 'none'; style-src 'nonce-${nonce}'; script-src 'nonce-${nonce}';">
  <title>${escapeHtml(lesson.title)} · Embedded Trainer</title>
  <style nonce="${nonce}">${styles}</style>
</head>
<body data-lesson-id="${escapeHtml(lesson.id)}" data-busy="${this.pending}">
  <div class="workbench">
    <header class="toolbar"><div class="brand">${icon('circuit')}<span>EMBEDDED <strong>TRAINER</strong></span></div>
      <nav aria-label="工具">${button('packages', '知识包', 'package')}${button('help', '使用说明', 'help')}</nav></header>
    <main>
      <header class="lesson-header">
        <div class="breadcrumb">${escapeHtml(TRACK_NAMES[lesson.track] || lesson.track)}<span aria-hidden="true">/</span>${escapeHtml(QUESTION_TYPE_NAMES[lesson.questionType] || lesson.questionType)}</div>
        <h1>${escapeHtml(lesson.title)}</h1><p class="summary">${escapeHtml(lesson.summary)}</p>
        <div class="meta"><span class="chip">${escapeHtml(LANGUAGE_NAMES[lesson.language] || lesson.language)}</span><span class="chip">${escapeHtml(DIFFICULTY_NAMES[lesson.difficulty] || lesson.difficulty)}</span>${lesson.target ? `<span class="chip">${escapeHtml(lesson.target)}</span>` : ''}<code class="lesson-id">${escapeHtml(lesson.id)}</code></div>
      </header>
      ${lesson.needsTrust && isProgramming ? `<section class="trust-notice" aria-label="代码执行权限">${icon('package')}<div><strong>此版本代码尚未获准执行</strong><p>先核对来源和源码，再通过“管理知识包”授权。校验通过不代表代码安全。</p></div>${button('packages', '管理知识包', 'package')}</section>` : ''}
      <div class="layout"><div class="primary-column">${question}
        <p id="activity-status" role="status" aria-live="polite"></p>${result}${hint}
      </div><aside aria-label="课程信息">
        <section class="context-section"><h2>学习状态</h2><div class="status ${statusClass}"><span class="status-mark" aria-hidden="true">${status === 'passed' ? icon('check') : '<span class="status-dot"></span>'}</span><strong>${escapeHtml(STATUS_NAMES[status] || status)}</strong></div><p class="attempts">已${isProgramming ? '评测' : '提交'} <strong>${Number(progress.attempts || 0)}</strong> 次</p></section>
        <section class="context-section"><h2>知识点</h2><div class="tags">${tags || '<span class="muted">未标注</span>'}</div></section>
        <section class="context-section"><h2>前置课程</h2>${prerequisites ? `<ul class="prerequisites">${prerequisites}</ul>` : '<p class="muted">无，可直接开始</p>'}</section>
        ${lesson.packId ? `<section class="context-section pack-info"><h2>${icon('package')}知识来源</h2><code>${escapeHtml(lesson.packId)}</code><p>版本 <code>${escapeHtml(lesson.packVersion)}</code></p></section>` : ''}
      </aside></div>
    </main>
    <footer><span class="footer-mark" aria-hidden="true"></span><span>EMBEDDED TRAINER</span><span>专注练习 · 逐步掌握</span></footer>
  </div>
  <script nonce="${nonce}">(${dashboardClient.toString()})();</script>
</body>
</html>`;
  }
}

module.exports = { LessonDashboard };
