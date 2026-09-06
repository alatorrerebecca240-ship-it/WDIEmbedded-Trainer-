// Consumer integration tests: actual Python catalog; package UI uses a fake backend.
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const Module = require('node:module');
const { test } = require('node:test');
const root = path.resolve(__dirname, '../../..');
const uri = (fsPath) => ({ fsPath });
let settings = {};
let notices = [];
const vscode = {
  Uri: { file: uri },
  ConfigurationTarget: { Global: 1 },
  workspace: { getConfiguration: () => ({
    get: (name, fallback) => settings[name] ?? fallback,
    update: async (name, value) => { settings[name] = value; }
  }) },
  window: {
    showInformationMessage: (text) => notices.push(text),
    showWarningMessage: (text) => notices.push(text)
  },
  TreeItem: class {}, ThemeIcon: class {}, ThemeColor: class {}
};
const originalLoad = Module._load;
let TrainerBackend, LessonCatalog, LessonDashboard, PackageManager;
try {
  Module._load = function (name, ...args) { return name === 'vscode' ? vscode : originalLoad.call(this, name, ...args); };
  ({ TrainerBackend } = require('../src/backend'));
  ({ LessonCatalog } = require('../src/catalog'));
  ({ LessonDashboard } = require('../src/dashboard'));
  ({ PackageManager } = require('../src/packages'));
} finally { Module._load = originalLoad; }

test('Python-backed catalog loads separated 198 lessons without terminal or content scanner', async () => {
  settings = {};
  const cache = await fs.mkdtemp(path.join(os.tmpdir(), 'trainer-js-pack-'));
  try {
    const backend = new TrainerBackend(uri(root), { append() {}, appendLine() {} }, {}, { packHome: cache });
    const catalog = new LessonCatalog(uri(root), backend);
    await catalog.reload();
    assert.equal(catalog.lessons.length, 198);
    assert.ok(catalog.lessons.every((q) => q.packId === 'foundation.core'));
    assert.ok(catalog.get('c.pointer.swap-01').statementUri.fsPath.includes('knowledge'));
    const retained = catalog.lessons;
    backend.run = async () => ({ code: 1, output: 'corrupt update' });
    await assert.rejects(catalog.reload(), /corrupt update/);
    assert.equal(catalog.lessons, retained, 'failed refresh must preserve the current UI');
  } finally { await fs.rm(cache, { recursive: true, force: true }); }
});

test('code reading escapes source, hides answers, and debugging has compile controls', () => {
  const lesson = { id: 'fixture.read', title: '代码阅读', track: 'c', language: 'c', difficulty: 'beginner', questionType: 'code-reading', summary: '填写输出', knowledge: ['printf'], hints: ['读代码'], prerequisites: [], packId: 'fixture.pack', packVersion: '1.0.0', needsTrust: true,
    quiz: { prompt: '填写输出整数', code: '<script>alert("x")</script>', blanks: [{ label: '输出', answers: ['secret-answer'] }], explanation: 'secret-explanation' } };
  const dashboard = new LessonDashboard(() => {});
  dashboard.lesson = lesson;
  let html = dashboard.render();
  assert.ok(html.includes('&lt;script&gt;'));
  assert.ok(!html.includes('<script>alert'));
  assert.ok(!html.includes('secret-answer'));
  assert.ok(!html.includes('secret-explanation'));
  assert.ok(html.includes('id="quiz-form"'));
  assert.ok(html.includes("questionType === 'code-reading'"));
  dashboard.lesson = { ...lesson, questionType: 'debugging' };
  html = dashboard.render();
  assert.ok(html.includes('data-command="check"'));
  assert.ok(!html.includes('id="quiz-form"'));
});

function context() {
  const values = {};
  return { subscriptions: [], globalState: { get: (k, fallback) => values[k] ?? fallback, update: async (k, v) => { values[k] = v; } } };
}

test('synced subscriptions install missing packs but do not execute or trust code', async () => {
  const source = 'https://example.github.io/questions/catalog.json';
  settings = { catalogUrls: [source], enabledPackages: [source + '#new.pack'] };
  notices = [];
  const calls = [];
  let refreshed = 0;
  const backend = { output: { appendLine() {} }, run: async (args, options) => {
    calls.push(args);
    assert.equal(options.silent, true);
    return { code: 0, stdout: JSON.stringify(args.includes('--id') ? {} : { installed: [], packages: [{ id: 'new.pack', installed: null }, { id: 'not-subscribed', installed: null }] }) };
  } };
  const manager = new PackageManager(context(), backend, async () => { refreshed++; });
  await manager.update(true);
  assert.deepEqual(calls, [['packs', 'sync', '--catalog', source], ['packs', 'sync', '--catalog', source, '--id', 'new.pack']]);
  assert.equal(refreshed, 1);
  assert.equal(notices.length, 1);
  assert.ok(!manager.busy);
});

test('background network failure keeps cache/UI and stays quiet', async () => {
  settings = { catalogUrls: ['https://example.github.io/catalog.json'] };
  notices = [];
  const logs = [];
  const manager = new PackageManager(context(), { output: { appendLine: (line) => logs.push(line) }, run: async () => ({ code: 1, output: 'offline' }) }, () => { throw new Error('should not refresh'); });
  await manager.update(true);
  assert.equal(notices.length, 0);
  assert.ok(logs[0].includes('offline'));
  assert.equal(manager.busy, false);
});

test('update timer observes opt-out and interval and disposes on deactivation', () => {
  const original = { setTimeout, setInterval, clearTimeout, clearInterval };
  const schedules = [], cleared = [];
  try {
    global.setTimeout = (fn, ms) => { schedules.push({ fn, ms }); return 11; };
    global.setInterval = (fn, ms) => { schedules.push({ fn, ms }); return 12; };
    global.clearTimeout = (id) => cleared.push(id);
    global.clearInterval = (id) => cleared.push(id);
    settings = { autoUpdatePacks: false };
    const ctx = context();
    const manager = new PackageManager(ctx, {}, () => {});
    let updates = 0;
    manager.update = () => { updates++; };
    manager.start();
    schedules[0].fn();
    assert.equal(updates, 0);
    settings.autoUpdatePacks = true;
    schedules[0].fn();
    assert.equal(updates, 1);
    void ctx.globalState.update('packagesLastCheck', Date.now());
    schedules[1].fn();
    assert.equal(updates, 1);
    assert.deepEqual(schedules.map((s) => s.ms), [10000, 3600000]);
    ctx.subscriptions[0].dispose();
    assert.deepEqual(cleared, [11, 12]);
  } finally { Object.assign(global, original); }
});
