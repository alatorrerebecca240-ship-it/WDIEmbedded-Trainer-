const assert = require('node:assert/strict');
const { test } = require('node:test');
const vm = require('node:vm');
const Module = require('node:module');
const { dashboardClient } = require('../src/dashboard-client');

const vscode = {
  TreeItem: class { constructor(label) { this.label = label; } },
  ThemeIcon: class {}, ThemeColor: class {},
  EventEmitter: class { fire() {} },
  TreeItemCollapsibleState: { Expanded: 2, Collapsed: 1, None: 0 },
  ViewColumn: { Active: 1 },
  window: { createWebviewPanel: () => ({
    reveal() {}, onDidDispose() {},
    webview: { html: '', messages: [], onDidReceiveMessage() {}, postMessage(message) { this.messages.push(message); } }
  }) }
};
const originalLoad = Module._load;
let LessonDashboard, LessonTreeProvider;
try {
  Module._load = function (name, ...args) { return name === 'vscode' ? vscode : originalLoad.call(this, name, ...args); };
  ({ LessonDashboard } = require('../src/dashboard'));
  ({ LessonTreeProvider } = require('../src/tree'));
} finally { Module._load = originalLoad; }

function lesson(questionType = 'single-choice') {
  return {
    id: `fixture.${questionType}`, title: '指针与变量', summary: '理解地址和解引用。',
    track: 'c-basics', language: 'c', difficulty: 'beginner', target: 'host', questionType,
    knowledge: ['指针', '地址'], prerequisites: [], hints: ['从变量的地址想起。'],
    packId: 'fixture.core', packVersion: '1.0.0', needsTrust: true,
    quiz: { prompt: '选择正确的操作。', options: [{ id: 'A', text: '读取地址' }, { id: 'B', text: '读取指向的值' }],
      blanks: [{ label: '输出', answers: ['DO-NOT-EXPOSE-ANSWER'] }],
      answer: 'DO-NOT-EXPOSE-ANSWER', explanation: 'DO-NOT-EXPOSE-EXPLANATION', code: 'int value = 7;\nint *p = &value;' }
  };
}

test('all six question types have native controls and do not expose reference answers', () => {
  for (const type of ['programming', 'debugging', 'single-choice', 'true-false', 'fill-blank', 'code-reading']) {
    const dashboard = new LessonDashboard(() => {});
    dashboard.lesson = lesson(type);
    const html = dashboard.render();
    const programming = ['programming', 'debugging'].includes(type);
    assert.equal(html.includes('id="quiz-form"'), !programming);
    assert.equal(html.includes('data-command="check"'), programming);
    assert.equal(html.includes('此版本代码尚未获准执行'), programming);
    assert.ok(html.includes('data-command="packages"'));
    assert.ok(html.includes('data-command="help"'));
    assert.ok(!html.includes('DO-NOT-EXPOSE'));
    if (!programming) assert.match(html, /required>/);
  }
});

test('render escapes every untrusted surface, uses nonce CSP, and supports native themes and narrow panes', () => {
  const dashboard = new LessonDashboard(() => {});
  const hostile = '</script><img src=x onerror="attack()">';
  dashboard.lesson = { ...lesson('code-reading'), id: hostile, title: hostile, summary: hostile,
    track: hostile, language: hostile, difficulty: hostile, target: hostile,
    packId: hostile, packVersion: hostile, knowledge: [hostile], prerequisites: [hostile],
    quiz: { prompt: hostile, code: hostile, blanks: [{ label: hostile, answers: ['secret'] }] } };
  dashboard.state = { hint: hostile, result: { ok: false, text: hostile } };
  const html = dashboard.render();
  assert.ok(!html.includes(hostile));
  assert.ok(html.includes('&lt;/script&gt;&lt;img'));
  assert.equal((html.match(/<script /g) || []).length, 1);
  const nonce = html.match(/script-src 'nonce-([a-f0-9]+)'/)[1];
  assert.match(html, new RegExp(`<style nonce="${nonce}">`));
  assert.match(html, new RegExp(`<script nonce="${nonce}">`));
  assert.ok(!html.includes('unsafe-inline'));
  for (const marker of ['--vscode-editor-background', 'vscode-high-contrast-light', 'max-width: 760px', ':focus-visible', 'aria-live="polite"']) assert.ok(html.includes(marker));
});

test('hint and progress refresh preserve results for the same lesson, switching lessons clears them', () => {
  const dashboard = new LessonDashboard(() => {});
  const first = lesson();
  dashboard.show(first, {}, { result: { ok: true, text: 'previous result' } });
  dashboard.show(first, {}, { hint: 'new hint' });
  dashboard.update(first, { attempts: 2, status: 'passed' });
  assert.equal(dashboard.state.hint, 'new hint');
  assert.equal(dashboard.state.result.text, 'previous result');
  assert.match(dashboard.panel.webview.html, /已提交 <strong>2<\/strong> 次/);
  dashboard.show(lesson('true-false'), {});
  assert.deepEqual(dashboard.state, {});
});

test('host rejects stale/unknown messages and serializes requests; ready handshake recovers busy state', async () => {
  let finish;
  let calls = 0;
  const dashboard = new LessonDashboard(() => { calls++; return new Promise((resolve) => { finish = resolve; }); });
  const first = lesson();
  dashboard.show(first, {});
  for (const message of [null, {}, { command: 'eval', lessonId: first.id }, { command: 'submit', lessonId: 'previous' }]) await dashboard.handleMessage(message);
  assert.equal(calls, 0);
  const pending = dashboard.handleMessage({ command: 'submit', lessonId: first.id, answer: 'A' });
  await dashboard.handleMessage({ command: 'submit', lessonId: first.id, answer: 'B' });
  assert.equal(calls, 1);
  assert.equal(dashboard.pending, true);
  dashboard.update(first, {});
  assert.match(dashboard.panel.webview.html, /data-busy="true"/);
  await dashboard.handleMessage({ command: 'ready', lessonId: first.id });
  assert.equal(dashboard.panel.webview.messages.at(-1).busy, true);
  finish();
  await pending;
  await dashboard.handleMessage({ command: 'ready', lessonId: first.id });
  assert.equal(dashboard.panel.webview.messages.at(-1).busy, false);
  assert.equal(calls, 1, 'ready is not a backend command');
});

test('host action failure displays feedback and releases controls for retry', async () => {
  const dashboard = new LessonDashboard(async () => { throw new Error('fixture failure <details>'); });
  const first = lesson();
  dashboard.show(first, {});
  await dashboard.handleMessage({ command: 'submit', lessonId: first.id, answer: 'A' });
  assert.equal(dashboard.pending, false);
  assert.match(dashboard.panel.webview.html, /fixture failure &lt;details&gt;/);
  assert.equal(dashboard.panel.webview.messages.at(-1).busy, false);
});

// Minimal DOM fixture for the shipped client function: no browser dependency,
// no engine invocation, and no writes to learner progress.
function clientFixture(type, saved) {
  const callbacks = new Map();
  const node = (properties = {}) => ({
    disabled: false, ...properties, listeners: {},
    addEventListener(event, listener) { this.listeners[event] = listener; },
    focus() { document.activeElement = this; }
  });
  const blankType = ['fill-blank', 'code-reading'].includes(type);
  const programming = ['programming', 'debugging'].includes(type);
  const inputs = programming ? [] : blankType
    ? [0, 1].map((index) => node({ id: `answer-${index}`, dataset: { blankIndex: String(index) }, value: '' }))
    : (type === 'true-false' ? ['true', 'false'] : ['A', 'B']).map((value, index) => node({ id: `answer-${index}`, value, checked: false }));
  const buttons = ['start', 'check', 'hint', 'instructions', 'help', 'packages'].map((command) => node({ dataset: { command } }));
  const submitButton = node();
  const form = programming ? null : node({ dataset: { questionType: type }, valid: true,
    reportValidity() { return this.valid && (blankType ? inputs.every((input) => input.value) : inputs.some((input) => input.checked)); },
    querySelectorAll(selector) { return selector === '[data-blank-index]' ? (blankType ? inputs : []) : (blankType ? [] : inputs); },
    querySelector() { return inputs.find((input) => input.checked); }
  });
  const activity = node({ textContent: '' });
  const document = {
    body: { dataset: { lessonId: 'fixture', busy: 'false' }, setAttribute() {} },
    activeElement: inputs[0],
    getElementById(id) { return id === 'quiz-form' ? form : id === 'activity-status' ? activity : inputs.find((input) => input.id === id); },
    querySelectorAll(selector) { return selector === '[data-command]' ? buttons : [...buttons, submitButton, ...inputs]; }
  };
  const window = { scrollY: 0, addEventListener: (event, callback) => callbacks.set(event, callback), scrollTo: (_, y) => { window.scrollY = y; } };
  const messages = [];
  let stored = saved;
  const api = { getState: () => saved, setState: (value) => { stored = JSON.parse(JSON.stringify(value)); }, postMessage: (message) => messages.push(JSON.parse(JSON.stringify(message))) };
  vm.runInNewContext(`(${dashboardClient.toString()})();`, { acquireVsCodeApi: () => api, document, window, requestAnimationFrame: (callback) => callback() });
  return { inputs, buttons, form, messages, activity, window, document,
    draft: () => stored,
    submit: () => form.listeners.submit({ preventDefault() {} }),
    finish: () => callbacks.get('message')({ data: { command: 'busy', busy: false } }) };
}

test('client sends typed answers for every objective type and blocks duplicate submits', () => {
  for (const type of ['single-choice', 'true-false', 'fill-blank', 'code-reading']) {
    const client = clientFixture(type);
    assert.deepEqual(client.messages, [{ command: 'ready', lessonId: 'fixture' }]);
    client.submit();
    assert.equal(client.messages.length, 1, 'empty answers are not submitted');
    if (['fill-blank', 'code-reading'].includes(type)) {
      client.inputs[0].value = ' 7 ';
      client.inputs[1].value = '*p';
    } else { client.inputs[1].checked = true; }
    client.submit();
    const expected = type === 'single-choice' ? 'B' : type === 'true-false' ? false : [' 7 ', '*p'];
    assert.deepEqual(client.messages.at(-1), { command: 'submit', lessonId: 'fixture', answer: expected });
    assert.ok(client.inputs.every((input) => input.disabled));
    client.submit();
    assert.equal(client.messages.length, 2);
    client.finish();
    assert.ok(client.inputs.every((input) => !input.disabled));
    assert.equal(client.activity.textContent, '');
    client.submit();
    assert.equal(client.messages.length, 3);
  }
});

test('client retains drafts, scroll and focus across hints and does not carry answers to another lesson', () => {
  const first = clientFixture('fill-blank');
  first.inputs[0].value = '<untrusted>';
  first.inputs[1].value = '12';
  first.window.scrollY = 160;
  first.form.listeners.input();
  first.buttons.find((button) => button.dataset.command === 'hint').listeners.click();
  const restored = clientFixture('fill-blank', first.draft());
  assert.deepEqual(restored.inputs.map((input) => input.value), ['<untrusted>', '12']);
  assert.equal(restored.window.scrollY, 160);
  assert.equal(restored.document.activeElement.id, 'answer-0');
  const other = clientFixture('fill-blank', { ...first.draft(), lessonId: 'other' });
  assert.deepEqual(other.inputs.map((input) => input.value), ['', '']);
  const falseAnswer = clientFixture('true-false', { lessonId: 'fixture', answer: false });
  assert.equal(falseAnswer.inputs[1].checked, true);
});

test('all toolbar and programming actions carry the originating lesson ID', () => {
  const client = clientFixture('programming');
  for (const button of client.buttons) {
    button.listeners.click();
    assert.deepEqual(client.messages.at(-1), { command: button.dataset.command, lessonId: 'fixture' });
    client.finish();
  }
});

test('native tree has stable identities and accurate completion counts after refresh', () => {
  const first = lesson('programming'), second = lesson('single-choice');
  let passed = false;
  const tree = new LessonTreeProvider({ lessons: [first, second], status: (id) => ({ status: passed && id === first.id ? 'passed' : 'not-started' }) });
  const before = tree.getChildren()[0];
  assert.equal(before.description, '2 题 · 0 已通过');
  passed = true;
  tree.refresh();
  const after = tree.getChildren()[0];
  assert.equal(after.id, before.id);
  assert.equal(after.description, '2 题 · 1 已通过');
  const group = tree.getChildren(after)[0];
  assert.equal(group.description, '1 题 · 1 已通过');
  assert.equal(tree.getChildren(group)[0].id, `lesson:${first.id}`);
});
