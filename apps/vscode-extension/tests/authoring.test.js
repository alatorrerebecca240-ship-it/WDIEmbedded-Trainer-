const assert = require('node:assert/strict');
const path = require('node:path');
const Module = require('node:module');
const { test, beforeEach } = require('node:test');
let picks, calls, opened, notices, token, failStat;
const vscode = {
  Uri: { file: (fsPath) => ({ fsPath }), parse: (value) => value },
  ProgressLocation: { Notification: 1 }, FileType: { Directory: 2 },
  workspace: {
    workspaceFolders: [{}],
    fs: { stat: async () => { if (failStat) throw new Error('missing'); }, readDirectory: async () => [['draft.pack', 2]] },
    openTextDocument: async (uri) => { opened.push(uri.fsPath); return uri; }
  },
  window: {
    withProgress: async (_, fn) => fn({}, token),
    showQuickPick: async (items, options) => { const choose = picks.shift(); return choose ? choose(items, options) : undefined; },
    showInputBox: async ({ validateInput }) => { assert.equal(validateInput('../bad'), '使用小写字母、数字、点和连字符；不要使用 Windows 保留名称。'); return 'draft.pack'; },
    showWarningMessage: async () => '导入草稿',
    showInformationMessage: (s) => { notices.push(s); }, showErrorMessage: (s) => { notices.push(s); },
    showTextDocument: async () => {}
  },
  commands: { executeCommand: async () => {} }, env: { openExternal: async () => {} }
};
const original = Module._load;
let AuthoringManager;
try {
  Module._load = function (name, ...args) { return name === 'vscode' ? vscode : original.call(this, name, ...args); };
  ({ AuthoringManager } = require('../src/authoring'));
} finally { Module._load = original; }

beforeEach(() => {
  picks = []; calls = []; opened = []; notices = []; token = { isCancellationRequested: false }; failStat = false;
  vscode.workspace.workspaceFolders = [{}];
});

function manager(result = { questions: 1 }) {
  return new AuthoringManager({ extensionUri: { fsPath: '/extension' } }, {
    rootUri: { fsPath: '/workspace' }, run: async (args) => { calls.push(args); return { code: 0, stdout: JSON.stringify(result) }; }
  });
}
const q = { key: 'c/leap', title: '闰年', language: 'c', difficulty: 'beginner', topics: ['条件'], commit: 'a'.repeat(40),
  license: 'MIT', frameworkLicense: 'MIT', recommended: true, supported: true };
const catalog = { candidates: [q, { ...q, key: 'c/advanced', recommended: false }], count: 2, recommendedCount: 1 };

test('native pilot selection imports drafts with packaged license, no terminal/trust/publish', async () => {
  picks = [(items) => items[0], (items, options) => {
    assert.equal(items.length, 1); assert.equal(options.canPickMany, true); assert.equal(items[0].picked, true); return items;
  }];
  await manager().chooseAndImport(catalog);
  assert.equal(calls.length, 1);
  assert.deepEqual(calls[0].slice(0, 2), ['packs', 'exercism-import']);
  assert.ok(calls[0].includes(path.join('/extension', 'LICENSE.txt')));
  assert.ok(calls[0].includes('c/leap'));
  assert.ok(opened[0].endsWith('import-manifest.json'));
  for (const bad of ['native', 'approve', 'build', 'trust', 'terminal', 'publish']) assert.ok(!calls[0].includes(bad));
});

test('development license fallback and cancellation before selection are harmless', async () => {
  failStat = true;
  picks = [(items) => items[0], (items) => items];
  await manager().chooseAndImport(catalog);
  assert.ok(calls[0].includes(path.join('/extension', 'LICENSE')));
  calls = [];
  await manager().chooseAndImport(catalog);
  assert.equal(calls.length, 0);
});

test('more than 50 questions never starts backend import', async () => {
  picks = [(items) => items[0], (items) => Array(51).fill(items[0])];
  await assert.rejects(manager().chooseAndImport(catalog), /最多 50/);
  assert.equal(calls.length, 0);
});

test('static report always uses runner none and opens audit rather than approves', async () => {
  picks = [(items) => items[0]];
  const m = manager();
  m.backend.run = async (args) => { calls.push(args); return { code: 1 }; };
  await m.report();
  assert.ok(calls[0].includes('--runner'));
  assert.equal(calls[0][calls[0].indexOf('--runner') + 1], 'none');
  assert.ok(opened[0].endsWith('.audit.json'));
  assert.ok(notices[0].includes('不能据此批准发布'));
});

test('cancelled scan cannot continue to cached import', async () => {
  token.isCancellationRequested = true;
  picks = [(items) => items[0]];
  await assert.rejects(manager().scan(), /已取消/);
  assert.equal(calls.length, 1);
});

test('manager requires workspace, serializes operations and resets on failure', async () => {
  const m = manager();
  vscode.workspace.workspaceFolders = [];
  await m.manage();
  assert.equal(calls.length, 0);
  vscode.workspace.workspaceFolders = [{}];
  picks = [() => ({ run: async () => { throw new Error('fixture failure'); } })];
  await m.manage();
  assert.equal(m.busy, false);
  assert.ok(notices.includes('fixture failure'));
  m.busy = true;
  await m.manage();
  assert.ok(notices.at(-1).includes('正在进行'));
});
