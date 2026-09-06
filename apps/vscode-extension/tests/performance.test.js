const assert = require('node:assert/strict');
const { test } = require('node:test');
const Module = require('node:module');
const path = require('node:path');
const { setTimeout: pause } = require('node:timers/promises');

const uri = (fsPath) => ({ fsPath });
const item = { id: 'fixture.swap', title: 'Swap', questionType: 'programming', language: 'c',
  manifestPath: '/project/questions.json', lessonDir: '/project/lesson', statement: 'README.md' };
let progress = {}, readError, started = false, dashboard, testing;
const calls = [], watchers = [], commands = new Map();
const vscode = {
  Uri: { file: uri, joinPath: (base, ...parts) => uri(path.join(base.fsPath, ...parts)) },
  FileType: { File: 1 }, StatusBarAlignment: { Left: 1 }, ProgressLocation: { Notification: 1 },
  RelativePattern: class { constructor(base, pattern) { this.base = base; this.pattern = pattern; } },
  commands: { registerCommand(name, fn) { commands.set(name, fn); return { dispose() {} }; }, async executeCommand() {} },
  languages: { createDiagnosticCollection: () => ({ clear() {}, dispose() {} }) },
  window: {
    createOutputChannel: () => ({ appendLine() {}, dispose() {} }),
    createTreeView: () => ({ dispose() {} }), createStatusBarItem: () => ({ show() {}, dispose() {} }),
    withProgress: (_, fn) => fn({}, {}), async showTextDocument() {},
    async showInformationMessage() {}, async showWarningMessage() {},
    showErrorMessage: (error) => assert.fail(error), async showQuickPick() {},
  },
  workspace: {
    workspaceFolders: [{ uri: uri('/project') }],
    fs: {
      async createDirectory() {},
      async stat(value) { if (value.fsPath.includes('exercises') && !started) throw new Error('missing'); return {}; },
      async readDirectory() { return [['swap.c', 1]]; },
      async readFile() { if (readError) throw readError; return Buffer.from(JSON.stringify(progress)); },
    },
    async openTextDocument() { return {}; }, async saveAll() {},
    createFileSystemWatcher(pattern) {
      const watcher = { pattern, onDidCreate(fn) { this.create = fn; }, onDidChange(fn) { this.change = fn; },
        onDidDelete(fn) { this.remove = fn; }, dispose() {} };
      watchers.push(watcher); return watcher;
    },
  },
};
class Backend {
  constructor() { this.output = { appendLine() {} }; }
  async run(args) {
    calls.push(args[0]);
    if (args[0] === 'catalog') return { code: 0, stdout: JSON.stringify({ lessons: [item], progress }) };
    if (args[0] === 'start') started = true;
    progress = { [item.id]: { status: args[0] === 'start' ? 'in-progress' : 'passed', attempts: 1 } };
    return { code: 0, output: 'OK', duration: 1 };
  }
}
class Dashboard {
  constructor(fn) { this.onMessage = fn; dashboard = this; }
  show(lesson) { this.lesson = lesson; }
  update() {}
}
class Testing {
  constructor(_, execute) { this.execute = execute; this.syncs = 0; testing = this; }
  sync() { this.syncs++; }
  runLesson(id, token) { return this.execute(id, token); }
}
const originalLoad = Module._load;
let activate, LessonCatalog;
try {
  Module._load = function(name, ...args) {
    if (name === 'vscode') return vscode;
    if (name === './src/backend') return { TrainerBackend: Backend };
    if (name === './src/tree') return { LessonTreeProvider: class { refresh() {} }, STATUS_NAMES: {}, QUESTION_TYPE_NAMES: {}, LANGUAGE_NAMES: {} };
    if (name === './src/dashboard') return { LessonDashboard: Dashboard };
    if (name === './src/testing') return { TestingIntegration: Testing };
    if (name === './src/packages') return { PackageManager: class { start() {} } };
    if (name === './src/authoring') return { AuthoringManager: class { start() {} } };
    return originalLoad.call(this, name, ...args);
  };
  ({ activate } = require('../extension'));
  ({ LessonCatalog } = require('../src/catalog'));
} finally { Module._load = originalLoad; }

test('progress reads need no Python, unchanged data is a no-op, errors preserve state', async () => {
  const catalog = new LessonCatalog(uri('/project'), { run: () => assert.fail('must not launch Python') });
  progress = { first: { status: 'passed' } };
  assert.equal(await catalog.reloadProgress(), true);
  assert.equal(await catalog.reloadProgress(), false);
  readError = new SyntaxError('invalid JSON');
  await assert.rejects(catalog.reloadProgress(), /invalid JSON/);
  assert.equal(catalog.progress.first.status, 'passed');
  readError = { code: 'ENOENT' };
  assert.equal(await catalog.reloadProgress(), true);
  assert.deepEqual(catalog.progress, {});
  readError = undefined; progress = {};
});

test('start/check/submit and progress watchers never reload the entire catalog', async () => {
  const context = {
    extensionUri: uri('/extension'), globalStorageUri: uri('/storage'), subscriptions: [],
    extension: { packageJSON: { version: 'fixture' } },
    globalState: { get: () => 'fixture', async update() {} },
  };
  try {
    await activate(context);
    assert.deepEqual(calls.splice(0), ['catalog']);
    assert.equal(testing.syncs, 1);
    await commands.get('embeddedTrainer.start')(item.id);
    assert.deepEqual(calls.splice(0), ['start']);
    await commands.get('embeddedTrainer.start')(item.id);
    assert.deepEqual(calls.splice(0), [], 'opening existing exercise needs no Python');
    await commands.get('embeddedTrainer.check')(item.id);
    assert.deepEqual(calls.splice(0), ['check']);
    await dashboard.onMessage({ command: 'submit', answer: true }, { id: item.id });
    assert.deepEqual(calls.splice(0), ['submit']);
    const watcher = watchers.find((w) => w.pattern.pattern === '.trainer/progress.json');
    progress = { [item.id]: { status: 'passed', attempts: 3 } };
    for (let i = 0; i < 10; i++) watcher.change();
    await pause(220);
    assert.deepEqual(calls.splice(0), []);
    assert.equal(testing.syncs, 1, 'progress must not rebuild VS Code test items');
    const source = watchers.find((w) => w.pattern.pattern === 'knowledge/packs/**/*');
    for (let i = 0; i < 10; i++) source.change();
    await pause(220);
    assert.deepEqual(calls.splice(0), ['catalog']);
    assert.equal(testing.syncs, 2);
  } finally {
    for (const disposable of context.subscriptions) disposable.dispose?.();
  }
});
